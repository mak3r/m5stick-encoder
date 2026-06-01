"""Concrete ``Display`` implementation using the UIFlow 2 ``M5.Lcd`` API.

MicroPython-only — excluded from host lint via ``pyproject.toml``.

Targets M5StickC PLUS running UIFlow 2.4.5+.  The ST7789 SPI driver is no
longer exposed; the board init configures the panel and exposes it via
``M5.Lcd``.

Logical dimensions: width=240, height=135 (landscape).

Color convention (matches ``screen.py``):
  0 = background (black)   → 0x000000
  1 = foreground (white)   → 0xFFFFFF
  2 = accent (amber)       → 0xFFB000
  3 = cursor (bright green) → 0x00FF00

UIFlow 2 M5.Lcd accepts 24-bit RGB888 color integers (0xRRGGBB), not
16-bit RGB565.  The previous RGB565 value 0x07E0 was interpreted as
RGB888 (R=0, G=7, B=224) which rendered blue on device.
"""

import M5

_PALETTE = {0: 0x000000, 1: 0xFFFFFF, 2: 0xFFB000, 3: 0x00FF00}

# UIFlow 2.4.5 on the M5StickC PLUS (ESP32-PICO-D4) emits:
#   E (...) gpio: gpio_pullup_en(78): GPIO number error
# twice during M5.begin().  GPIO 78 is valid on ESP32-S3 (Plus 2) but not on
# the original PICO-D4 (max GPIO 39).  This is an upstream UIFlow firmware bug;
# see https://github.com/m5stack/uiflow-micropython (issue filed from #58).
# The error is cosmetic — M5.begin() continues and all peripherals initialise
# correctly — but _EXPECTED_BOARD lets us catch a board-misidentification that
# would indicate a deeper problem.
_EXPECTED_BOARD = "m5stickc_plus"


def _check_board() -> None:
    """Warn if M5.getBoard() does not match the expected M5StickC Plus."""
    try:
        board = M5.getBoard()
        expected = getattr(M5.BOARD, "M5StickCPlus", None)
        if expected is not None and board != expected:
            print(
                f"WARNING display_m5: M5.getBoard()={board!r} expected"
                f" M5.BOARD.M5StickCPlus={expected!r} — wrong board?"
            )
    except AttributeError:
        # UIFlow build without BOARD constants — skip the check.
        pass


class M5Display:
    """``Display`` Protocol implementation backed by ``M5.Lcd``."""

    width: int = 240
    height: int = 135

    def __init__(self) -> None:
        M5.begin()
        _check_board()
        M5.Lcd.setRotation(1)  # 1 = landscape 240×135 on M5StickC PLUS

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

    def sleep(self) -> None:
        """Turn the backlight off to save power."""
        M5.Lcd.setBrightness(0)

    def wake(self) -> None:
        """Restore the backlight to full brightness."""
        M5.Lcd.setBrightness(100)
