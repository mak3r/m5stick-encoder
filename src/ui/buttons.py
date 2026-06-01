from collections.abc import Callable

from ui.events import Button, ButtonEvent, Edge

DEBOUNCE_MS = 20
LONG_PRESS_MS = 1000
DOUBLE_WINDOW_MS = 300

# BtnB auto-scroll: initial delay before repeat begins, then interval.
BTN_B_REPEAT_DELAY_MS = 500
BTN_B_SCROLL_MS = 300


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

    BTN_B rules:
    - BTN_B_PRESS emits immediately on PRESS.
    - While held past BTN_B_REPEAT_DELAY_MS, drain() emits BTN_B_LONG
      every BTN_B_SCROLL_MS so the caller scrolls the wheel continuously.
    - RELEASE clears the hold state; no event is emitted on release.

    All timing is driven by an injected ``time_ms_fn`` so tests can run
    against a virtual clock.
    """

    def __init__(
        self,
        time_ms_fn: Callable[[], int],
        btn_b_repeat_delay_ms: int = BTN_B_REPEAT_DELAY_MS,
        btn_b_scroll_ms: int = BTN_B_SCROLL_MS,
    ):
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

        # BtnB auto-scroll state
        self._btn_b_press_ms: int | None = None
        self._btn_b_last_scroll_ms: int | None = None
        self._btn_b_repeat_delay_ms = btn_b_repeat_delay_ms
        self._btn_b_scroll_ms = btn_b_scroll_ms

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
            self._btn_b_press_ms = now
            self._btn_b_last_scroll_ms = None
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
        if button is Button.B:
            self._btn_b_press_ms = None
            self._btn_b_last_scroll_ms = None
        elif button is Button.A:
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
        # BtnB auto-scroll: emit BTN_B_LONG while held past the repeat delay.
        if self._btn_b_press_ms is not None:
            held = now - self._btn_b_press_ms
            if held >= self._btn_b_repeat_delay_ms:
                if self._btn_b_last_scroll_ms is None:
                    # First repeat tick.
                    self._pending.append(ButtonEvent.BTN_B_LONG)
                    self._btn_b_last_scroll_ms = now
                elif now - self._btn_b_last_scroll_ms >= self._btn_b_scroll_ms:
                    self._pending.append(ButtonEvent.BTN_B_LONG)
                    self._btn_b_last_scroll_ms = now
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
