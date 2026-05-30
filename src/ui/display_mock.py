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


@dataclass
class RectCall:
    x: int
    y: int
    w: int
    h: int
    color: int
    fill: bool = False


@dataclass
class ShowCall:
    pass


@dataclass
class DisplayMock:
    width: int = 240
    height: int = 135
    calls: list = field(default_factory=list)

    def fill(self, color: int) -> None:
        self.calls.append(FillCall(color=color))

    def text(self, s: str, x: int, y: int, color: int, scale: int = 1) -> None:
        self.calls.append(TextCall(s=s, x=x, y=y, color=color, scale=scale))

    def rect(self, x: int, y: int, w: int, h: int, color: int, fill: bool = False) -> None:
        self.calls.append(RectCall(x=x, y=y, w=w, h=h, color=color, fill=fill))

    def show(self) -> None:
        self.calls.append(ShowCall())

    def texts(self) -> list[TextCall]:
        return [c for c in self.calls if isinstance(c, TextCall)]

    def rects(self) -> list[RectCall]:
        return [c for c in self.calls if isinstance(c, RectCall)]
