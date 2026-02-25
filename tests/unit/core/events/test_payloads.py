"""Unit tests for agent event payload models."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError as PydanticValidationError

from senzey_bots.core.events.payloads import (
    AgentCompletedPayload,
    AgentFailedPayload,
    AgentProgressPayload,
    AgentStartedPayload,
)


class TestAgentStartedPayload:
    def test_valid_minimal(self) -> None:
        p = AgentStartedPayload(run_type="strategy_generation")
        assert p.run_type == "strategy_generation"
        assert p.strategy_id is None
        assert p.strategy_name is None
        assert p.input_type is None

    def test_valid_full(self) -> None:
        p = AgentStartedPayload(
            run_type="strategy_generation",
            strategy_id=42,
            strategy_name="RSI Bot",
            input_type="rules_text",
        )
        assert p.strategy_id == 42
        assert p.strategy_name == "RSI Bot"
        assert p.input_type == "rules_text"

    def test_frozen(self) -> None:
        p = AgentStartedPayload(run_type="strategy_generation")
        with pytest.raises((TypeError, AttributeError, PydanticValidationError)):
            p.run_type = "other"  # type: ignore[misc]

    def test_serializes_to_json_snake_case(self) -> None:
        p = AgentStartedPayload(
            run_type="strategy_generation", strategy_id=1
        )
        data = json.loads(p.model_dump_json())
        assert "run_type" in data
        assert "strategy_id" in data


class TestAgentProgressPayload:
    def test_valid_minimal(self) -> None:
        p = AgentProgressPayload(step="llm_call_started", message="Calling LLM...")
        assert p.step == "llm_call_started"
        assert p.message == "Calling LLM..."
        assert p.details is None

    def test_valid_with_details(self) -> None:
        p = AgentProgressPayload(
            step="llm_call_completed",
            message="LLM responded",
            details={"tokens": 1500},
        )
        assert p.details == {"tokens": 1500}

    def test_frozen(self) -> None:
        p = AgentProgressPayload(step="s", message="m")
        with pytest.raises((TypeError, AttributeError, PydanticValidationError)):
            p.step = "other"  # type: ignore[misc]

    def test_missing_required_fields(self) -> None:
        with pytest.raises(PydanticValidationError):
            AgentProgressPayload(step="s")  # type: ignore[call-arg]


class TestAgentCompletedPayload:
    def test_valid_minimal(self) -> None:
        p = AgentCompletedPayload(run_type="strategy_generation", duration_ms=1200)
        assert p.run_type == "strategy_generation"
        assert p.duration_ms == 1200
        assert p.result_summary is None

    def test_valid_full(self) -> None:
        p = AgentCompletedPayload(
            run_type="strategy_generation",
            duration_ms=1500,
            result_summary="Generated MyStrategy",
        )
        assert p.result_summary == "Generated MyStrategy"

    def test_frozen(self) -> None:
        p = AgentCompletedPayload(run_type="r", duration_ms=0)
        with pytest.raises((TypeError, AttributeError, PydanticValidationError)):
            p.duration_ms = 999  # type: ignore[misc]

    def test_serializes_snake_case(self) -> None:
        p = AgentCompletedPayload(run_type="r", duration_ms=100)
        data = json.loads(p.model_dump_json())
        assert "run_type" in data
        assert "duration_ms" in data


class TestAgentFailedPayload:
    def test_valid(self) -> None:
        p = AgentFailedPayload(
            run_type="strategy_generation",
            error_type="llm_error",
            error_message="API timeout",
            duration_ms=500,
        )
        assert p.error_type == "llm_error"
        assert p.error_message == "API timeout"

    def test_frozen(self) -> None:
        p = AgentFailedPayload(
            run_type="r", error_type="e", error_message="m", duration_ms=0
        )
        with pytest.raises((TypeError, AttributeError, PydanticValidationError)):
            p.error_type = "other"  # type: ignore[misc]

    def test_missing_required_fields(self) -> None:
        with pytest.raises(PydanticValidationError):
            AgentFailedPayload(run_type="r")  # type: ignore[call-arg]
