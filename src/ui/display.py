"""Abstract Display protocol used by ``screen.render``.

Concrete implementations: ``display_mock.DisplayMock`` for host tests,
``display_m5.M5Display`` (Phase 1 issue #7) for the real ST7789V2 panel.

Font/scale convention
---------------------
Glyphs are drawn from an 8x8 base font. ``scale`` multiplies the cell
size in both axes:

- ``scale=1`` → 8x8 per glyph (default body text, the cipher wheel)
- ``scale=2`` → 16x16 per glyph
- ``scale=3`` → 24x24 per glyph (center scroll-wheel letter, no smooth font)

When a smooth font is loaded via ``load_font()``, pass ``scale=1`` —
the .vlw file encodes the size natively and setTextSize would scale it
again. Call ``text_width(s)`` after loading to measure character advance
(returns the sum of per-glyph xAdvance values).

Callers compute pixel positions assuming this convention; concrete
displays must honor it so layouts produced against the mock match what
appears on hardware.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class Display(Protocol):
    width: int
    height: int

    def fill(self, color: int) -> None: ...

    def text(  # noqa: PLR0913
        self, s: str, x: int, y: int, color: int, scale: int = 1, center_x: bool = False
    ) -> None: ...

    def load_font(self, name: str) -> None: ...
    def unload_font(self) -> None: ...
    def text_width(self, s: str) -> int: ...

    def rect(self, x: int, y: int, w: int, h: int, color: int, fill: bool = False) -> None: ...

    def show(self) -> None: ...

    def sleep(self) -> None: ...

    def wake(self) -> None: ...
