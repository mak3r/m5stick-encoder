"""UIFlow 2 PWR-button wrapper for M5StickC PLUS.

Replaces AxpButtons to eliminate the I2C conflict between UIFlow 2's AXP192
driver (initialised by M5.begin()) and the old direct-register approach.

M5Display.__init__ calls M5.begin() before this class is instantiated,
so M5.BtnPWR is available immediately.

MicroPython-only — host stub raises RuntimeError like axp_buttons.py.
"""

from ui.events import ButtonEvent

try:
    import M5  # type: ignore[import]

    class PwrButton:
        """Poll UIFlow 2 M5.BtnPWR and return ButtonEvents.

        M5.update() must be called each tick to latch fresh button state;
        we call it here so callers need no UIFlow 2 knowledge.
        """

        def poll(self) -> list[ButtonEvent]:
            """Return pending PWR-button events for this tick."""
            M5.update()
            events: list[ButtonEvent] = []
            if M5.BtnPWR.wasHold():
                events.append(ButtonEvent.PWR_LONG)
            if M5.BtnPWR.wasClicked():
                events.append(ButtonEvent.PWR_SHORT)
            return events

except ImportError:
    class PwrButton:  # type: ignore[no-redef]
        """Stub: hardware not available on host."""

        def poll(self) -> list[ButtonEvent]:  # pragma: no cover
            raise RuntimeError("PwrButton requires UIFlow 2 M5 module")
