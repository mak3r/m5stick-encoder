"""Tests for screen.render_splash via DisplayMock."""

from ui.display_mock import DisplayMock, ShowCall
from ui.screen import ACCENT, FG, render_splash


def test_splash_calls_show_last():
    mock = DisplayMock()
    render_splash(mock)
    assert isinstance(mock.calls[-1], ShowCall)


def test_splash_starts_with_fill():
    mock = DisplayMock()
    render_splash(mock)
    assert mock.calls[0].__class__.__name__ == "FillCall"


def test_splash_contains_title():
    mock = DisplayMock()
    render_splash(mock)
    titles = [c for c in mock.texts() if "SECRET CODE" in c.s]
    assert titles, "expected 'SECRET CODE 1.0' in splash"


def test_splash_title_uses_accent_color():
    mock = DisplayMock()
    render_splash(mock)
    title_call = next(c for c in mock.texts() if "SECRET CODE" in c.s)
    assert title_call.color == ACCENT


def test_splash_title_uses_scale_2():
    mock = DisplayMock()
    render_splash(mock)
    title_call = next(c for c in mock.texts() if "SECRET CODE" in c.s)
    assert title_call.scale == 2


def test_splash_shows_battery_unknown_by_default():
    mock = DisplayMock()
    render_splash(mock)
    batt_calls = [c for c in mock.texts() if "BAT:" in c.s]
    assert batt_calls
    assert "?" in batt_calls[0].s


def test_splash_shows_battery_pct_when_provided():
    mock = DisplayMock()
    render_splash(mock, battery_pct="78")
    batt_calls = [c for c in mock.texts() if "BAT:" in c.s]
    assert batt_calls
    assert "78" in batt_calls[0].s


def test_splash_battery_uses_fg_color():
    mock = DisplayMock()
    render_splash(mock)
    batt_call = next(c for c in mock.texts() if "BAT:" in c.s)
    assert batt_call.color == FG


def test_splash_title_above_battery():
    mock = DisplayMock()
    render_splash(mock)
    title_y = next(c for c in mock.texts() if "SECRET CODE" in c.s).y
    batt_y = next(c for c in mock.texts() if "BAT:" in c.s).y
    assert title_y < batt_y
