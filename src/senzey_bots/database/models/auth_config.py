"""ORM model for authentication configuration."""

from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from senzey_bots.database.base import Base


class AuthConfig(Base):
    """Stores the owner password hash and fernet salt for key derivation."""

    __tablename__ = "auth_config"

    id: Mapped[int] = mapped_column(primary_key=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    fernet_salt: Mapped[str] = mapped_column(String(44), nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    updated_at: Mapped[datetime] = mapped_column(nullable=False)
