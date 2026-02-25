"""Symmetric encryption using Fernet (AES-128-CBC + HMAC-SHA256)."""

import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

_PBKDF2_ITERATIONS = 480_000


def derive_master_key(password: str, salt: bytes) -> bytes:
    """Derive a Fernet-compatible 44-byte key from password + salt via PBKDF2.

    The returned bytes are base64url-encoded and ready for direct use with
    Fernet(key). The salt must be stored separately (not embedded in the key).
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_PBKDF2_ITERATIONS,
    )
    raw_key = kdf.derive(password.encode())
    return base64.urlsafe_b64encode(raw_key)  # 44-byte Fernet-compatible key


def encrypt(plaintext: str, master_key: bytes) -> str:
    """Encrypt plaintext and return a URL-safe base64 Fernet token string."""
    return Fernet(master_key).encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str, master_key: bytes) -> str:
    """Decrypt a Fernet token string and return plaintext."""
    return Fernet(master_key).decrypt(ciphertext.encode()).decode()
