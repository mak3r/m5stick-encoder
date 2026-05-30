import pytest

from encoder.rot13 import Rot13Cipher

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
ROTATED = "NOPQRSTUVWXYZABCDEFGHIJKLM"


def test_name_attribute():
    assert Rot13Cipher.name == "rot13"


def test_full_alphabet_encodes_to_rotated():
    assert Rot13Cipher().encode(ALPHABET) == ROTATED


def test_full_alphabet_decodes_to_rotated():
    assert Rot13Cipher().decode(ALPHABET) == ROTATED


def test_encode_equals_decode_self_inverse():
    cipher = Rot13Cipher()
    for ch in ALPHABET:
        assert cipher.encode(ch) == cipher.decode(ch)


def test_round_trip_every_letter():
    cipher = Rot13Cipher()
    for ch in ALPHABET:
        assert cipher.decode(cipher.encode(ch)) == ch


def test_round_trip_full_alphabet():
    cipher = Rot13Cipher()
    assert cipher.decode(cipher.encode(ALPHABET)) == ALPHABET


def test_empty_string():
    cipher = Rot13Cipher()
    assert cipher.encode("") == ""
    assert cipher.decode("") == ""


@pytest.mark.parametrize("ch", ["a", "z", "0", " ", "!", "\n"])
def test_unsupported_characters_raise(ch):
    cipher = Rot13Cipher()
    with pytest.raises(ValueError):
        cipher.encode(ch)
    with pytest.raises(ValueError):
        cipher.decode(ch)
