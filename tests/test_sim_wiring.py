"""Tests for ``tools/sim.py``'s pure-logic adapter.

These verify the keyboard -> FSM -> App pipeline without opening a window.
The tkinter pieces (canvas drawing, mainloop) are exercised manually.
"""

import os
import sys
from collections.abc import Callable

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOOLS = os.path.join(_REPO_ROOT, "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

from sim import AUTO_REPEAT_GUARD_MS, COLOR_MAP, KeyboardAdapter  # noqa: E402

from encoder.rot13 import Rot13Cipher  # noqa: E402
from ui.app import App  # noqa: E402
from ui.buttons import DOUBLE_WINDOW_MS, LONG_PRESS_MS, ButtonFSM  # noqa: E402
from ui.events import ButtonEvent  # noqa: E402
from ui.state import State  # noqa: E402

# ---------------------------------------------------------------------------
# COLOR_MAP tests — ensure cursor color is present and visually distinct


def test_color_map_has_cursor_entry():
    assert 3 in COLOR_MAP, "COLOR_MAP must define color 3 (cursor green)"


def test_color_map_cursor_is_green():
    # Cursor must be a visibly green hex color (green channel dominant).
    rgb = COLOR_MAP[3].lstrip("#")
    r = int(rgb[0:2], 16)
    g = int(rgb[2:4], 16)
    b = int(rgb[4:6], 16)
    assert g > r and g > b, "cursor color must be green (green channel dominant)"


def test_color_map_cursor_differs_from_fg():
    assert COLOR_MAP[3] != COLOR_MAP[1], "cursor must be distinct from foreground (white)"


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


def test_btn_b_key_decrements_wheel(stack):
    # BTN_B now scrolls left (decrement); starting at 0 wraps to 25.
    adapter, app, _fsm, _clock, renders = stack
    adapter.on_key_press("b")
    adapter.on_key_release("b")
    assert app.state.wheel_idx == 25
    assert renders == [25]


def test_bracket_right_key_is_alias_for_btn_b(stack):
    adapter, app, _fsm, _clock, _renders = stack
    adapter.on_key_press("bracketright")
    adapter.on_key_release("bracketright")
    assert app.state.wheel_idx == 25


def test_bracket_left_key_appends_letter(stack):
    # BTN_A now uses short/double/long timing; the single-press resolves after
    # the double-window expires via a drain() tick.
    adapter, app, _fsm, clock, _renders = stack
    app.state.wheel_idx = 0  # letter A
    adapter.on_key_press("bracketleft")
    clock.advance(50)
    adapter.on_key_release("bracketleft")
    clock.advance(DOUBLE_WINDOW_MS + 1)
    adapter.tick()
    assert app.state.in_buf == "A"
    assert app.state.out_buf == "N"


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
    # Only one decrement (0 → 25).
    assert app.state.wheel_idx == 25
    adapter.on_key_release("b")
    clock.advance(50)
    adapter.on_key_press("b")
    assert app.state.wheel_idx == 24


def test_key_a_appends_letter_through_fsm(stack):
    # BTN_A now has short/double/long timing; single press resolves after the
    # double-window expires.
    adapter, app, _fsm, clock, _renders = stack
    app.state.wheel_idx = 0  # letter A
    adapter.on_key_press("a")
    clock.advance(50)
    adapter.on_key_release("a")
    clock.advance(DOUBLE_WINDOW_MS + 1)
    adapter.tick()
    assert app.state.in_buf == "A"
    assert app.state.out_buf == "N"


def test_space_short_scrolls_forward_through_fsm(stack):
    # PWR short tap now scrolls right (increment).
    adapter, app, _fsm, clock, _renders = stack
    app.state.wheel_idx = 3
    adapter.on_key_press("space")
    clock.advance(50)
    adapter.on_key_release("space")
    # Short press resolves on the next tick after the double window expires.
    clock.advance(DOUBLE_WINDOW_MS + 1)
    adapter.tick()
    assert app.state.wheel_idx == 4
    assert app.state.in_buf == ""


def test_btn_a_long_press_toggles_mode(stack):
    # BTN_A long press now toggles mode; space (PWR) long press is unhandled.
    adapter, app, _fsm, clock, _renders = stack
    adapter.on_key_press("a")
    clock.advance(LONG_PRESS_MS)
    # Tick eagerly emits BTN_A_LONG even without release.
    adapter.tick()
    assert app.state.mode == "DEC"
    adapter.on_key_release("a")
    # No spurious extra event on release.
    clock.advance(DOUBLE_WINDOW_MS + 1)
    adapter.tick()
    assert app.state.mode == "DEC"


# ---------------------------------------------------------------------------
# Auto-repeat guard (issue #27)
#
# When the host OS auto-repeats a held key it interleaves phantom
# KeyRelease/KeyPress pairs ~33 ms apart. The injected scheduler defers the
# RELEASE edge by AUTO_REPEAT_GUARD_MS so a phantom PRESS arriving inside
# the window cancels it.


class FakeScheduler:
    """Synchronous stand-in for ``tk.after`` / ``after_cancel``."""

    def __init__(self) -> None:
        self._next_token = 0
        self._pending: dict[int, Callable[[], None]] = {}

    def schedule(self, ms: int, cb: Callable[[], None]) -> int:
        tok = self._next_token
        self._next_token += 1
        self._pending[tok] = cb
        return tok

    def cancel(self, token: object) -> None:
        self._pending.pop(token, None)  # type: ignore[arg-type]

    def flush(self) -> None:
        """Fire every still-pending callback as if its timer expired."""
        for cb in list(self._pending.values()):
            cb()
        self._pending.clear()

    def pending_count(self) -> int:
        return len(self._pending)


class RecordingApp:
    """Wraps ``App.handle`` so tests can assert which events reached it."""

    def __init__(self, app: App) -> None:
        self._app = app
        self.events: list[ButtonEvent] = []

    @property
    def state(self):
        return self._app.state

    def handle(self, event: ButtonEvent) -> bool:
        self.events.append(event)
        return self._app.handle(event)


def _build_recording_stack(guard_ms: int = AUTO_REPEAT_GUARD_MS):
    clock = FakeClock()
    state = State()
    real_app = App(state, {"rot13": Rot13Cipher()})
    app = RecordingApp(real_app)
    fsm = ButtonFSM(clock)
    sched = FakeScheduler()
    renders: list[int] = []
    adapter = KeyboardAdapter(
        app,
        fsm,
        lambda: renders.append(state.wheel_idx),
        schedule_after=sched.schedule,
        cancel_scheduled=sched.cancel,
        guard_ms=guard_ms,
    )
    return adapter, app, fsm, clock, sched, renders


def test_phantom_autorepeat_does_not_emit_double():
    """PRESS/RELEASE/PRESS/RELEASE all inside the guard window must not
    produce a PWR_DOUBLE -- it's OS auto-repeat, not a real double tap."""
    adapter, app, _fsm, clock, sched, _renders = _build_recording_stack()

    # Phantom auto-repeat cycle: each step within the guard window.
    adapter.on_key_press("space")
    clock.advance(10)
    adapter.on_key_release("space")
    clock.advance(10)
    adapter.on_key_press("space")
    clock.advance(10)
    adapter.on_key_release("space")

    # The release schedules a deferred fire. The second PRESS cancelled the
    # first deferred release, leaving exactly one outstanding.
    assert sched.pending_count() == 1

    # Fire the still-pending deferred release; advance the FSM clock past
    # the deferral so the FSM sees a coherent press-release window.
    clock.advance(AUTO_REPEAT_GUARD_MS)
    sched.flush()

    # No spurious double-press.
    assert ButtonEvent.PWR_DOUBLE not in app.events


def test_space_long_hold_survives_autorepeat():
    """A 1.1 s hold punctuated by 33 ms phantom release/press cycles must
    emit exactly one PWR_LONG and zero PWR_DOUBLEs."""
    adapter, app, _fsm, clock, sched, _renders = _build_recording_stack()

    adapter.on_key_press("space")
    # 33 phantom cycles * ~33 ms ~= 1089 ms of held time.
    for _ in range(33):
        clock.advance(33)
        adapter.on_key_release("space")
        # Phantom PRESS arrives well inside the guard window.
        clock.advance(1)
        adapter.on_key_press("space")
        # Tick periodically so the FSM can fire eager PWR_LONG.
        adapter.tick()
    # The real release.
    clock.advance(5)
    adapter.on_key_release("space")
    clock.advance(AUTO_REPEAT_GUARD_MS)
    sched.flush()
    clock.advance(DOUBLE_WINDOW_MS + 1)
    adapter.tick()

    assert app.events.count(ButtonEvent.PWR_LONG) == 1
    assert ButtonEvent.PWR_DOUBLE not in app.events
    # PWR_LONG is unhandled by App now; mode should remain ENC.
    assert app.state.mode == "ENC"


def test_real_short_tap_still_scrolls_forward():
    """A genuine tap (no auto-repeat) should still produce a PWR_SHORT
    after the guard window + double window have both expired — scrolling right."""
    adapter, app, _fsm, clock, sched, _renders = _build_recording_stack()

    app.state.wheel_idx = 5
    adapter.on_key_press("space")
    clock.advance(20)
    adapter.on_key_release("space")

    # Guard window expires; the deferred release fires for real.
    clock.advance(AUTO_REPEAT_GUARD_MS)
    sched.flush()

    # Double-press window expires; PWR_SHORT resolves at next drain.
    clock.advance(DOUBLE_WINDOW_MS + 1)
    adapter.tick()

    assert ButtonEvent.PWR_SHORT in app.events
    assert app.state.wheel_idx == 6  # incremented
    assert app.state.in_buf == ""


def test_real_double_tap_outside_guard_window():
    """Two real taps ~150 ms apart (well outside the 50 ms guard window
    but inside the 300 ms double-press window) should still produce one
    PWR_DOUBLE."""
    adapter, app, _fsm, clock, sched, _renders = _build_recording_stack()

    # PWR_DOUBLE is unhandled by App; seed a visible state we can probe.
    app.state.wheel_idx = 5

    # First tap.
    adapter.on_key_press("space")
    clock.advance(20)
    adapter.on_key_release("space")
    # Honour the guard window for the first release.
    clock.advance(AUTO_REPEAT_GUARD_MS)
    sched.flush()

    # Gap between the two taps: 150 ms total from the first release fire.
    clock.advance(150 - AUTO_REPEAT_GUARD_MS)

    # Second tap.
    adapter.on_key_press("space")
    clock.advance(20)
    adapter.on_key_release("space")
    clock.advance(AUTO_REPEAT_GUARD_MS)
    sched.flush()

    clock.advance(DOUBLE_WINDOW_MS + 1)
    adapter.tick()

    assert app.events.count(ButtonEvent.PWR_DOUBLE) == 1


def test_btn_b_autorepeat_does_not_double_decrement():
    """BTN_B emits on PRESS only; phantom auto-repeat must not decrement the
    wheel a second time during a single physical hold."""
    adapter, app, _fsm, clock, sched, _renders = _build_recording_stack()

    adapter.on_key_press("b")
    # Phantom auto-repeat cycles.
    for _ in range(5):
        clock.advance(10)
        adapter.on_key_release("b")
        clock.advance(10)
        adapter.on_key_press("b")
    # Real release.
    clock.advance(10)
    adapter.on_key_release("b")
    clock.advance(AUTO_REPEAT_GUARD_MS)
    sched.flush()

    # Exactly one wheel decrement from the single physical press.
    assert app.events.count(ButtonEvent.BTN_B_PRESS) == 1
    assert app.state.wheel_idx == 25  # 0 → 25 (wraps)


def test_existing_immediate_release_behavior_preserved(stack):
    """With no scheduler injected, the adapter behaves exactly as it did
    before #27: RELEASE reaches the FSM immediately, no deferral."""
    adapter, app, _fsm, clock, _renders = stack
    # Space tap now scrolls forward; seed wheel_idx so the change is visible.
    app.state.wheel_idx = 5
    adapter.on_key_press("space")
    clock.advance(20)
    adapter.on_key_release("space")
    # Without a scheduler, no flush() is needed; the FSM should already
    # have the release.
    clock.advance(DOUBLE_WINDOW_MS + 1)
    adapter.tick()
    assert app.state.wheel_idx == 6  # incremented
    assert app.state.in_buf == ""
