"""Host-side ``Display`` that records every draw call.

Tests assert against the call log (``calls`` / typed accessors) instead
of inspecting pixels — layout is verified by intent (what was drawn,
where, at which scale) rather than bitmap content.
"""

from dataclasses import dataclass, field


@dataclass
class FillCall:
    color: int


@dataclass
class TextCall:
    s: str
    x: int
    y: int
    color: int
    scale: int = 1
    center_x: bool = False


@dataclass
class RectCall:
    x: int
    y: int
    w: int
    h: int
    color: int
    fill: bool = False


@dataclass
class LoadFontCall:
    name: str


@dataclass
class UnloadFontCall:
    pass


@dataclass
class ShowCall:
    pass


@dataclass
class SleepCall:
    pass


@dataclass
class WakeCall:
    pass


@dataclass
class DisplayMock:
    width: int = 240
    height: int = 135
    calls: list = field(default_factory=list)
    _font: str = field(default="", repr=False)  # currently-loaded font name ("")=none

    def fill(self, color: int) -> None:
        self.calls.append(FillCall(color=color))

    def text(  # noqa: PLR0913
        self, s: str, x: int, y: int, color: int, scale: int = 1, center_x: bool = False
    ) -> None:
        self.calls.append(TextCall(s=s, x=x, y=y, color=color, scale=scale, center_x=center_x))

    def rect(self, x: int, y: int, w: int, h: int, color: int, fill: bool = False) -> None:
        self.calls.append(RectCall(x=x, y=y, w=w, h=h, color=color, fill=fill))

    def load_font(self, name: str) -> None:
        self._font = name
        self.calls.append(LoadFontCall(name=name))

    def unload_font(self) -> None:
        self._font = ""
        self.calls.append(UnloadFontCall())

    def text_width(self, s: str) -> int:
        # Mock returns GLYPH_W per character regardless of font — consistent
        # for layout tests which check relative spacing, not pixel accuracy.
        from ui.screen import GLYPH_W
        return len(s) * GLYPH_W

    def show(self) -> None:
        self.calls.append(ShowCall())

    def sleep(self) -> None:
        self.calls.append(SleepCall())

    def wake(self) -> None:
        self.calls.append(WakeCall())

    def texts(self) -> list[TextCall]:
        return [c for c in self.calls if isinstance(c, TextCall)]

    def rects(self) -> list[RectCall]:
        return [c for c in self.calls if isinstance(c, RectCall)]
