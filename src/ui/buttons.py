from collections.abc import Callable

from ui.events import Button, ButtonEvent, Edge

DEBOUNCE_MS = 20
LONG_PRESS_MS = 1000
DOUBLE_WINDOW_MS = 300


class ButtonFSM:
    """Translate raw (button, edge) inputs into high-level ButtonEvents.

    BtnA rules (mirrors PWR double/long logic):
    - hold >= LONG_PRESS_MS emits BTN_A_LONG (fired on release, or eagerly
      during drain() if the hold has already crossed the threshold)
    - a release within < LONG_PRESS_MS is provisionally a short:
      if a second short arrives within DOUBLE_WINDOW_MS, the pair is
      emitted as BTN_A_DOUBLE; otherwise BTN_A_PRESS is emitted once the
      window expires (checked at drain() time)

    PWR rules:
    - hold >= LONG_PRESS_MS emits PWR_LONG (fired on release, or eagerly
      during drain() if the hold has already crossed the threshold and no
      release has been observed yet)
    - a release within < LONG_PRESS_MS of press is provisionally a short:
      if a second short arrives within DOUBLE_WINDOW_MS, the pair is
      emitted as PWR_DOUBLE; otherwise PWR_SHORT is emitted once the
      window expires (checked at drain() time)

    BTN_B emits BTN_B_PRESS immediately on PRESS; RELEASE is ignored.

    All timing is driven by an injected ``time_ms_fn`` so tests can run
    against a virtual clock.
    """

    def __init__(self, time_ms_fn: Callable[[], int]):
        self._now = time_ms_fn
        self._pending: list[ButtonEvent] = []
        self._last_press_ms: dict[Button, int] = {}

        self._btn_a_press_ms: int | None = None
        self._btn_a_long_emitted = False
        self._btn_a_pending_short_release_ms: int | None = None
        self._btn_a_press_consumed_by_double = False

        self._pwr_press_ms: int | None = None
        self._pwr_long_emitted = False
        self._pwr_pending_short_release_ms: int | None = None
        self._pwr_press_consumed_by_double = False

    def feed(self, button: Button, edge: Edge) -> None:
        now = self._now()
        if edge is Edge.PRESS:
            # Debounce: drop any PRESS edge that arrives within DEBOUNCE_MS
            # of the previous PRESS on the same button.
            last = self._last_press_ms.get(button)
            if last is not None and now - last < DEBOUNCE_MS:
                return
            self._last_press_ms[button] = now
            self._on_press(button, now)
        else:
            self._on_release(button, now)

    def _on_press(self, button: Button, now: int) -> None:
        if button is Button.B:
            self._pending.append(ButtonEvent.BTN_B_PRESS)
            return
        if button is Button.A:
            self._on_btn_a_press(now)
            return
        # PWR press
        self._on_pwr_press(now)

    def _on_btn_a_press(self, now: int) -> None:
        if self._btn_a_pending_short_release_ms is not None:
            if now - self._btn_a_pending_short_release_ms <= DOUBLE_WINDOW_MS:
                self._pending.append(ButtonEvent.BTN_A_DOUBLE)
                self._btn_a_pending_short_release_ms = None
                self._btn_a_press_ms = now
                self._btn_a_long_emitted = False
                self._btn_a_press_consumed_by_double = True
                return
            # Stale pending short — flush it before starting a new press.
            self._pending.append(ButtonEvent.BTN_A_PRESS)
            self._btn_a_pending_short_release_ms = None
        self._btn_a_press_ms = now
        self._btn_a_long_emitted = False
        self._btn_a_press_consumed_by_double = False

    def _on_pwr_press(self, now: int) -> None:
        if self._pwr_pending_short_release_ms is not None:
            if now - self._pwr_pending_short_release_ms <= DOUBLE_WINDOW_MS:
                self._pending.append(ButtonEvent.PWR_DOUBLE)
                self._pwr_pending_short_release_ms = None
                self._pwr_press_ms = now
                self._pwr_long_emitted = False
                self._pwr_press_consumed_by_double = True
                return
            # Stale pending short — flush it before starting a new press.
            self._pending.append(ButtonEvent.PWR_SHORT)
            self._pwr_pending_short_release_ms = None
        self._pwr_press_ms = now
        self._pwr_long_emitted = False
        self._pwr_press_consumed_by_double = False

    def _on_release(self, button: Button, now: int) -> None:
        if button is Button.A:
            self._on_btn_a_release(now)
        elif button is Button.PWR:
            self._on_pwr_release(now)

    def _on_btn_a_release(self, now: int) -> None:
        if self._btn_a_press_ms is None:
            return
        held = now - self._btn_a_press_ms
        press_consumed = self._btn_a_press_consumed_by_double
        self._btn_a_press_ms = None
        self._btn_a_press_consumed_by_double = False
        if self._btn_a_long_emitted:
            return
        if held >= LONG_PRESS_MS:
            self._pending.append(ButtonEvent.BTN_A_LONG)
            return
        if press_consumed:
            return
        self._btn_a_pending_short_release_ms = now

    def _on_pwr_release(self, now: int) -> None:
        if self._pwr_press_ms is None:
            return
        held = now - self._pwr_press_ms
        press_consumed = self._pwr_press_consumed_by_double
        self._pwr_press_ms = None
        self._pwr_press_consumed_by_double = False
        if self._pwr_long_emitted:
            return
        if held >= LONG_PRESS_MS:
            self._pending.append(ButtonEvent.PWR_LONG)
            return
        if press_consumed:
            return
        self._pwr_pending_short_release_ms = now

    def drain(self) -> list[ButtonEvent]:
        now = self._now()
        # Eager BTN_A_LONG: held past threshold with no release yet.
        if (
            self._btn_a_press_ms is not None
            and not self._btn_a_long_emitted
            and now - self._btn_a_press_ms >= LONG_PRESS_MS
        ):
            self._pending.append(ButtonEvent.BTN_A_LONG)
            self._btn_a_long_emitted = True
        # Resolve pending BTN_A short whose double-window has expired.
        if (
            self._btn_a_pending_short_release_ms is not None
            and now - self._btn_a_pending_short_release_ms > DOUBLE_WINDOW_MS
        ):
            self._pending.append(ButtonEvent.BTN_A_PRESS)
            self._btn_a_pending_short_release_ms = None
        # Eager PWR_LONG: held past threshold with no release yet.
        if (
            self._pwr_press_ms is not None
            and not self._pwr_long_emitted
            and now - self._pwr_press_ms >= LONG_PRESS_MS
        ):
            self._pending.append(ButtonEvent.PWR_LONG)
            self._pwr_long_emitted = True
        # Resolve any pending short whose double-window has expired.
        if (
            self._pwr_pending_short_release_ms is not None
            and now - self._pwr_pending_short_release_ms > DOUBLE_WINDOW_MS
        ):
            self._pending.append(ButtonEvent.PWR_SHORT)
            self._pwr_pending_short_release_ms = None
        events = self._pending
        self._pending = []
        return events
