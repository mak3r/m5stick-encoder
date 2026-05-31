# MicroPython shim: enum — Enum
# Members are singletons; identity (is) and equality (==) both work.


class EnumMeta(type):
    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)
        members = {}
        inherited = set()
        for b in bases:
            if b is not object:
                inherited.update(b.__dict__)
        for key, val in list(namespace.items()):
            if key.startswith("_"):
                continue
            if key in inherited:
                continue
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
        return cls

    def __iter__(cls):
        return iter(cls._member_map_.values())

    def __contains__(cls, item):
        return item in cls._member_map_.values()

    def __len__(cls):
        return len(cls._member_map_)


class Enum(metaclass=EnumMeta):
    @property
    def name(self):
        return self._name_

    @property
    def value(self):
        return self._value_

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self._name_}: {self._value_!r}>"

    def __str__(self):
        return f"{self.__class__.__name__}.{self._name_}"

    def __hash__(self):
        return hash(self._value_)

    def __eq__(self, other):
        return self is other
