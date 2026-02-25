"""Unit tests for orchestrator command/result contracts."""

import json

import pytest
from pydantic import BaseModel, ValidationError as PydanticValidationError

from senzey_bots.core.errors.domain_errors import BrokerError
from senzey_bots.core.orchestrator.contracts import (
    CommandFailure,
    CommandSuccess,
    ErrorPayload,
    failure,
    failure_from_domain_error,
    success,
)


class _SampleData(BaseModel):
    value: int
    name: str


def test_error_payload_creation() -> None:
    payload = ErrorPayload(code="BROKER_ERROR", message="connection lost", details={"host": "api.ig.com"})
    assert payload.code == "BROKER_ERROR"
    assert payload.message == "connection lost"
    assert payload.details == {"host": "api.ig.com"}


def test_error_payload_defaults_details_to_none() -> None:
    payload = ErrorPayload(code="BROKER_ERROR", message="failed")
    assert payload.details is None


def test_error_payload_is_frozen() -> None:
    payload = ErrorPayload(code="X", message="msg")
    with pytest.raises(PydanticValidationError):
        payload.code = "Y"  # type: ignore[misc]


def test_success_returns_command_success() -> None:
    data = _SampleData(value=42, name="test")
    result = success(data)
    assert isinstance(result, CommandSuccess)
    assert result.ok is True
    assert result.data == data


def test_command_success_serialization() -> None:
    data = _SampleData(value=1, name="foo")
    result = success(data)
    raw = json.loads(result.model_dump_json())
    assert raw["ok"] is True
    assert raw["data"]["value"] == 1
    assert raw["data"]["name"] == "foo"
    # Verify snake_case keys
    assert "ok" in raw
    assert "data" in raw


def test_failure_returns_command_failure() -> None:
    result = failure(code="BROKER_ERROR", message="failed", details={"x": 1})
    assert isinstance(result, CommandFailure)
    assert result.ok is False
    assert result.error.code == "BROKER_ERROR"
    assert result.error.message == "failed"
    assert result.error.details == {"x": 1}


def test_command_failure_serialization() -> None:
    result = failure(code="RISK_LIMIT_ERROR", message="limit exceeded")
    raw = json.loads(result.model_dump_json())
    assert raw["ok"] is False
    assert raw["error"]["code"] == "RISK_LIMIT_ERROR"
    assert raw["error"]["message"] == "limit exceeded"
    assert raw["error"]["details"] is None


def test_failure_from_domain_error_with_broker_error() -> None:
    exc = BrokerError(message="connection timeout", details={"timeout": 30})
    result = failure_from_domain_error(exc)
    assert isinstance(result, CommandFailure)
    assert result.ok is False
    assert result.error.code == "BROKER_ERROR"
    assert result.error.message == "connection timeout"
    assert result.error.details == {"timeout": 30}


def test_failure_from_domain_error_with_plain_exception() -> None:
    exc = RuntimeError("unexpected failure")
    result = failure_from_domain_error(exc)
    assert isinstance(result, CommandFailure)
    assert result.ok is False
    assert result.error.code == "INTERNAL_ERROR"
    assert result.error.message == "unexpected failure"


def test_command_success_is_frozen() -> None:
    data = _SampleData(value=1, name="x")
    result = success(data)
    with pytest.raises(PydanticValidationError):
        result.ok = False  # type: ignore[misc]


def test_command_failure_is_frozen() -> None:
    result = failure(code="X", message="y")
    with pytest.raises(PydanticValidationError):
        result.ok = True  # type: ignore[misc]
