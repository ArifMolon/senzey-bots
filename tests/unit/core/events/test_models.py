"""Unit tests for EventEnvelope model."""

import json
import uuid
from datetime import datetime

import pytest
from pydantic import BaseModel, ValidationError as PydanticValidationError

from senzey_bots.core.events.models import EventEnvelope


class _TestPayload(BaseModel):
    action: str
    amount: float


def _make_envelope(**kwargs: object) -> EventEnvelope[_TestPayload]:
    defaults: dict[str, object] = {
        "event_name": "strategy.generated.v1",
        "source": "test_service",
        "correlation_id": str(uuid.uuid4()),
        "payload": _TestPayload(action="buy", amount=100.0),
    }
    defaults.update(kwargs)
    return EventEnvelope[_TestPayload](**defaults)  # type: ignore[arg-type]


def test_event_envelope_creation_with_valid_name() -> None:
    env = _make_envelope(event_name="strategy.generated.v1")
    assert env.event_name == "strategy.generated.v1"


def test_event_envelope_rejects_invalid_name_not_valid() -> None:
    with pytest.raises(PydanticValidationError):
        _make_envelope(event_name="NotValid")


def test_event_envelope_rejects_no_version() -> None:
    with pytest.raises(PydanticValidationError):
        _make_envelope(event_name="strategy.generated")


def test_event_envelope_rejects_upper_case() -> None:
    with pytest.raises(PydanticValidationError):
        _make_envelope(event_name="UPPER.case.v1")


def test_event_envelope_rejects_missing_action() -> None:
    with pytest.raises(PydanticValidationError):
        _make_envelope(event_name="strategy.v1")


def test_event_envelope_auto_generates_event_id() -> None:
    env = _make_envelope()
    assert env.event_id is not None
    # Should be a valid UUID
    uuid.UUID(env.event_id)


def test_event_envelope_auto_generates_occurred_at() -> None:
    env = _make_envelope()
    assert isinstance(env.occurred_at, datetime)
    assert env.occurred_at.tzinfo is not None


def test_event_envelope_is_frozen() -> None:
    env = _make_envelope()
    with pytest.raises(PydanticValidationError):
        env.event_name = "other.event.v1"  # type: ignore[misc]


def test_event_envelope_serialization_snake_case() -> None:
    cid = str(uuid.uuid4())
    env = _make_envelope(correlation_id=cid)
    raw = json.loads(env.model_dump_json())
    # All keys should be snake_case
    assert "event_id" in raw
    assert "event_name" in raw
    assert "occurred_at" in raw
    assert "correlation_id" in raw
    assert raw["correlation_id"] == cid


def test_event_envelope_with_typed_payload() -> None:
    payload = _TestPayload(action="sell", amount=50.0)
    env = _make_envelope(payload=payload)
    assert env.payload.action == "sell"
    assert env.payload.amount == 50.0


def test_event_envelope_model_dump_json_valid() -> None:
    env = _make_envelope()
    json_str = env.model_dump_json()
    parsed = json.loads(json_str)
    assert isinstance(parsed, dict)
    assert "event_name" in parsed


def test_event_envelope_rejects_non_uuid_correlation_id() -> None:
    with pytest.raises(PydanticValidationError):
        _make_envelope(correlation_id="not-a-uuid")


def test_event_envelope_rejects_non_v4_uuid_correlation_id() -> None:
    # UUID v1 (time-based) — version digit is 1
    uuid_v1 = "550e8400-e29b-11d4-a716-446655440000"
    with pytest.raises(PydanticValidationError):
        _make_envelope(correlation_id=uuid_v1)


def test_event_envelope_accepts_valid_uuid_v4_correlation_id() -> None:
    valid_cid = str(uuid.uuid4())
    env = _make_envelope(correlation_id=valid_cid)
    assert env.correlation_id == valid_cid


def test_event_envelope_valid_names() -> None:
    valid_names = [
        "order.opened.v1",
        "risk.halt_triggered.v1",
        "strategy.generated.v2",
        "domain.action.v10",
    ]
    for name in valid_names:
        env = _make_envelope(event_name=name)
        assert env.event_name == name
