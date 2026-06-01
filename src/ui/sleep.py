"""Inactivity-based sleep policy — pure logic, no hardware imports.

SleepManager tracks elapsed idle time and emits signals when the LCD
should sleep (90 s default) or the device should power off (600 s default).
All timing is driven by an injected ``time_ms_fn`` so tests run against a
virtual clock.
"""

from collections.abc import Callable

LCD_SLEEP_MS = 90_000
POWER_OFF_MS = 600_000


class SleepManager:
    """Emit sleep/power-off signals based on inactivity duration.

    Call ``poke()`` whenever user activity occurs (any handled event).
    Call ``tick()`` each polling loop iteration; it returns the next action
    to take, or ``None`` if nothing has changed.

    Signals (str): ``"lcd_sleep"``, ``"lcd_wake"``, ``"power_off"``.
    Only one signal is returned per call; callers should call ``tick()``
    once per loop iteration and handle the result.
    """

    def __init__(
        self,
        time_ms_fn: Callable[[], int],
        lcd_sleep_ms: int = LCD_SLEEP_MS,
        power_off_ms: int = POWER_OFF_MS,
    ) -> None:
        self._now = time_ms_fn
        self._lcd_sleep_ms = lcd_sleep_ms
        self._power_off_ms = power_off_ms
        self._last_activity_ms = time_ms_fn()
        self._lcd_asleep = False

    def poke(self) -> None:
        """Record activity; wake the LCD if it was sleeping."""
        self._last_activity_ms = self._now()
        self._lcd_asleep = False

    def tick(self) -> str | None:
        idle = self._now() - self._last_activity_ms
        if idle >= self._power_off_ms:
            return "power_off"
        if idle >= self._lcd_sleep_ms and not self._lcd_asleep:
            self._lcd_asleep = True
            return "lcd_sleep"
        return None
