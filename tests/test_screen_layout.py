import pytest

from ui.display import Display
from ui.display_mock import DisplayMock, ShowCall, TextCall
from ui.screen import ALPHABET, FOCUS_SCALE, LINE_CHARS, _wheel_x, render
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


def test_cipher_wheel_contains_all_26_letters_in_order(mock: DisplayMock):
    render(mock, State())
    # Single-character text calls in draw order should spell the alphabet.
    single_chars = [c.s for c in mock.texts() if len(c.s) == 1 and c.s.isalpha()]
    # The focus row uses a multi-char string ("A > N"), so single-char draws
    # come exclusively from the wheel row.
    assert single_chars == list(ALPHABET)


def test_cipher_wheel_letters_are_scale_1(mock: DisplayMock):
    render(mock, State())
    wheel_calls = [c for c in mock.texts() if len(c.s) == 1 and c.s.isalpha()]
    assert all(c.scale == 1 for c in wheel_calls)


@pytest.mark.parametrize("idx", [0, 1, 12, 25])
def test_caret_position_tracks_wheel_idx(mock: DisplayMock, idx: int):
    render(mock, State(wheel_idx=idx))
    expected_x = _wheel_x(idx)
    # The caret is the only filled rect drawn at the wheel x-axis stride.
    caret = next(r for r in mock.rects() if r.fill and r.x == expected_x)
    assert caret.x == expected_x


def test_in_and_out_show_full_content_when_short(mock: DisplayMock):
    render(mock, State(in_buf="HELLO", out_buf="URYYB"))
    seen = {c.s for c in mock.texts()}
    assert "in: HELLO" in seen
    assert "out: URYYB" in seen


def test_in_line_shows_last_16_when_longer(mock: DisplayMock):
    long_in = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"  # 26 chars
    render(mock, State(in_buf=long_in))
    expected = "in: " + long_in[-LINE_CHARS:]
    assert any(c.s == expected for c in mock.texts())
    # And the head must NOT appear.
    assert not any(c.s.startswith("in: A") for c in mock.texts())


def test_out_line_shows_last_16_when_longer(mock: DisplayMock):
    long_out = "NOPQRSTUVWXYZABCDEFGHIJKLM"  # 26 chars
    render(mock, State(out_buf=long_out))
    expected = "out: " + long_out[-LINE_CHARS:]
    assert any(c.s == expected for c in mock.texts())


def test_focused_letter_row_uses_scale_at_least_2(mock: DisplayMock):
    render(mock, State(wheel_idx=0))
    big = [c for c in mock.texts() if c.scale >= 2]
    assert big, "expected at least one text call at scale >= 2 (focused-letter row)"
    assert FOCUS_SCALE >= 2


def test_focused_letter_row_shows_mapping_for_rot13_enc(mock: DisplayMock):
    render(mock, State(mode="ENC", algorithm="rot13", wheel_idx=0))
    focus = next(c for c in mock.texts() if c.scale >= 2)
    # A under rot13 ENC → N.
    assert "A" in focus.s
    assert "N" in focus.s


def test_focused_letter_row_shows_mapping_for_rot13_dec(mock: DisplayMock):
    # rot13 is self-inverse, so DEC of A is still N — but the source/target
    # ordering on screen should not have swapped erroneously.
    render(mock, State(mode="DEC", algorithm="rot13", wheel_idx=13))
    focus = next(c for c in mock.texts() if c.scale >= 2)
    # N decoded under rot13 → A. Source letter ("N") appears before the arrow.
    assert focus.s.startswith("N")
    assert focus.s.endswith("A")


def test_word_length_counter_reflects_in_buf(mock: DisplayMock):
    render(mock, State(in_buf="HELLO"))
    assert any(c.s == f"5/{LINE_CHARS}" for c in mock.texts())


def test_word_length_counter_caps_at_line_chars(mock: DisplayMock):
    render(mock, State(in_buf="A" * 30))
    assert any(c.s == f"{LINE_CHARS}/{LINE_CHARS}" for c in mock.texts())


def test_layout_band_ordering(mock: DisplayMock):
    """Top bar text sits above the wheel which sits above the focus row
    which sits above the in/out lines which sit above the footer.
    Tests intent (relative y), not pixel-perfect coordinates."""
    render(mock, State(in_buf="HI", out_buf="UV"))
    by_s = {c.s: c for c in mock.texts()}
    tag_y = by_s["[ENC]"].y
    wheel_y = by_s["A"].y  # any wheel glyph
    focus_y = next(c for c in mock.texts() if c.scale >= 2).y
    in_y = by_s["in: HI"].y
    out_y = by_s["out: UV"].y
    footer_y = by_s["A:next  B:add  PWR:mode"].y
    assert tag_y < wheel_y < focus_y < in_y < out_y < footer_y


def test_render_starts_with_fill(mock: DisplayMock):
    render(mock, State())
    # First call must clear the frame so stale pixels don't bleed through.
    assert mock.calls[0].__class__.__name__ == "FillCall"


def test_caret_x_differs_between_indices(mock: DisplayMock):
    m1 = DisplayMock()
    m2 = DisplayMock()
    render(m1, State(wheel_idx=0))
    render(m2, State(wheel_idx=25))
    x0 = next(r for r in m1.rects() if r.fill).x
    x25 = next(r for r in m2.rects() if r.fill).x
    assert x0 < x25


def test_text_call_default_scale_is_one(mock: DisplayMock):
    # Sanity: the protocol/mock default scale is 1.
    mock.text("X", 0, 0, 1)
    call: TextCall = mock.texts()[0]
    assert call.scale == 1
