"""State-machine App: consume ButtonEvents, mutate State.

Pure logic, no timing, no rendering, no hardware. The platform-specific
busy loop and host simulator own the event source and the render call;
this module just decides what each event does to State.

Screens
-------
``state.screen`` determines which handler processes each event:

- ``"setup_cipher"`` — boot cipher selection; B/PWR scroll, A confirms.
- ``"setup_key"``    — keyword entry; same wheel gestures, A_LONG confirms.
- ``"encode"``       — main encode/decode; clean, no setup gestures.
- ``"about"``        — per-algorithm info pages; B/PWR scroll footer, A selects.

Future cipher delivery (WiFi, resistor) bypasses the setup screens by
setting ``state.algorithm``, ``state.cipher_key``, and
``state.screen = "encode"`` directly.
"""

from encoder.base import Cipher
from ui.events import ButtonEvent
from ui.state import State

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


class App:
    def __init__(
        self,
        state: State,
        ciphers: dict[str, Cipher],
        on_save_key=None,
    ) -> None:
        self.state = state
        self.ciphers = ciphers
        self._on_save_key = on_save_key

    def handle(self, event: ButtonEvent) -> bool:
        s = self.state
        if s.screen == "setup_cipher":
            return self._handle_setup_cipher(event)
        if s.screen == "setup_key":
            return self._handle_setup_key(event)
        if s.screen == "about":
            return self._handle_about(event)
        return self._handle_encode(event)

    # ------------------------------------------------------------------
    # setup_cipher screen: scroll through cipher list, press A to select
    # ------------------------------------------------------------------

    def _handle_setup_cipher(self, event: ButtonEvent) -> bool:
        s = self.state
        order = list(self.ciphers.keys()) + ["about"]
        if event is ButtonEvent.BTN_B_PRESS or event is ButtonEvent.BTN_B_LONG:
            s.setup_idx = (s.setup_idx - 1) % len(order)
            return True
        if event is ButtonEvent.PWR_SHORT:
            s.setup_idx = (s.setup_idx + 1) % len(order)
            return True
        if event is ButtonEvent.BTN_A_PRESS:
            selected = order[s.setup_idx]
            if selected == "about":
                s.about_idx = 0
                s.about_footer_idx = 1
                s.screen = "about"
                return True
            s.algorithm = selected
            cipher = self.ciphers.get(s.algorithm)
            if hasattr(cipher, 'key'):
                # Keyed cipher: enter key-entry screen, pre-fill the saved key
                # for this algorithm (each cipher keeps its own key field).
                s.key_buf = s.caesar_key if s.algorithm == "caesar" else s.cipher_key
                s.screen = "setup_key"
            else:
                s.screen = "encode"
            return True
        return False

    # ------------------------------------------------------------------
    # setup_key screen: wheel selects letters, A_LONG confirms
    # ------------------------------------------------------------------

    def _handle_setup_key(self, event: ButtonEvent) -> bool:
        s = self.state
        if event is ButtonEvent.BTN_A_PRESS:
            cipher = self.ciphers.get(s.algorithm)
            max_len = getattr(cipher, 'max_key_len', None)
            if max_len and len(s.key_buf) >= max_len:
                # At the key-length limit: replace the last char rather than append.
                s.key_buf = s.key_buf[:-1] + ALPHABET[s.wheel_idx]
            else:
                s.key_buf = s.key_buf + ALPHABET[s.wheel_idx]
            return True
        if event is ButtonEvent.BTN_A_DOUBLE:
            if not s.key_buf:
                return False
            s.key_buf = s.key_buf[:-1]
            return True
        if event is ButtonEvent.BTN_A_LONG:
            if s.algorithm == "caesar":
                fallback = s.caesar_key
                new_key = s.key_buf if s.key_buf else fallback
                s.caesar_key = new_key
            else:
                fallback = s.cipher_key
                new_key = s.key_buf if s.key_buf else fallback
                s.cipher_key = new_key
            s.key_buf = ""
            s.screen = "encode"
            cipher = self.ciphers.get(s.algorithm)
            if hasattr(cipher, 'key'):
                cipher.key = new_key  # type: ignore[attr-defined]
            if self._on_save_key is not None:
                self._on_save_key(new_key)
            return True
        if event is ButtonEvent.BTN_B_PRESS or event is ButtonEvent.BTN_B_LONG:
            s.wheel_idx = (s.wheel_idx - 1) % 26
            return True
        if event is ButtonEvent.PWR_SHORT:
            s.wheel_idx = (s.wheel_idx + 1) % 26
            return True
        return False

    # ------------------------------------------------------------------
    # encode screen: clean encode/decode, no setup gestures
    # ------------------------------------------------------------------

    def _handle_encode(self, event: ButtonEvent) -> bool:
        s = self.state
        if event is ButtonEvent.BTN_A_PRESS:
            s.in_buf = s.in_buf + ALPHABET[s.wheel_idx]
            s.out_buf = self._transform(s.in_buf)
            return True
        if event is ButtonEvent.BTN_A_DOUBLE:
            if not s.in_buf:
                return False
            s.in_buf = s.in_buf[:-1]
            s.out_buf = self._transform(s.in_buf)
            return True
        if event is ButtonEvent.BTN_A_LONG:
            # Always toggle ENC↔DEC — no context-sensitivity.
            s.mode = "DEC" if s.mode == "ENC" else "ENC"
            s.in_buf = s.out_buf
            s.out_buf = self._transform(s.in_buf)
            return True
        if event is ButtonEvent.BTN_B_PRESS or event is ButtonEvent.BTN_B_LONG:
            s.wheel_idx = (s.wheel_idx - 1) % 26
            return True
        if event is ButtonEvent.PWR_SHORT:
            s.wheel_idx = (s.wheel_idx + 1) % 26
            return True
        # PWR_DOUBLE and PWR_LONG unhandled: no runtime cipher switching.
        return False

    # ------------------------------------------------------------------
    # about screen: scroll footer with B/PWR, A selects prev/exit/next
    # ------------------------------------------------------------------

    def _handle_about(self, event: ButtonEvent) -> bool:
        s = self.state
        page_count = len(self.ciphers)
        if event is ButtonEvent.PWR_SHORT:
            s.about_footer_idx = (s.about_footer_idx + 1) % 3
            return True
        if event is ButtonEvent.BTN_B_PRESS or event is ButtonEvent.BTN_B_LONG:
            s.about_footer_idx = (s.about_footer_idx - 1) % 3
            return True
        if event is ButtonEvent.BTN_A_PRESS:
            if s.about_footer_idx == 0:       # <-prev
                s.about_idx = (s.about_idx - 1) % page_count
                s.about_footer_idx = 1
            elif s.about_footer_idx == 2:     # next->
                s.about_idx = (s.about_idx + 1) % page_count
                s.about_footer_idx = 1
            else:                             # exit
                s.screen = "setup_cipher"
            return True
        return False

    def _transform(self, text: str) -> str:
        cipher = self.ciphers[self.state.algorithm]
        return cipher.encode(text) if self.state.mode == "ENC" else cipher.decode(text)
