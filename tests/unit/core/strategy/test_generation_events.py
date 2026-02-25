"""Unit tests for strategy generation event emission."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

from senzey_bots.core.events.buffer import clear_buffer, get_events
from senzey_bots.core.strategy.generation_events import emit_event

_SOURCE = "core.strategy.generator"


@pytest.fixture(autouse=True)
def _clear_buffer() -> None:
    """Clear buffer before/after each test (autouse for this module)."""
    clear_buffer()
    yield  # type: ignore[misc]
    clear_buffer()


class TestEmitEvent:
    def test_emit_publishes_to_audit_trail(self) -> None:
        corr = str(uuid.uuid4())
        with patch(
            "senzey_bots.core.strategy.generation_events.publish_event"
        ) as mock_publish:
            emit_event(
                "agent.started.v1",
                _SOURCE,
                corr,
                {"run_type": "strategy_generation"},
            )
            mock_publish.assert_called_once()

    def test_emit_pushes_to_buffer(self) -> None:
        corr = str(uuid.uuid4())
        with patch("senzey_bots.core.strategy.generation_events.publish_event"):
            emit_event(
                "agent.progress.v1",
                _SOURCE,
                corr,
                {"step": "llm_call_started", "message": "Calling LLM..."},
            )
        events = get_events(correlation_id=corr)
        assert len(events) == 1
        assert events[0].event_name == "agent.progress.v1"

    def test_buffered_event_has_masked_payload(self) -> None:
        corr = str(uuid.uuid4())
        with patch("senzey_bots.core.strategy.generation_events.publish_event"):
            emit_event(
                "agent.started.v1",
                _SOURCE,
                corr,
                {"api_key": "sk-abc123", "run_type": "strategy_generation"},
            )
        events = get_events(correlation_id=corr)
        assert len(events) == 1
        # api_key must be masked in the buffer
        assert events[0].payload_summary["api_key"] == "sk-a***"
        # non-sensitive field preserved
        assert events[0].payload_summary["run_type"] == "strategy_generation"

    def test_buffered_event_has_correct_metadata(self) -> None:
        corr = str(uuid.uuid4())
        with patch("senzey_bots.core.strategy.generation_events.publish_event"):
            emit_event(
                "agent.completed.v1",
                _SOURCE,
                corr,
                {"run_type": "strategy_generation", "duration_ms": 1200},
            )
        events = get_events(correlation_id=corr)
        assert len(events) == 1
        ev = events[0]
        assert ev.event_name == "agent.completed.v1"
        assert ev.source == _SOURCE
        assert ev.correlation_id == corr

    def test_emit_multiple_events_same_correlation(self) -> None:
        corr = str(uuid.uuid4())
        with patch("senzey_bots.core.strategy.generation_events.publish_event"):
            emit_event("agent.started.v1", _SOURCE, corr, {"run_type": "r"})
            emit_event("agent.progress.v1", _SOURCE, corr, {"step": "s", "message": "m"})
            emit_event("agent.completed.v1", _SOURCE, corr, {"run_type": "r", "duration_ms": 0})
        events = get_events(correlation_id=corr)
        assert len(events) == 3

    def test_sensitive_data_not_in_buffer(self) -> None:
        """Sensitive data from raw payload should never appear unmasked in buffer."""
        corr = str(uuid.uuid4())
        with patch("senzey_bots.core.strategy.generation_events.publish_event"):
            emit_event(
                "agent.started.v1",
                _SOURCE,
                corr,
                {"token": "supersecrettoken12345", "step": "auth"},
            )
        events = get_events(correlation_id=corr)
        assert len(events) == 1
        payload = events[0].payload_summary
        # Full token must not appear
        assert "supersecrettoken12345" not in str(payload)
        # Masked version is present
        assert payload["token"] == "supe***"
