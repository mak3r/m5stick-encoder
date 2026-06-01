import pytest

from encoder.keyword import KeywordCipher


def test_default_key_is_KEY():
    c = KeywordCipher()
    assert c.key == "KEY"


def test_no_arg_constructor_works():
    c = KeywordCipher()
    assert isinstance(c, KeywordCipher)


def test_key_is_uppercased_on_init():
    c = KeywordCipher("secret")
    assert c.key == "SECRET"


def test_key_setter_uppercases():
    c = KeywordCipher()
    c.key = "abc"
    assert c.key == "ABC"


def test_key_setter_empty_falls_back_to_default():
    c = KeywordCipher("HELLO")
    c.key = ""
    assert c.key == "KEY"


def test_encode_single_letter_key_is_caesar():
    # Key "C" = shift 2; A → C, Z → B
    c = KeywordCipher("C")
    assert c.encode("A") == "C"
    assert c.encode("Z") == "B"


def test_decode_single_letter_key_is_inverse_caesar():
    c = KeywordCipher("C")
    assert c.decode("C") == "A"
    assert c.decode("B") == "Z"


def test_encode_decode_round_trip_multi_letter_key():
    c = KeywordCipher("SECRET")
    plaintext = "HELLO"
    assert c.decode(c.encode(plaintext)) == plaintext


def test_encode_decode_round_trip_long_message():
    c = KeywordCipher("KEY")
    msg = "THEQUICKBROWNFOXJUMPSOVERTHELAZYDOG"
    assert c.decode(c.encode(msg)) == msg


def test_encode_is_not_same_as_decode_for_nontrivial_key():
    c = KeywordCipher("SECRET")
    text = "HELLO"
    assert c.encode(text) != c.decode(text)


def test_encode_key_cycles_over_message():
    # Key "AB": A=shift 0, B=shift 1 → H→H, E→F, L→L, L→M, O→O
    c = KeywordCipher("AB")
    assert c.encode("HELLO") == "HFLMO"


def test_decode_key_cycles_over_message():
    c = KeywordCipher("AB")
    assert c.decode("HFLMO") == "HELLO"


def test_encode_empty_string_returns_empty():
    c = KeywordCipher()
    assert c.encode("") == ""


def test_decode_empty_string_returns_empty():
    c = KeywordCipher()
    assert c.decode("") == ""


def test_raises_on_lowercase():
    c = KeywordCipher()
    with pytest.raises(ValueError):
        c.encode("hello")


def test_raises_on_digit():
    c = KeywordCipher()
    with pytest.raises(ValueError):
        c.encode("A1B")


def test_raises_on_space():
    c = KeywordCipher()
    with pytest.raises(ValueError):
        c.encode("A B")


def test_encode_decode_all_letters():
    c = KeywordCipher("PYTHON")
    alpha = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    assert c.decode(c.encode(alpha)) == alpha
