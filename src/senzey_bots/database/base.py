"""Shared declarative base for all ORM models (SQLAlchemy 2.0)."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
