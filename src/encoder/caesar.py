"""Caesar cipher — a single-letter-key shift cipher restricted to A-Z uppercase.

The key letter maps to a shift: A=0, B=1, … Z=25.  Traditional default is
'D' (shift 3).  Unlike the Vigenère/keyword cipher, the same shift applies to
every position in the message, making this a monoalphabetic cipher.

``encode`` and ``decode`` are inverse operations (unlike rot13 which is
self-inverse).  Character-set contract matches Rot13Cipher and KeywordCipher:
only A-Z uppercase; anything else raises ``ValueError``.
"""

_A = ord("A")
_DEFAULT_KEY = "D"


class CaesarCipher:
    name = "caesar"
    max_key_len = 1   # setup_key screen replaces rather than appends at this limit

    def __init__(self, key: str = _DEFAULT_KEY) -> None:
        self._key = key[0].upper() if key else _DEFAULT_KEY

    @property
    def key(self) -> str:
        return self._key

    @key.setter
    def key(self, value: str) -> None:
        self._key = value[0].upper() if value else _DEFAULT_KEY

    def encode(self, text: str) -> str:
        shift = ord(self._key) - _A
        return self._shift(text, shift)

    def decode(self, text: str) -> str:
        shift = ord(self._key) - _A
        return self._shift(text, -shift)

    def _shift(self, text: str, shift: int) -> str:
        result = []
        for ch in text:
            code = ord(ch)
            if code < _A or code > _A + 25:
                raise ValueError(f"caesar cipher only supports A-Z, got {ch!r}")
            result.append(chr(_A + (code - _A + shift) % 26))
        return "".join(result)
