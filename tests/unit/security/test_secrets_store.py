"""Unit tests for secrets_store module."""

import os
from contextlib import contextmanager
from collections.abc import Generator

import pytest
from sqlalchemy.orm import Session

from senzey_bots.core.errors.domain_errors import SecretsError
from senzey_bots.security import secrets_store
from senzey_bots.security.crypto_service import derive_master_key


@pytest.fixture
def patched_session(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> Generator[Session, None, None]:
    """Patch secrets_store.get_session to use the in-memory test session."""

    @contextmanager  # type: ignore[arg-type]
    def mock_get_session() -> Generator[Session, None, None]:
        yield db_session

    monkeypatch.setattr("senzey_bots.security.secrets_store.get_session", mock_get_session)
    yield db_session


@pytest.fixture
def master_key() -> bytes:
    return derive_master_key("test_password", os.urandom(16))


def test_store_and_get_secret_round_trip(
    patched_session: Session, master_key: bytes
) -> None:
    secrets_store.store_secret("ig_api_key", "plaintext_value", master_key)
    patched_session.expire_all()
    result = secrets_store.get_secret("ig_api_key", master_key)
    assert result == "plaintext_value"


def test_list_secret_names(patched_session: Session, master_key: bytes) -> None:
    secrets_store.store_secret("key_a", "val_a", master_key)
    secrets_store.store_secret("key_b", "val_b", master_key)
    patched_session.expire_all()
    names = secrets_store.list_secret_names()
    assert "key_a" in names
    assert "key_b" in names


def test_delete_secret_removes_entry(
    patched_session: Session, master_key: bytes
) -> None:
    secrets_store.store_secret("to_delete", "value", master_key)
    patched_session.expire_all()
    secrets_store.delete_secret("to_delete")
    patched_session.expire_all()
    with pytest.raises(SecretsError):
        secrets_store.get_secret("to_delete", master_key)


def test_get_secret_unknown_key_raises(
    patched_session: Session, master_key: bytes
) -> None:
    with pytest.raises(SecretsError, match="Secret not found"):
        secrets_store.get_secret("nonexistent_key", master_key)


def test_store_secret_updates_existing_value(
    patched_session: Session, master_key: bytes
) -> None:
    """store_secret called twice for the same key must update the value (lines 22-23)."""
    secrets_store.store_secret("ig_api_key", "original_value", master_key)
    patched_session.expire_all()
    secrets_store.store_secret("ig_api_key", "rotated_value", master_key)
    patched_session.expire_all()
    result = secrets_store.get_secret("ig_api_key", master_key)
    assert result == "rotated_value"


def test_store_secret_does_not_expose_plaintext(
    patched_session: Session, master_key: bytes
) -> None:
    secrets_store.store_secret("api_key", "super_secret", master_key)
    patched_session.expire_all()
    from senzey_bots.database.models.secret_metadata import SecretMetadata
    from sqlalchemy import select

    row = patched_session.scalar(
        select(SecretMetadata).where(SecretMetadata.key_name == "api_key")
    )
    assert row is not None
    assert row.encrypted_value != "super_secret"
