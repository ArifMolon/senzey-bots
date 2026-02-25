"""ORM model for encrypted secrets storage."""

from datetime import datetime

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from senzey_bots.database.base import Base


class SecretMetadata(Base):
    """Stores encrypted API keys and other secrets — no plaintext column."""

    __tablename__ = "secrets_metadata"

    id: Mapped[int] = mapped_column(primary_key=True)
    key_name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    encrypted_value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    updated_at: Mapped[datetime] = mapped_column(nullable=False)
