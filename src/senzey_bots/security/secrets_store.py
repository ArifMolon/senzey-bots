"""Encrypted secrets store — stores and retrieves API keys securely."""

from sqlalchemy import select

from senzey_bots.core.errors.domain_errors import SecretsError
from senzey_bots.database.engine import get_session
from senzey_bots.database.models.secret_metadata import SecretMetadata
from senzey_bots.security import crypto_service
from senzey_bots.shared.clock import utcnow


def store_secret(key_name: str, plaintext: str, master_key: bytes) -> None:
    """Encrypt plaintext and upsert into secrets_metadata table."""
    encrypted = crypto_service.encrypt(plaintext, master_key)
    now = utcnow()

    with get_session() as session:
        existing = session.scalar(
            select(SecretMetadata).where(SecretMetadata.key_name == key_name)
        )
        if existing is not None:
            existing.encrypted_value = encrypted
            existing.updated_at = now
        else:
            session.add(
                SecretMetadata(
                    key_name=key_name,
                    encrypted_value=encrypted,
                    created_at=now,
                    updated_at=now,
                )
            )
        session.commit()


def get_secret(key_name: str, master_key: bytes) -> str:
    """Decrypt and return the plaintext secret for key_name.

    Raises:
        SecretsError: if the key is not found.
    """
    with get_session() as session:
        row = session.scalar(
            select(SecretMetadata).where(SecretMetadata.key_name == key_name)
        )

    if row is None:
        raise SecretsError(f"Secret not found: {key_name!r}")

    return crypto_service.decrypt(row.encrypted_value, master_key)


def list_secret_names() -> list[str]:
    """Return all stored key names (no encrypted values exposed)."""
    with get_session() as session:
        rows = session.scalars(select(SecretMetadata.key_name)).all()
    return list(rows)


def delete_secret(key_name: str) -> None:
    """Remove the secret row for key_name from the database."""
    with get_session() as session:
        row = session.scalar(
            select(SecretMetadata).where(SecretMetadata.key_name == key_name)
        )
        if row is not None:
            session.delete(row)
            session.commit()
