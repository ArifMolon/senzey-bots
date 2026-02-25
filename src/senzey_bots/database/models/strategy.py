"""Strategy draft model — persists user-provided strategy inputs."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from senzey_bots.database.base import Base


class Strategy(Base):
    """Persists strategy drafts created from the input workspace.

    input_type: one of "rules_text", "pinescript", "python_upload"
    status lifecycle: draft → validated → generating → generated → failed
    """

    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    input_type: Mapped[str] = mapped_column(String(20), nullable=False)
    input_content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    updated_at: Mapped[datetime] = mapped_column(nullable=False)
