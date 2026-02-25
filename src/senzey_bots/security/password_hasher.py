"""Password hashing using argon2-cffi (Argon2id algorithm)."""

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()  # Argon2id, RFC 9106 LOW_MEMORY profile defaults


def hash_password(plain: str) -> str:
    """Return an Argon2id hash of the plaintext password."""
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the stored hash, False otherwise.

    Note: argon2 verify() arg order is (hash, password) — hash first.
    """
    try:
        return _hasher.verify(hashed, plain)
    except VerifyMismatchError:
        return False


def check_needs_rehash(hashed: str) -> bool:
    """Return True if the hash should be upgraded to current parameters."""
    return _hasher.check_needs_rehash(hashed)
