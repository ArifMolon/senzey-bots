"""Unit tests for crypto_service module."""

import os

import pytest
from cryptography.fernet import InvalidToken

from senzey_bots.security.crypto_service import decrypt, derive_master_key, encrypt


@pytest.fixture
def master_key() -> bytes:
    salt = os.urandom(16)
    return derive_master_key("test_password", salt)


def test_encrypt_decrypt_round_trip(master_key: bytes) -> None:
    plaintext = "my_api_key_value"
    ciphertext = encrypt(plaintext, master_key)
    assert decrypt(ciphertext, master_key) == plaintext


def test_encrypted_differs_from_plaintext(master_key: bytes) -> None:
    plaintext = "secret"
    assert encrypt(plaintext, master_key) != plaintext


def test_tampered_ciphertext_raises_invalid_token(master_key: bytes) -> None:
    ciphertext = encrypt("value", master_key)
    tampered = ciphertext[:-4] + "XXXX"
    with pytest.raises(InvalidToken):
        decrypt(tampered, master_key)


def test_derive_master_key_returns_44_bytes() -> None:
    salt = os.urandom(16)
    key = derive_master_key("password", salt)
    assert isinstance(key, bytes)
    assert len(key) == 44


def test_derive_master_key_is_deterministic() -> None:
    salt = os.urandom(16)
    key1 = derive_master_key("password", salt)
    key2 = derive_master_key("password", salt)
    assert key1 == key2


def test_derive_master_key_different_salt_gives_different_key() -> None:
    salt1 = os.urandom(16)
    salt2 = os.urandom(16)
    assert derive_master_key("password", salt1) != derive_master_key("password", salt2)
