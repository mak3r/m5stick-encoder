"""rot13 cipher restricted to the A-Z uppercase alphabet.

Phase 1 scope: only the 26 uppercase letters are valid input. Lowercase
letters, digits, whitespace, and punctuation are out of scope (Phase 4)
and raise ``ValueError`` rather than silently passing through.
"""


class Rot13Cipher:
    """rot13 over A-Z. ``encode`` and ``decode`` are identical (self-inverse).

    Any character outside ``A``-``Z`` raises ``ValueError``. This is
    deliberate for Phase 1; broader character support arrives in Phase 4.
    """

    name = "rot13"

    _A = ord("A")
    _Z = ord("Z")

    def encode(self, text: str) -> str:
        result = []
        for ch in text:
            code = ord(ch)
            if code < self._A or code > self._Z:
                raise ValueError(f"rot13 only supports A-Z, got {ch!r}")
            result.append(chr(self._A + (code - self._A + 13) % 26))
        return "".join(result)

    def decode(self, text: str) -> str:
        return self.encode(text)
