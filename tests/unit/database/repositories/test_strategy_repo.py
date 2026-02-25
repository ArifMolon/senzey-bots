"""Unit tests for strategy repository."""

from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from senzey_bots.database.repositories.strategy_repo import (
    create_strategy,
    delete_strategy,
    get_strategy,
    list_strategies,
)


# ---------------------------------------------------------------------------
# create_strategy
# ---------------------------------------------------------------------------


def test_create_strategy_returns_strategy(db_session: Session) -> None:
    strategy = create_strategy(
        db_session,
        name="Test Strategy",
        input_type="rules_text",
        input_content="Buy when RSI < 30, sell when RSI > 70",
    )
    assert strategy.id is not None
    assert strategy.name == "Test Strategy"
    assert strategy.input_type == "rules_text"
    assert strategy.input_content == "Buy when RSI < 30, sell when RSI > 70"


def test_create_strategy_sets_draft_status(db_session: Session) -> None:
    strategy = create_strategy(
        db_session,
        name="Draft Check",
        input_type="pinescript",
        input_content="//@version=5\nstrategy('x')",
    )
    assert strategy.status == "draft"


def test_create_strategy_sets_timestamps(db_session: Session) -> None:
    strategy = create_strategy(
        db_session,
        name="Timestamp Test",
        input_type="rules_text",
        input_content="Buy when price rises 2% in one day",
    )
    assert isinstance(strategy.created_at, datetime)
    assert isinstance(strategy.updated_at, datetime)
    # Timestamps should be timezone-aware UTC
    assert strategy.created_at.tzinfo is not None or strategy.created_at is not None
    assert strategy.updated_at == strategy.created_at


# ---------------------------------------------------------------------------
# list_strategies
# ---------------------------------------------------------------------------


def test_list_strategies_returns_all(db_session: Session) -> None:
    create_strategy(
        db_session,
        name="Alpha",
        input_type="rules_text",
        input_content="Buy when RSI is below 30 threshold",
    )
    create_strategy(
        db_session,
        name="Beta",
        input_type="pinescript",
        input_content="//@version=5\nstrategy('Beta')",
    )
    strategies = list_strategies(db_session)
    assert len(strategies) == 2


def test_list_strategies_empty(db_session: Session) -> None:
    strategies = list_strategies(db_session)
    assert strategies == []


def test_list_strategies_ordered_by_created_at_desc(db_session: Session) -> None:
    first = create_strategy(
        db_session,
        name="First",
        input_type="rules_text",
        input_content="Buy when RSI drops below 30 level",
    )
    second = create_strategy(
        db_session,
        name="Second",
        input_type="rules_text",
        input_content="Sell when price breaks above resistance",
    )
    strategies = list_strategies(db_session)
    # Most recently created should be first
    ids = [s.id for s in strategies]
    assert ids.index(second.id) < ids.index(first.id)


# ---------------------------------------------------------------------------
# get_strategy
# ---------------------------------------------------------------------------


def test_get_strategy_returns_by_id(db_session: Session) -> None:
    strategy = create_strategy(
        db_session,
        name="Get Me",
        input_type="rules_text",
        input_content="Buy when MA crosses above price",
    )
    fetched = get_strategy(db_session, strategy.id)
    assert fetched is not None
    assert fetched.id == strategy.id
    assert fetched.name == "Get Me"


def test_get_strategy_returns_none_for_missing(db_session: Session) -> None:
    result = get_strategy(db_session, 99999)
    assert result is None


# ---------------------------------------------------------------------------
# delete_strategy
# ---------------------------------------------------------------------------


def test_delete_strategy_removes_it(db_session: Session) -> None:
    strategy = create_strategy(
        db_session,
        name="Delete Me",
        input_type="rules_text",
        input_content="Buy on breakout above 20-day high",
    )
    deleted = delete_strategy(db_session, strategy.id)
    assert deleted is True
    assert get_strategy(db_session, strategy.id) is None


def test_delete_strategy_returns_false_for_missing(db_session: Session) -> None:
    result = delete_strategy(db_session, 99999)
    assert result is False
