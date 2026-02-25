"""Event payload masking — masks sensitive fields before UI display.

Applies pattern-based masking to prevent exposure of API keys, secrets,
and other sensitive data in the agent communication timeline.
"""

from __future__ import annotations

import re
from typing import Any

# Field name patterns that indicate sensitive data
_SENSITIVE_PATTERNS = re.compile(
    r"(api_key|secret|password|token|credential|auth|private_key|"
    r"encrypted|master_key|fernet)",
    re.IGNORECASE,
)


def mask_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Recursively mask sensitive fields in a payload dict.

    Sensitive fields (matching _SENSITIVE_PATTERNS) have their values
    replaced with a masked preview showing only the first 4 characters.

    Args:
        payload: The raw payload dictionary to mask.

    Returns:
        New dictionary with sensitive values masked.
    """
    masked: dict[str, Any] = {}
    for key, value in payload.items():
        if _SENSITIVE_PATTERNS.search(key):
            masked[key] = _mask_value(value)
        elif isinstance(value, dict):
            masked[key] = mask_payload(value)
        else:
            masked[key] = value
    return masked


def _mask_value(value: Any) -> str:
    """Mask a sensitive value, showing only a short prefix."""
    s = str(value)
    if len(s) <= 4:
        return "***"
    return f"{s[:4]}***"
