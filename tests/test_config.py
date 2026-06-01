"""Tests for ui.config — config file loading and accessor helpers."""

import json
import os
import tempfile

from ui.buttons import BTN_B_REPEAT_DELAY_MS, BTN_B_SCROLL_MS
from ui.config import btn_b_repeat_delay_ms, btn_b_scroll_ms, load_config


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
