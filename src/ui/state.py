from dataclasses import dataclass
from typing import Literal


@dataclass
class State:
    """Phase 1 UI state. Mutated in place by ``App.handle()`` (issue #8).

    - ``mode``: ENC encodes plain→cipher; DEC decodes cipher→plain.
    - ``algorithm``: key into ``encoder.ALGORITHMS``.
    - ``wheel_idx``: 0..25, indexes into ``A``..``Z`` for the current
      focused source letter on the cipher wheel.
    - ``in_buf`` / ``out_buf``: source and result strings; ``screen.render``
      shows only the trailing 16 chars when they grow past the line width.
    """

    mode: Literal["ENC", "DEC"] = "ENC"
    algorithm: str = "rot13"
    wheel_idx: int = 0
    in_buf: str = ""
    out_buf: str = ""
    battery_pct: str = "?"
