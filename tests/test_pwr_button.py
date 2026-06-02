"""Tests for hw/pwr_button.py.

PwrButton wraps M5.BtnPWR from UIFlow 2; M5 is not available on host,
so tests inject a fake M5 module via sys.modules and reload the hw module.
"""

import importlib
import sys

import pytest

from ui.events import ButtonEvent

# ---------------------------------------------------------------------------
# Module-level import must succeed on host
# ---------------------------------------------------------------------------


def test_module_imports_on_host():
    import hw.pwr_button  # noqa: F401


def test_host_poll_raises_runtime_error():
    import hw.pwr_button as m

    btn = m.PwrButton()
    with pytest.raises(RuntimeError, match="M5"):
        btn.poll()


# ---------------------------------------------------------------------------
# Fake-M5 integration tests for the hardware path
# ---------------------------------------------------------------------------


class FakeBtnPWR:
    """Controllable stub for M5.BtnPWR."""

    def __init__(self, clicked: bool = False, held: bool = False) -> None:
        self._clicked = clicked
        self._held = held

    def wasClicked(self) -> bool:  # noqa: N802
        return self._clicked

    def wasHold(self) -> bool:  # noqa: N802
        return self._held


class FakeM5:
    """Minimal M5 module stub."""

    def __init__(self, clicked: bool = False, held: bool = False) -> None:
        self.BtnPWR = FakeBtnPWR(clicked=clicked, held=held)
        self._update_calls = 0

    def update(self) -> None:
        self._update_calls += 1


def _load_hw_path(clicked: bool = False, held: bool = False):
    """Reload pwr_button with a fake M5 module; returns (module, fake_m5, PwrButton)."""
    fake_m5 = FakeM5(clicked=clicked, held=held)

    saved = sys.modules.copy()
    sys.modules["M5"] = fake_m5  # type: ignore[assignment]
    if "hw.pwr_button" in sys.modules:
        del sys.modules["hw.pwr_button"]

    try:
        mod = importlib.import_module("hw.pwr_button")
    finally:
        sys.modules.clear()
        sys.modules.update(saved)
        if "hw.pwr_button" in sys.modules:
            del sys.modules["hw.pwr_button"]

    # Always inject a fixed-time clock so __init__ never tries time.ticks_ms on host.
    btn = mod.PwrButton(time_ms_fn=lambda: 0)
    return mod, fake_m5, btn


def _load_hw_path_with_clock(clicked_seq, time_fn):
    """Load pwr_button with a sequenced wasClicked() and an injectable clock."""
    clicks = iter(clicked_seq)

    class SeqBtnPWR:
        def wasClicked(self):  # noqa: N802
            return next(clicks, False)

        def wasHold(self):  # noqa: N802
            return False

    class SeqM5:
        BtnPWR = SeqBtnPWR()
        _update_calls = 0

        @staticmethod
        def update() -> None:
            SeqM5._update_calls += 1

    saved = sys.modules.copy()
    sys.modules["M5"] = SeqM5  # type: ignore[assignment]
    if "hw.pwr_button" in sys.modules:
        del sys.modules["hw.pwr_button"]

    try:
        mod = importlib.import_module("hw.pwr_button")
    finally:
        sys.modules.clear()
        sys.modules.update(saved)
        if "hw.pwr_button" in sys.modules:
            del sys.modules["hw.pwr_button"]

    btn = mod.PwrButton(time_ms_fn=time_fn)
    return btn


def test_poll_no_press_returns_empty():
    _, _, btn = _load_hw_path(clicked=False, held=False)
    assert btn.poll() == []


def test_poll_single_click_pending_then_flushes():
    """A single click is held pending until the double-window expires."""
    t = [0]
    btn = _load_hw_path_with_clock([True, False, False], lambda: t[0])

    # First poll: click registered, pending started — no event yet.
    events1 = btn.poll()
    assert ButtonEvent.PWR_SHORT not in events1
    assert ButtonEvent.PWR_DOUBLE not in events1

    # Second poll: within window, no second click — still pending.
    t[0] = 100
    events2 = btn.poll()
    assert ButtonEvent.PWR_SHORT not in events2

    # Third poll: window expired — flush as PWR_SHORT.
    t[0] = 300
    events3 = btn.poll()
    assert ButtonEvent.PWR_SHORT in events3
    assert ButtonEvent.PWR_DOUBLE not in events3


def test_poll_double_click_emits_pwr_double():
    """Two clicks within DOUBLE_WINDOW_MS → PWR_DOUBLE."""
    t = [0]
    btn = _load_hw_path_with_clock([True, True], lambda: t[0])

    # First click at t=0.
    btn.poll()

    # Second click at t=200 (within 300ms window) → PWR_DOUBLE.
    t[0] = 200
    events = btn.poll()
    assert ButtonEvent.PWR_DOUBLE in events
    assert ButtonEvent.PWR_SHORT not in events


def test_poll_two_clicks_outside_window_emit_two_shorts():
    """Two clicks >300ms apart → two separate PWR_SHORT events."""
    t = [0]
    btn = _load_hw_path_with_clock([True, False, True, False], lambda: t[0])

    btn.poll()       # click1 at t=0, pending
    t[0] = 300
    btn.poll()       # t=300: flush pending → PWR_SHORT, no second click
    t[0] = 400
    btn.poll()       # click2 at t=400, new pending
    t[0] = 700
    events = btn.poll()   # t=700: flush second pending → PWR_SHORT
    assert ButtonEvent.PWR_SHORT in events
    assert ButtonEvent.PWR_DOUBLE not in events


def test_poll_held_does_not_emit_pwr_long():
    """wasHold() is silenced — PWR_LONG races hardware power-off."""
    _, _, btn = _load_hw_path(clicked=False, held=True)
    events = btn.poll()
    assert ButtonEvent.PWR_LONG not in events


def test_poll_calls_m5_update():
    """M5.update() must be called once per poll() invocation."""
    _, fake_m5, btn = _load_hw_path(clicked=False, held=False)
    btn.poll()
    assert fake_m5._update_calls == 1


def test_poll_calls_m5_update_each_tick():
    """M5.update() must be called on every poll(), not just once."""
    _, fake_m5, btn = _load_hw_path(clicked=False, held=False)
    btn.poll()
    btn.poll()
    btn.poll()
    assert fake_m5._update_calls == 3
