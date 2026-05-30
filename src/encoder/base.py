"""Cipher protocol every algorithm in ``ALGORITHMS`` must satisfy.

A ``Protocol`` (rather than an ``abc.ABC``) is used so structural checks
work without forcing existing ciphers to inherit a base class. The
``@runtime_checkable`` decorator lets tests assert conformance via
``isinstance``.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class Cipher(Protocol):
    name: str

    def encode(self, text: str) -> str: ...

    def decode(self, text: str) -> str: ...
