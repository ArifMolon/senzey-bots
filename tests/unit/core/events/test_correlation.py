"""Unit tests for correlation ID propagation."""

import uuid
from collections.abc import Generator

import pytest

import senzey_bots.core.events.correlation as corr_module
from senzey_bots.core.events.correlation import (
    get_correlation_id,
    new_correlation_id,
    set_correlation_id,
)


@pytest.fixture(autouse=True)
def reset_correlation_context() -> Generator[None, None, None]:
    """Reset correlation ID to None before each test to prevent cross-test contamination."""
    token = corr_module._correlation_id.set(None)
    yield
    corr_module._correlation_id.reset(token)


def test_new_correlation_id_returns_valid_uuid_v4() -> None:
    cid = new_correlation_id()
    parsed = uuid.UUID(cid)
    assert parsed.version == 4


def test_get_correlation_id_returns_same_id_twice() -> None:
    cid1 = get_correlation_id()
    cid2 = get_correlation_id()
    assert cid1 == cid2


def test_get_correlation_id_creates_new_when_none() -> None:
    # After reset_correlation_context fixture, context is None
    cid = get_correlation_id()
    assert cid is not None
    assert len(cid) > 0
    # Validate it's a UUID
    uuid.UUID(cid)


def test_set_correlation_id_overrides_current() -> None:
    original = get_correlation_id()
    new_id = "aaaabbbb-cccc-dddd-eeee-ffffaaaabbbb"
    set_correlation_id(new_id)
    assert get_correlation_id() == new_id
    assert get_correlation_id() != original or original == new_id


def test_set_correlation_id_returns_token_for_reset() -> None:
    first_id = "11111111-1111-4111-a111-111111111111"
    second_id = "22222222-2222-4222-a222-222222222222"

    token = set_correlation_id(first_id)
    assert get_correlation_id() == first_id

    set_correlation_id(second_id)
    assert get_correlation_id() == second_id

    # Reset to before first_id was set (which was None due to fixture)
    corr_module._correlation_id.reset(token)
    assert corr_module._correlation_id.get() is None
