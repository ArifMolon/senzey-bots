"""Unit tests for auth_service module."""

from contextlib import contextmanager
from collections.abc import Generator
from typing import Any

import pytest
from sqlalchemy.orm import Session

from senzey_bots.core.errors.domain_errors import AuthenticationError
from senzey_bots.security import auth_service


@pytest.fixture
def patched_session(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> Generator[Session, None, None]:
    """Patch auth_service.get_session to use the in-memory test session."""

    @contextmanager  # type: ignore[arg-type]
    def mock_get_session() -> Generator[Session, None, None]:
        yield db_session

    monkeypatch.setattr("senzey_bots.security.auth_service.get_session", mock_get_session)
    yield db_session


def test_is_configured_false_before_setup(patched_session: Session) -> None:
    assert auth_service.is_configured() is False


def test_is_configured_true_after_setup(patched_session: Session) -> None:
    auth_service.setup_password("mypassword")
    patched_session.expire_all()
    assert auth_service.is_configured() is True


def test_setup_and_authenticate_returns_bytes(patched_session: Session) -> None:
    auth_service.setup_password("correct_horse")
    patched_session.expire_all()
    master_key = auth_service.authenticate("correct_horse")
    assert isinstance(master_key, bytes)
    assert len(master_key) == 44


def test_authenticate_wrong_password_raises(patched_session: Session) -> None:
    auth_service.setup_password("correct")
    patched_session.expire_all()
    with pytest.raises(AuthenticationError):
        auth_service.authenticate("wrong")


def test_authenticate_before_setup_raises(patched_session: Session) -> None:
    with pytest.raises(AuthenticationError, match="No password configured"):
        auth_service.authenticate("anything")


def test_same_password_gives_same_master_key(patched_session: Session) -> None:
    auth_service.setup_password("stable_pass")
    patched_session.expire_all()
    key1 = auth_service.authenticate("stable_pass")
    patched_session.expire_all()
    key2 = auth_service.authenticate("stable_pass")
    assert key1 == key2


def test_setup_password_update_replaces_existing_row(patched_session: Session) -> None:
    """Setup called twice must update the existing row (upsert path, lines 33-35)."""
    auth_service.setup_password("initial_pass")
    patched_session.expire_all()
    auth_service.setup_password("new_pass")
    patched_session.expire_all()
    # Old password must no longer authenticate
    with pytest.raises(AuthenticationError):
        auth_service.authenticate("initial_pass")
    # New password must authenticate and return a master key
    key = auth_service.authenticate("new_pass")
    assert isinstance(key, bytes)


def test_authenticate_rehashes_when_needed(
    patched_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Re-hash path (lines 70-76) runs when check_needs_rehash returns True."""
    auth_service.setup_password("rehash_pass")
    patched_session.expire_all()

    # Force the re-hash branch to execute
    monkeypatch.setattr(
        "senzey_bots.security.auth_service.password_hasher.check_needs_rehash",
        lambda _: True,
    )
    key = auth_service.authenticate("rehash_pass")
    assert isinstance(key, bytes)
    # After re-hash the password must still authenticate
    patched_session.expire_all()
    key2 = auth_service.authenticate("rehash_pass")
    assert key == key2
