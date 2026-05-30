"""Phase 1 landscape (240x135) screen renderer.

The layout is intentionally additive: each ``render`` call paints the
full frame from scratch against the ``Display`` Protocol. Concrete
displays may double-buffer; the protocol contract is that ``show()``
makes the most recent draw calls visible.
"""

from ui.display import Display
from ui.state import State

WIDTH = 240
HEIGHT = 135

# Colors are kept as small integers; concrete displays map them to the
# panel's native format. 0 = background, 1 = foreground, 2 = accent.
BG = 0
FG = 1
ACCENT = 2

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LINE_CHARS = 16

# Font cell sizes — see ``display.Display`` docstring.
GLYPH_W = 8
GLYPH_H = 8

# Vertical anchor points for each layout band.
TOP_BAR_Y = 2
WHEEL_Y = 22
CARET_Y = WHEEL_Y + GLYPH_H + 2
FOCUS_Y = 44
IN_Y = 88
OUT_Y = 102
FOOTER_Y = 124

# The focused-letter row uses scale 3 so the mapping reads as a "magic
# reveal" across the device. ``A -> N`` rendered at scale 3 is 5 glyphs
# wide (120px) and fits centered on 240px.
FOCUS_SCALE = 3


def _wheel_x(idx: int) -> int:
    # Wheel is centered horizontally: 26 glyphs × 8px = 208, left margin = 16.
    return 16 + idx * GLYPH_W


def _tail(buf: str, n: int = LINE_CHARS) -> str:
    return buf[-n:] if len(buf) > n else buf


def _focus_letters(state: State) -> tuple[str, str]:
    """Return (left, right) for the focused-letter mapping row.

    ENC mode shows plain→cipher; DEC mode shows cipher→plain. The cipher
    is resolved through ``encoder.ALGORITHMS``; if the algorithm is not
    registered the source letter is shown on both sides as a fallback so
    rendering never raises.
    """
    from encoder import ALGORITHMS  # local import keeps ui.* host-portable

    src = ALPHABET[state.wheel_idx]
    cls = ALGORITHMS.get(state.algorithm)
    if cls is None:
        return src, src
    cipher = cls()
    mapped = cipher.encode(src) if state.mode == "ENC" else cipher.decode(src)
    return src, mapped


def render(display: Display, state: State) -> None:
    display.fill(BG)

    # Top bar: mode tag, algorithm name, word-length counter.
    tag = f"[{state.mode}]"
    display.text(tag, 2, TOP_BAR_Y, ACCENT, scale=1)
    display.text(state.algorithm, 50, TOP_BAR_Y, FG, scale=1)
    counter = f"{min(len(state.in_buf), LINE_CHARS)}/{LINE_CHARS}"
    display.text(counter, WIDTH - 5 * GLYPH_W, TOP_BAR_Y, FG, scale=1)

    # Cipher wheel: full A-Z in order, plus a caret rect under wheel_idx.
    for i, ch in enumerate(ALPHABET):
        display.text(ch, _wheel_x(i), WHEEL_Y, FG, scale=1)
    caret_x = _wheel_x(state.wheel_idx)
    display.rect(caret_x, CARET_Y, GLYPH_W, 2, ACCENT, fill=True)

    # Focused-letter mapping row at scale 3 — centered.
    left, right = _focus_letters(state)
    arrow = ">"  # plain ASCII so the host font works without unicode.
    focus_str = f"{left} {arrow} {right}"
    focus_w = len(focus_str) * GLYPH_W * FOCUS_SCALE
    focus_x = max(0, (WIDTH - focus_w) // 2)
    display.text(focus_str, focus_x, FOCUS_Y, FG, scale=FOCUS_SCALE)

    # in: / out: lines, trailing 16 chars only.
    display.text(f"in: {_tail(state.in_buf)}", 2, IN_Y, FG, scale=1)
    display.text(f"out: {_tail(state.out_buf)}", 2, OUT_Y, FG, scale=1)

    # Footer: button legend.
    display.text("A:next  B:add  PWR:mode", 2, FOOTER_Y, FG, scale=1)

    display.show()
