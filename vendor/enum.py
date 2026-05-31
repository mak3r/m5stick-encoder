# MicroPython shim: enum — Enum
# Uses __init_subclass__ to avoid metaclass; MicroPython metaclass support segfaults.


class Enum:
    def __init_subclass__(cls, **kwargs):
        members = {}
        for key in list(cls.__dict__):
            if key.startswith("_"):
                continue
            val = cls.__dict__[key]
            if isinstance(val, (classmethod, staticmethod, property)):
                continue
            if callable(val):
                continue
            obj = object.__new__(cls)
            obj._name_ = key
            obj._value_ = val
            members[key] = obj
            setattr(cls, key, obj)
        cls._member_map_ = members

    @property
    def name(self):
        return self._name_

    @property
    def value(self):
        return self._value_

    def __repr__(self):
        return f"<{type(self).__name__}.{self._name_}: {self._value_!r}>"

    def __str__(self):
        return f"{type(self).__name__}.{self._name_}"

    def __hash__(self):
        return hash(self._value_)

    def __eq__(self, other):
        return self is other
