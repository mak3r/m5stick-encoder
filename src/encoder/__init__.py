from encoder.base import Cipher
from encoder.keyword import KeywordCipher
from encoder.rot13 import Rot13Cipher

ALGORITHMS: dict[str, type[Cipher]] = {
    "rot13": Rot13Cipher,
    "keyword": KeywordCipher,
}

__all__ = ["ALGORITHMS", "Cipher", "KeywordCipher", "Rot13Cipher"]
