"""Strategy input validation — validates user-provided strategy inputs before persistence.

Validates three input types: rules_text, pinescript, python_upload.
Returns structured validation results, never raises exceptions for invalid input.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass

VALID_INPUT_TYPES = frozenset({"rules_text", "pinescript", "python_upload"})

_MAX_INPUT_SIZE = 500_000  # 500 KB in characters
_MIN_INPUT_LENGTH = 10  # Minimum meaningful input

# PineScript markers — at least one must be present
_PINESCRIPT_MARKERS = (
    "//@version",
    "strategy(",
    "indicator(",
    "study(",
    "plot(",
    "hline(",
)

# Forbidden Python imports/calls — security blocklist
# NOTE: `importlib` is intentionally scoped to `importlib.import_module` and `importlib.util`
# because `importlib.metadata` is a legitimate stdlib usage (e.g., version checking).
_FORBIDDEN_PATTERNS = re.compile(
    r"\b(os\.system|subprocess|eval\s*\(|exec\s*\(|__import__|importlib\.import_module|importlib\.util|shutil\.rmtree)"
)


@dataclass(frozen=True)
class ValidationResult:
    """Result of input validation."""

    valid: bool
    error: str | None = None


def validate_strategy_input(
    input_type: str,
    input_content: str,
    file_name: str | None = None,
) -> ValidationResult:
    """Validate strategy input based on type.

    Returns ValidationResult with valid=True or valid=False with error message.
    """
    if input_type not in VALID_INPUT_TYPES:
        valid_types = ", ".join(sorted(VALID_INPUT_TYPES))
        return ValidationResult(
            valid=False,
            error=f"Unsupported input type: '{input_type}'. Must be one of: {valid_types}.",
        )

    if len(input_content) > _MAX_INPUT_SIZE:
        size = len(input_content)
        return ValidationResult(
            valid=False,
            error=f"Input too large ({size:,} chars). Maximum is {_MAX_INPUT_SIZE:,} chars.",
        )

    if len(input_content.strip()) < _MIN_INPUT_LENGTH:
        return ValidationResult(
            valid=False,
            error="Input is too short. Please provide meaningful strategy content.",
        )

    if input_type == "rules_text":
        return _validate_rules_text(input_content)
    if input_type == "pinescript":
        return _validate_pinescript(input_content)
    return _validate_python_upload(input_content, file_name)


def _validate_rules_text(content: str) -> ValidationResult:
    """Validate plain-text strategy rules."""
    # Rules text just needs to be non-empty and not too short (already checked above)
    return ValidationResult(valid=True)


def _validate_pinescript(content: str) -> ValidationResult:
    """Validate PineScript code has expected markers."""
    content_lower = content.lower()
    has_marker = any(marker.lower() in content_lower for marker in _PINESCRIPT_MARKERS)
    if not has_marker:
        return ValidationResult(
            valid=False,
            error=(
                "Input doesn't look like PineScript. "
                "Expected markers like '//@version', 'strategy(', or 'indicator('."
            ),
        )
    return ValidationResult(valid=True)


def _validate_python_upload(content: str, file_name: str | None) -> ValidationResult:
    """Validate uploaded Python strategy code."""
    if file_name and not file_name.endswith(".py"):
        return ValidationResult(
            valid=False,
            error=f"File must be a Python file (.py). Got: '{file_name}'.",
        )

    # Check for forbidden patterns (security)
    forbidden_match = _FORBIDDEN_PATTERNS.search(content)
    if forbidden_match:
        return ValidationResult(
            valid=False,
            error=f"Security violation: forbidden pattern '{forbidden_match.group()}' detected. "
            "Strategy code must not use os.system, subprocess, eval, exec, or __import__.",
        )

    # Verify parseable Python via AST
    try:
        ast.parse(content)
    except SyntaxError as e:
        return ValidationResult(
            valid=False,
            error=f"Python syntax error at line {e.lineno}: {e.msg}. Please fix and re-upload.",
        )

    return ValidationResult(valid=True)
