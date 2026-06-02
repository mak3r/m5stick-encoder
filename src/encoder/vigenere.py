"""Vigenère cipher restricted to the A-Z uppercase alphabet.

Each letter of the key shifts the corresponding plaintext letter forward
(encode) or backward (decode) in the alphabet. The key cycles to cover
longer messages. ``encode`` and ``decode`` are inverse operations, unlike
rot13.

Character-set contract matches Rot13Cipher: only A-Z uppercase; anything
else raises ``ValueError``.
"""

_A = ord("A")
_DEFAULT_KEY = "KEY"


class VigenèreCipher:
    name = "vigenere"

    def __init__(self, key: str = _DEFAULT_KEY) -> None:
        self._key = key.upper() if key else _DEFAULT_KEY

    @property
    def key(self) -> str:
        return self._key

    @key.setter
    def key(self, value: str) -> None:
        self._key = value.upper() if value else _DEFAULT_KEY

    def encode(self, text: str) -> str:
        return self._vigenere(text, encrypt=True)

    def decode(self, text: str) -> str:
        return self._vigenere(text, encrypt=False)

    def _vigenere(self, text: str, encrypt: bool) -> str:
        key = self._key
        result = []
        for ki, ch in enumerate(text):
            code = ord(ch)
            if code < _A or code > _A + 25:
                raise ValueError(f"vigenere cipher only supports A-Z, got {ch!r}")
            shift = ord(key[ki % len(key)]) - _A
            if encrypt:
                result.append(chr(_A + (code - _A + shift) % 26))
            else:
                result.append(chr(_A + (code - _A - shift) % 26))
        return "".join(result)
