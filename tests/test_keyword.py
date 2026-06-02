"""Tests for encoder/keyword.py — KeywordCipher (substitution)."""

import pytest

from encoder.keyword import KeywordCipher

# ---------------------------------------------------------------------------
# Alphabet construction
# ---------------------------------------------------------------------------

def test_build_zebra():
    c = KeywordCipher("ZEBRA")
    assert c._cipher == "ZEBRACDFGHIJKLMNOPQSTUVWXY"


def test_build_hello_collapses_duplicate_l():
    c = KeywordCipher("HELLO")
    assert c._cipher == "HELOABCDFGIJKMNPQRSTUVWXYZ"


def test_build_single_letter():
    c = KeywordCipher("Z")
    assert c._cipher == "ZABCDEFGHIJKLMNOPQRSTUVWXY"


def test_build_full_alphabet_key_is_identity():
    # Key covers all 26 letters — cipher alphabet equals the key.
    key = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    c = KeywordCipher(key)
    assert c._cipher == key


def test_build_all_same_letter():
    # "AAAAA" dedupes to "A"; remaining in order.
    c = KeywordCipher("AAAAA")
    assert c._cipher == "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


# ---------------------------------------------------------------------------
# Known-answer encode
# ---------------------------------------------------------------------------

def test_encode_a_with_zebra_gives_z():
    assert KeywordCipher("ZEBRA").encode("A") == "Z"


def test_encode_abcde_with_zebra_gives_zebra():
    assert KeywordCipher("ZEBRA").encode("ABCDE") == "ZEBRA"


def test_encode_hello_with_zebra():
    # H→G, E→A, L→J, L→J, O→N  (cipher: ZEBRACDFGHIJKLMNOPQSTUVWXY)
    # A(0)→Z, B(1)→E, C(2)→B, D(3)→R, E(4)→A, F(5)→C, G(6)→D, H(7)→F,
    # I(8)→G, J(9)→H, K(10)→I, L(11)→J, M(12)→K, N(13)→L, O(14)→M
    assert KeywordCipher("ZEBRA").encode("HELLO") == "FAJJM"


def test_encode_is_identity_when_key_is_alphabet():
    key = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    plain = "THEQUICKBROWNFOX"
    assert KeywordCipher(key).encode(plain) == plain


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("key", ["ZEBRA", "HELLO", "KEY", "A", "SECRET"])
def test_round_trip(key):
    plain = "THEQUICKBROWNFOXJUMPSOVERTHELAZYDOG"
    c = KeywordCipher(key)
    assert c.decode(c.encode(plain)) == plain


def test_encode_empty_returns_empty():
    assert KeywordCipher("ZEBRA").encode("") == ""


def test_decode_empty_returns_empty():
    assert KeywordCipher("ZEBRA").decode("") == ""


# ---------------------------------------------------------------------------
# Key property
# ---------------------------------------------------------------------------

def test_default_key_is_KEY():
    assert KeywordCipher().key == "KEY"


def test_name_attribute():
    assert KeywordCipher.name == "keyword"


def test_init_empty_key_falls_back_to_default():
    assert KeywordCipher("").key == "KEY"


def test_key_is_uppercased_on_init():
    assert KeywordCipher("secret").key == "SECRET"


def test_key_setter_rebuilds_alphabet():
    c = KeywordCipher("A")
    old_cipher = c._cipher
    c.key = "ZEBRA"
    assert c._cipher != old_cipher
    assert c._cipher == "ZEBRACDFGHIJKLMNOPQSTUVWXY"


def test_key_setter_empty_resets_to_default():
    c = KeywordCipher("ZEBRA")
    c.key = ""
    assert c.key == "KEY"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def test_encode_raises_on_lowercase():
    with pytest.raises(ValueError):
        KeywordCipher("ZEBRA").encode("hello")


def test_encode_raises_on_digit():
    with pytest.raises(ValueError):
        KeywordCipher("ZEBRA").encode("A1B")


def test_decode_raises_on_space():
    with pytest.raises(ValueError):
        KeywordCipher("ZEBRA").decode("A B")


# ---------------------------------------------------------------------------
# Monoalphabetic: cipher row never changes with in_buf
# ---------------------------------------------------------------------------

def test_encode_alphabet_is_permutation():
    # encode(A-Z) must be a permutation — 26 distinct letters, no duplicates.
    plain = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    result = KeywordCipher("ZEBRA").encode(plain)
    assert sorted(result) == list(plain)
