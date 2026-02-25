"""Agent run repository — CRUD operations for agent execution tracking."""

from __future__ import annotations

from sqlalchemy.orm import Session

from senzey_bots.database.models.agent_run import AgentRun
from senzey_bots.shared.clock import utcnow
from senzey_bots.shared.logger import get_logger

logger = get_logger(__name__)


def create_agent_run(
    session: Session,
    *,
    correlation_id: str,
    run_type: str,
    strategy_id: int | None = None,
    metadata_json: str | None = None,
) -> AgentRun:
    """Create a new agent run record with status 'running'."""
    run = AgentRun(
        correlation_id=correlation_id,
        run_type=run_type,
        status="running",
        strategy_id=strategy_id,
        metadata_json=metadata_json,
        started_at=utcnow(),
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def complete_agent_run(
    session: Session,
    correlation_id: str,
    *,
    status: str = "completed",
) -> AgentRun | None:
    """Mark an agent run as completed or failed.

    Returns updated AgentRun or None if not found.
    """
    run = _get_by_correlation(session, correlation_id)
    if run is None:
        return None
    run.status = status
    run.ended_at = utcnow()
    session.commit()
    session.refresh(run)
    return run


def get_agent_run(
    session: Session, correlation_id: str
) -> AgentRun | None:
    """Get an agent run by correlation ID."""
    return _get_by_correlation(session, correlation_id)


def list_recent_agent_runs(
    session: Session, *, limit: int = 20
) -> list[AgentRun]:
    """Return recent agent runs ordered by started_at descending."""
    return list(
        session.query(AgentRun)
        .order_by(AgentRun.started_at.desc())
        .limit(limit)
        .all()
    )


def list_agent_runs_for_strategy(
    session: Session, strategy_id: int
) -> list[AgentRun]:
    """Return all agent runs for a specific strategy."""
    return list(
        session.query(AgentRun)
        .filter(AgentRun.strategy_id == strategy_id)
        .order_by(AgentRun.started_at.desc())
        .all()
    )


def _get_by_correlation(
    session: Session, correlation_id: str
) -> AgentRun | None:
    """Internal helper to find agent run by correlation_id."""
    return session.query(AgentRun).filter(
        AgentRun.correlation_id == correlation_id
    ).first()
