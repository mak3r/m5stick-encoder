"""AXP192 PMIC PWR-button reader for M5StickC PLUS.

Hardware wiring:
  I2C SDA=G21, SCL=G22, address=0x34, IRQ on G35 (latched, active-low).

Gate all hardware access behind the ``machine`` import so this file
can be imported on host for inspection without raising ImportError.
"""

from ui.events import ButtonEvent

_AXP_ADDR = 0x34

# REG 0x36 — PEK (Power Enable Key) control
# bits[5:4] = short-press confirm threshold: 10 → 1 s
# bits[3:2] = long-press threshold: 00 → 1 s
# bits[1:0] = power-off hold time: 00 → 4 s
_REG_PEK_CFG = 0x36
_PEK_CFG_VALUE = 0b00_10_00_00  # short=1s, long=1s, shutdown=4s

# REG 0x46 — IRQ status 2 (read to detect, write 1 to clear)
_REG_IRQ2 = 0x46
_IRQ2_PEK_SHORT = 1 << 1  # bit 1 = short-press flag
_IRQ2_PEK_LONG = 1 << 0   # bit 0 = long-press flag

try:
    from machine import I2C, Pin  # type: ignore[import]

    def _make_bus() -> I2C:
        return I2C(0, sda=Pin(21), scl=Pin(22), freq=400_000)

    def _reg_read(bus: I2C, reg: int) -> int:
        return bus.readfrom_mem(_AXP_ADDR, reg, 1)[0]

    def _reg_write(bus: I2C, reg: int, value: int) -> None:
        bus.writeto_mem(_AXP_ADDR, reg, bytes([value]))

    class AxpButtons:
        """Poll the AXP192 IRQ2 register and return ButtonEvents.

        Instantiate once at startup; call ``poll()`` from the main loop.
        The AXP decides short vs long — no software edge timing.
        """

        def __init__(self) -> None:
            self._bus = _make_bus()
            # Configure PEK thresholds.
            _reg_write(self._bus, _REG_PEK_CFG, _PEK_CFG_VALUE)
            # Clear any stale IRQ flags left from a previous boot.
            _reg_write(self._bus, _REG_IRQ2, _IRQ2_PEK_SHORT | _IRQ2_PEK_LONG)

        def poll(self) -> list[ButtonEvent]:
            """Return any pending PWR-button events and clear the IRQ flags."""
            status = _reg_read(self._bus, _REG_IRQ2)
            events: list[ButtonEvent] = []
            if status & _IRQ2_PEK_LONG:
                events.append(ButtonEvent.PWR_LONG)
            if status & _IRQ2_PEK_SHORT:
                events.append(ButtonEvent.PWR_SHORT)
            if status & (_IRQ2_PEK_SHORT | _IRQ2_PEK_LONG):
                # Clear only the bits we consumed; write 1 to clear.
                _reg_write(self._bus, _REG_IRQ2, status & (_IRQ2_PEK_SHORT | _IRQ2_PEK_LONG))
            return events

except ImportError:
    # Running on host — AxpButtons is not available, but the module loads fine.
    class AxpButtons:  # type: ignore[no-redef]
        """Stub: hardware not available on host."""

        def __init__(self) -> None:
            raise RuntimeError("AxpButtons requires MicroPython machine module")

        def poll(self) -> list[ButtonEvent]:  # pragma: no cover
            raise RuntimeError("AxpButtons requires MicroPython machine module")
