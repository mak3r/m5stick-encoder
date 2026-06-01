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
# panel's native format. 0 = background, 1 = foreground, 2 = accent,
# 3 = cursor (bright green).
BG = 0
FG = 1
ACCENT = 2
CURSOR = 3

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LINE_CHARS = 16

# Font cell sizes — see ``display.Display`` docstring.
GLYPH_W = 8
GLYPH_H = 8

# Vertical anchor points for each layout band.
TOP_BAR_Y = 2
WHEEL_Y = 22
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


def _focus_letters(
    state: State, ciphers: dict | None = None
) -> tuple[str, str]:
    """Return (left, right) for the focused-letter mapping row.

    ENC mode shows plain→cipher; DEC mode shows cipher→plain. When
    ``ciphers`` is provided the live instance is used (so key changes in
    the keyword cipher reflect immediately). Falls back to constructing a
    fresh instance from ``ALGORITHMS`` so rendering is always correct.
    """
    from encoder import ALGORITHMS  # local import keeps ui.* host-portable

    src = ALPHABET[state.wheel_idx]
    cipher = None
    if ciphers is not None:
        cipher = ciphers.get(state.algorithm)
    if cipher is None:
        cls = ALGORITHMS.get(state.algorithm)
        if cls is None:
            return src, src
        cipher = cls()
    try:
        mapped = cipher.encode(src) if state.mode == "ENC" else cipher.decode(src)
    except ValueError:
        mapped = src
    return src, mapped


def render_splash(display: Display, battery_pct: str = "?") -> None:
    """Draw boot splash: title + battery %, then call show().

    Caller is responsible for delaying ~1.5 s before calling ``render``.
    ``battery_pct`` is a string so callers can pass "?" when unavailable.
    """
    display.fill(BG)
    title = "SECRET CODE 1.0"
    title_w = len(title) * GLYPH_W * 2
    title_x = max(0, (WIDTH - title_w) // 2)
    title_y = (HEIGHT - GLYPH_H * 2) // 2 - 10
    display.text(title, title_x, title_y, ACCENT, scale=2)
    batt_str = f"BAT: {battery_pct}%"
    batt_w = len(batt_str) * GLYPH_W
    batt_x = max(0, (WIDTH - batt_w) // 2)
    display.text(batt_str, batt_x, title_y + GLYPH_H * 2 + 6, FG, scale=1)
    display.show()


def render(display: Display, state: State, ciphers: dict | None = None) -> None:
    if state.editing_key:
        _render_key_edit(display, state)
        return

    display.fill(BG)

    # Top bar: mode tag, algorithm name (+ key hint for keyword), counter, battery.
    tag = f"[{state.mode}]"
    display.text(tag, 2, TOP_BAR_Y, ACCENT, scale=1)
    algo_str = f"keyword {state.cipher_key}" if state.algorithm == "keyword" else state.algorithm
    display.text(algo_str, 50, TOP_BAR_Y, FG, scale=1)
    counter = f"{min(len(state.in_buf), LINE_CHARS)}/{LINE_CHARS}"
    display.text(counter, WIDTH - 12 * GLYPH_W, TOP_BAR_Y, FG, scale=1)
    # Battery: right-aligned; "B:100%" is the widest case (6 chars × 8px).
    batt_str = f"B:{state.battery_pct}%"
    display.text(batt_str, WIDTH - 6 * GLYPH_W, TOP_BAR_Y, FG, scale=1)

    # Cipher wheel: full A-Z in order; cursor character is bright green.
    for i, ch in enumerate(ALPHABET):
        color = CURSOR if i == state.wheel_idx else FG
        display.text(ch, _wheel_x(i), WHEEL_Y, color, scale=1)

    # Focused-letter mapping row at scale 3 — centered.
    left, right = _focus_letters(state, ciphers)
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


def _render_key_edit(display: Display, state: State) -> None:
    display.fill(BG)

    display.text("[KEY EDIT]", 2, TOP_BAR_Y, ACCENT, scale=1)

    # Cipher wheel: same layout as main screen.
    for i, ch in enumerate(ALPHABET):
        color = CURSOR if i == state.wheel_idx else FG
        display.text(ch, _wheel_x(i), WHEEL_Y, color, scale=1)

    # Current key being built, large and centered.
    key_display = state.key_buf if state.key_buf else "_"
    key_w = len(key_display) * GLYPH_W * FOCUS_SCALE
    key_x = max(0, (WIDTH - key_w) // 2)
    display.text(key_display, key_x, FOCUS_Y, ACCENT, scale=FOCUS_SCALE)

    display.text(f"key: {_tail(state.key_buf)}", 2, IN_Y, FG, scale=1)

    # Footer: key-edit button legend.
    display.text("A:add  AA:del  AL:save", 2, FOOTER_Y, FG, scale=1)

    display.show()
