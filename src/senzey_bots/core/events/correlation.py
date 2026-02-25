"""Correlation ID propagation via contextvars.

Provides request-scoped correlation IDs that propagate correctly across
asyncio task boundaries. Every critical flow (orders, risk checks, agent runs)
must carry a correlation_id.
"""

from __future__ import annotations

import contextvars
import uuid

_correlation_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)


def new_correlation_id() -> str:
    """Generate a new UUID v4 correlation ID and set it in context."""
    cid = str(uuid.uuid4())
    _correlation_id.set(cid)
    return cid


def get_correlation_id() -> str:
    """Return the current correlation ID, creating one if absent."""
    cid = _correlation_id.get()
    if cid is None:
        return new_correlation_id()
    return cid


def set_correlation_id(cid: str) -> contextvars.Token[str | None]:
    """Explicitly set a correlation ID (e.g., from an incoming request).

    Returns a Token that can restore the previous value via .reset().
    """
    return _correlation_id.set(cid)
