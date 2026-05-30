"""Host simulator for the m5stick-encoder UI.

Opens a tkinter window approximating the M5StickC PLUS landscape display
(240x135 logical pixels, scaled 4x to 960x540 for visibility) and runs the
same ``App`` + ``screen.render`` that ships to the device. Keyboard input
is fed through the same ``ButtonFSM`` used on hardware so short/double/
long-press semantics are exercised end-to-end.

Keyboard map (also displayed in the help overlay):
- ``[`` or ``a`` -> BTN A
- ``]`` or ``b`` -> BTN B
- ``space`` -> PWR (tap = short, double-tap = double, hold ~1s = long)

Run with ``make sim`` or ``python tools/sim.py``. No dependencies beyond
stdlib tkinter.
"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Callable

# Make ``src/`` importable when invoked as ``python tools/sim.py`` from the
# repo root.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(_REPO_ROOT, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from encoder import ALGORITHMS  # noqa: E402
from ui.app import App  # noqa: E402
from ui.buttons import ButtonFSM  # noqa: E402
from ui.events import Button, Edge  # noqa: E402
from ui.screen import render  # noqa: E402
from ui.state import State  # noqa: E402

LOGICAL_W = 240
LOGICAL_H = 135
DEFAULT_SCALE = 4
TICK_MS = 50

# Map the abstract color ints from screen.render to concrete RGB tuples.
# BG=0 black, FG=1 white (panel reads in ambient light), ACCENT=2 amber/
# orange to evoke the M5StickC's amber PWR LED for the focused selection.
COLOR_MAP: dict[int, str] = {
    0: "#000000",
    1: "#ffffff",
    2: "#ffb000",
}

# Keyboard symbols mapped to logical buttons. Lowercase is canonical; the
# tkinter ``keysym`` for ``[`` / ``]`` is ``bracketleft`` / ``bracketright``
# and for the space key is ``space``.
KEY_TO_BUTTON: dict[str, Button] = {
    "a": Button.A,
    "bracketleft": Button.A,
    "b": Button.B,
    "bracketright": Button.B,
    "space": Button.PWR,
}


class KeyboardAdapter:
    """Pure-logic glue between keyboard events and the App stack.

    Suppresses tkinter's auto-repeat: only the first PRESS for a held key
    is forwarded to the FSM; the matching RELEASE clears the held flag.
    """

    def __init__(
        self,
        app: App,
        fsm: ButtonFSM,
        render_fn: Callable[[], None],
    ) -> None:
        self._app = app
        self._fsm = fsm
        self._render = render_fn
        self._held: dict[Button, bool] = {b: False for b in Button}

    def on_key_press(self, keysym: str) -> bool:
        button = self._lookup(keysym)
        if button is None:
            return False
        if self._held[button]:
            # Auto-repeat suppression: only the first PRESS counts.
            return self._drain_and_render()
        self._held[button] = True
        self._fsm.feed(button, Edge.PRESS)
        return self._drain_and_render()

    def on_key_release(self, keysym: str) -> bool:
        button = self._lookup(keysym)
        if button is None:
            return False
        if not self._held[button]:
            return False
        self._held[button] = False
        self._fsm.feed(button, Edge.RELEASE)
        return self._drain_and_render()

    def tick(self) -> bool:
        """Drain time-driven events (e.g. eager PWR_LONG, expiring shorts)."""
        return self._drain_and_render()

    def _lookup(self, keysym: str) -> Button | None:
        return KEY_TO_BUTTON.get(keysym.lower())

    def _drain_and_render(self) -> bool:
        dirty = False
        for event in self._fsm.drain():
            if self._app.handle(event):
                dirty = True
        if dirty:
            self._render()
        return dirty


def _import_tk():
    """Import tkinter; return (tk_module, None) or (None, error_str)."""
    try:
        import tkinter as tk

        return tk, None
    except ImportError as exc:  # pragma: no cover - exercised only without Tk
        return None, str(exc)


class TkDisplay:
    """Tkinter-backed ``Display`` implementation.

    Operates in logical 240x135 pixel coordinates; the canvas size is
    ``logical * scale``. Glyph metrics match the 8x8 base font convention
    documented in ``ui.display`` so layouts produced here match the panel.
    """

    def __init__(self, canvas, scale: int = DEFAULT_SCALE) -> None:
        self.width = LOGICAL_W
        self.height = LOGICAL_H
        self._canvas = canvas
        self._scale = scale
        # Monospace font sized so each char cell is ``8 * scale`` px wide.
        # Tk font sizing is in points; matching cell width exactly is fiddly,
        # so use ``size = 8 * scale`` which yields glyphs slightly narrower
        # than 8px cells in most monospace faces -- visually close enough
        # for usability testing.
        self._base_px = 8 * scale

    def fill(self, color: int) -> None:
        self._canvas.delete("all")
        rgb = COLOR_MAP.get(color, "#000000")
        self._canvas.create_rectangle(
            0, 0, self.width * self._scale, self.height * self._scale,
            fill=rgb, outline=rgb,
        )

    def text(self, s: str, x: int, y: int, color: int, scale: int = 1) -> None:
        rgb = COLOR_MAP.get(color, "#ffffff")
        size_px = self._base_px * scale
        self._canvas.create_text(
            x * self._scale,
            y * self._scale,
            text=s,
            fill=rgb,
            anchor="nw",
            font=("Courier", -size_px, "bold"),
        )

    def rect(self, x: int, y: int, w: int, h: int, color: int, fill: bool = False) -> None:
        rgb = COLOR_MAP.get(color, "#ffffff")
        x0 = x * self._scale
        y0 = y * self._scale
        x1 = (x + w) * self._scale
        y1 = (y + h) * self._scale
        if fill:
            self._canvas.create_rectangle(x0, y0, x1, y1, fill=rgb, outline=rgb)
        else:
            self._canvas.create_rectangle(x0, y0, x1, y1, outline=rgb)

    def show(self) -> None:
        self._canvas.update_idletasks()


def _time_ms() -> int:
    return int(time.monotonic() * 1000)


def _build_app() -> tuple[App, ButtonFSM, State]:
    state = State()
    ciphers = {name: cls() for name, cls in ALGORITHMS.items()}
    app = App(state, ciphers)
    fsm = ButtonFSM(_time_ms)
    return app, fsm, state


HELP_TEXT = (
    "Keys: [ / a = BTN A   ] / b = BTN B   space = PWR "
    "(tap=short, double=back, hold=mode)"
)


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        print(HELP_TEXT)
        return 0

    tk, err = _import_tk()
    if tk is None:
        print(
            f"sim: tkinter is not available in this Python build: {err}",
            file=sys.stderr,
        )
        print(
            "Install Python with Tk support (e.g. python.org installer on macOS)",
            file=sys.stderr,
        )
        return 2

    try:
        root = tk.Tk()
    except tk.TclError as exc:  # pragma: no cover - DISPLAY-less environments
        print(f"sim: cannot open Tk window: {exc}", file=sys.stderr)
        return 2

    scale = DEFAULT_SCALE
    root.title("m5stick-encoder simulator")
    root.resizable(False, False)

    canvas = tk.Canvas(
        root,
        width=LOGICAL_W * scale,
        height=LOGICAL_H * scale,
        background=COLOR_MAP[0],
        highlightthickness=0,
    )
    canvas.pack()

    help_label = tk.Label(
        root,
        text=HELP_TEXT,
        font=("Helvetica", 11),
        fg="#dddddd",
        bg="#222222",
        padx=8,
        pady=4,
        anchor="w",
        justify="left",
    )
    help_label.pack(fill="x")

    app, fsm, _state = _build_app()
    display = TkDisplay(canvas, scale=scale)

    def do_render() -> None:
        render(display, app.state)

    adapter = KeyboardAdapter(app, fsm, do_render)

    # Initial paint scheduled via root.after(0, ...) so it runs after the
    # mainloop starts and the canvas is realized. Painting before
    # realization is a no-op on macOS system Tk and leaves the canvas blank.
    root.after(0, do_render)

    def on_press(event) -> None:
        adapter.on_key_press(event.keysym)

    def on_release(event) -> None:
        adapter.on_key_release(event.keysym)

    root.bind("<KeyPress>", on_press)
    root.bind("<KeyRelease>", on_release)

    def tick() -> None:
        adapter.tick()
        root.after(TICK_MS, tick)

    root.after(TICK_MS, tick)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
