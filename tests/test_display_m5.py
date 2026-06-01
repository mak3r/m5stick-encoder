"""Structural tests for ``src/ui/display_m5.py``.

``display_m5.py`` imports MicroPython builtins (``M5``) and cannot be imported
on the host.  These tests verify its structure by reading and parsing the source
file, and confirm that the linter exclusion is present in ``pyproject.toml``.
"""

import ast
import os
import re

import pytest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MODULE_PATH = os.path.join(_REPO, "src", "ui", "display_m5.py")
_PYPROJECT_PATH = os.path.join(_REPO, "pyproject.toml")


@pytest.fixture(scope="module")
def source() -> str:
    with open(_MODULE_PATH) as f:
        return f.read()


@pytest.fixture(scope="module")
def tree(source) -> ast.Module:
    return ast.parse(source)


# ---------------------------------------------------------------------------
# Linter exclusion

def test_pyproject_excludes_display_m5():
    """``display_m5.py`` must be in ``extend-exclude`` so ruff skips it."""
    with open(_PYPROJECT_PATH) as f:
        content = f.read()
    assert "display_m5.py" in content, (
        "display_m5.py must appear in [tool.ruff] extend-exclude in pyproject.toml"
    )


# ---------------------------------------------------------------------------
# UIFlow 2 API: M5 import present, st7789/machine/framebuf must NOT appear


def test_imports_M5(source):
    assert "import M5" in source


def test_does_not_import_st7789(source):
    assert "import st7789" not in source, "UIFlow 2 has no st7789 module"


def test_does_not_import_machine(source):
    assert "import machine" not in source, "SPI wiring is handled by M5.begin()"


def test_does_not_import_framebuf(source):
    assert "import framebuf" not in source, "pixel-doubling via framebuf is replaced by M5.Lcd"


# ---------------------------------------------------------------------------
# M5.Lcd API usage


def test_uses_M5_Lcd_fillScreen(source):
    assert "M5.Lcd.fillScreen(" in source


def test_uses_M5_Lcd_fillRect(source):
    assert "M5.Lcd.fillRect(" in source


def test_uses_M5_Lcd_drawRect(source):
    assert "M5.Lcd.drawRect(" in source


def test_uses_M5_Lcd_drawString(source):
    assert "M5.Lcd.drawString(" in source


def test_uses_M5_Lcd_setTextSize(source):
    assert "M5.Lcd.setTextSize(" in source


def test_uses_M5_Lcd_setTextColor(source):
    assert "M5.Lcd.setTextColor(" in source


# ---------------------------------------------------------------------------
# Color palette


def _dict_const(tree: ast.Module, name: str) -> dict | None:
    """Return the dict literal value of a module-level assignment, or None."""
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name
            and isinstance(node.value, ast.Dict)
        ):
            return {
                k.value: v.value
                for k, v in zip(node.value.keys, node.value.values, strict=False)
                if isinstance(k, ast.Constant) and isinstance(v, ast.Constant)
            }
    return None


def test_palette_black(tree):
    p = _dict_const(tree, "_PALETTE")
    assert p is not None, "_PALETTE dict not found"
    assert p.get(0) == 0x000000, "color 0 must be black (0x000000)"


def test_palette_white(tree):
    p = _dict_const(tree, "_PALETTE")
    assert p is not None
    assert p.get(1) == 0xFFFFFF, "color 1 must be white (0xFFFFFF)"


def test_palette_amber(tree):
    p = _dict_const(tree, "_PALETTE")
    assert p is not None
    assert p.get(2) == 0xFFB000, "color 2 must be amber (0xFFB000)"


def test_palette_cursor_green(tree):
    p = _dict_const(tree, "_PALETTE")
    assert p is not None
    # UIFlow 2 M5.Lcd uses 24-bit RGB888; 0x00FF00 = pure green on device.
    # The former RGB565 value 0x07E0 was interpreted as blue (B=0xE0=224).
    assert p.get(3) == 0x00FF00, "color 3 must be bright green (0x00FF00)"


# ---------------------------------------------------------------------------
# Class-level width/height attributes


def _class_attr(source: str, cls: str, attr: str) -> int | None:
    """Extract a simple integer class attribute ``cls.attr = N``."""
    pattern = rf"class {cls}.*?(?=\nclass |\Z)"
    body_match = re.search(pattern, source, re.DOTALL)
    if body_match is None:
        return None
    body = body_match.group(0)
    m = re.search(rf"{attr}\s*:\s*int\s*=\s*(\d+)", body)
    if m:
        return int(m.group(1))
    m = re.search(rf"{attr}\s*=\s*(\d+)", body)
    return int(m.group(1)) if m else None


def test_m5display_width_is_240(source):
    assert _class_attr(source, "M5Display", "width") == 240


def test_m5display_height_is_135(source):
    assert _class_attr(source, "M5Display", "height") == 135


# ---------------------------------------------------------------------------
# Protocol surface: required methods exist


@pytest.mark.parametrize("method", ["fill", "text", "rect", "show"])
def test_m5display_has_method(source, method):
    assert f"def {method}(" in source, f"M5Display must define {method}()"


# ---------------------------------------------------------------------------
# text() method handles scale parameter


def test_text_method_has_scale_parameter(source):
    assert "scale: int = 1" in source or "scale=1" in source


def test_show_is_noop(source):
    """show() must be present and M5.Lcd needs no explicit flush."""
    assert "def show(" in source
    # The method exists; the body should be a no-op (just pass or a comment).
    assert "pass" in source


def test_init_calls_setRotation(source):
    """__init__ must call M5.Lcd.setRotation() to fix landscape orientation."""
    assert "M5.Lcd.setRotation(" in source


def test_rotation_value_is_1_or_3(source):
    """Landscape rotation must be 1 or 3 for 240×135 on M5StickC PLUS."""
    import re
    m = re.search(r"M5\.Lcd\.setRotation\((\d+)\)", source)
    assert m is not None, "M5.Lcd.setRotation(N) call not found"
    assert int(m.group(1)) in (1, 3), "rotation value must be 1 or 3 for landscape"


# ---------------------------------------------------------------------------
# Board-check guard (issue #58 — GPIO 78 / board misidentification)


def test_check_board_function_exists(source):
    """_check_board() must be defined to validate M5.getBoard() at boot."""
    assert "def _check_board(" in source


def test_check_board_calls_getBoard(source):
    """_check_board() must call M5.getBoard() to detect board-type mismatch."""
    assert "M5.getBoard()" in source


def test_check_board_references_M5StickCPlus(source):
    """_check_board() must compare against M5.BOARD.M5StickCPlus."""
    assert "M5StickCPlus" in source


def test_check_board_prints_warning(source):
    """_check_board() must print a WARNING when the board does not match."""
    assert "WARNING" in source


def test_init_calls_check_board(source):
    """M5Display.__init__ must call _check_board() after M5.begin()."""
    # Locate __init__ body and verify the call is present.
    m = re.search(r"def __init__\(.*?\).*?(?=\n    def |\Z)", source, re.DOTALL)
    assert m is not None, "__init__ not found"
    assert "_check_board()" in m.group(0), "__init__ must call _check_board()"


def test_check_board_called_after_begin(source):
    """_check_board() must appear after M5.begin() in __init__, not before."""
    begin_pos = source.find("M5.begin()")
    check_pos = source.find("_check_board()")
    assert begin_pos != -1, "M5.begin() not found"
    assert check_pos != -1, "_check_board() call not found"
    assert check_pos > begin_pos, "_check_board() must be called after M5.begin()"


def test_check_board_tolerates_missing_attribute(source):
    """_check_board() must handle AttributeError if BOARD constants are absent."""
    assert "AttributeError" in source


def test_expected_board_constant_defined(source):
    """_EXPECTED_BOARD module constant must be defined."""
    assert "_EXPECTED_BOARD" in source


# ---------------------------------------------------------------------------
# sleep() / wake() use UIFlow 2.4.5 powerSave API, not setBrightness or sleep/wakeup


def test_sleep_calls_powerSaveOn(source):
    """sleep() must call M5.Lcd.powerSaveOn() — the actual UIFlow 2.4.5 display-sleep API."""
    assert "M5.Lcd.powerSaveOn()" in source, "sleep() must use M5.Lcd.powerSaveOn()"


def test_wake_calls_powerSaveOff(source):
    """wake() must call M5.Lcd.powerSaveOff() to restore the panel."""
    assert "M5.Lcd.powerSaveOff()" in source, "wake() must use M5.Lcd.powerSaveOff()"


def test_sleep_does_not_use_setBrightness(source):
    """setBrightness is not reliable on AXP192 LDO3 — must not be used."""
    assert "setBrightness" not in source, "setBrightness must be replaced by M5.Lcd.powerSaveOn/Off"


def test_sleep_does_not_use_M5_Lcd_sleep(source):
    """M5.Lcd.sleep() does not exist on UIFlow 2.4.5 — must not be called."""
    assert "M5.Lcd.sleep()" not in source, "M5.Lcd.sleep() causes AttributeError on device"


def test_wake_does_not_use_M5_Lcd_wakeup(source):
    """M5.Lcd.wakeup() does not exist on UIFlow 2.4.5 — must not be called."""
    assert "M5.Lcd.wakeup()" not in source, "M5.Lcd.wakeup() causes AttributeError on device"
