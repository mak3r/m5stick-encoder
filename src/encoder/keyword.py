"""Keyword substitution cipher restricted to the A-Z uppercase alphabet.

The keyword is deduplicated (preserving order) and placed at the front of
the cipher alphabet; the remaining letters follow in alphabetical order.

Example — key "ZEBRA":
  cipher alphabet: ZEBRACDFGHIJKLMNOPQSTUVWXY
  A→Z, B→E, C→B, D→R, E→A, …

Example — key "HELLO" (duplicate L collapsed):
  deduped: HELO
  cipher alphabet: HELOABCDFGIJKMNPQRSTUVWXYZ

This is a monoalphabetic cipher: the mapping never changes as the user types.
Character-set contract matches Rot13Cipher: only A-Z uppercase; anything
else raises ``ValueError``.
"""

_PLAIN = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_DEFAULT_KEY = "KEY"


class KeywordCipher:
    name = "keyword"

    def __init__(self, key: str = _DEFAULT_KEY) -> None:
        self._key = key.upper() if key else _DEFAULT_KEY
        self._cipher = self._build(self._key)

    @property
    def key(self) -> str:
        return self._key

    @key.setter
    def key(self, value: str) -> None:
        self._key = value.upper() if value else _DEFAULT_KEY
        self._cipher = self._build(self._key)

    @staticmethod
    def _build(key: str) -> str:
        seen: set = set()
        out = []
        for ch in key:
            if ch not in seen:
                seen.add(ch)
                out.append(ch)
        for ch in _PLAIN:
            if ch not in seen:
                out.append(ch)
        return "".join(out)

    def encode(self, text: str) -> str:
        return self._sub(text, _PLAIN, self._cipher)

    def decode(self, text: str) -> str:
        return self._sub(text, self._cipher, _PLAIN)

    def _sub(self, text: str, src: str, dst: str) -> str:
        out = []
        for ch in text:
            idx = src.find(ch)
            if idx < 0:
                raise ValueError(f"keyword cipher only supports A-Z, got {ch!r}")
            out.append(dst[idx])
        return "".join(out)
