"""Tests for SleepManager inactivity policy (issue #68)."""

from ui.sleep import LCD_SLEEP_MS, POWER_OFF_MS, SleepManager


def _mgr(start_ms: int = 0, lcd_sleep_ms: int = LCD_SLEEP_MS, power_off_ms: int = POWER_OFF_MS):
    clock = [start_ms]
    mgr = SleepManager(lambda: clock[0], lcd_sleep_ms=lcd_sleep_ms, power_off_ms=power_off_ms)
    return mgr, clock


# ---------------------------------------------------------------------------
# Idle below both thresholds
# ---------------------------------------------------------------------------


def test_no_signal_before_lcd_threshold():
    mgr, clock = _mgr(lcd_sleep_ms=1000, power_off_ms=5000)
    clock[0] = 999
    assert mgr.tick() is None


def test_no_signal_at_zero():
    mgr, clock = _mgr()
    assert mgr.tick() is None


# ---------------------------------------------------------------------------
# LCD sleep threshold
# ---------------------------------------------------------------------------


def test_lcd_sleep_emitted_exactly_at_threshold():
    mgr, clock = _mgr(lcd_sleep_ms=1000, power_off_ms=5000)
    clock[0] = 1000
    assert mgr.tick() == "lcd_sleep"


def test_lcd_sleep_emitted_past_threshold():
    mgr, clock = _mgr(lcd_sleep_ms=1000, power_off_ms=5000)
    clock[0] = 2000
    assert mgr.tick() == "lcd_sleep"


def test_lcd_sleep_emitted_only_once():
    mgr, clock = _mgr(lcd_sleep_ms=1000, power_off_ms=5000)
    clock[0] = 1000
    assert mgr.tick() == "lcd_sleep"
    clock[0] = 1500
    # Already asleep — no second lcd_sleep signal.
    assert mgr.tick() is None


def test_no_signal_between_thresholds_after_sleep():
    mgr, clock = _mgr(lcd_sleep_ms=1000, power_off_ms=5000)
    clock[0] = 1000
    mgr.tick()  # consume lcd_sleep
    clock[0] = 3000
    assert mgr.tick() is None


# ---------------------------------------------------------------------------
# Power-off threshold
# ---------------------------------------------------------------------------


def test_power_off_at_threshold():
    mgr, clock = _mgr(lcd_sleep_ms=1000, power_off_ms=5000)
    clock[0] = 5000
    assert mgr.tick() == "power_off"


def test_power_off_past_threshold():
    mgr, clock = _mgr(lcd_sleep_ms=1000, power_off_ms=5000)
    clock[0] = 9999
    assert mgr.tick() == "power_off"


def test_power_off_takes_priority_over_lcd_sleep():
    # When both thresholds are exceeded simultaneously (e.g. device just woke),
    # power_off wins because it's checked first.
    mgr, clock = _mgr(lcd_sleep_ms=1000, power_off_ms=5000)
    clock[0] = 5000
    assert mgr.tick() == "power_off"


# ---------------------------------------------------------------------------
# poke() resets timer and wakes LCD
# ---------------------------------------------------------------------------


def test_poke_resets_timer():
    mgr, clock = _mgr(lcd_sleep_ms=1000, power_off_ms=5000)
    clock[0] = 2000
    mgr.poke()
    clock[0] = 2500  # only 500 ms since poke — below threshold
    assert mgr.tick() is None


def test_poke_after_lcd_sleep_re_arms_sleep_signal():
    mgr, clock = _mgr(lcd_sleep_ms=1000, power_off_ms=5000)
    clock[0] = 1000
    mgr.tick()  # consume lcd_sleep; now lcd_asleep=True
    clock[0] = 1001
    mgr.poke()  # wakes LCD, resets timer
    clock[0] = 2001  # 1000 ms since poke — threshold again
    assert mgr.tick() == "lcd_sleep"


def test_poke_prevents_power_off():
    mgr, clock = _mgr(lcd_sleep_ms=1000, power_off_ms=5000)
    clock[0] = 4999
    mgr.poke()  # reset at 4999
    clock[0] = 5000  # only 1 ms since poke
    assert mgr.tick() is None


# ---------------------------------------------------------------------------
# Default thresholds sanity check
# ---------------------------------------------------------------------------


def test_default_lcd_sleep_ms():
    assert LCD_SLEEP_MS == 90_000


def test_default_power_off_ms():
    assert POWER_OFF_MS == 600_000


def test_defaults_used_when_not_overridden():
    clock = [0]
    mgr = SleepManager(lambda: clock[0])
    clock[0] = LCD_SLEEP_MS - 1
    assert mgr.tick() is None
    clock[0] = LCD_SLEEP_MS
    assert mgr.tick() == "lcd_sleep"
    clock[0] = POWER_OFF_MS
    assert mgr.tick() == "power_off"
