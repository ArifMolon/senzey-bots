"""AgentRun model — tracks agent execution sessions for timeline display."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from senzey_bots.database.base import Base


class AgentRun(Base):
    """Tracks individual agent execution sessions.

    run_type: "strategy_generation", "backtest", "auto_fix", etc.
    status lifecycle: running → completed | failed
    """

    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    correlation_id: Mapped[str] = mapped_column(
        String(36), nullable=False, unique=True
    )
    run_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="running"
    )
    strategy_id: Mapped[int | None] = mapped_column(
        ForeignKey("strategies.id"), nullable=True
    )
    metadata_json: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None
    )
    started_at: Mapped[datetime] = mapped_column(nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(
        nullable=True, default=None
    )
