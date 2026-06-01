"""Tests for Phase 1 main.py boot wiring (issue #10).

main.py is MicroPython-device-only and cannot be imported on host, so
these tests verify the surrounding collaborators: battery-pct storage on
State, the battery field rendered by screen.render, and a loop harness
that exercises the same dispatch logic as _run_loop using pure Python
stubs for all hardware dependencies.
"""

from __future__ import annotations

import ast
import os

import pytest

from encoder.rot13 import Rot13Cipher
from ui.app import App
from ui.buttons import ButtonFSM
from ui.display_mock import DisplayMock
from ui.events import Button, ButtonEvent, Edge
from ui.screen import render
from ui.state import State

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MAIN_PATH = os.path.join(_REPO, "src", "main.py")


# ---------------------------------------------------------------------------
# main.py entry-point guard (issue #48)
# ---------------------------------------------------------------------------


def test_main_uses_name_guard():
    """main() must only be called under ``if __name__ == "__main__"`` so that
    ``import main`` from the smoke test doesn't enter the infinite loop."""
    with open(_MAIN_PATH) as f:
        source = f.read()
    tree = ast.parse(source)

    # Only inspect direct module-level statements (not nested nodes).
    for node in tree.body:
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "main"
        ):
            pytest.fail(
                "main() is called unconditionally at module level; "
                "wrap it in `if __name__ == '__main__':` to fix the smoke-test hang"
            )


def test_main_name_guard_present_in_source():
    """The source must contain the ``if __name__`` guard string."""
    with open(_MAIN_PATH) as f:
        source = f.read()
    assert '__name__ == "__main__"' in source or "__name__ == '__main__'" in source


# ---------------------------------------------------------------------------
# State.battery_pct
# ---------------------------------------------------------------------------


def test_state_battery_pct_default_is_question_mark():
    s = State()
    assert s.battery_pct == "?"


def test_state_battery_pct_can_be_set():
    s = State()
    s.battery_pct = "78"
    assert s.battery_pct == "78"


# ---------------------------------------------------------------------------
# Battery indicator in render output
# ---------------------------------------------------------------------------


def test_render_shows_battery_pct():
    mock = DisplayMock()
    s = State()
    s.battery_pct = "85"
    render(mock, s)
    batt_calls = [c for c in mock.texts() if "B:" in c.s and "%" in c.s]
    assert batt_calls, "expected a battery indicator in the rendered top bar"
    assert "85" in batt_calls[0].s


def test_render_shows_unknown_battery_by_default():
    mock = DisplayMock()
    render(mock, State())
    batt_calls = [c for c in mock.texts() if "B:" in c.s and "%" in c.s]
    assert batt_calls
    assert "?" in batt_calls[0].s


def test_render_battery_in_top_bar():
    """Battery text must share the same y-coordinate as the mode tag."""
    mock = DisplayMock()
    render(mock, State())
    mode_y = next(c for c in mock.texts() if c.s.startswith("[")).y
    batt_calls = [c for c in mock.texts() if "B:" in c.s and "%" in c.s]
    assert batt_calls
    assert batt_calls[0].y == mode_y


# ---------------------------------------------------------------------------
# Loop-logic harness: exercise _run_loop dispatch with stub hardware
# ---------------------------------------------------------------------------


class _StubAxp:
    """Delivers a fixed sequence of ButtonEvents then an empty list."""

    def __init__(self, events: list[ButtonEvent]) -> None:
        self._events = list(events)

    def poll(self) -> list[ButtonEvent]:
        if self._events:
            return [self._events.pop(0)]
        return []


class _StubPin:
    """Simulates an active-low GPIO pin."""

    def __init__(self, initial: int = 1) -> None:
        self._v = initial

    def value(self) -> int:
        return self._v

    def press(self) -> None:
        self._v = 0

    def release(self) -> None:
        self._v = 1


def _make_loop_stubs(btn_a_val: int = 1) -> tuple[App, ButtonFSM, _StubAxp, _StubPin, _StubPin]:
    """Return a minimal set of stubs wired identically to _run_loop."""
    state = State()
    app = App(state, {"rot13": Rot13Cipher()})
    clock = [0]
    fsm = ButtonFSM(lambda: clock[0])
    axp = _StubAxp([])
    pin_a = _StubPin(btn_a_val)
    pin_b = _StubPin(1)
    return app, fsm, axp, pin_a, pin_b


def _tick(
    app: App,
    fsm: ButtonFSM,
    axp: _StubAxp,
    pin_a: _StubPin,
    pin_b: _StubPin,
    prev_a: list[int],
    prev_b: list[int],
) -> bool:
    """One iteration of the _run_loop dispatch logic (no sleep, no time)."""
    dirty = False

    cur_a = pin_a.value()
    cur_b = pin_b.value()
    if cur_a != prev_a[0]:
        fsm.feed(Button.A, Edge.PRESS if cur_a == 0 else Edge.RELEASE)
        prev_a[0] = cur_a
    if cur_b != prev_b[0]:
        fsm.feed(Button.B, Edge.PRESS if cur_b == 0 else Edge.RELEASE)
        prev_b[0] = cur_b

    for event in fsm.drain():
        if app.handle(event):
            dirty = True

    for event in axp.poll():
        if app.handle(event):
            dirty = True

    return dirty


def test_gpio_btn_b_press_decrements_wheel():
    # BTN_B now scrolls left (decrement).
    app, fsm, axp, pin_a, pin_b = _make_loop_stubs()
    prev_a = [pin_a.value()]
    prev_b = [pin_b.value()]

    app.state.wheel_idx = 5
    pin_b.press()
    _tick(app, fsm, axp, pin_a, pin_b, prev_a, prev_b)
    pin_b.release()
    _tick(app, fsm, axp, pin_a, pin_b, prev_a, prev_b)

    assert app.state.wheel_idx == 4


def test_axp_pwr_short_scrolls_forward():
    # PWR short tap now scrolls right (increment).
    app, fsm, axp, pin_a, pin_b = _make_loop_stubs()
    axp._events = [ButtonEvent.PWR_SHORT]
    prev_a = [pin_a.value()]
    prev_b = [pin_b.value()]

    app.state.wheel_idx = 3
    _tick(app, fsm, axp, pin_a, pin_b, prev_a, prev_b)

    assert app.state.wheel_idx == 4
    assert app.state.in_buf == ""


def test_axp_pwr_long_is_unhandled():
    # PWR_LONG is no longer handled by App (hardware AXP shuts down instead).
    app, fsm, axp, pin_a, pin_b = _make_loop_stubs()
    axp._events = [ButtonEvent.PWR_LONG]
    prev_a = [pin_a.value()]
    prev_b = [pin_b.value()]

    assert app.state.mode == "ENC"
    _tick(app, fsm, axp, pin_a, pin_b, prev_a, prev_b)
    assert app.state.mode == "ENC"  # unchanged


def test_dirty_flag_set_on_state_change():
    app, fsm, axp, pin_a, pin_b = _make_loop_stubs()
    axp._events = [ButtonEvent.PWR_SHORT]
    prev_a = [pin_a.value()]
    prev_b = [pin_b.value()]

    dirty = _tick(app, fsm, axp, pin_a, pin_b, prev_a, prev_b)
    assert dirty is True


def test_dirty_flag_false_with_no_events():
    app, fsm, axp, pin_a, pin_b = _make_loop_stubs()
    prev_a = [pin_a.value()]
    prev_b = [pin_b.value()]

    dirty = _tick(app, fsm, axp, pin_a, pin_b, prev_a, prev_b)
    assert dirty is False


# ---------------------------------------------------------------------------
# _read_battery ADC calculation logic (pure-Python re-implementation)
# ---------------------------------------------------------------------------


def _calc_battery_pct(raw_hi: int, raw_lo: int) -> str:
    """Mirror of _read_battery arithmetic in main.py."""
    vbat_mv = ((raw_hi << 4) | (raw_lo & 0x0F)) * 1.1
    pct = int((vbat_mv - 3300) / (4200 - 3300) * 100)
    return str(max(0, min(100, pct)))


def test_battery_full_charge_returns_near_100():
    # 4200 mV / 1.1 ≈ 3818 raw; truncation means we land at 99-100 %.
    raw_int = int(4200 / 1.1)
    hi = (raw_int >> 4) & 0xFF
    lo = raw_int & 0x0F
    pct = int(_calc_battery_pct(hi, lo))
    assert pct >= 99


def test_battery_empty_returns_0():
    # vbat = 3300 mV / 1.1 = 3000 → raw = 3000
    # hi = 3000 >> 4 = 187, lo = 3000 & 0x0F = 8
    raw = 3300 / 1.1
    raw_int = int(raw)
    hi = (raw_int >> 4) & 0xFF
    lo = raw_int & 0x0F
    assert _calc_battery_pct(hi, lo) == "0"


def test_battery_midpoint_is_near_50():
    # vbat = 3750 mV / 1.1 ≈ 3409 → pct ≈ 50
    raw = 3750 / 1.1
    raw_int = int(raw)
    hi = (raw_int >> 4) & 0xFF
    lo = raw_int & 0x0F
    pct = int(_calc_battery_pct(hi, lo))
    assert 45 <= pct <= 55


def test_battery_below_min_clamps_to_0():
    # Deeply discharged: vbat = 2800 mV / 1.1 ≈ 2545 raw
    raw_int = int(2800 / 1.1)
    hi = (raw_int >> 4) & 0xFF
    lo = raw_int & 0x0F
    assert _calc_battery_pct(hi, lo) == "0"


def test_battery_above_max_clamps_to_100():
    # Overcharge scenario: vbat = 4500 mV / 1.1 ≈ 4090 raw
    raw_int = int(4500 / 1.1)
    hi = (raw_int >> 4) & 0xFF
    lo = raw_int & 0x0F
    assert _calc_battery_pct(hi, lo) == "100"


# ---------------------------------------------------------------------------
# _axp_power_off signature (issue #76)
# ---------------------------------------------------------------------------


def test_axp_power_off_takes_no_arguments():
    """_axp_power_off must accept zero arguments — axp_bus removed per issue #76."""
    with open(_MAIN_PATH) as f:
        source = f.read()
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_axp_power_off":
            args = node.args
            total_args = len(args.args) + len(args.posonlyargs) + len(args.kwonlyargs)
            assert total_args == 0, (
                f"_axp_power_off must take 0 args, found {total_args}: "
                f"{[a.arg for a in args.args]}"
            )
            return
    pytest.fail("_axp_power_off not found in main.py")


def test_axp_power_off_not_called_with_axp_bus_arg():
    """_run_loop must call _axp_power_off() with no args (not passing axp_bus)."""
    with open(_MAIN_PATH) as f:
        source = f.read()
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_axp_power_off"
        ):
            assert node.args == [] and node.keywords == [], (
                "_axp_power_off() must be called with no arguments in _run_loop"
            )
    # No assertion needed if no call site found — the signature test covers existence.


def test_axp_bus_constants_removed():
    """The old _AXP_ADDR / _REG_AXP_POWEROFF / _AXP_POWEROFF_BIT constants must be gone."""
    with open(_MAIN_PATH) as f:
        source = f.read()
    for name in ("_AXP_ADDR", "_REG_AXP_POWEROFF", "_AXP_POWEROFF_BIT"):
        assert name not in source, f"old constant {name!r} should be removed from main.py"
