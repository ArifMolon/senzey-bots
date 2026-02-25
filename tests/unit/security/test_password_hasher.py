"""Unit tests for password_hasher module."""

from senzey_bots.security.password_hasher import (
    check_needs_rehash,
    hash_password,
    verify_password,
)


def test_hash_password_returns_non_empty_string() -> None:
    hashed = hash_password("secret")
    assert isinstance(hashed, str)
    assert len(hashed) > 0


def test_hash_password_not_equal_to_plaintext() -> None:
    plain = "my_password"
    assert hash_password(plain) != plain


def test_hash_uses_argon2id_variant() -> None:
    hashed = hash_password("test")
    assert hashed.startswith("$argon2id$")


def test_verify_password_correct_plain() -> None:
    plain = "correct_horse"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed) is True


def test_verify_password_wrong_plain() -> None:
    hashed = hash_password("correct")
    assert verify_password("wrong", hashed) is False


def test_check_needs_rehash_returns_false_for_fresh_hash() -> None:
    hashed = hash_password("fresh")
    assert check_needs_rehash(hashed) is False
