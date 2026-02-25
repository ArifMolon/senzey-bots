"""In-memory event buffer — thread-safe buffer for real-time UI streaming.

Events published via publish_event() are also pushed to this buffer.
The UI polls the buffer to display events in near real time.
Buffer is bounded (maxlen) to prevent unbounded memory growth.
"""

from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class BufferedEvent:
    """Lightweight event record for UI display."""

    event_name: str
    occurred_at: datetime
    source: str
    correlation_id: str
    payload_summary: dict[str, Any] = field(default_factory=dict)


_MAX_BUFFER_SIZE = 500
_lock = threading.Lock()
_buffer: deque[BufferedEvent] = deque(maxlen=_MAX_BUFFER_SIZE)


def push_event(event: BufferedEvent) -> None:
    """Add an event to the buffer (thread-safe)."""
    with _lock:
        _buffer.append(event)


def get_events(
    correlation_id: str | None = None,
    since: datetime | None = None,
) -> list[BufferedEvent]:
    """Get events from buffer, optionally filtered.

    Args:
        correlation_id: Filter to events matching this correlation ID.
        since: Filter to events after this timestamp.

    Returns:
        List of matching events in chronological order.
    """
    with _lock:
        events = list(_buffer)

    if correlation_id is not None:
        events = [e for e in events if e.correlation_id == correlation_id]
    if since is not None:
        events = [e for e in events if e.occurred_at > since]

    return events


def clear_buffer() -> None:
    """Clear all events from the buffer (for testing)."""
    with _lock:
        _buffer.clear()
