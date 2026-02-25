"""Unit tests for the agent run repository."""

from __future__ import annotations

import uuid

# Force-import both models so Base.metadata registers both tables
from senzey_bots.database.models.agent_run import AgentRun  # noqa: F401
from senzey_bots.database.models.strategy import Strategy  # noqa: F401
from senzey_bots.database.repositories.agent_run_repo import (
    complete_agent_run,
    create_agent_run,
    get_agent_run,
    list_agent_runs_for_strategy,
    list_recent_agent_runs,
)


def _new_corr() -> str:
    return str(uuid.uuid4())


class TestCreateAgentRun:
    def test_creates_with_required_fields(self, db_session) -> None:  # type: ignore[no-untyped-def]
        corr = _new_corr()
        run = create_agent_run(
            db_session, correlation_id=corr, run_type="strategy_generation"
        )
        assert run.id is not None
        assert run.correlation_id == corr
        assert run.run_type == "strategy_generation"

    def test_sets_status_running(self, db_session) -> None:  # type: ignore[no-untyped-def]
        run = create_agent_run(
            db_session,
            correlation_id=_new_corr(),
            run_type="strategy_generation",
        )
        assert run.status == "running"

    def test_sets_started_at(self, db_session) -> None:  # type: ignore[no-untyped-def]
        run = create_agent_run(
            db_session,
            correlation_id=_new_corr(),
            run_type="strategy_generation",
        )
        assert run.started_at is not None

    def test_ended_at_is_none_on_creation(self, db_session) -> None:  # type: ignore[no-untyped-def]
        run = create_agent_run(
            db_session,
            correlation_id=_new_corr(),
            run_type="strategy_generation",
        )
        assert run.ended_at is None

    def test_strategy_id_optional(self, db_session) -> None:  # type: ignore[no-untyped-def]
        run = create_agent_run(
            db_session,
            correlation_id=_new_corr(),
            run_type="strategy_generation",
            strategy_id=None,
        )
        assert run.strategy_id is None

    def test_metadata_json_optional(self, db_session) -> None:  # type: ignore[no-untyped-def]
        run = create_agent_run(
            db_session,
            correlation_id=_new_corr(),
            run_type="strategy_generation",
            metadata_json='{"model": "claude-sonnet"}',
        )
        assert run.metadata_json == '{"model": "claude-sonnet"}'


class TestCompleteAgentRun:
    def test_updates_status_completed(self, db_session) -> None:  # type: ignore[no-untyped-def]
        corr = _new_corr()
        create_agent_run(
            db_session, correlation_id=corr, run_type="strategy_generation"
        )
        run = complete_agent_run(db_session, corr)
        assert run is not None
        assert run.status == "completed"

    def test_updates_status_failed(self, db_session) -> None:  # type: ignore[no-untyped-def]
        corr = _new_corr()
        create_agent_run(
            db_session, correlation_id=corr, run_type="strategy_generation"
        )
        run = complete_agent_run(db_session, corr, status="failed")
        assert run is not None
        assert run.status == "failed"

    def test_sets_ended_at(self, db_session) -> None:  # type: ignore[no-untyped-def]
        corr = _new_corr()
        create_agent_run(
            db_session, correlation_id=corr, run_type="strategy_generation"
        )
        run = complete_agent_run(db_session, corr)
        assert run is not None
        assert run.ended_at is not None

    def test_returns_none_for_nonexistent_correlation_id(self, db_session) -> None:  # type: ignore[no-untyped-def]
        result = complete_agent_run(db_session, "non-existent-corr-id")
        assert result is None


class TestGetAgentRun:
    def test_returns_run_by_correlation_id(self, db_session) -> None:  # type: ignore[no-untyped-def]
        corr = _new_corr()
        create_agent_run(
            db_session, correlation_id=corr, run_type="strategy_generation"
        )
        found = get_agent_run(db_session, corr)
        assert found is not None
        assert found.correlation_id == corr

    def test_returns_none_for_nonexistent(self, db_session) -> None:  # type: ignore[no-untyped-def]
        result = get_agent_run(db_session, "does-not-exist")
        assert result is None


class TestListRecentAgentRuns:
    def test_returns_runs_ordered_by_started_at_desc(self, db_session) -> None:  # type: ignore[no-untyped-def]
        corr1 = _new_corr()
        corr2 = _new_corr()
        corr3 = _new_corr()
        create_agent_run(db_session, correlation_id=corr1, run_type="r")
        create_agent_run(db_session, correlation_id=corr2, run_type="r")
        create_agent_run(db_session, correlation_id=corr3, run_type="r")
        runs = list_recent_agent_runs(db_session)
        # Most recent first (IDs in descending order since we insert sequentially)
        assert runs[0].id > runs[1].id > runs[2].id

    def test_respects_limit(self, db_session) -> None:  # type: ignore[no-untyped-def]
        for _ in range(10):
            create_agent_run(db_session, correlation_id=_new_corr(), run_type="r")
        runs = list_recent_agent_runs(db_session, limit=3)
        assert len(runs) == 3

    def test_returns_empty_when_no_runs(self, db_session) -> None:  # type: ignore[no-untyped-def]
        assert list_recent_agent_runs(db_session) == []


class TestListAgentRunsForStrategy:
    def test_filters_by_strategy_id(self, db_session) -> None:  # type: ignore[no-untyped-def]
        # Create a real strategy to satisfy FK constraint
        from senzey_bots.database.repositories.strategy_repo import create_strategy
        strategy = create_strategy(
            db_session,
            name="Test",
            input_type="rules_text",
            input_content="buy when RSI < 30",
        )
        s_id = strategy.id

        create_agent_run(
            db_session,
            correlation_id=_new_corr(),
            run_type="strategy_generation",
            strategy_id=s_id,
        )
        create_agent_run(
            db_session,
            correlation_id=_new_corr(),
            run_type="strategy_generation",
            strategy_id=None,
        )

        runs = list_agent_runs_for_strategy(db_session, s_id)
        assert len(runs) == 1
        assert runs[0].strategy_id == s_id

    def test_returns_empty_for_unknown_strategy(self, db_session) -> None:  # type: ignore[no-untyped-def]
        runs = list_agent_runs_for_strategy(db_session, 9999)
        assert runs == []
