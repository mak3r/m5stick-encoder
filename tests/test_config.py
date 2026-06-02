"""Tests for ui.config — config file loading and accessor helpers."""

import json
import os
import tempfile

from ui.buttons import BTN_B_REPEAT_DELAY_MS, BTN_B_SCROLL_MS, ButtonFSM
from ui.config import btn_b_repeat_delay_ms, btn_b_scroll_ms, load_config
from ui.events import Button, ButtonEvent, Edge

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONFIG_JSON = os.path.join(_REPO, "config.json")
_CONFIG_EXAMPLE = os.path.join(_REPO, "config.json.example")


class _Clock:
    def __init__(self) -> None:
        self.t = 0

    def __call__(self) -> int:
        return self.t

    def advance(self, ms: int) -> None:
        self.t += ms


def test_load_config_returns_empty_dict_when_file_missing():
    assert load_config("/nonexistent/path/config.json") == {}


def test_load_config_returns_empty_dict_on_invalid_json():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("not valid json {{")
        path = f.name
    try:
        assert load_config(path) == {}
    finally:
        os.unlink(path)


def test_load_config_reads_values():
    data = {"btn_b_scroll_ms": 150, "btn_b_repeat_delay_ms": 400}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        path = f.name
    try:
        cfg = load_config(path)
        assert cfg["btn_b_scroll_ms"] == 150
        assert cfg["btn_b_repeat_delay_ms"] == 400
    finally:
        os.unlink(path)


def test_btn_b_scroll_ms_returns_default_on_empty_config():
    assert btn_b_scroll_ms({}) == BTN_B_SCROLL_MS


def test_btn_b_repeat_delay_ms_returns_default_on_empty_config():
    assert btn_b_repeat_delay_ms({}) == BTN_B_REPEAT_DELAY_MS


def test_btn_b_scroll_ms_uses_config_value():
    assert btn_b_scroll_ms({"btn_b_scroll_ms": 150}) == 150


def test_btn_b_repeat_delay_ms_uses_config_value():
    assert btn_b_repeat_delay_ms({"btn_b_repeat_delay_ms": 400}) == 400


# ---------------------------------------------------------------------------
# Integration: load_config → ButtonFSM observable timing
# ---------------------------------------------------------------------------


def _write_config(data: dict) -> str:
    """Write data to a temp JSON file; caller is responsible for unlinking."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        return f.name


def test_config_btn_b_scroll_ms_reaches_fsm():
    """Custom btn_b_scroll_ms from config.json is used by ButtonFSM."""
    path = _write_config({"btn_b_scroll_ms": 50, "btn_b_repeat_delay_ms": 100})
    try:
        cfg = load_config(path)
        clock = _Clock()
        fsm = ButtonFSM(
            clock,
            btn_b_repeat_delay_ms=btn_b_repeat_delay_ms(cfg),
            btn_b_scroll_ms=btn_b_scroll_ms(cfg),
        )
        fsm.feed(Button.B, Edge.PRESS)
        fsm.drain()  # consume BTN_B_PRESS
        clock.advance(100)
        fsm.drain()  # first repeat
        # With scroll_ms=50, advancing 49 ms should not yet fire.
        clock.advance(49)
        assert fsm.drain() == []
        # One more ms brings us to 50 ms — repeat fires.
        clock.advance(1)
        assert fsm.drain() == [ButtonEvent.BTN_B_LONG]
    finally:
        os.unlink(path)


def test_config_btn_b_repeat_delay_ms_reaches_fsm():
    """Custom btn_b_repeat_delay_ms from config.json is used by ButtonFSM."""
    path = _write_config({"btn_b_repeat_delay_ms": 200, "btn_b_scroll_ms": 300})
    try:
        cfg = load_config(path)
        clock = _Clock()
        fsm = ButtonFSM(
            clock,
            btn_b_repeat_delay_ms=btn_b_repeat_delay_ms(cfg),
            btn_b_scroll_ms=btn_b_scroll_ms(cfg),
        )
        fsm.feed(Button.B, Edge.PRESS)
        fsm.drain()  # consume BTN_B_PRESS
        # Advance to just before the custom repeat delay.
        clock.advance(199)
        assert fsm.drain() == []
        # At 200 ms the first repeat fires.
        clock.advance(1)
        assert fsm.drain() == [ButtonEvent.BTN_B_LONG]
    finally:
        os.unlink(path)


def test_absent_config_produces_default_timing():
    """load_config() on a missing file falls back to compiled-in defaults."""
    cfg = load_config("/nonexistent/path/config.json")
    assert btn_b_scroll_ms(cfg) == BTN_B_SCROLL_MS
    assert btn_b_repeat_delay_ms(cfg) == BTN_B_REPEAT_DELAY_MS
    # Verify defaults reach FSM without error.
    clock = _Clock()
    fsm = ButtonFSM(
        clock,
        btn_b_repeat_delay_ms=btn_b_repeat_delay_ms(cfg),
        btn_b_scroll_ms=btn_b_scroll_ms(cfg),
    )
    fsm.feed(Button.B, Edge.PRESS)
    # Default repeat delay is 500 ms; at 499 ms no repeat should fire.
    clock.advance(499)
    assert fsm.drain() == [ButtonEvent.BTN_B_PRESS]
    clock.advance(1)
    assert fsm.drain() == [ButtonEvent.BTN_B_LONG]


# ---------------------------------------------------------------------------
# Repo config files must be valid JSON (issue #82)
# ---------------------------------------------------------------------------


def test_repo_config_json_is_valid():
    """config.json at repo root must be valid JSON (quoted keys)."""
    with open(_CONFIG_JSON) as f:
        data = json.load(f)
    assert isinstance(data, dict)


def test_repo_config_json_example_exists_and_is_valid():
    """config.json.example must exist and contain valid JSON."""
    assert os.path.exists(_CONFIG_EXAMPLE), "config.json.example is missing from repo root"
    with open(_CONFIG_EXAMPLE) as f:
        data = json.load(f)
    assert isinstance(data, dict)


# ---------------------------------------------------------------------------
# screen.configure() integration
# ---------------------------------------------------------------------------


def test_configure_empty_cfg_keeps_defaults():
    import ui.screen as screen
    before = {
        "wheel_scale": screen.WHEEL_SCALE,
        "wheel_center_scale": screen.WHEEL_CENTER_SCALE,
        "wheel_letter_gap": screen.WHEEL_LETTER_GAP,
        "wheel_center_extra": screen.WHEEL_CENTER_EXTRA,
        "in_scale": screen.IN_SCALE,
        "out_scale": screen.OUT_SCALE,
        "wheel_y": screen.WHEEL_Y,
        "cipher_row_y": screen.CIPHER_ROW_Y,
        "in_y": screen.IN_Y,
        "out_y": screen.OUT_Y,
        "footer_y": screen.FOOTER_Y,
    }
    screen.configure({})
    assert before["wheel_scale"] == screen.WHEEL_SCALE
    assert before["cipher_row_y"] == screen.CIPHER_ROW_Y
    assert before["in_scale"] == screen.IN_SCALE
    assert before["out_scale"] == screen.OUT_SCALE


def test_configure_overrides_take_effect():
    import ui.screen as screen
    saved = screen.WHEEL_SCALE, screen.WHEEL_LETTER_GAP, screen.CIPHER_ROW_Y
    try:
        screen.configure({"wheel_scale": 1, "wheel_letter_gap": 2, "cipher_row_y": 40})
        assert screen.WHEEL_SCALE == 1
        assert screen.WHEEL_LETTER_GAP == 2
        assert screen.CIPHER_ROW_Y == 40
    finally:
        screen.WHEEL_SCALE, screen.WHEEL_LETTER_GAP, screen.CIPHER_ROW_Y = saved


def test_config_example_contains_wheel_keys():
    with open(_CONFIG_EXAMPLE) as f:
        data = json.load(f)
    for key in ("wheel_font", "wheel_center_font",
                "wheel_scale", "wheel_center_scale", "wheel_letter_gap",
                "wheel_center_extra", "wheel_center_y_offset",
                "in_font", "in_scale", "out_font", "out_scale",
                "wheel_y", "cipher_row_y", "in_y", "out_y", "footer_y"):
        assert key in data, f"config.json.example missing key: {key}"


def test_load_config_returns_empty_dict_on_unquoted_keys():
    """Files with unquoted JSON keys (a common mistake) fall back to {}."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("{ btn_b_scroll_ms: 300 }")
        path = f.name
    try:
        assert load_config(path) == {}
    finally:
        os.unlink(path)
