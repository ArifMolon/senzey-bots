"""Event envelope model — typed, validated, audit-compatible.

Events follow the domain.action.v1 naming convention and are serializable
to append-only JSONL for immutable audit trails.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

PayloadT = TypeVar("PayloadT", bound=BaseModel)

_EVENT_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*\.v\d+$")


class EventEnvelope(BaseModel, Generic[PayloadT]):
    """Typed event envelope for domain events.

    Validates event_name against domain.action.v1 pattern.
    Serializes to JSON with snake_case keys for JSONL audit logs.
    """

    model_config = ConfigDict(frozen=True)

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_name: str
    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC)
    )
    source: str
    correlation_id: str
    payload: PayloadT

    @field_validator("event_name")
    @classmethod
    def validate_event_name(cls, v: str) -> str:
        """Enforce domain.action.v1 naming convention."""
        if not _EVENT_NAME_RE.match(v):
            msg = f"event_name must match 'domain.action.vN' pattern, got '{v}'"
            raise ValueError(msg)
        return v

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, v: str) -> str:
        """Enforce UUID v4 format for event IDs (consistent with correlation_id)."""
        try:
            parsed = uuid.UUID(v)
        except ValueError:
            raise ValueError(f"event_id must be a valid UUID, got {v!r}")
        if parsed.version != 4:
            raise ValueError(
                f"event_id must be UUID v4, got version {parsed.version}"
            )
        return v

    @field_validator("correlation_id")
    @classmethod
    def validate_correlation_id(cls, v: str) -> str:
        """Enforce UUID v4 format for correlation IDs (AC#2)."""
        try:
            parsed = uuid.UUID(v)
        except ValueError:
            raise ValueError(f"correlation_id must be a valid UUID, got {v!r}")
        if parsed.version != 4:
            raise ValueError(
                f"correlation_id must be UUID v4, got version {parsed.version}"
            )
        return v
