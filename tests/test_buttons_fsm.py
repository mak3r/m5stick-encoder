import pytest

from ui.buttons import DEBOUNCE_MS, DOUBLE_WINDOW_MS, LONG_PRESS_MS, ButtonFSM
from ui.events import Button, ButtonEvent, Edge


class FakeClock:
    def __init__(self, start: int = 0):
        self.t = start

    def __call__(self) -> int:
        return self.t

    def advance(self, ms: int) -> None:
        self.t += ms


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def fsm(clock: FakeClock) -> ButtonFSM:
    return ButtonFSM(clock)


# ---------------------------------------------------------------------------
# BTN_B: immediate press, no double/long semantics
# ---------------------------------------------------------------------------

def test_btn_b_press_emits_immediately(fsm: ButtonFSM):
    fsm.feed(Button.B, Edge.PRESS)
    assert fsm.drain() == [ButtonEvent.BTN_B_PRESS]


def test_btn_b_release_emits_nothing(fsm: ButtonFSM):
    fsm.feed(Button.B, Edge.RELEASE)
    assert fsm.drain() == []


def test_btn_b_rapid_presses_each_emit(fsm: ButtonFSM, clock: FakeClock):
    fsm.feed(Button.B, Edge.PRESS)
    fsm.feed(Button.B, Edge.RELEASE)
    clock.advance(50)
    fsm.feed(Button.B, Edge.PRESS)
    fsm.feed(Button.B, Edge.RELEASE)
    assert fsm.drain() == [ButtonEvent.BTN_B_PRESS, ButtonEvent.BTN_B_PRESS]


# ---------------------------------------------------------------------------
# BTN_A: single press (after double-window expires)
# ---------------------------------------------------------------------------

def test_btn_a_lone_press_emits_after_window(fsm: ButtonFSM, clock: FakeClock):
    fsm.feed(Button.A, Edge.PRESS)
    clock.advance(50)
    fsm.feed(Button.A, Edge.RELEASE)
    # Before window expires: nothing emitted.
    assert fsm.drain() == []
    clock.advance(DOUBLE_WINDOW_MS)
    # At exactly the window boundary: still pending (window is exclusive).
    assert fsm.drain() == []
    clock.advance(1)
    assert fsm.drain() == [ButtonEvent.BTN_A_PRESS]


def test_btn_a_release_without_press_is_noop(fsm: ButtonFSM):
    fsm.feed(Button.A, Edge.RELEASE)
    assert fsm.drain() == []


# ---------------------------------------------------------------------------
# BTN_A: double-click
# ---------------------------------------------------------------------------

def test_btn_a_double_within_window_emits_double(fsm: ButtonFSM, clock: FakeClock):
    fsm.feed(Button.A, Edge.PRESS)
    clock.advance(50)
    fsm.feed(Button.A, Edge.RELEASE)
    clock.advance(100)
    fsm.feed(Button.A, Edge.PRESS)
    # DOUBLE is emitted on the second press, not after another window.
    assert fsm.drain() == [ButtonEvent.BTN_A_DOUBLE]
    clock.advance(50)
    fsm.feed(Button.A, Edge.RELEASE)
    # No spurious extra short from the trailing release.
    clock.advance(DOUBLE_WINDOW_MS + 10)
    assert fsm.drain() == []


def test_btn_a_double_at_window_boundary(fsm: ButtonFSM, clock: FakeClock):
    fsm.feed(Button.A, Edge.PRESS)
    clock.advance(10)
    fsm.feed(Button.A, Edge.RELEASE)
    clock.advance(DOUBLE_WINDOW_MS)  # exactly at boundary, still counts as double
    fsm.feed(Button.A, Edge.PRESS)
    assert fsm.drain() == [ButtonEvent.BTN_A_DOUBLE]


def test_btn_a_second_press_just_outside_window_two_singles(fsm: ButtonFSM, clock: FakeClock):
    fsm.feed(Button.A, Edge.PRESS)
    clock.advance(10)
    fsm.feed(Button.A, Edge.RELEASE)
    clock.advance(DOUBLE_WINDOW_MS + 1)  # just past window
    fsm.feed(Button.A, Edge.PRESS)
    # Stale pending short gets flushed.
    assert fsm.drain() == [ButtonEvent.BTN_A_PRESS]
    clock.advance(10)
    fsm.feed(Button.A, Edge.RELEASE)
    clock.advance(DOUBLE_WINDOW_MS + 1)
    assert fsm.drain() == [ButtonEvent.BTN_A_PRESS]


# ---------------------------------------------------------------------------
# BTN_A: long press
# ---------------------------------------------------------------------------

def test_btn_a_long_press_emits_on_release(fsm: ButtonFSM, clock: FakeClock):
    fsm.feed(Button.A, Edge.PRESS)
    clock.advance(LONG_PRESS_MS)
    fsm.feed(Button.A, Edge.RELEASE)
    assert fsm.drain() == [ButtonEvent.BTN_A_LONG]


def test_btn_a_long_press_eagerly_emitted_during_drain(fsm: ButtonFSM, clock: FakeClock):
    """If no release is observed but the hold exceeds the threshold, drain()
    emits BTN_A_LONG eagerly so the app can react without waiting for release."""
    fsm.feed(Button.A, Edge.PRESS)
    clock.advance(LONG_PRESS_MS)
    assert fsm.drain() == [ButtonEvent.BTN_A_LONG]
    # Subsequent drains do not re-fire.
    clock.advance(500)
    assert fsm.drain() == []
    # Eventual release does not produce another event.
    fsm.feed(Button.A, Edge.RELEASE)
    assert fsm.drain() == []


def test_btn_a_hold_just_below_threshold_is_single(fsm: ButtonFSM, clock: FakeClock):
    fsm.feed(Button.A, Edge.PRESS)
    clock.advance(LONG_PRESS_MS - 1)
    fsm.feed(Button.A, Edge.RELEASE)
    clock.advance(DOUBLE_WINDOW_MS + 1)
    assert fsm.drain() == [ButtonEvent.BTN_A_PRESS]


# ---------------------------------------------------------------------------
# BTN_A: debounce
# ---------------------------------------------------------------------------

def test_btn_a_debounce_ignores_rapid_repress(fsm: ButtonFSM, clock: FakeClock):
    fsm.feed(Button.A, Edge.PRESS)
    clock.advance(DEBOUNCE_MS - 1)
    fsm.feed(Button.A, Edge.PRESS)
    # Only one press registered; window expires → single BTN_A_PRESS
    clock.advance(50)
    fsm.feed(Button.A, Edge.RELEASE)
    clock.advance(DOUBLE_WINDOW_MS + 1)
    assert fsm.drain() == [ButtonEvent.BTN_A_PRESS]


def test_btn_a_press_after_debounce_window_emits(fsm: ButtonFSM, clock: FakeClock):
    fsm.feed(Button.A, Edge.PRESS)
    fsm.feed(Button.A, Edge.RELEASE)
    clock.advance(DEBOUNCE_MS)
    fsm.feed(Button.A, Edge.PRESS)
    # Both presses within double window → DOUBLE
    assert fsm.drain() == [ButtonEvent.BTN_A_DOUBLE]


# ---------------------------------------------------------------------------
# PWR: single press (after double-window expires)
# ---------------------------------------------------------------------------

def test_lone_pwr_short_emits_after_window(fsm: ButtonFSM, clock: FakeClock):
    fsm.feed(Button.PWR, Edge.PRESS)
    clock.advance(50)
    fsm.feed(Button.PWR, Edge.RELEASE)
    # Before window expires: nothing emitted.
    assert fsm.drain() == []
    clock.advance(DOUBLE_WINDOW_MS)
    # At exactly the window boundary: still pending (window is exclusive).
    assert fsm.drain() == []
    clock.advance(1)
    assert fsm.drain() == [ButtonEvent.PWR_SHORT]


# ---------------------------------------------------------------------------
# PWR: double-click
# ---------------------------------------------------------------------------

def test_pwr_double_within_window_emits_double(fsm: ButtonFSM, clock: FakeClock):
    fsm.feed(Button.PWR, Edge.PRESS)
    clock.advance(50)
    fsm.feed(Button.PWR, Edge.RELEASE)
    clock.advance(100)
    fsm.feed(Button.PWR, Edge.PRESS)
    # DOUBLE is emitted on the second press, not after another window.
    assert fsm.drain() == [ButtonEvent.PWR_DOUBLE]
    clock.advance(50)
    fsm.feed(Button.PWR, Edge.RELEASE)
    # No spurious extra short from the trailing release.
    clock.advance(DOUBLE_WINDOW_MS + 10)
    assert fsm.drain() == []


def test_pwr_double_at_window_boundary(fsm: ButtonFSM, clock: FakeClock):
    fsm.feed(Button.PWR, Edge.PRESS)
    clock.advance(10)
    fsm.feed(Button.PWR, Edge.RELEASE)
    clock.advance(DOUBLE_WINDOW_MS)  # exactly at boundary, still counts as double
    fsm.feed(Button.PWR, Edge.PRESS)
    assert fsm.drain() == [ButtonEvent.PWR_DOUBLE]


def test_pwr_second_press_just_outside_window_two_shorts(fsm: ButtonFSM, clock: FakeClock):
    fsm.feed(Button.PWR, Edge.PRESS)
    clock.advance(10)
    fsm.feed(Button.PWR, Edge.RELEASE)
    clock.advance(DOUBLE_WINDOW_MS + 1)  # just past window
    fsm.feed(Button.PWR, Edge.PRESS)
    # Stale pending short gets flushed.
    assert fsm.drain() == [ButtonEvent.PWR_SHORT]
    clock.advance(10)
    fsm.feed(Button.PWR, Edge.RELEASE)
    clock.advance(DOUBLE_WINDOW_MS + 1)
    assert fsm.drain() == [ButtonEvent.PWR_SHORT]


# ---------------------------------------------------------------------------
# PWR: long press
# ---------------------------------------------------------------------------

def test_pwr_long_press_emits_on_release(fsm: ButtonFSM, clock: FakeClock):
    fsm.feed(Button.PWR, Edge.PRESS)
    clock.advance(LONG_PRESS_MS)
    fsm.feed(Button.PWR, Edge.RELEASE)
    assert fsm.drain() == [ButtonEvent.PWR_LONG]


def test_pwr_long_press_eagerly_emitted_during_drain(fsm: ButtonFSM, clock: FakeClock):
    """If no release is observed but the hold exceeds the threshold, drain()
    emits PWR_LONG eagerly so the app can react without waiting for release."""
    fsm.feed(Button.PWR, Edge.PRESS)
    clock.advance(LONG_PRESS_MS)
    assert fsm.drain() == [ButtonEvent.PWR_LONG]
    # Subsequent drains do not re-fire.
    clock.advance(500)
    assert fsm.drain() == []
    # Eventual release does not produce another event.
    fsm.feed(Button.PWR, Edge.RELEASE)
    assert fsm.drain() == []


def test_pwr_hold_just_below_threshold_is_short(fsm: ButtonFSM, clock: FakeClock):
    fsm.feed(Button.PWR, Edge.PRESS)
    clock.advance(LONG_PRESS_MS - 1)
    fsm.feed(Button.PWR, Edge.RELEASE)
    clock.advance(DOUBLE_WINDOW_MS + 1)
    assert fsm.drain() == [ButtonEvent.PWR_SHORT]


def test_pwr_debounce_ignores_rapid_repress(fsm: ButtonFSM, clock: FakeClock):
    """Rapid re-press chatter on PWR within debounce window is ignored;
    only the original press is tracked, so the hold-then-release still
    produces a single PWR_LONG."""
    fsm.feed(Button.PWR, Edge.PRESS)
    clock.advance(DEBOUNCE_MS - 1)
    # Bouncy re-press within debounce window is ignored.
    fsm.feed(Button.PWR, Edge.PRESS)
    clock.advance(LONG_PRESS_MS)
    fsm.feed(Button.PWR, Edge.RELEASE)
    assert fsm.drain() == [ButtonEvent.PWR_LONG]


# ---------------------------------------------------------------------------
# Misc / cross-button
# ---------------------------------------------------------------------------

def test_drain_clears_pending(fsm: ButtonFSM):
    fsm.feed(Button.B, Edge.PRESS)
    assert fsm.drain() == [ButtonEvent.BTN_B_PRESS]
    assert fsm.drain() == []


def test_triple_pwr_press_emits_double_then_short(fsm: ButtonFSM, clock: FakeClock):
    """Three rapid presses → first two form a DOUBLE, third becomes a SHORT."""
    fsm.feed(Button.PWR, Edge.PRESS)
    clock.advance(10)
    fsm.feed(Button.PWR, Edge.RELEASE)
    clock.advance(100)
    fsm.feed(Button.PWR, Edge.PRESS)
    clock.advance(10)
    fsm.feed(Button.PWR, Edge.RELEASE)
    assert fsm.drain() == [ButtonEvent.PWR_DOUBLE]
    clock.advance(100)
    fsm.feed(Button.PWR, Edge.PRESS)
    clock.advance(10)
    fsm.feed(Button.PWR, Edge.RELEASE)
    clock.advance(DOUBLE_WINDOW_MS + 1)
    assert fsm.drain() == [ButtonEvent.PWR_SHORT]


def test_pwr_and_btn_a_interleaved(fsm: ButtonFSM, clock: FakeClock):
    fsm.feed(Button.PWR, Edge.PRESS)
    clock.advance(10)
    fsm.feed(Button.A, Edge.PRESS)
    clock.advance(10)
    fsm.feed(Button.PWR, Edge.RELEASE)
    clock.advance(10)
    fsm.feed(Button.A, Edge.RELEASE)
    # Both releases are short; their double-windows are still open.
    assert fsm.drain() == []
    clock.advance(DOUBLE_WINDOW_MS + 1)
    # Both single-press windows expire.
    events = fsm.drain()
    assert ButtonEvent.BTN_A_PRESS in events
    assert ButtonEvent.PWR_SHORT in events
