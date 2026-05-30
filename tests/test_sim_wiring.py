"""Tests for ``tools/sim.py``'s pure-logic adapter.

These verify the keyboard -> FSM -> App pipeline without opening a window.
The tkinter pieces (canvas drawing, mainloop) are exercised manually.
"""

import os
import sys

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOOLS = os.path.join(_REPO_ROOT, "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

from sim import KeyboardAdapter  # noqa: E402

from encoder.rot13 import Rot13Cipher  # noqa: E402
from ui.app import App  # noqa: E402
from ui.buttons import DOUBLE_WINDOW_MS, LONG_PRESS_MS, ButtonFSM  # noqa: E402
from ui.state import State  # noqa: E402


class FakeClock:
    def __init__(self, start: int = 0) -> None:
        self.t = start

    def __call__(self) -> int:
        return self.t

    def advance(self, ms: int) -> None:
        self.t += ms


@pytest.fixture
def stack():
    clock = FakeClock()
    state = State()
    app = App(state, {"rot13": Rot13Cipher()})
    fsm = ButtonFSM(clock)
    renders = []
    adapter = KeyboardAdapter(app, fsm, lambda: renders.append(state.wheel_idx))
    return adapter, app, fsm, clock, renders


def test_btn_b_key_advances_wheel(stack):
    adapter, app, _fsm, _clock, renders = stack
    adapter.on_key_press("b")
    adapter.on_key_release("b")
    assert app.state.wheel_idx == 1
    assert renders == [1]


def test_bracket_keys_are_aliases(stack):
    adapter, app, _fsm, _clock, _renders = stack
    adapter.on_key_press("bracketright")
    adapter.on_key_release("bracketright")
    adapter.on_key_press("bracketleft")
    adapter.on_key_release("bracketleft")
    # +1 then -1 lands back on 0.
    assert app.state.wheel_idx == 0


def test_unknown_key_is_ignored(stack):
    adapter, app, _fsm, _clock, renders = stack
    assert adapter.on_key_press("x") is False
    assert adapter.on_key_release("x") is False
    assert app.state.wheel_idx == 0
    assert renders == []


def test_held_key_does_not_repeat(stack):
    """Tkinter auto-repeat fires KeyPress over and over; the adapter must
    only emit one logical PRESS until the matching RELEASE arrives."""
    adapter, app, _fsm, clock, _renders = stack
    adapter.on_key_press("b")
    # Simulate tkinter auto-repeat: many press events while still held.
    adapter.on_key_press("b")
    clock.advance(100)
    adapter.on_key_press("b")
    assert app.state.wheel_idx == 1
    adapter.on_key_release("b")
    clock.advance(50)
    adapter.on_key_press("b")
    assert app.state.wheel_idx == 2


def test_space_short_commits_letter_through_fsm(stack):
    adapter, app, _fsm, clock, _renders = stack
    # Advance wheel to A->A; default state has wheel_idx=0, mode=ENC.
    adapter.on_key_press("space")
    clock.advance(50)
    adapter.on_key_release("space")
    # Short press resolves on the next tick after the double window expires.
    clock.advance(DOUBLE_WINDOW_MS + 1)
    adapter.tick()
    assert app.state.in_buf == "A"
    assert app.state.out_buf == "N"


def test_space_long_press_toggles_mode(stack):
    adapter, app, _fsm, clock, _renders = stack
    adapter.on_key_press("space")
    clock.advance(LONG_PRESS_MS)
    # Tick eagerly emits PWR_LONG even without release.
    adapter.tick()
    assert app.state.mode == "DEC"
    adapter.on_key_release("space")
    # No spurious extra event on release.
    clock.advance(DOUBLE_WINDOW_MS + 1)
    adapter.tick()
    assert app.state.mode == "DEC"
