"""Landscape (240x135) screen renderer.

The layout is intentionally additive: each ``render`` call paints the
full frame from scratch against the ``Display`` Protocol. Concrete
displays may double-buffer; the protocol contract is that ``show()``
makes the most recent draw calls visible.

``render()`` dispatches on ``state.screen``:
  "setup_cipher" → _render_setup_cipher  (boot cipher selection)
  "setup_key"    → _render_setup_key     (keyword entry)
  "encode"       → _render_encode        (main encode/decode screen)
"""

from encoder import ALGORITHMS as _ALGORITHMS
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

# Scroll wheel font scales: non-center letters use WHEEL_SCALE; the center
# letter uses WHEEL_CENTER_SCALE so it stands out as larger and bolder.
WHEEL_SCALE = 2
WHEEL_CENTER_SCALE = 3
IN_SCALE = 1         # scale for the "in: …" label + value line
OUT_SCALE = 1        # scale for the "out: …" label + value line

# Scroll wheel letter spacing.
# Hardware renders glyphs with variable visible width (W/M are widest).
# Using center_x=True in display.text() centres each glyph within its slot.
WHEEL_LETTER_GAP = 6    # pixels between consecutive non-center letter slots
WHEEL_CENTER_EXTRA = 3  # extra pixels of clearance on each side of the center letter
WHEEL_CENTER_Y_OFFSET = 0  # vertical shift for center letter only (negative = up)

# Smooth font names (stems only, no path, no .vlw extension).
# Empty string = use the default GLCDFONT with WHEEL_SCALE / WHEEL_CENTER_SCALE.
# When set, load_font() is called before wheel rendering and scale=1 is passed
# to display.text() so the .vlw size is used directly.
WHEEL_FONT = ""         # font for non-center wheel letters
WHEEL_CENTER_FONT = ""  # font for the center letter; falls back to WHEEL_FONT if empty
IN_FONT = ""            # font for the "in: …" line; "" = GLCDFONT
OUT_FONT = ""           # font for the "out: …" line; "" = GLCDFONT

# Vertical anchor points for each layout band.
# Budget: scale-3 rows ~28px tall (GLYPH_H*3 + 4px margin); scale-1 rows ~12px.
TOP_BAR_Y = 2
WHEEL_Y = 18
CIPHER_ROW_Y = 52   # 18 + 28(wheel) + 6(gap)
IN_Y = 86           # 52 + 28(cipher) + 6(gap)
OUT_Y = 100         # 86 + 12(in:) + 2(gap)
FOOTER_Y = 114      # 100 + 12(out:) + 2(gap);  bottom=122 < 135 ✓

# Vertical spacing for setup_cipher list items.
_SETUP_LIST_Y0 = 30   # y of first cipher item
_SETUP_LIST_DY = 18   # pixels between items

# setup_key: key-buf display and key-tail label — all configurable via configure().
_SETUP_KEY_FOCUS_Y = 54       # top-y of the large key-buf display
_SETUP_KEY_FOCUS_SCALE = 3    # integer scale when no VLW font is loaded
_SETUP_KEY_FOCUS_FONT = ""    # VLW font stem for the large key-buf display
_SETUP_KEY_LINE_Y = 84        # top-y of the "key: …" tail label
_SETUP_KEY_LINE_SCALE = 1     # integer scale when no VLW font is loaded
_SETUP_KEY_LINE_FONT = ""     # VLW font stem for the "key: …" tail label


def configure(cfg: dict) -> None:
    """Apply layout overrides from a runtime config dict (loaded from config.json).

    Every key is optional; missing keys keep the compiled-in default.
    Call once at boot after ``load_config()``, before the first ``render()``.

    Tunable keys
    ------------
    wheel_scale              int  scale for non-center wheel letters          (default 2)
    wheel_center_scale       int  scale for the selected center letter         (default 3)
    wheel_letter_gap         int  px between consecutive non-center slots      (default 6)
    wheel_center_extra       int  extra px of clearance around center letter   (default 3)
    wheel_center_y_offset    int  vertical shift of center letter only         (default 0)
    wheel_font               str  stem of .vlw file for non-center letters     (default "")
    wheel_center_font        str  stem of .vlw file for center letter          (default "")
    in_font                  str  stem of .vlw file for the in: line           (default "")
    in_scale                 int  scale for the in: line                       (default 1)
    out_font                 str  stem of .vlw file for the out: line          (default "")
    out_scale                int  scale for the out: line                      (default 1)
    wheel_y                  int  top-y of both scroll wheels                  (default 18)
    cipher_row_y             int  top-y of cipher scroll wheel                 (default 52)
    in_y                     int  top-y of in: line                            (default 86)
    out_y                    int  top-y of out: line                           (default 100)
    footer_y                 int  top-y of footer hint line                    (default 114)
    setup_key_focus_y        int  top-y of the large key-buf on setup_key      (default 54)
    setup_key_focus_scale    int  integer scale for key-buf (no VLW font)      (default 3)
    setup_key_focus_font     str  stem of .vlw file for the large key-buf      (default "")
    setup_key_line_y         int  top-y of the "key: …" tail on setup_key      (default 84)
    setup_key_line_scale     int  integer scale for "key:" label (no VLW font) (default 1)
    setup_key_line_font      str  stem of .vlw file for the "key: …" label     (default "")
    """
    global WHEEL_SCALE, WHEEL_CENTER_SCALE, IN_SCALE, OUT_SCALE
    global WHEEL_LETTER_GAP, WHEEL_CENTER_EXTRA, WHEEL_CENTER_Y_OFFSET
    global WHEEL_FONT, WHEEL_CENTER_FONT, IN_FONT, OUT_FONT
    global WHEEL_Y, CIPHER_ROW_Y, IN_Y, OUT_Y, FOOTER_Y
    global _SETUP_KEY_FOCUS_Y, _SETUP_KEY_FOCUS_SCALE, _SETUP_KEY_FOCUS_FONT
    global _SETUP_KEY_LINE_Y, _SETUP_KEY_LINE_SCALE, _SETUP_KEY_LINE_FONT
    WHEEL_SCALE             = int(cfg.get("wheel_scale",             WHEEL_SCALE))
    WHEEL_CENTER_SCALE      = int(cfg.get("wheel_center_scale",      WHEEL_CENTER_SCALE))
    # in_out_scale is a legacy fallback; in_scale / out_scale take precedence.
    _io = int(cfg.get("in_out_scale", IN_SCALE))
    IN_SCALE                = int(cfg.get("in_scale",                _io))
    OUT_SCALE               = int(cfg.get("out_scale",               _io))
    WHEEL_LETTER_GAP        = int(cfg.get("wheel_letter_gap",        WHEEL_LETTER_GAP))
    WHEEL_CENTER_EXTRA      = int(cfg.get("wheel_center_extra",      WHEEL_CENTER_EXTRA))
    WHEEL_CENTER_Y_OFFSET   = int(cfg.get("wheel_center_y_offset",   WHEEL_CENTER_Y_OFFSET))
    WHEEL_FONT              = str(cfg.get("wheel_font",              WHEEL_FONT))
    WHEEL_CENTER_FONT       = str(cfg.get("wheel_center_font",       WHEEL_CENTER_FONT))
    IN_FONT                 = str(cfg.get("in_font",                 IN_FONT))
    OUT_FONT                = str(cfg.get("out_font",                OUT_FONT))
    WHEEL_Y                 = int(cfg.get("wheel_y",                 WHEEL_Y))
    CIPHER_ROW_Y            = int(cfg.get("cipher_row_y",            CIPHER_ROW_Y))
    IN_Y                    = int(cfg.get("in_y",                    IN_Y))
    OUT_Y                   = int(cfg.get("out_y",                   OUT_Y))
    FOOTER_Y                = int(cfg.get("footer_y",                FOOTER_Y))
    _SETUP_KEY_FOCUS_Y      = int(cfg.get("setup_key_focus_y",       _SETUP_KEY_FOCUS_Y))
    _SETUP_KEY_FOCUS_SCALE  = int(cfg.get("setup_key_focus_scale",   _SETUP_KEY_FOCUS_SCALE))
    _SETUP_KEY_FOCUS_FONT   = str(cfg.get("setup_key_focus_font",    _SETUP_KEY_FOCUS_FONT))
    _SETUP_KEY_LINE_Y       = int(cfg.get("setup_key_line_y",        _SETUP_KEY_LINE_Y))
    _SETUP_KEY_LINE_SCALE   = int(cfg.get("setup_key_line_scale",    _SETUP_KEY_LINE_SCALE))
    _SETUP_KEY_LINE_FONT    = str(cfg.get("setup_key_line_font",     _SETUP_KEY_LINE_FONT))


def _wheel_char_widths(display: Display) -> tuple[int, int]:
    """Return ``(char_w, center_char_w)`` for the current font configuration.

    When smooth fonts are configured, loads them to query the advance width
    via ``display.text_width("A")``, then restores the non-center font.
    When no fonts are configured, returns the GLYPH_W-based defaults.
    """
    if not WHEEL_FONT:
        return GLYPH_W * WHEEL_SCALE, GLYPH_W * WHEEL_CENTER_SCALE
    display.load_font(WHEEL_FONT)
    char_w = display.text_width("A")
    center_w = char_w  # default: same size as non-center
    if WHEEL_CENTER_FONT and WHEEL_CENTER_FONT != WHEEL_FONT:
        display.load_font(WHEEL_CENTER_FONT)
        center_w = display.text_width("A")
        display.load_font(WHEEL_FONT)  # restore non-center font for rendering
    return char_w, center_w


def _slot(idx: int, wheel_idx: int, char_w: int, center_char_w: int) -> tuple[int, int, bool]:
    """Return ``(left_x, center_x, is_center)`` for the scroll-wheel slot at ``idx``.

    ``left_x``    – used for off-screen clipping (``-char_w < left_x < WIDTH``).
    ``center_x``  – passed to ``display.text(..., center_x=True)``.
    ``is_center`` – True only for the currently-selected letter.
    """
    n = len(ALPHABET)
    offset = (idx - wheel_idx) % n
    if offset > n // 2:
        offset -= n
    cx = WIDTH // 2
    if offset == 0:
        lx = cx - center_char_w // 2
        return lx, cx, True
    center_gap = WHEEL_LETTER_GAP + WHEEL_CENTER_EXTRA
    stride = char_w + WHEEL_LETTER_GAP
    if offset > 0:
        lx = cx + center_char_w // 2 + center_gap + (offset - 1) * stride
    else:
        k = -offset
        lx = cx - center_char_w // 2 - center_gap - char_w - (k - 1) * stride
    return lx, lx + char_w // 2, False


def _tail(buf: str, n: int = LINE_CHARS) -> str:
    return buf[-n:] if len(buf) > n else buf


def _active_key(state: State) -> str:
    """Return the saved key for the current algorithm."""
    return state.caesar_key if state.algorithm == "caesar" else state.cipher_key


def _focus_letters(
    state: State, ciphers: dict | None = None
) -> tuple[str, str]:
    """Return (left, right) for the focused-letter mapping row."""
    src = ALPHABET[state.wheel_idx]
    cipher = None
    if ciphers is not None:
        cipher = ciphers.get(state.algorithm)
    if cipher is None:
        cls = _ALGORITHMS.get(state.algorithm)
        if cls is None:
            return src, src
        cipher = cls()
    try:
        mapped = cipher.encode(src) if state.mode == "ENC" else cipher.decode(src)
    except ValueError:
        mapped = src
    return src, mapped


def _cipher_row(state: State, ciphers: dict | None = None) -> list[str]:
    """Return 26 cipher-alphabet characters (always encode direction).

    For monoalphabetic ciphers (rot13): encode(ALPHABET) is a permutation —
    every plaintext letter maps to a unique cipher letter, so showing all 26
    gives the full bijection.

    For polyalphabetic ciphers (Vigenère/keyword): encode(ALPHABET) cycles the
    key across 26 DIFFERENT positions, producing duplicates (e.g. 'ZEBRA'
    gives three J's, three E's, …).  Instead we show the Caesar shift for the
    CURRENT key position — key[len(in_buf) % len(key)] — which is always a
    permutation and changes as the user types, making the polyalphabetic nature
    visible.

    Both ENC and DEC modes use the same cipher alphabet so _render_encode can
    swap which row sits on top rather than recomputing a reversed mapping.
    """
    # Polyalphabetic (keyword/Vigenère): show the Caesar alphabet for the
    # current key character.  A fresh cipher instance with a 1-char key applies
    # the same shift to every position → guaranteed permutation, no duplicates.
    if state.algorithm == "keyword" and state.cipher_key:
        ki = len(state.in_buf) % len(state.cipher_key)
        shift = ord(state.cipher_key[ki]) - ord('A')
        return [ALPHABET[(i + shift) % 26] for i in range(26)]

    # Monoalphabetic: encode(ALPHABET) is always a permutation.
    cipher = None
    if ciphers is not None:
        cipher = ciphers.get(state.algorithm)
    if cipher is None:
        cls = _ALGORITHMS.get(state.algorithm)
        if cls is None:
            return list(ALPHABET)
        cipher = cls()
    try:
        return list(cipher.encode(ALPHABET))
    except (ValueError, KeyError):
        return list(ALPHABET)


def render_splash(display: Display, battery_pct: str = "?") -> None:
    """Draw boot splash: title + battery %, then call show()."""
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
    if state.screen == "setup_cipher":
        _render_setup_cipher(display, state, ciphers)
    elif state.screen == "setup_key":
        _render_setup_key(display, state)
    else:
        _render_encode(display, state, ciphers)


def _render_setup_cipher(
    display: Display, state: State, ciphers: dict | None = None
) -> None:
    display.fill(BG)

    display.text("[SETUP]", 2, TOP_BAR_Y, ACCENT, scale=1)
    batt_str = f"B:{state.battery_pct}%"
    display.text(batt_str, WIDTH - 6 * GLYPH_W, TOP_BAR_Y, FG, scale=1)

    order = list((ciphers or _ALGORITHMS).keys())
    for i, name in enumerate(order):
        y = _SETUP_LIST_Y0 + i * _SETUP_LIST_DY
        cursor = ">" if i == state.setup_idx else " "
        color = ACCENT if i == state.setup_idx else FG
        display.text(f"{cursor} {name}", 16, y, color, scale=1)

    display.text("B:prev  PWR:next  A:select", 2, FOOTER_Y, FG, scale=1)
    display.show()


def _render_setup_key(display: Display, state: State) -> None:
    display.fill(BG)

    display.text("[SETUP KEY]", 2, TOP_BAR_Y, ACCENT, scale=1)

    # Scroll wheel for letter selection.
    char_w, center_char_w = _wheel_char_widths(display)
    wheel_scale = 1 if WHEEL_FONT else WHEEL_SCALE
    center_scale = 1 if (WHEEL_FONT or WHEEL_CENTER_FONT) else WHEEL_CENTER_SCALE
    for i, ch in enumerate(ALPHABET):
        lx, slot_cx, is_center = _slot(i, state.wheel_idx, char_w, center_char_w)
        gw = center_char_w if is_center else char_w
        if -gw < lx < WIDTH:
            color = CURSOR if is_center else FG
            scale = center_scale if is_center else wheel_scale
            y = WHEEL_Y + (WHEEL_CENTER_Y_OFFSET if is_center else 0)
            if is_center and WHEEL_CENTER_FONT and WHEEL_CENTER_FONT != WHEEL_FONT:
                display.load_font(WHEEL_CENTER_FONT)
            display.text(ch, slot_cx, y, color, scale=scale, center_x=True)
            if is_center and WHEEL_CENTER_FONT and WHEEL_CENTER_FONT != WHEEL_FONT:
                display.load_font(WHEEL_FONT) if WHEEL_FONT else display.unload_font()

    # Current key being assembled, large and centered.
    key_display = state.key_buf if state.key_buf else "_"
    if _SETUP_KEY_FOCUS_FONT:
        display.load_font(_SETUP_KEY_FOCUS_FONT)
        key_w = display.text_width(key_display)
    else:
        key_w = len(key_display) * GLYPH_W * _SETUP_KEY_FOCUS_SCALE
    key_x = max(0, (WIDTH - key_w) // 2)
    display.text(key_display, key_x, _SETUP_KEY_FOCUS_Y, ACCENT,
                 scale=1 if _SETUP_KEY_FOCUS_FONT else _SETUP_KEY_FOCUS_SCALE)
    if _SETUP_KEY_FOCUS_FONT:
        display.unload_font()

    if _SETUP_KEY_LINE_FONT:
        display.load_font(_SETUP_KEY_LINE_FONT)
    display.text(f"key: {_tail(state.key_buf)}", 2, _SETUP_KEY_LINE_Y, FG,
                 scale=1 if _SETUP_KEY_LINE_FONT else _SETUP_KEY_LINE_SCALE)
    if _SETUP_KEY_LINE_FONT:
        display.unload_font()
    display.text("A:letter  AA:del  AL:done", 2, FOOTER_Y, FG, scale=1)
    display.show()


def _render_encode(
    display: Display, state: State, ciphers: dict | None = None
) -> None:
    display.fill(BG)

    # Top bar: mode tag at 2×, algorithm + key hint, counter, battery.
    tag = f"[{state.mode}]"
    display.text(tag, 2, TOP_BAR_Y, ACCENT, scale=2)
    algo_x = 2 + len(tag) * GLYPH_W * 2 + 4   # clear the 2× tag
    algo_y = TOP_BAR_Y + GLYPH_H // 2           # vertically centre vs the taller tag
    if state.algorithm != "rot13":
        algo_str = f"{state.algorithm} {_active_key(state)[:5]}"
    else:
        algo_str = state.algorithm
    display.text(algo_str, algo_x, algo_y, FG, scale=1)
    counter = f"{min(len(state.in_buf), LINE_CHARS)}/{LINE_CHARS}"
    display.text(counter, WIDTH - 12 * GLYPH_W, algo_y, FG, scale=1)
    batt_str = f"B:{state.battery_pct}%"
    display.text(batt_str, WIDTH - 6 * GLYPH_W, algo_y, FG, scale=1)

    # Two scroll wheels: in ENC mode plain is on top, cipher on bottom;
    # in DEC mode they swap so the user always selects from the input alphabet.
    char_w, center_char_w = _wheel_char_widths(display)
    wheel_scale = 1 if WHEEL_FONT else WHEEL_SCALE
    center_scale = 1 if (WHEEL_FONT or WHEEL_CENTER_FONT) else WHEEL_CENTER_SCALE
    cipher_chars = _cipher_row(state, ciphers)
    if state.mode == "ENC":
        top_chars = list(ALPHABET)
        bottom_chars = cipher_chars
    else:
        top_chars = cipher_chars
        bottom_chars = list(ALPHABET)

    for i, ch in enumerate(top_chars):
        lx, slot_cx, is_center = _slot(i, state.wheel_idx, char_w, center_char_w)
        gw = center_char_w if is_center else char_w
        if -gw < lx < WIDTH:
            color = CURSOR if is_center else FG
            scale = center_scale if is_center else wheel_scale
            y = WHEEL_Y + (WHEEL_CENTER_Y_OFFSET if is_center else 0)
            if is_center and WHEEL_CENTER_FONT and WHEEL_CENTER_FONT != WHEEL_FONT:
                display.load_font(WHEEL_CENTER_FONT)
            display.text(ch, slot_cx, y, color, scale=scale, center_x=True)
            if is_center and WHEEL_CENTER_FONT and WHEEL_CENTER_FONT != WHEEL_FONT:
                display.load_font(WHEEL_FONT) if WHEEL_FONT else display.unload_font()

    for i, ch in enumerate(bottom_chars):
        lx, slot_cx, is_center = _slot(i, state.wheel_idx, char_w, center_char_w)
        gw = center_char_w if is_center else char_w
        if -gw < lx < WIDTH:
            color = CURSOR if is_center else FG
            scale = center_scale if is_center else wheel_scale
            y = CIPHER_ROW_Y + (WHEEL_CENTER_Y_OFFSET if is_center else 0)
            if is_center and WHEEL_CENTER_FONT and WHEEL_CENTER_FONT != WHEEL_FONT:
                display.load_font(WHEEL_CENTER_FONT)
            display.text(ch, slot_cx, y, color, scale=scale, center_x=True)
            if is_center and WHEEL_CENTER_FONT and WHEEL_CENTER_FONT != WHEEL_FONT:
                display.load_font(WHEEL_FONT) if WHEEL_FONT else display.unload_font()

    if WHEEL_FONT:
        display.unload_font()

    if IN_FONT:
        display.load_font(IN_FONT)
    display.text(f"in: {_tail(state.in_buf)}", 2, IN_Y, FG, scale=IN_SCALE)
    if IN_FONT:
        display.unload_font()
    if OUT_FONT:
        display.load_font(OUT_FONT)
    display.text("out: ", 2, OUT_Y, FG, scale=OUT_SCALE)
    out_value = _tail(state.out_buf)
    if out_value:
        label_w = display.text_width("out: ") if OUT_FONT else len("out: ") * GLYPH_W * OUT_SCALE
        display.text(out_value, 2 + label_w, OUT_Y, ACCENT, scale=OUT_SCALE)
    if OUT_FONT:
        display.unload_font()
    display.text("A:add  AA:back  AL:flip", 2, FOOTER_Y, FG, scale=1)
    display.show()
