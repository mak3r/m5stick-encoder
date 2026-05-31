from __future__ import annotations

from encoder.base import Cipher
from encoder.rot13 import Rot13Cipher

ALGORITHMS: dict[str, type[Cipher]] = {
    "rot13": Rot13Cipher,
}

__all__ = ["ALGORITHMS", "Cipher", "Rot13Cipher"]
