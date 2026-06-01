"""Structural tests for ``src/ui/display_m5.py``.

``display_m5.py`` imports MicroPython builtins (``machine``, ``st7789``,
``framebuf``) and cannot be imported on the host.  These tests verify its
structure and configuration values by reading and parsing the source file,
and confirm that the linter exclusion is present in ``pyproject.toml``.
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
# MicroPython-only imports present


def test_imports_machine(source):
    assert "import machine" in source


def test_imports_st7789(source):
    assert "import st7789" in source


def test_imports_framebuf(source):
    assert "import framebuf" in source


# ---------------------------------------------------------------------------
# Panel geometry constants


def _const(tree: ast.Module, name: str) -> int | None:
    """Return the integer value of a module-level assignment, or None."""
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name
            and isinstance(node.value, ast.Constant)
        ):
            return node.value.value
    return None


def test_col_offset_is_40(tree):
    assert _const(tree, "_COL_OFFSET") == 40, "Column offset must be 40"


def test_row_offset_is_53(tree):
    assert _const(tree, "_ROW_OFFSET") == 53, "Row offset must be 53"


def test_logical_width_is_240(tree):
    # width is a class attribute, not a module-level constant; check source.
    # Accept either a class-level annotation or a simple assignment.
    assert _const(tree, "_PHYS_H") == 240, "_PHYS_H (landscape width) must be 240"


def test_logical_height_is_135(tree):
    assert _const(tree, "_PHYS_W") == 135, "_PHYS_W (landscape height) must be 135"


def test_glyph_dimensions_are_8x8(tree):
    assert _const(tree, "_GLYPH_W") == 8
    assert _const(tree, "_GLYPH_H") == 8


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
# Scale handling: pixel-doubling branch exists for scale > 1


def test_text_method_has_scale_parameter(source):
    # Signature: def text(self, s, x, y, color, scale=1)
    assert "scale: int = 1" in source or "scale=1" in source


def test_pixel_doubling_uses_fill_rect(source):
    """The scale > 1 path must use fill_rect to draw scaled pixels."""
    assert "fill_rect" in source, (
        "Pixel-doubling for scale>1 must use fill_rect"
    )


def test_scale_1_fast_path_exists(source):
    """A fast path that skips pixel-doubling when scale == 1."""
    assert "scale == 1" in source
