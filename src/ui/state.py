from dataclasses import dataclass
from typing import Literal


@dataclass
class State:
    """UI state. Mutated in place by ``App.handle()``.

    - ``screen``: active screen — "setup_cipher" | "setup_key" | "encode" | "about".
    - ``setup_idx``: cursor position in the cipher-selection list.
    - ``about_idx``: algorithm page shown in the about screen (0=rot13..3=vigenere).
    - ``about_footer_idx``: footer cursor in the about screen (0=<-prev 1=exit 2=next->).
    - ``mode``: ENC encodes plain→cipher; DEC decodes cipher→plain.
    - ``algorithm``: key into ``encoder.ALGORITHMS``.
    - ``wheel_idx``: 0..25, indexes into ``A``..``Z`` for the current
      focused source letter on the cipher wheel.
    - ``in_buf`` / ``out_buf``: source and result strings; ``screen.render``
      shows only the trailing 16 chars when they grow past the line width.
    - ``cipher_key``: active keyword for keyed ciphers.
    - ``key_buf``: key being assembled during setup_key screen.
    """

    screen: str = "encode"
    setup_idx: int = 0
    about_idx: int = 0
    about_footer_idx: int = 1
    mode: Literal["ENC", "DEC"] = "ENC"
    algorithm: str = "rot13"
    wheel_idx: int = 0
    in_buf: str = ""
    out_buf: str = ""
    battery_pct: str = "?"
    cipher_key: str = "KEY"
    caesar_key: str = "D"
    key_buf: str = ""
