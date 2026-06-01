"""PWM buzzer on G2 for audible feedback.

MicroPython-only — excluded from host lint via ``pyproject.toml``.

Hold BTN A during boot to mute for the session: callers check
``Buzzer.muted`` and skip playback (actual boot-guard wiring lives in
``main.py``, see issue #10).
"""

try:
    from machine import PWM, Pin  # type: ignore[import]
    import time  # MicroPython built-in

    # G2 is the built-in buzzer pin on M5StickC PLUS.
    _PIN_BUZZ = 2

    def _tone(pwm: PWM, freq: int, ms: int) -> None:
        """Drive ``pwm`` at ``freq`` Hz for ``ms`` milliseconds, then silence."""
        pwm.freq(freq)
        pwm.duty(512)  # 50 % duty — audible, not maximally harsh
        time.sleep_ms(ms)
        pwm.duty(0)

    class Buzzer:
        """Audible feedback driver.

        Pass ``muted=True`` at construction (boot-flag check done by caller)
        to disable all playback for the session.
        """

        def __init__(self, muted: bool = False) -> None:
            self.muted = muted
            self._pwm = PWM(Pin(_PIN_BUZZ), freq=440, duty=0)

        def _play(self, notes: list[tuple[int, int]]) -> None:
            """Play a sequence of (freq_hz, duration_ms) pairs."""
            if self.muted:
                return
            for freq, ms in notes:
                _tone(self._pwm, freq, ms)

        def beep_commit(self) -> None:
            """Short single tone: letter committed to buffer."""
            self._play([(880, 50)])

        def beep_backspace(self) -> None:
            """Descending two-tone: last letter erased."""
            self._play([(880, 60), (440, 60)])

        def beep_mode(self) -> None:
            """Ascending two-tone: ENC/DEC mode toggled."""
            self._play([(440, 60), (880, 60)])

        def jingle_boot(self) -> None:
            """Four-note rising jingle played at startup."""
            self._play([(330, 80), (440, 80), (550, 80), (660, 120)])

        def deinit(self) -> None:
            self._pwm.deinit()

except ImportError:
    # Running on host — Buzzer is not available but the module loads fine.
    class Buzzer:  # type: ignore[no-redef]
        """Stub: hardware not available on host."""

        def __init__(self, muted: bool = False) -> None:
            self.muted = muted

        def _play(self, notes: list) -> None:  # pragma: no cover
            raise RuntimeError("Buzzer requires MicroPython machine module")

        def beep_commit(self) -> None:
            raise RuntimeError("Buzzer requires MicroPython machine module")

        def beep_backspace(self) -> None:
            raise RuntimeError("Buzzer requires MicroPython machine module")

        def beep_mode(self) -> None:
            raise RuntimeError("Buzzer requires MicroPython machine module")

        def jingle_boot(self) -> None:
            raise RuntimeError("Buzzer requires MicroPython machine module")

        def deinit(self) -> None:
            raise RuntimeError("Buzzer requires MicroPython machine module")
