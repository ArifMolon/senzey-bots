"""Strategy repository — CRUD operations for strategy drafts."""

from __future__ import annotations

from sqlalchemy.orm import Session

from senzey_bots.database.models.strategy import Strategy
from senzey_bots.shared.clock import utcnow
from senzey_bots.shared.logger import get_logger

logger = get_logger(__name__)


def create_strategy(
    session: Session,
    *,
    name: str,
    input_type: str,
    input_content: str,
) -> Strategy:
    """Create a new strategy draft."""
    now = utcnow()
    strategy = Strategy(
        name=name,
        input_type=input_type,
        input_content=input_content,
        status="draft",
        created_at=now,
        updated_at=now,
    )
    session.add(strategy)
    session.commit()
    session.refresh(strategy)
    return strategy


def list_strategies(session: Session) -> list[Strategy]:
    """Return all strategies ordered by creation date descending."""
    return list(
        session.query(Strategy).order_by(Strategy.created_at.desc()).all()
    )


def get_strategy(session: Session, strategy_id: int) -> Strategy | None:
    """Get a single strategy by ID. Returns None if not found."""
    return session.get(Strategy, strategy_id)


def delete_strategy(session: Session, strategy_id: int) -> bool:
    """Delete a strategy by ID. Returns True if deleted, False if not found."""
    strategy = session.get(Strategy, strategy_id)
    if strategy is None:
        return False
    session.delete(strategy)
    session.commit()
    return True
