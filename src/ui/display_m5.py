"""Concrete ``Display`` implementation using the UIFlow 2 ``M5.Lcd`` API.

MicroPython-only — excluded from host lint via ``pyproject.toml``.

Targets M5StickC PLUS running UIFlow 2.4.5+.  The ST7789 SPI driver is no
longer exposed; the board init configures the panel and exposes it via
``M5.Lcd``.

Logical dimensions: width=240, height=135 (landscape).

Color convention (matches ``screen.py``):
  0 = background (black)   → 0x0000
  1 = foreground (white)   → 0xFFFF
  2 = accent (amber)       → 0xFB00
"""

import M5

_PALETTE = {0: 0x0000, 1: 0xFFFF, 2: 0xFB00}


class M5Display:
    """``Display`` Protocol implementation backed by ``M5.Lcd``."""

    width: int = 240
    height: int = 135

    def __init__(self) -> None:
        M5.begin()

    def fill(self, color: int) -> None:
        M5.Lcd.fillScreen(_PALETTE.get(color, 0x0000))

    def text(self, s: str, x: int, y: int, color: int, scale: int = 1) -> None:
        fg = _PALETTE.get(color, 0xFFFF)
        bg = _PALETTE.get(0, 0x0000)
        M5.Lcd.setTextSize(scale)
        M5.Lcd.setTextColor(fg, bg)
        M5.Lcd.drawString(s, x, y)

    def rect(self, x: int, y: int, w: int, h: int, color: int, fill: bool = False) -> None:
        c = _PALETTE.get(color, 0xFFFF)
        if fill:
            M5.Lcd.fillRect(x, y, w, h, c)
        else:
            M5.Lcd.drawRect(x, y, w, h, c)

    def show(self) -> None:
        # M5.Lcd writes through to the panel immediately; no explicit flush needed.
        pass
