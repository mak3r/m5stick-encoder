"""Phase 1 state-machine App: consume ButtonEvents, mutate State.

Pure logic, no timing, no rendering, no hardware. The platform-specific
busy loop (#10) and host simulator (#18) own the event source and the
render call; this module just decides what each event does to State.
"""

from encoder.base import Cipher
from ui.events import ButtonEvent
from ui.state import State

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


class App:
    def __init__(self, state: State, ciphers: dict[str, Cipher]) -> None:
        self.state = state
        self.ciphers = ciphers

    def handle(self, event: ButtonEvent) -> bool:
        s = self.state
        if event is ButtonEvent.BTN_A_PRESS:
            letter = ALPHABET[s.wheel_idx]
            s.in_buf = s.in_buf + letter
            s.out_buf = self._transform(s.in_buf)
            return True
        if event is ButtonEvent.BTN_B_PRESS:
            s.wheel_idx = (s.wheel_idx + 1) % 26
            return True
        if event is ButtonEvent.PWR_SHORT:
            s.wheel_idx = (s.wheel_idx - 1) % 26
            return True
        if event is ButtonEvent.PWR_DOUBLE:
            if not s.in_buf:
                return False
            s.in_buf = s.in_buf[:-1]
            s.out_buf = self._transform(s.in_buf)
            return True
        if event is ButtonEvent.PWR_LONG:
            s.mode = "DEC" if s.mode == "ENC" else "ENC"
            # Swap-and-re-derive: previous output becomes new input, then
            # recompute under the new mode. Demonstrates encode/decode are
            # inverse operations rather than discarding the kid's work.
            s.in_buf = s.out_buf
            s.out_buf = self._transform(s.in_buf)
            return True
        return False

    def _transform(self, text: str) -> str:
        # Full-recompute: derive out_buf from the entire in_buf every time.
        # Safer than incremental append for future stateful ciphers, and
        # keeps backspace trivially correct.
        cipher = self.ciphers[self.state.algorithm]
        return cipher.encode(text) if self.state.mode == "ENC" else cipher.decode(text)
