"""Events package — envelope models, correlation IDs, and publishing."""

from senzey_bots.core.events.correlation import (
    get_correlation_id,
    new_correlation_id,
    set_correlation_id,
)
from senzey_bots.core.events.models import EventEnvelope
from senzey_bots.core.events.publisher import publish_event

__all__ = [
    "EventEnvelope",
    "get_correlation_id",
    "new_correlation_id",
    "publish_event",
    "set_correlation_id",
]
