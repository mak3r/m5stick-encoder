"""Concrete ``Display`` implementation for the M5StickC PLUS ST7789V2 panel.

MicroPython-only — excluded from host lint via ``pyproject.toml``.

Panel is 135 wide × 240 tall in portrait, wired landscape so the logical
dimensions exposed here are width=240, height=135.  Column offset 40 and
row offset 53 correct the panel's internal addressing so the image fills
the glass without a black bar on the left edge.

Color convention (matches ``screen.py``):
  0 = background (black)
  1 = foreground (white)
  2 = accent (amber, ~#ffb000)

Text rendering uses ``framebuf.FrameBuffer`` at 8×8 per glyph in MONO_HLSB
mode.  The ``scale`` argument to ``text()`` repeats each pixel as an
``scale×scale`` filled rectangle, giving 2× and 3× glyphs without an
external large-font module.
"""

import framebuf
import machine
import st7789

# Hardware SPI pins on M5StickC PLUS (VSPI bus)
_PIN_MOSI = 15
_PIN_CLK = 13
_PIN_DC = 23
_PIN_CS = 5
_PIN_RST = 18
_SPI_BAUD = 20_000_000

# Panel geometry — portrait physical, landscape logical.
_PHYS_W = 135
_PHYS_H = 240
_COL_OFFSET = 40
_ROW_OFFSET = 53

# RGB-565 colour values for the three abstract colour indices.
# Calculation: ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
# black  (0,   0,   0)  → 0x0000
# white  (255, 255, 255) → 0xffff
# amber  (255, 176,   0) → 0xfb00  (r=31 g=22 b=0 → 31<<11 | 22<<5 | 0)
_PALETTE = {0: 0x0000, 1: 0xFFFF, 2: 0xFB00}

# Glyph cell size for the 8×8 MicroPython built-in font.
_GLYPH_W = 8
_GLYPH_H = 8

# Temporary 1-bit framebuffer large enough for a single line of up to 30
# glyphs (240px / 8px × 8px rows).  Allocated once and reused to avoid
# heap pressure on the ESP32.
_FBUF_COLS = 30
_FBUF_ROWS = 1
_fbuf_bytes = bytearray(_GLYPH_W * _FBUF_COLS * _GLYPH_H // 8)
_fbuf = framebuf.FrameBuffer(
    _fbuf_bytes, _GLYPH_W * _FBUF_COLS, _GLYPH_H, framebuf.MONO_HLSB
)


def _rgb565_swap(c: int) -> int:
    """Byte-swap a 16-bit colour for big-endian SPI transfer."""
    return ((c & 0xFF) << 8) | (c >> 8)


class M5Display:
    """``Display`` Protocol implementation for the M5StickC PLUS panel."""

    width: int = 240
    height: int = 135

    def __init__(self) -> None:
        spi = machine.SPI(
            1,
            baudrate=_SPI_BAUD,
            polarity=0,
            phase=0,
            sck=machine.Pin(_PIN_CLK),
            mosi=machine.Pin(_PIN_MOSI),
        )
        self._d = st7789.ST7789(
            spi,
            _PHYS_W,
            _PHYS_H,
            reset=machine.Pin(_PIN_RST, machine.Pin.OUT),
            dc=machine.Pin(_PIN_DC, machine.Pin.OUT),
            cs=machine.Pin(_PIN_CS, machine.Pin.OUT),
            # rotation=1 → 90° clockwise, producing 240-wide landscape output
            rotation=1,
            color_order=st7789.BGR,
        )
        self._d.offset(x=_COL_OFFSET, y=_ROW_OFFSET)
        self._d.fill(0x0000)

    def fill(self, color: int) -> None:
        self._d.fill(_PALETTE.get(color, 0x0000))

    def text(self, s: str, x: int, y: int, color: int, scale: int = 1) -> None:
        fg = _PALETTE.get(color, 0xFFFF)
        bg = _PALETTE.get(0, 0x0000)
        if scale == 1:
            # Fast path: native driver text at 1:1.
            self._d.text(s, x, y, fg, bg)
            return
        # Pixel-doubling/tripling: render into the 1-bit framebuffer then
        # paint each set pixel as a ``scale×scale`` filled rectangle.
        n = len(s)
        if n > _FBUF_COLS:
            s = s[:_FBUF_COLS]
            n = _FBUF_COLS
        fbuf_w = n * _GLYPH_W
        _fbuf.fill(0)
        _fbuf.text(s, 0, 0, 1)
        for row in range(_GLYPH_H):
            for col in range(fbuf_w):
                if _fbuf.pixel(col, row):
                    self._d.fill_rect(
                        x + col * scale,
                        y + row * scale,
                        scale,
                        scale,
                        fg,
                    )

    def rect(self, x: int, y: int, w: int, h: int, color: int, fill: bool = False) -> None:
        c = _PALETTE.get(color, 0xFFFF)
        if fill:
            self._d.fill_rect(x, y, w, h, c)
        else:
            self._d.rect(x, y, w, h, c)

    def show(self) -> None:
        # ST7789 writes through to the panel immediately; no explicit flush.
        pass
