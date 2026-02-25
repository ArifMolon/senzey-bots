"""Authentication service — password setup, verification, and key derivation."""

import base64
import json
import os
import uuid

from sqlalchemy import select

from senzey_bots.core.errors.domain_errors import AuthenticationError
from senzey_bots.database.engine import get_session
from senzey_bots.database.models.auth_config import AuthConfig
from senzey_bots.security import crypto_service, password_hasher
from senzey_bots.shared.clock import utcnow
from senzey_bots.shared.logger import get_logger

logger = get_logger(__name__)


def setup_password(plain: str) -> None:
    """Hash password and persist it with a fresh fernet_salt.

    Idempotent: a second call replaces the existing row (upsert).
    """
    hashed = password_hasher.hash_password(plain)
    salt_bytes = os.urandom(16)
    fernet_salt = base64.urlsafe_b64encode(salt_bytes).decode()
    now = utcnow()

    with get_session() as session:
        existing = session.scalar(select(AuthConfig))
        if existing is not None:
            existing.password_hash = hashed
            existing.fernet_salt = fernet_salt
            existing.updated_at = now
        else:
            session.add(
                AuthConfig(
                    password_hash=hashed,
                    fernet_salt=fernet_salt,
                    created_at=now,
                    updated_at=now,
                )
            )
        session.commit()


def authenticate(plain: str) -> bytes:
    """Verify password and return the derived Fernet master key.

    Returns:
        44-byte base64url-encoded Fernet key (bytes).

    Raises:
        AuthenticationError: on wrong password or missing configuration.
    """
    with get_session() as session:
        row = session.scalar(select(AuthConfig))

    if row is None:
        raise AuthenticationError("No password configured")

    if not password_hasher.verify_password(plain, row.password_hash):
        correlation_id = str(uuid.uuid4())
        logger.warning(json.dumps({"event": "auth_failed", "correlation_id": correlation_id}))
        raise AuthenticationError("Invalid password")

    # Optionally re-hash with updated parameters
    if password_hasher.check_needs_rehash(row.password_hash):
        new_hash = password_hasher.hash_password(plain)
        with get_session() as session:
            r = session.scalar(select(AuthConfig))
            if r is not None:
                r.password_hash = new_hash
                r.updated_at = utcnow()
                session.commit()

    salt = base64.urlsafe_b64decode(row.fernet_salt)
    return crypto_service.derive_master_key(plain, salt)


def is_configured() -> bool:
    """Return True if a password row exists in auth_config."""
    with get_session() as session:
        return session.scalar(select(AuthConfig)) is not None
