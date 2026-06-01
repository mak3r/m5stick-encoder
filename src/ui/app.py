"""State-machine App: consume ButtonEvents, mutate State.

Pure logic, no timing, no rendering, no hardware. The platform-specific
busy loop and host simulator own the event source and the render call;
this module just decides what each event does to State.
"""

from encoder.base import Cipher
from ui.events import ButtonEvent
from ui.state import State

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_ALGORITHM_ORDER = ["rot13", "keyword"]


class App:
    def __init__(
        self,
        state: State,
        ciphers: dict[str, Cipher],
        on_save_key=None,
    ) -> None:
        self.state = state
        self.ciphers = ciphers
        # Called with the confirmed key string when the user exits key-edit mode.
        self._on_save_key = on_save_key

    def handle(self, event: ButtonEvent) -> bool:
        s = self.state

        if s.editing_key:
            return self._handle_key_edit(event)

        if event is ButtonEvent.BTN_A_PRESS:
            letter = ALPHABET[s.wheel_idx]
            s.in_buf = s.in_buf + letter
            s.out_buf = self._transform(s.in_buf)
            return True
        if event is ButtonEvent.BTN_A_DOUBLE:
            if not s.in_buf:
                return False
            s.in_buf = s.in_buf[:-1]
            s.out_buf = self._transform(s.in_buf)
            return True
        if event is ButtonEvent.BTN_A_LONG:
            s.mode = "DEC" if s.mode == "ENC" else "ENC"
            # Swap-and-re-derive: previous output becomes new input, then
            # recompute under the new mode. Demonstrates encode/decode are
            # inverse operations rather than discarding the kid's work.
            s.in_buf = s.out_buf
            s.out_buf = self._transform(s.in_buf)
            return True
        if event is ButtonEvent.BTN_B_PRESS:
            s.wheel_idx = (s.wheel_idx - 1) % 26
            return True
        if event is ButtonEvent.BTN_B_LONG:
            s.wheel_idx = (s.wheel_idx - 1) % 26
            return True
        if event is ButtonEvent.PWR_SHORT:
            s.wheel_idx = (s.wheel_idx + 1) % 26
            return True
        if event is ButtonEvent.PWR_DOUBLE:
            self._cycle_algorithm()
            return True
        if event is ButtonEvent.PWR_LONG:
            if s.algorithm == "keyword":
                s.key_buf = s.cipher_key
                s.editing_key = True
                return True
            return False
        return False

    def _handle_key_edit(self, event: ButtonEvent) -> bool:
        s = self.state
        if event is ButtonEvent.BTN_A_PRESS:
            letter = ALPHABET[s.wheel_idx]
            s.key_buf = s.key_buf + letter
            return True
        if event is ButtonEvent.BTN_A_DOUBLE:
            if not s.key_buf:
                return False
            s.key_buf = s.key_buf[:-1]
            return True
        if event is ButtonEvent.BTN_A_LONG:
            # Confirm: commit key_buf (fall back to old key if empty).
            new_key = s.key_buf if s.key_buf else s.cipher_key
            s.cipher_key = new_key
            s.key_buf = ""
            s.editing_key = False
            # Update the live cipher instance if present.
            kw = self.ciphers.get("keyword")
            if kw is not None:
                kw.key = new_key  # type: ignore[attr-defined]
            # Recompute encode/decode buffers with the new key.
            s.out_buf = self._transform(s.in_buf)
            if self._on_save_key is not None:
                self._on_save_key(new_key)
            return True
        if event is ButtonEvent.PWR_LONG:
            # Cancel: discard key_buf, exit edit mode.
            s.key_buf = ""
            s.editing_key = False
            return True
        if event is ButtonEvent.BTN_B_PRESS:
            s.wheel_idx = (s.wheel_idx - 1) % 26
            return True
        if event is ButtonEvent.BTN_B_LONG:
            s.wheel_idx = (s.wheel_idx - 1) % 26
            return True
        if event is ButtonEvent.PWR_SHORT:
            s.wheel_idx = (s.wheel_idx + 1) % 26
            return True
        return False

    def _cycle_algorithm(self) -> None:
        s = self.state
        order = _ALGORITHM_ORDER
        # Fall back gracefully if current algorithm is not in the cycle list.
        try:
            idx = order.index(s.algorithm)
        except ValueError:
            idx = -1
        s.algorithm = order[(idx + 1) % len(order)]
        s.in_buf = ""
        s.out_buf = ""

    def _transform(self, text: str) -> str:
        # Full-recompute: derive out_buf from the entire in_buf every time.
        # Safer than incremental append for future stateful ciphers, and
        # keeps backspace trivially correct.
        cipher = self.ciphers[self.state.algorithm]
        return cipher.encode(text) if self.state.mode == "ENC" else cipher.decode(text)
