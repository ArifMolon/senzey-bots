"""Agent event payload models — typed payloads for agent communication events.

These Pydantic models define the payload structure for events published
during agent runs. Used with EventEnvelope[PayloadT] for type-safe event creation.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class AgentStartedPayload(BaseModel):
    """Payload for agent.started.v1 events."""

    model_config = ConfigDict(frozen=True)

    run_type: str
    strategy_id: int | None = None
    strategy_name: str | None = None
    input_type: str | None = None


class AgentProgressPayload(BaseModel):
    """Payload for agent.progress.v1 events."""

    model_config = ConfigDict(frozen=True)

    step: str  # e.g., "llm_call_started", "llm_call_completed", "validation_started"
    message: str
    details: dict[str, object] | None = None


class AgentCompletedPayload(BaseModel):
    """Payload for agent.completed.v1 events."""

    model_config = ConfigDict(frozen=True)

    run_type: str
    duration_ms: int
    result_summary: str | None = None


class AgentFailedPayload(BaseModel):
    """Payload for agent.failed.v1 events."""

    model_config = ConfigDict(frozen=True)

    run_type: str
    error_type: str
    error_message: str
    duration_ms: int
