from encoder.base import Cipher
from encoder.caesar import CaesarCipher
from encoder.keyword import KeywordCipher
from encoder.rot13 import Rot13Cipher
from encoder.vigenere import VigenèreCipher

ALGORITHMS: dict[str, type[Cipher]] = {
    "rot13": Rot13Cipher,
    "caesar": CaesarCipher,
    "keyword": KeywordCipher,
    "vigenere": VigenèreCipher,
}

__all__ = ["ALGORITHMS", "CaesarCipher", "Cipher", "KeywordCipher", "Rot13Cipher", "VigenèreCipher"]
