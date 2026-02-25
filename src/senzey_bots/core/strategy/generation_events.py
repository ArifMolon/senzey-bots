"""Event emission hooks for strategy generation — publishes events during generation.

Provides helper functions that wrap EventEnvelope creation and publishing
for common generation lifecycle events.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from senzey_bots.core.events.buffer import BufferedEvent, push_event
from senzey_bots.core.events.masking import mask_payload
from senzey_bots.core.events.models import EventEnvelope
from senzey_bots.core.events.publisher import publish_event


class _DictPayload(BaseModel):
    """Module-level payload wrapper for dict-based events.

    Defined at module level (not inside emit_event) to avoid mypy strict
    mode issues with locally-defined classes and prevent class re-creation
    on every call.
    """

    model_config = ConfigDict(frozen=True)

    data: dict[str, Any]


def emit_event(
    event_name: str,
    source: str,
    correlation_id: str,
    payload: dict[str, Any],
) -> None:
    """Publish an event to both audit trail (JSONL) and in-memory buffer.

    This is the primary entry point for emitting agent events.
    The payload is masked before buffering for UI display.
    """
    envelope: EventEnvelope[_DictPayload] = EventEnvelope(
        event_name=event_name,
        source=source,
        correlation_id=correlation_id,
        payload=_DictPayload(data=payload),
    )

    # Publish to audit trail (JSONL)
    publish_event(envelope)

    # Push masked event to UI buffer
    push_event(BufferedEvent(
        event_name=event_name,
        occurred_at=envelope.occurred_at,
        source=source,
        correlation_id=correlation_id,
        payload_summary=mask_payload(payload),
    ))
