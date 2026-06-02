"""Tests for encoder/caesar.py — CaesarCipher."""

import pytest

from encoder.caesar import CaesarCipher


def test_default_key_is_d():
    assert CaesarCipher().key == "D"


def test_name_attribute():
    assert CaesarCipher.name == "caesar"


def test_max_key_len_is_1():
    assert CaesarCipher.max_key_len == 1


# ---------------------------------------------------------------------------
# Known-answer tests
# ---------------------------------------------------------------------------

def test_encode_hello_key_f():
    # F = shift 5; H+5=M, E+5=J, L+5=Q, L+5=Q, O+5=T
    assert CaesarCipher("F").encode("HELLO") == "MJQQT"


def test_decode_mjqqt_key_f():
    assert CaesarCipher("F").decode("MJQQT") == "HELLO"


def test_encode_key_a_is_identity():
    # A = shift 0: no change
    assert CaesarCipher("A").encode("HELLO") == "HELLO"


def test_encode_key_z_wraps():
    # Z = shift 25: A→Z, B→A
    assert CaesarCipher("Z").encode("AB") == "ZA"


def test_decode_key_z_wraps():
    assert CaesarCipher("Z").decode("ZA") == "AB"


def test_encode_full_alphabet_key_d():
    # shift 3: ABCDE...XYZ → DEFGH...ABC
    result = CaesarCipher("D").encode("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    assert result == "DEFGHIJKLMNOPQRSTUVWXYZABC"


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("key", ["A", "D", "F", "N", "Z"])
def test_encode_decode_round_trip(key):
    plain = "THEQUICKBROWNFOXJUMPSOVERTHELAZYDOG"
    assert CaesarCipher(key).decode(CaesarCipher(key).encode(plain)) == plain


def test_encode_is_not_self_inverse():
    # Unlike rot13, caesar with non-N shift is not self-inverse.
    assert CaesarCipher("D").encode("HELLO") != "HELLO"
    assert CaesarCipher("D").encode(CaesarCipher("D").encode("HELLO")) != "HELLO"


# ---------------------------------------------------------------------------
# Key property
# ---------------------------------------------------------------------------

def test_key_setter_updates_shift():
    c = CaesarCipher("A")
    c.key = "F"
    assert c.encode("HELLO") == "MJQQT"


def test_key_setter_takes_first_char():
    c = CaesarCipher()
    c.key = "FXX"   # only 'F' should be used
    assert c.key == "F"


def test_key_setter_empty_resets_to_default():
    c = CaesarCipher("Z")
    c.key = ""
    assert c.key == "D"


def test_init_empty_key_defaults_to_d():
    assert CaesarCipher("").key == "D"


def test_key_is_uppercased():
    assert CaesarCipher("f").key == "F"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def test_encode_raises_on_lowercase():
    with pytest.raises(ValueError):
        CaesarCipher().encode("hello")


def test_encode_raises_on_digit():
    with pytest.raises(ValueError):
        CaesarCipher().encode("A1B")


def test_decode_raises_on_non_az():
    with pytest.raises(ValueError):
        CaesarCipher().decode("A B")
