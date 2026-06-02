"""Device entrypoint. Boots hardware, runs the Phase 1 polling loop.

MicroPython only — not host-runnable. Ruff and pytest exclude this file.
The polling helper is factored into _run_loop() so tests can inject stubs
(see tests/test_main.py).
"""

import sys
import time

from encoder import ALGORITHMS
from hw.buzzer import Buzzer
from hw.pwr_button import PwrButton
from ui.app import App
from ui.buttons import ButtonFSM
from ui.config import btn_b_repeat_delay_ms, btn_b_scroll_ms, load_config
from ui.events import Button, Edge
from ui.key_store import load_setup, save_setup
import ui.screen as screen
from ui.sleep import SleepManager
from ui.state import State

# GPIO wiring on M5StickC PLUS.
_PIN_BTN_A = 37   # side button A (active-low, internal pull-up)
_PIN_BTN_B = 39   # side button B (active-low, internal pull-up)

_BATT_REFRESH_MS = 10_000  # refresh battery readout every ~10 s


def _time_ms() -> int:
    return time.ticks_ms()


def _read_battery(axp_bus) -> str:
    """Read VBAT from AXP192 ADC; return percentage string or '?' on error.

    REG 0x78/0x79 = VBAT (12-bit, 1.1 mV/LSB). Usable LiPo range 3300–4200 mV.
    """
    try:
        raw_hi = axp_bus.readfrom_mem(0x34, 0x78, 1)[0]
        raw_lo = axp_bus.readfrom_mem(0x34, 0x79, 1)[0]
        vbat_mv = ((raw_hi << 4) | (raw_lo & 0x0F)) * 1.1
        pct = int((vbat_mv - 3300) / (4200 - 3300) * 100)
        return str(max(0, min(100, pct)))
    except Exception:
        return "?"


def _axp_power_off() -> None:
    """Shut down via UIFlow 2 power API; falls back to raw AXP192 write."""
    try:
        from M5 import Power  # type: ignore[import]
        try:
            Power.powerOff()
            return
        except AttributeError:
            pass
        try:
            Power.timerSleep(0)
            return
        except AttributeError:
            pass
    except ImportError:
        pass
    # Last resort: direct AXP192 register write (may conflict with UIFlow 2 bus).
    try:
        from machine import I2C, Pin  # type: ignore[import]
        bus = I2C(0, sda=Pin(21), scl=Pin(22), freq=400_000)
        current = bus.readfrom_mem(0x34, 0x32, 1)[0]
        bus.writeto_mem(0x34, 0x32, bytes([current | (1 << 7)]))
    except Exception:
        import machine  # type: ignore[import]
        machine.reset()


def _run_loop(
    display,
    app: App,
    fsm: ButtonFSM,
    pwr: PwrButton,
    btn_a_pin,
    btn_b_pin,
    buzzer: Buzzer,
    axp_bus=None,
    sleep_mgr: SleepManager | None = None,
) -> None:
    """Polling loop: drain button events, update state, render when dirty.

    Extracted from main() so tests can inject stubs for all hardware.
    ``axp_bus`` is optional; when None battery reads return '?'.
    ``sleep_mgr`` is optional; when None the idle-sleep feature is disabled.
    """
    last_batt_ms = _time_ms() - _BATT_REFRESH_MS  # force an immediate read

    prev_a = btn_a_pin.value()
    prev_b = btn_b_pin.value()

    while True:
        now = _time_ms()

        # GPIO edge detection (pins are active-low: 1→0 is PRESS, 0→1 is RELEASE).
        cur_a = btn_a_pin.value()
        cur_b = btn_b_pin.value()
        if cur_a != prev_a:
            fsm.feed(Button.A, Edge.PRESS if cur_a == 0 else Edge.RELEASE)
            prev_a = cur_a
        if cur_b != prev_b:
            fsm.feed(Button.B, Edge.PRESS if cur_b == 0 else Edge.RELEASE)
            prev_b = cur_b

        dirty = False
        for event in fsm.drain():
            if app.handle(event):
                dirty = True

        for event in pwr.poll():
            if app.handle(event):
                dirty = True

        if dirty and sleep_mgr is not None:
            sleep_mgr.poke()
            display.wake()

        if time.ticks_diff(now, last_batt_ms) >= _BATT_REFRESH_MS:
            app.state.battery_pct = _read_battery(axp_bus) if axp_bus is not None else "?"
            last_batt_ms = now
            dirty = True

        if dirty:
            screen.render(display, app.state, app.ciphers)

        if sleep_mgr is not None:
            signal = sleep_mgr.tick()
            if signal == "lcd_sleep":
                display.sleep()
            elif signal == "power_off":
                display.sleep()
                _axp_power_off()

        time.sleep_ms(20)


def main() -> None:
    from machine import I2C, Pin  # type: ignore[import]

    # Check BTN A before any other hardware init.
    btn_a = Pin(_PIN_BTN_A, Pin.IN, Pin.PULL_UP)
    if btn_a.value() == 0:
        print("BTN A held at boot — dropping to REPL (safe mode)")
        sys.exit(0)

    try:
        from ui.display_m5 import M5Display  # type: ignore[import]

        buzzer = Buzzer(muted=False)

        axp_bus = I2C(0, sda=Pin(21), scl=Pin(22), freq=400_000)

        display = M5Display()
        pwr = PwrButton()
        batt = _read_battery(axp_bus)

        screen.render_splash(display, battery_pct=batt)
        buzzer.jingle_boot()
        time.sleep_ms(1500)

        btn_b = Pin(_PIN_BTN_B, Pin.IN, Pin.PULL_UP)

        saved_algo, saved_key = load_setup()
        state = State()
        state.screen = "setup_cipher"   # explicit: MicroPython shim ignores constructor kwargs
        state.algorithm = saved_algo
        state.cipher_key = saved_key
        ciphers = {name: cls() for name, cls in ALGORITHMS.items()}
        order = list(ciphers.keys())
        state.setup_idx = order.index(saved_algo) if saved_algo in order else 0
        cipher = ciphers.get(saved_algo)
        if hasattr(cipher, 'key'):
            cipher.key = saved_key  # type: ignore[attr-defined]

        def _save_fn(key: str) -> None:
            save_setup(state.algorithm, key)

        app = App(state, ciphers, on_save_key=_save_fn)
        cfg = load_config()
        screen.configure(cfg)
        fsm = ButtonFSM(
            _time_ms,
            btn_b_repeat_delay_ms=btn_b_repeat_delay_ms(cfg),
            btn_b_scroll_ms=btn_b_scroll_ms(cfg),
        )
        sleep_mgr = SleepManager(_time_ms)

        _run_loop(display, app, fsm, pwr, btn_a, btn_b, buzzer, axp_bus=axp_bus, sleep_mgr=sleep_mgr)

    except Exception as exc:
        print("CRASH:", exc)
        sys.print_exception(exc)
        print("Dropping to REPL — press Ctrl-D to soft-reboot")
        sys.exit(1)


if __name__ == "__main__":
    main()
