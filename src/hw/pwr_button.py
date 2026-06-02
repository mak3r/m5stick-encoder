"""UIFlow 2 PWR-button wrapper for M5StickC PLUS.

Replaces AxpButtons to eliminate the I2C conflict between UIFlow 2's AXP192
driver (initialised by M5.begin()) and the old direct-register approach.

M5Display.__init__ calls M5.begin() before this class is instantiated,
so M5.BtnPWR is available immediately.

MicroPython-only — host stub raises RuntimeError like axp_buttons.py.

PWR_LONG is intentionally not emitted: wasHold() fires at roughly the same
hold duration that the AXP192 IC interprets as a power-off command, making
the event unreliable for app use on M5StickC PLUS.
"""

from ui.events import ButtonEvent

DOUBLE_WINDOW_MS = 300  # time budget for a second click to form a double


try:
    from time import ticks_diff as _ticks_diff
except ImportError:
    def _ticks_diff(a: int, b: int) -> int:  # type: ignore[misc]
        return a - b


try:
    import M5  # type: ignore[import]

    class PwrButton:
        """Poll UIFlow 2 M5.BtnPWR and return ButtonEvents.

        M5.update() must be called each tick to latch fresh button state;
        we call it here so callers need no UIFlow 2 knowledge.

        PWR_SHORT is held pending for DOUBLE_WINDOW_MS so that two rapid
        clicks can be detected as PWR_DOUBLE before the first click is
        released as a short.
        """

        def __init__(self, time_ms_fn=None) -> None:
            if time_ms_fn is None:
                import time
                time_ms_fn = time.ticks_ms
            self._time_ms = time_ms_fn
            self._pending_click_ms: int | None = None

        def poll(self) -> list[ButtonEvent]:
            """Return pending PWR-button events for this tick."""
            M5.update()
            events: list[ButtonEvent] = []
            now = self._time_ms()

            if M5.BtnPWR.wasClicked():
                if (self._pending_click_ms is not None
                        and _ticks_diff(now, self._pending_click_ms) < DOUBLE_WINDOW_MS):
                    # Second click within window → double click.
                    events.append(ButtonEvent.PWR_DOUBLE)
                    self._pending_click_ms = None
                else:
                    # First click (or a new click after the previous window expired).
                    if self._pending_click_ms is not None:
                        # Previous pending click's window has lapsed — flush it.
                        events.append(ButtonEvent.PWR_SHORT)
                    self._pending_click_ms = now

            # Flush a pending single click whose double-window has expired.
            if (self._pending_click_ms is not None
                    and _ticks_diff(now, self._pending_click_ms) >= DOUBLE_WINDOW_MS):
                events.append(ButtonEvent.PWR_SHORT)
                self._pending_click_ms = None

            return events

except ImportError:
    class PwrButton:  # type: ignore[no-redef]
        """Stub: hardware not available on host."""

        def __init__(self, time_ms_fn=None) -> None:
            pass

        def poll(self) -> list[ButtonEvent]:  # pragma: no cover
            raise RuntimeError("PwrButton requires UIFlow 2 M5 module")
