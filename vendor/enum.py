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


# metaclass= keyword is not supported in MicroPython class bodies; use EnumMeta() directly.
def _name_prop(self):
    return self._name_


def _value_prop(self):
    return self._value_


def _enum_repr(self):
    return f"<{self.__class__.__name__}.{self._name_}: {self._value_!r}>"


def _enum_str(self):
    return f"{self.__class__.__name__}.{self._name_}"


def _enum_hash(self):
    return hash(self._value_)


def _enum_eq(self, other):
    return self is other


Enum = EnumMeta(
    "Enum",
    (object,),
    {
        "name": property(_name_prop),
        "value": property(_value_prop),
        "__repr__": _enum_repr,
        "__str__": _enum_str,
        "__hash__": _enum_hash,
        "__eq__": _enum_eq,
    },
)
