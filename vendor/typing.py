# MicroPython shim: typing — Protocol, runtime_checkable, Literal
# Device uses these only for class *definition*; isinstance checks are host-only.
# metaclass= keyword is not supported in MicroPython class bodies; use type() directly.


def _identity(cls):
    return cls


def runtime_checkable(cls):
    return cls


_ProtocolMeta = type("_ProtocolMeta", (type,), {})
Protocol = _ProtocolMeta("Protocol", (object,), {})


class _LiteralForm:
    def __getitem__(self, params):
        return params


Literal = _LiteralForm()
