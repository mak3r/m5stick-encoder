from encoder import ALGORITHMS, Cipher
from encoder.rot13 import Rot13Cipher


def test_algorithms_contains_rot13():
    assert "rot13" in ALGORITHMS
    assert ALGORITHMS["rot13"] is Rot13Cipher


def test_rot13_instance_satisfies_cipher_protocol():
    assert isinstance(Rot13Cipher(), Cipher)


def test_all_registered_algorithms_satisfy_cipher_protocol():
    for key, cls in ALGORITHMS.items():
        instance = cls()
        assert isinstance(instance, Cipher), f"{key} does not satisfy Cipher protocol"


def test_registered_name_matches_key():
    for key, cls in ALGORITHMS.items():
        assert cls.name == key


def test_registry_values_are_callable_classes():
    for cls in ALGORITHMS.values():
        assert callable(cls)
        instance = cls()
        assert hasattr(instance, "encode")
        assert hasattr(instance, "decode")
