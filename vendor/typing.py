# MicroPython shim: typing — Protocol, runtime_checkable, Literal
# Device uses these only for class *definition*; isinstance checks are host-only.


def _identity(cls):
    return cls


def runtime_checkable(cls):
    return cls


class _ProtocolMeta(type):
    pass


class Protocol(metaclass=_ProtocolMeta):
    pass


class _LiteralForm:
    def __getitem__(self, params):
        return params


Literal = _LiteralForm()
