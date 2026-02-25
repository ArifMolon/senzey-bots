"""Database engine stub — Story 1.2 will implement the full engine."""

from sqlalchemy import create_engine as _create_engine
from sqlalchemy.engine import Engine


def get_engine(database_url: str) -> Engine:
    """Return a SQLAlchemy engine for the given database URL."""
    return _create_engine(database_url)
