import pytest

from ui.display import Display
from ui.display_mock import DisplayMock, LoadFontCall, ShowCall, TextCall, UnloadFontCall
from ui.screen import (
    ACCENT,
    ALPHABET,
    CIPHER_ROW_Y,
    CURSOR,
    FG,
    FOOTER_Y,
    GLYPH_W,
    IN_SCALE,
    IN_Y,
    LINE_CHARS,
    OUT_SCALE,
    TOP_BAR_Y,
    WHEEL_CENTER_EXTRA,
    WHEEL_CENTER_SCALE,
    WHEEL_SCALE,
    WHEEL_Y,
    _ABOUT_BODY_DY,
    _ABOUT_BODY_Y0,
    _ABOUT_FOOTER_LABELS,
    _ABOUT_FOOTER_X,
    _ABOUT_HEADER_SCALE,
    render,
)
from ui.state import State


@pytest.fixture
def mock() -> DisplayMock:
    return DisplayMock()


def test_display_mock_satisfies_display_protocol(mock: DisplayMock):
    assert isinstance(mock, Display)


def test_render_calls_show_last(mock: DisplayMock):
    render(mock, State())
    assert isinstance(mock.calls[-1], ShowCall)


def test_mode_tag_enc(mock: DisplayMock):
    render(mock, State(mode="ENC"))
    assert any(c.s == "[ENC]" for c in mock.texts())
    assert not any(c.s == "[DEC]" for c in mock.texts())


def test_mode_tag_dec(mock: DisplayMock):
    render(mock, State(mode="DEC"))
    assert any(c.s == "[DEC]" for c in mock.texts())
    assert not any(c.s == "[ENC]" for c in mock.texts())


def test_wheel_center_has_extra_padding(mock: DisplayMock):
    # With center_x=True, c.x is the slot centre.
    # Gap from center RIGHT EDGE to right neighbour LEFT EDGE is WHEEL_CENTER_EXTRA wider
    # than the gap between two non-centre neighbours.
    render(mock, State(wheel_idx=12))
    gw_c = GLYPH_W * WHEEL_CENTER_SCALE
    gw = GLYPH_W * WHEEL_SCALE
    calls = sorted(
        [c for c in mock.texts() if c.y == WHEEL_Y and len(c.s) == 1 and c.s.isalpha()],
        key=lambda c: c.x,
    )
    center_idx = next(i for i, c in enumerate(calls) if c.color == CURSOR)
    center = calls[center_idx]
    right = calls[center_idx + 1]
    next_right = calls[center_idx + 2]
    # Gaps measured as: neighbour_left_edge - prev_right_edge
    # left_edge = cx - gw//2;  right_edge = cx + gw//2
    center_to_right_gap = (right.x - gw // 2) - (center.x + gw_c // 2)
    nonc_gap = (next_right.x - gw // 2) - (right.x + gw // 2)
    assert center_to_right_gap == nonc_gap + WHEEL_CENTER_EXTRA


def test_cipher_wheel_wraps_at_boundary(mock: DisplayMock):
    # When A is centered, Z must appear to the LEFT of A (circular wrap).
    render(mock, State(wheel_idx=0))
    wheel_calls = [c for c in mock.texts() if c.y == WHEEL_Y and len(c.s) == 1 and c.s.isalpha()]
    letters = [c.s for c in wheel_calls]
    assert "Z" in letters, "Z must wrap into the visible window when A is centered"
    z_x = next(c.x for c in wheel_calls if c.s == "Z")
    a_x = next(c.x for c in wheel_calls if c.s == "A")
    assert z_x < a_x, "Z should appear to the left of A on the wheel"


def test_cipher_wheel_shows_visible_subset_in_order(mock: DisplayMock):
    # With a scroll wheel, only letters near wheel_idx are drawn; full alphabet is not visible.
    render(mock, State(wheel_idx=12))
    wheel_chars = [c.s for c in mock.texts() if c.y == WHEEL_Y and len(c.s) == 1 and c.s.isalpha()]
    assert len(wheel_chars) < 26, "scroll wheel must clip off-screen letters"
    assert ALPHABET[12] in wheel_chars, "center letter must be visible"
    # Visible letters must appear in alphabetical order.
    assert wheel_chars == sorted(wheel_chars)


def test_cipher_wheel_non_center_letters_are_wheel_scale(mock: DisplayMock):
    render(mock, State(wheel_idx=12))
    wheel_calls = [c for c in mock.texts() if c.y == WHEEL_Y and len(c.s) == 1 and c.s.isalpha()]
    non_center = [c for c in wheel_calls if c.s != ALPHABET[12]]
    assert all(c.scale == WHEEL_SCALE for c in non_center)


def test_cipher_wheel_center_letter_uses_center_scale(mock: DisplayMock):
    render(mock, State(wheel_idx=12))
    wheel_calls = [c for c in mock.texts() if c.y == WHEEL_Y and len(c.s) == 1 and c.s.isalpha()]
    center = next(c for c in wheel_calls if c.s == ALPHABET[12])
    assert center.scale == WHEEL_CENTER_SCALE


@pytest.mark.parametrize("idx", [0, 1, 12, 25])
def test_cursor_character_is_green(mock: DisplayMock, idx: int):
    render(mock, State(wheel_idx=idx))
    wheel_calls = [c for c in mock.texts() if c.y == WHEEL_Y and len(c.s) == 1 and c.s.isalpha()]
    cursor_char = next(c for c in wheel_calls if c.s == ALPHABET[idx])
    assert cursor_char.color == CURSOR


@pytest.mark.parametrize("idx", [0, 1, 12, 25])
def test_non_cursor_characters_are_fg(mock: DisplayMock, idx: int):
    render(mock, State(wheel_idx=idx))
    wheel_calls = [c for c in mock.texts() if c.y == WHEEL_Y and len(c.s) == 1 and c.s.isalpha()]
    non_cursor = [c for c in wheel_calls if c.s != ALPHABET[idx]]
    assert all(c.color == FG for c in non_cursor)


def test_no_caret_rect_drawn(mock: DisplayMock):
    render(mock, State(wheel_idx=5))
    # Sub-cursor rect has been replaced by a green character; no filled rects.
    assert not mock.rects()


def test_in_and_out_show_full_content_when_short(mock: DisplayMock):
    render(mock, State(in_buf="HELLO", out_buf="URYYB"))
    seen = {c.s for c in mock.texts()}
    assert "in: HELLO" in seen
    assert "out: " in seen
    assert "URYYB" in seen


def test_in_line_shows_last_line_chars_when_longer(mock: DisplayMock):
    long_in = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"  # 26 chars
    render(mock, State(in_buf=long_in))
    expected = "in: " + long_in[-LINE_CHARS:]
    assert any(c.s == expected for c in mock.texts())
    assert not any(c.s.startswith("in: A") for c in mock.texts())


def test_out_line_shows_last_line_chars_when_longer(mock: DisplayMock):
    long_out = "NOPQRSTUVWXYZABCDEFGHIJKLM"  # 26 chars
    render(mock, State(out_buf=long_out))
    expected_value = long_out[-LINE_CHARS:]
    assert any(c.s == expected_value for c in mock.texts())


def test_in_line_uses_in_scale(mock: DisplayMock):
    render(mock, State(in_buf="HI", out_buf="UV"))
    in_call = next(c for c in mock.texts() if c.s.startswith("in: "))
    assert in_call.scale == IN_SCALE


def test_out_line_uses_out_scale(mock: DisplayMock):
    render(mock, State(in_buf="HI", out_buf="UV"))
    out_call = next(c for c in mock.texts() if c.s.startswith("out: "))
    assert out_call.scale == OUT_SCALE


def test_word_length_counter_reflects_in_buf(mock: DisplayMock):
    render(mock, State(in_buf="HELLO"))
    assert any(c.s == f"5/{LINE_CHARS}" for c in mock.texts())


def test_word_length_counter_caps_at_line_chars(mock: DisplayMock):
    render(mock, State(in_buf="A" * 30))
    assert any(c.s == f"{LINE_CHARS}/{LINE_CHARS}" for c in mock.texts())


def test_layout_band_ordering(mock: DisplayMock):
    """Top bar sits above wheel which sits above cipher row which sits above
    in/out lines which sit above footer. Tests intent (relative y), not pixels."""
    render(mock, State(in_buf="HI", out_buf="UV"))
    by_s = {c.s: c for c in mock.texts()}
    tag_y = by_s["[ENC]"].y
    wheel_y = next(c for c in mock.texts() if c.y == WHEEL_Y and len(c.s) == 1).y
    in_y = by_s["in: HI"].y
    out_y = by_s["out: "].y
    footer_y = by_s["A:add  AA:back  AL:flip"].y
    assert tag_y < wheel_y < in_y < out_y < footer_y


def test_render_starts_with_fill(mock: DisplayMock):
    render(mock, State())
    # First call must clear the frame so stale pixels don't bleed through.
    assert mock.calls[0].__class__.__name__ == "FillCall"


def test_cursor_always_at_screen_center():
    # With center_x=True, the cursor letter is always passed x = WIDTH//2.
    from ui.screen import WIDTH
    for idx in (0, 1, 12, 25):
        m = DisplayMock()
        render(m, State(wheel_idx=idx))
        wheel_calls = [c for c in m.texts() if c.y == WHEEL_Y and len(c.s) == 1 and c.s.isalpha()]
        cursor_x = next(c.x for c in wheel_calls if c.color == CURSOR)
        assert cursor_x == WIDTH // 2, f"cursor not centered for wheel_idx={idx}"


def test_text_call_default_scale_is_one(mock: DisplayMock):
    # Sanity: the protocol/mock default scale is 1.
    mock.text("X", 0, 0, 1)
    call: TextCall = mock.texts()[0]
    assert call.scale == 1


def test_vigenere_top_bar_shows_key_hint(mock: DisplayMock):
    from ui.state import State

    render(mock, State(algorithm="vigenere", cipher_key="SECRET"))
    # Key hint is truncated to 5 chars.
    assert any("vigenere SECRE" in c.s for c in mock.texts())


def test_rot13_top_bar_shows_algorithm_name(mock: DisplayMock):
    render(mock, State(algorithm="rot13"))
    assert any(c.s == "rot13" for c in mock.texts())
    assert not any("vigenere" in c.s for c in mock.texts())


def test_caesar_top_bar_shows_key_hint(mock: DisplayMock):
    render(mock, State(algorithm="caesar", caesar_key="D"))
    assert any("caesar D" in c.s for c in mock.texts())


def test_caesar_top_bar_updates_with_key(mock: DisplayMock):
    render(mock, State(algorithm="caesar", caesar_key="F"))
    assert any("caesar F" in c.s for c in mock.texts())


def test_caesar_top_bar_does_not_show_cipher_key(mock: DisplayMock):
    # cipher_key belongs to keyword; it must not leak into the caesar top bar.
    render(mock, State(algorithm="caesar", caesar_key="D", cipher_key="ZEBRA"))
    assert not any("ZEBRA" in c.s for c in mock.texts())


def test_key_edit_renders_key_edit_header(mock: DisplayMock):
    from ui.state import State

    render(mock, State(algorithm="vigenere", screen="setup_key", key_buf="AB"))
    assert any("[SETUP KEY]" in c.s for c in mock.texts())


def test_key_edit_renders_key_buf_large(mock: DisplayMock):
    from ui.state import State

    render(mock, State(algorithm="vigenere", screen="setup_key", key_buf="AB"))
    big = [c for c in mock.texts() if c.scale >= 2]
    assert any("AB" in c.s for c in big)


def test_key_edit_renders_footer_legend(mock: DisplayMock):
    from ui.state import State

    render(mock, State(algorithm="vigenere", screen="setup_key", key_buf="X"))
    assert any("A:letter" in c.s for c in mock.texts())


def test_key_edit_calls_show(mock: DisplayMock):
    from ui.state import State

    render(mock, State(algorithm="vigenere", screen="setup_key"))
    assert isinstance(mock.calls[-1], ShowCall)


# ---------------------------------------------------------------------------
# Cipher alphabet row
# ---------------------------------------------------------------------------

def test_cipher_row_y_between_wheel_y_and_in_y(mock: DisplayMock):
    assert WHEEL_Y < CIPHER_ROW_Y < IN_Y


def test_cipher_row_shows_visible_subset(mock: DisplayMock):
    render(mock, State(wheel_idx=12))
    cipher_row_calls = [
        c for c in mock.texts() if c.y == CIPHER_ROW_Y and len(c.s) == 1 and c.s.isalpha()
    ]
    assert 0 < len(cipher_row_calls) < 26, "cipher scroll wheel must show a clipped window"


def test_cipher_row_rot13_enc_shows_shifted_alphabet(mock: DisplayMock):
    render(mock, State(mode="ENC", algorithm="rot13", wheel_idx=0))
    cipher_row_calls = [c for c in mock.texts() if c.y == CIPHER_ROW_Y and len(c.s) == 1]
    assert cipher_row_calls[0].s == "N"   # A → N under rot13


def test_cipher_row_rot13_dec_shows_inverse(mock: DisplayMock):
    # In DEC mode the rows swap: top wheel shows the cipher alphabet so the
    # user selects a cipher letter; bottom row shows the corresponding plaintext.
    # wheel_idx=13 → ALPHABET[13]='N'; encode('N') for rot13 = 'A'.
    render(mock, State(mode="DEC", algorithm="rot13", wheel_idx=13))
    wheel_calls = [c for c in mock.texts() if c.y == WHEEL_Y and len(c.s) == 1]
    cursor_wheel = next(c for c in wheel_calls if c.color == CURSOR)
    assert cursor_wheel.s == "A"   # cipher letter at position 13: encode(N)=A
    cipher_row_calls = [c for c in mock.texts() if c.y == CIPHER_ROW_Y and len(c.s) == 1]
    cursor_plain = next(c for c in cipher_row_calls if c.color == CURSOR)
    assert cursor_plain.s == "N"   # plaintext letter at position 13


def test_cipher_row_cursor_aligns_with_wheel_cursor(mock: DisplayMock):
    render(mock, State(wheel_idx=5))
    wheel_calls = [c for c in mock.texts() if c.y == WHEEL_Y and len(c.s) == 1]
    cipher_calls = [c for c in mock.texts() if c.y == CIPHER_ROW_Y and len(c.s) == 1]
    wheel_cursor_x = next(c.x for c in wheel_calls if c.color == CURSOR)
    cipher_cursor_x = next(c.x for c in cipher_calls if c.color == CURSOR)
    assert wheel_cursor_x == cipher_cursor_x


# ---------------------------------------------------------------------------
# Smooth font path
# ---------------------------------------------------------------------------


def test_wheel_font_causes_load_and_unload(mock: DisplayMock):
    import ui.screen as screen
    saved = screen.WHEEL_FONT
    try:
        screen.WHEEL_FONT = "TestMono16"
        render(mock, State())
        load_names = [c.name for c in mock.calls if isinstance(c, LoadFontCall)]
        assert "TestMono16" in load_names, "load_font('TestMono16') must be called"
        assert any(isinstance(c, UnloadFontCall) for c in mock.calls), \
            "unload_font() must be called after wheel rendering"
    finally:
        screen.WHEEL_FONT = saved


def test_wheel_font_passes_scale_1_to_text(mock: DisplayMock):
    import ui.screen as screen
    saved = screen.WHEEL_FONT
    try:
        screen.WHEEL_FONT = "TestMono16"
        render(mock, State(wheel_idx=12))
        wheel_texts = [c for c in mock.texts()
                       if c.y == WHEEL_Y and len(c.s) == 1 and c.s.isalpha()]
        assert all(c.scale == 1 for c in wheel_texts), \
            "scale=1 must be used for all wheel letters when WHEEL_FONT is set"
    finally:
        screen.WHEEL_FONT = saved


def test_cipher_row_not_shown_in_key_edit_mode(mock: DisplayMock):
    render(mock, State(algorithm="vigenere", screen="setup_key", cipher_key="X", key_buf="X"))
    cipher_row_calls = [c for c in mock.texts() if c.y == CIPHER_ROW_Y]
    assert cipher_row_calls == []


# ---------------------------------------------------------------------------
# Vigenère cipher row — no duplicates
# ---------------------------------------------------------------------------

def _cipher_row_chars(mock: DisplayMock, state) -> list[str]:
    """Render and return all single-letter texts drawn at CIPHER_ROW_Y."""
    render(mock, state)
    return [c.s for c in mock.texts() if c.y == CIPHER_ROW_Y and len(c.s) == 1]


def test_vigenere_cipher_row_no_duplicates_zebra(mock: DisplayMock):
    # 'ZEBRA' triggered triplicate J/E/O/T/Y with the old encode(ALPHABET) approach.
    state = State(algorithm="vigenere", cipher_key="ZEBRA", wheel_idx=0)
    chars = _cipher_row_chars(mock, state)
    assert len(chars) == len(set(chars)), f"duplicate cipher-row letters: {chars}"


@pytest.mark.parametrize("key", ["APPLE", "AAAAA", "SECRET", "ABCDE", "Z"])
def test_vigenere_cipher_row_no_duplicates_any_key(mock: DisplayMock, key: str):
    state = State(algorithm="vigenere", cipher_key=key, wheel_idx=0)
    chars = _cipher_row_chars(mock, state)
    assert len(chars) == len(set(chars)), f"key={key!r} produced duplicates: {chars}"


def test_vigenere_cipher_row_uses_current_key_position(mock: DisplayMock):
    # With key='ZEBRA' and no chars typed (ki=0 → 'Z', shift=25):
    # plain A(0) + shift(25) = 25 = 'Z'; cipher row at wheel_idx=0 shows 'Z' at center.
    state = State(algorithm="vigenere", cipher_key="ZEBRA", wheel_idx=0)
    chars = _cipher_row_chars(mock, state)
    assert chars[0] == "Z", f"expected 'Z' at cipher position 0, got {chars[0]!r}"


def test_vigenere_cipher_row_advances_with_in_buf(mock: DisplayMock):
    # After typing one char, ki=1 → 'E' (shift=4): plain A(0)+4 = 'E'.
    state = State(algorithm="vigenere", cipher_key="ZEBRA", wheel_idx=0, in_buf="H")
    chars = _cipher_row_chars(mock, state)
    assert chars[0] == "E", f"expected 'E' at cipher position 0 after 1 char, got {chars[0]!r}"


# ---------------------------------------------------------------------------
# Keyword substitution cipher row
# ---------------------------------------------------------------------------

def test_keyword_subst_top_bar_shows_key_hint(mock: DisplayMock):
    render(mock, State(algorithm="keyword", cipher_key="ZEBRA"))
    assert any("keyword ZEBRA" in c.s for c in mock.texts())


def test_keyword_subst_top_bar_default_key(mock: DisplayMock):
    render(mock, State(algorithm="keyword", cipher_key="KEY"))
    assert any("keyword KEY" in c.s for c in mock.texts())


def test_keyword_subst_cipher_row_is_permutation(mock: DisplayMock):
    # encode(A-Z) for a substitution cipher is a 26-letter permutation — no duplicates.
    state = State(algorithm="keyword", cipher_key="ZEBRA", wheel_idx=0)
    chars = _cipher_row_chars(mock, state)
    assert len(chars) == len(set(chars)), f"duplicate cipher-row letters: {chars}"


def test_keyword_subst_cipher_row_does_not_change_with_in_buf(mock: DisplayMock):
    # Monoalphabetic: the cipher row must be the same regardless of how many
    # chars have been typed.
    state_empty = State(algorithm="keyword", cipher_key="ZEBRA", wheel_idx=0, in_buf="")
    state_typed = State(algorithm="keyword", cipher_key="ZEBRA", wheel_idx=0, in_buf="HELLO")
    mock1 = type(mock)()
    mock2 = type(mock)()
    render(mock1, state_empty)
    render(mock2, state_typed)
    chars_empty = [c.s for c in mock1.texts() if c.y == CIPHER_ROW_Y and len(c.s) == 1]
    chars_typed = [c.s for c in mock2.texts() if c.y == CIPHER_ROW_Y and len(c.s) == 1]
    assert chars_empty == chars_typed, "keyword substitution cipher row must not change with in_buf"


def test_keyword_subst_cipher_row_center_is_z_for_zebra(mock: DisplayMock):
    # With key ZEBRA at wheel_idx=0 (A), the cipher row center should be Z
    # because A→Z in the ZEBRA substitution alphabet.
    state = State(algorithm="keyword", cipher_key="ZEBRA", wheel_idx=0)
    chars = _cipher_row_chars(mock, state)
    assert chars[0] == "Z", f"expected 'Z' at cipher position 0, got {chars[0]!r}"


# ---------------------------------------------------------------------------
# About screen layout
# ---------------------------------------------------------------------------

def test_about_screen_calls_show_last(mock: DisplayMock):
    render(mock, State(screen="about", about_idx=0))
    assert isinstance(mock.calls[-1], ShowCall)


def test_about_header_shows_algorithm_name_uppercased(mock: DisplayMock):
    render(mock, State(screen="about", about_idx=0))
    assert any(c.s == "ROT13" for c in mock.texts())


def test_about_header_is_accent_color(mock: DisplayMock):
    render(mock, State(screen="about", about_idx=0))
    header = next(c for c in mock.texts() if c.s == "ROT13")
    assert header.color == ACCENT


def test_about_header_at_top_bar_y(mock: DisplayMock):
    render(mock, State(screen="about", about_idx=0))
    header = next(c for c in mock.texts() if c.s == "ROT13")
    assert header.y == TOP_BAR_Y


def test_about_body_first_line_at_body_y0(mock: DisplayMock):
    render(mock, State(screen="about", about_idx=0))
    assert any(c.y == _ABOUT_BODY_Y0 for c in mock.texts())


def test_about_body_lines_spaced_by_body_dy(mock: DisplayMock):
    render(mock, State(screen="about", about_idx=0))
    ys = sorted({
        c.y for c in mock.texts()
        if _ABOUT_BODY_Y0 <= c.y < FOOTER_Y
    })
    for a, b in zip(ys, ys[1:]):
        assert b - a == _ABOUT_BODY_DY


def test_about_shows_all_five_body_lines(mock: DisplayMock):
    for idx in range(4):
        m = DisplayMock()
        render(m, State(screen="about", about_idx=idx))
        body_calls = [c for c in m.texts() if _ABOUT_BODY_Y0 <= c.y < FOOTER_Y]
        assert len(body_calls) == 5, f"about_idx={idx}: expected 5 body lines, got {len(body_calls)}"


def test_about_body_lines_above_footer(mock: DisplayMock):
    for idx in range(4):
        m = DisplayMock()
        render(m, State(screen="about", about_idx=idx))
        body_calls = [c for c in m.texts() if _ABOUT_BODY_Y0 <= c.y < FOOTER_Y]
        assert all(c.y + 8 <= FOOTER_Y for c in body_calls)


def test_about_footer_three_items_rendered(mock: DisplayMock):
    render(mock, State(screen="about", about_idx=0))
    footer_strings = {c.s for c in mock.texts() if c.y == FOOTER_Y}
    for label in _ABOUT_FOOTER_LABELS:
        assert label in footer_strings


def test_about_footer_items_at_correct_x_positions(mock: DisplayMock):
    render(mock, State(screen="about", about_idx=0, about_footer_idx=1))
    footer = {c.s: c for c in mock.texts() if c.y == FOOTER_Y and c.s in _ABOUT_FOOTER_LABELS}
    for label, expected_x in zip(_ABOUT_FOOTER_LABELS, _ABOUT_FOOTER_X):
        assert footer[label].x == expected_x, f"{label!r} expected x={expected_x}, got {footer[label].x}"


def test_about_footer_selected_item_is_accent(mock: DisplayMock):
    render(mock, State(screen="about", about_idx=0, about_footer_idx=1))
    exit_call = next(c for c in mock.texts() if c.s == "exit")
    assert exit_call.color == ACCENT


def test_about_footer_unselected_items_are_fg(mock: DisplayMock):
    render(mock, State(screen="about", about_idx=0, about_footer_idx=1))
    for label in ("<-prev", "next->"):
        call = next(c for c in mock.texts() if c.s == label)
        assert call.color == FG


@pytest.mark.parametrize("cursor_idx", [0, 1, 2])
def test_about_footer_cursor_highlights_correct_item(cursor_idx: int):
    m = DisplayMock()
    render(m, State(screen="about", about_idx=0, about_footer_idx=cursor_idx))
    footer = {c.s: c for c in m.texts() if c.s in _ABOUT_FOOTER_LABELS}
    for i, label in enumerate(_ABOUT_FOOTER_LABELS):
        expected = ACCENT if i == cursor_idx else FG
        assert footer[label].color == expected, f"{label!r} at cursor_idx={cursor_idx}: expected color {expected}"


def test_about_different_pages_show_different_headers(mock: DisplayMock):
    headers = set()
    for idx in range(4):
        m = DisplayMock()
        render(m, State(screen="about", about_idx=idx))
        h = next(c for c in m.texts() if c.y == TOP_BAR_Y and c.color == ACCENT)
        headers.add(h.s)
    assert len(headers) == 4, "each about page must have a unique header"


def test_about_setup_cipher_shows_about_item(mock: DisplayMock):
    render(mock, State(screen="setup_cipher", setup_idx=0))
    assert any("about" in c.s for c in mock.texts())


def test_about_setup_cipher_about_item_highlighted_when_selected(mock: DisplayMock):
    render(mock, State(screen="setup_cipher", setup_idx=4))
    about_line = next(c for c in mock.texts() if "about" in c.s and c.color == ACCENT)
    assert about_line is not None
