"""Database engine — SQLite singleton with session factory."""

import contextlib
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

_DB_PATH = Path("var/db/senzey_bots.db")
_DATABASE_URL = f"sqlite:///{_DB_PATH}"

_engine: Engine | None = None


def get_engine() -> Engine:
    """Return the module-level SQLite engine (lazy-init singleton)."""
    global _engine
    if _engine is None:
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(
            _DATABASE_URL,
            connect_args={"check_same_thread": False},
        )
    return _engine


@contextlib.contextmanager
def get_session() -> Iterator[Session]:
    """Yield a SQLAlchemy 2.0 Session, closing it on exit."""
    with Session(get_engine()) as session:
        yield session
