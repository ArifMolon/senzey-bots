"""Structured JSON logger — outputs machine-readable JSON log lines only.

Architecture enforcement: never use plain-text logging.basicConfig().
All log output must be structured JSON.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


class _JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),  # noqa: UP017
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Return a logger that emits structured JSON to stdout.

    Args:
        name: Logger name (typically __name__).
        level: Logging level (default: INFO).

    Returns:
        Configured Logger instance.

    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(_JsonFormatter())
        logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger
