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
        self.update_calls = 0

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
    """Reload pwr_button with a fake M5 module injected into sys.modules."""
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

    return mod, fake_m5


def test_poll_no_press_returns_empty():
    mod, _ = _load_hw_path(clicked=False, held=False)
    btn = mod.PwrButton()
    assert btn.poll() == []


def test_poll_clicked_returns_pwr_short():
    mod, _ = _load_hw_path(clicked=True, held=False)
    btn = mod.PwrButton()
    events = btn.poll()
    assert ButtonEvent.PWR_SHORT in events
    assert ButtonEvent.PWR_LONG not in events


def test_poll_held_returns_pwr_long():
    mod, _ = _load_hw_path(clicked=False, held=True)
    btn = mod.PwrButton()
    events = btn.poll()
    assert ButtonEvent.PWR_LONG in events
    assert ButtonEvent.PWR_SHORT not in events


def test_poll_both_returns_both_events():
    mod, _ = _load_hw_path(clicked=True, held=True)
    btn = mod.PwrButton()
    events = btn.poll()
    assert ButtonEvent.PWR_SHORT in events
    assert ButtonEvent.PWR_LONG in events


def test_poll_calls_m5_update():
    """M5.update() must be called once per poll() invocation."""
    mod, fake_m5 = _load_hw_path(clicked=False, held=False)
    btn = mod.PwrButton()
    btn.poll()
    assert fake_m5._update_calls == 1


def test_poll_calls_m5_update_each_tick():
    """M5.update() must be called on every poll(), not just once."""
    mod, fake_m5 = _load_hw_path(clicked=False, held=False)
    btn = mod.PwrButton()
    btn.poll()
    btn.poll()
    btn.poll()
    assert fake_m5._update_calls == 3


def test_pwr_long_before_pwr_short_in_event_order():
    """wasHold() is checked before wasClicked() — long comes first in the list."""
    mod, _ = _load_hw_path(clicked=True, held=True)
    btn = mod.PwrButton()
    events = btn.poll()
    assert events.index(ButtonEvent.PWR_LONG) < events.index(ButtonEvent.PWR_SHORT)
