"""Tests for hw/axp_buttons.py.

We can't instantiate the real AxpButtons on host (no machine module), so
the tests exercise the module-level constants and verify that:
  1. The module imports cleanly on host.
  2. Host-side instantiation raises RuntimeError (not ImportError or crash).
  3. Register constant values match the AXP192 datasheet intent.
  4. A fake I2C driver wired into the hardware path produces correct events.
"""

import importlib
import sys
import types

import pytest

# ---------------------------------------------------------------------------
# Module-level import must succeed on host
# ---------------------------------------------------------------------------


def test_module_imports_on_host():
    """axp_buttons must import without error even without MicroPython."""
    import hw.axp_buttons  # noqa: F401  (side-effect: verifies no crash)


def test_host_instantiation_raises_runtime_error():
    import hw.axp_buttons as m

    with pytest.raises(RuntimeError, match="machine"):
        m.AxpButtons()


# ---------------------------------------------------------------------------
# Register constant correctness
# ---------------------------------------------------------------------------


def test_pek_cfg_value_encodes_correct_thresholds():
    import hw.axp_buttons as m

    # bits[5:4] = 0b10 → short-press confirm = 1 s
    short_field = (m._PEK_CFG_VALUE >> 4) & 0b11
    assert short_field == 0b10, "short-press threshold must be 1 s (0b10)"

    # bits[3:2] = 0b00 → long-press threshold = 1 s
    long_field = (m._PEK_CFG_VALUE >> 2) & 0b11
    assert long_field == 0b00, "long-press threshold must be 1 s (0b00)"

    # bits[1:0] = 0b00 → power-off hold = 4 s
    shutdown_field = m._PEK_CFG_VALUE & 0b11
    assert shutdown_field == 0b00, "shutdown hold must be 4 s (0b00)"


def test_irq_bit_masks_are_distinct_and_nonzero():
    import hw.axp_buttons as m

    assert m._IRQ2_PEK_SHORT != 0
    assert m._IRQ2_PEK_LONG != 0
    assert m._IRQ2_PEK_SHORT != m._IRQ2_PEK_LONG


# ---------------------------------------------------------------------------
# Fake-I2C integration tests for the hardware path
# ---------------------------------------------------------------------------


class FakeI2C:
    """Minimal I2C stub with per-register memory.

    REG 0x46 uses AXP192 write-1-to-clear semantics: writing a 1 to a bit
    clears it; writing 0 leaves it unchanged.  All other registers behave as
    plain read/write.
    """

    _W1C_REGS = {0x46}

    def __init__(self, regs: dict[int, int] | None = None):
        self.mem: dict[int, int] = dict(regs or {})
        self.writes: list[tuple[int, int]] = []  # (reg, value)

    def readfrom_mem(self, addr: int, reg: int, n: int) -> bytes:
        return bytes([self.mem.get(reg, 0)] * n)

    def writeto_mem(self, addr: int, reg: int, data: bytes) -> None:
        value = data[0]
        self.writes.append((reg, value))
        if reg in self._W1C_REGS:
            # Write-1-to-clear: clear only the bits that are written as 1.
            self.mem[reg] = self.mem.get(reg, 0) & ~value
        else:
            self.mem[reg] = value


def _load_hw_path(irq2_initial: int) -> tuple[types.ModuleType, FakeI2C]:
    """Reload axp_buttons with a fake machine module injected into sys.modules."""
    fake_i2c = FakeI2C({0x46: irq2_initial})

    fake_machine = types.ModuleType("machine")
    fake_machine.I2C = lambda bus_id, sda, scl, freq: fake_i2c  # type: ignore[attr-defined]
    fake_machine.Pin = lambda pin_id: pin_id  # type: ignore[attr-defined]

    saved = sys.modules.copy()
    sys.modules["machine"] = fake_machine
    # Force reload so the try-branch is re-evaluated with machine present.
    if "hw.axp_buttons" in sys.modules:
        del sys.modules["hw.axp_buttons"]

    try:
        mod = importlib.import_module("hw.axp_buttons")
    finally:
        # Restore sys.modules so other tests see the real (missing) machine.
        sys.modules.clear()
        sys.modules.update(saved)
        if "hw.axp_buttons" in sys.modules:
            del sys.modules["hw.axp_buttons"]

    return mod, fake_i2c


@pytest.fixture()
def hw_module_no_flags():
    """Hardware module reloaded with no pending IRQ flags."""
    mod, i2c = _load_hw_path(irq2_initial=0x00)
    return mod, i2c


@pytest.fixture()
def hw_module_short_flag():
    """Hardware module reloaded with the short-press IRQ flag set."""
    import hw.axp_buttons as ref
    mod, i2c = _load_hw_path(irq2_initial=ref._IRQ2_PEK_SHORT)
    return mod, i2c


@pytest.fixture()
def hw_module_long_flag():
    """Hardware module reloaded with the long-press IRQ flag set."""
    import hw.axp_buttons as ref
    mod, i2c = _load_hw_path(irq2_initial=ref._IRQ2_PEK_LONG)
    return mod, i2c


@pytest.fixture()
def hw_module_both_flags():
    """Hardware module reloaded with both IRQ flags set simultaneously."""
    import hw.axp_buttons as ref
    mod, i2c = _load_hw_path(irq2_initial=ref._IRQ2_PEK_SHORT | ref._IRQ2_PEK_LONG)
    return mod, i2c


def _make_instance(mod):
    """Instantiate AxpButtons from the given (reloaded) module."""
    return mod.AxpButtons()


def test_hw_poll_no_flags_returns_empty(hw_module_no_flags):
    mod, i2c = hw_module_no_flags
    axp = _make_instance(mod)
    # Clear writes from __init__; reset mem to 0 for a clean poll.
    i2c.mem[0x46] = 0x00
    assert axp.poll() == []


def test_hw_poll_short_flag_returns_pwr_short(hw_module_short_flag):
    from ui.events import ButtonEvent
    mod, i2c = hw_module_short_flag
    axp = _make_instance(mod)
    # After init clears stale flags, set them again for the poll test.
    import hw.axp_buttons as ref
    i2c.mem[0x46] = ref._IRQ2_PEK_SHORT
    events = axp.poll()
    assert ButtonEvent.PWR_SHORT in events
    assert ButtonEvent.PWR_LONG not in events


def test_hw_poll_long_flag_returns_pwr_long(hw_module_long_flag):
    from ui.events import ButtonEvent
    mod, i2c = hw_module_long_flag
    axp = _make_instance(mod)
    import hw.axp_buttons as ref
    i2c.mem[0x46] = ref._IRQ2_PEK_LONG
    events = axp.poll()
    assert ButtonEvent.PWR_LONG in events
    assert ButtonEvent.PWR_SHORT not in events


def test_hw_poll_both_flags_returns_both_events(hw_module_both_flags):
    from ui.events import ButtonEvent
    mod, i2c = hw_module_both_flags
    axp = _make_instance(mod)
    import hw.axp_buttons as ref
    i2c.mem[0x46] = ref._IRQ2_PEK_SHORT | ref._IRQ2_PEK_LONG
    events = axp.poll()
    assert ButtonEvent.PWR_SHORT in events
    assert ButtonEvent.PWR_LONG in events


def test_hw_poll_clears_irq_flags(hw_module_short_flag):
    mod, i2c = hw_module_short_flag
    axp = _make_instance(mod)
    import hw.axp_buttons as ref
    i2c.mem[0x46] = ref._IRQ2_PEK_SHORT
    axp.poll()
    # After poll, the register should be cleared.
    assert i2c.mem[0x46] & ref._IRQ2_PEK_SHORT == 0


def test_hw_poll_second_call_returns_empty_after_clear(hw_module_short_flag):
    mod, i2c = hw_module_short_flag
    axp = _make_instance(mod)
    import hw.axp_buttons as ref
    i2c.mem[0x46] = ref._IRQ2_PEK_SHORT
    axp.poll()
    # Second poll with cleared register → no events.
    assert axp.poll() == []


def test_hw_init_writes_pek_cfg(hw_module_no_flags):
    mod, i2c = hw_module_no_flags
    _make_instance(mod)
    # __init__ must write _PEK_CFG_VALUE to _REG_PEK_CFG (0x36).
    cfg_writes = [(reg, val) for reg, val in i2c.writes if reg == 0x36]
    assert len(cfg_writes) >= 1
    import hw.axp_buttons as ref
    assert cfg_writes[0][1] == ref._PEK_CFG_VALUE


def test_hw_init_clears_irq_flags(hw_module_no_flags):
    mod, i2c = hw_module_no_flags
    _make_instance(mod)
    # __init__ must write to 0x46 to clear stale flags.
    irq_writes = [(reg, val) for reg, val in i2c.writes if reg == 0x46]
    assert len(irq_writes) >= 1
