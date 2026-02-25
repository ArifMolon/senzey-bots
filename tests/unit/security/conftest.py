"""Shared fixtures for security unit tests."""

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from senzey_bots.database.base import Base


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Yield an in-memory SQLite session with all tables created."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)
