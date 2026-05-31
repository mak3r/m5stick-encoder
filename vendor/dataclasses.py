# MicroPython shim: dataclasses — dataclass, field
# Implements enough for @dataclass classes with typed fields and defaults.


_MISSING = object()


class Field:
    __slots__ = ("name", "default", "default_factory", "repr", "init")

    def __init__(self, default, default_factory, repr, init):
        self.name = None
        self.default = default
        self.default_factory = default_factory
        self.repr = repr
        self.init = init


def field(*, default=_MISSING, default_factory=_MISSING, repr=True, init=True):
    if default is not _MISSING and default_factory is not _MISSING:
        raise ValueError("cannot specify both default and default_factory")
    return Field(default, default_factory, repr, init)


def _process_class(cls):
    annotations = {}
    for klass in reversed(cls.__mro__):
        annotations.update(getattr(klass, "__annotations__", {}))

    fields = []
    for name, _ in annotations.items():
        val = getattr(cls, name, _MISSING)
        f = val if isinstance(val, Field) else Field(val, _MISSING, True, True)
        f.name = name
        fields.append(f)

    def __init__(self, *args, **kwargs):
        init_fields = [f for f in fields if f.init]
        for i, f in enumerate(init_fields):
            if i < len(args):
                setattr(self, f.name, args[i])
            elif f.name in kwargs:
                setattr(self, f.name, kwargs[f.name])
            elif f.default is not _MISSING:
                setattr(self, f.name, f.default)
            elif f.default_factory is not _MISSING:
                setattr(self, f.name, f.default_factory())
            else:
                raise TypeError(f"missing argument: {f.name!r}")

    def __repr__(self):
        parts = [f"{f.name}={getattr(self, f.name)!r}" for f in fields if f.repr]
        return f"{cls.__name__}({', '.join(parts)})"

    def __eq__(self, other):
        if other.__class__ is not self.__class__:
            return NotImplemented
        return all(getattr(self, f.name) == getattr(other, f.name) for f in fields)

    cls.__init__ = __init__
    cls.__repr__ = __repr__
    cls.__eq__ = __eq__
    cls.__dataclass_fields__ = {f.name: f for f in fields}
    return cls


def dataclass(cls=None, *, eq=True, repr=True, init=True):
    def wrap(cls):
        return _process_class(cls)

    if cls is None:
        return wrap
    return wrap(cls)
