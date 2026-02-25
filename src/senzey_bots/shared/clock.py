"""Clock utilities — provides a testable UTC time source."""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return the current UTC datetime (timezone-aware).

    Returns:
        Current datetime in UTC with tzinfo set.

    """
    return datetime.now(tz=timezone.utc)  # noqa: UP017
