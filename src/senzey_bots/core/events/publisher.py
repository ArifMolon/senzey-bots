"""Append-only event publisher — writes EventEnvelopes to JSONL audit files.

File path: var/audit/YYYY/MM/DD/events.jsonl
Each line is a single JSON object (one event envelope).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from senzey_bots.core.events.models import EventEnvelope
from senzey_bots.shared.logger import get_logger

logger = get_logger(__name__)

_AUDIT_BASE = Path("var/audit")


def publish_event(envelope: EventEnvelope[Any]) -> None:
    """Write an event envelope as a single JSONL line to the daily audit file.

    Creates parent directories if they do not exist.
    Logs the event via structured logger for operational visibility.
    """
    ts = envelope.occurred_at
    day_dir = _AUDIT_BASE / f"{ts.year:04d}" / f"{ts.month:02d}" / f"{ts.day:02d}"
    day_dir.mkdir(parents=True, exist_ok=True)

    audit_file = day_dir / "events.jsonl"
    line = envelope.model_dump_json()

    with audit_file.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

    logger.info(
        json.dumps(
            {
                "event": "event_published",
                "event_name": envelope.event_name,
                "event_id": envelope.event_id,
                "correlation_id": envelope.correlation_id,
            }
        )
    )
