"""Orchestrator command/result contracts — Pydantic models for service communication.

All payloads use snake_case keys. Command results are discriminated on the `ok` field.
"""

from __future__ import annotations

from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T", bound=BaseModel)


class ErrorPayload(BaseModel):
    """Serializable error payload for transport/logging."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    code: str
    message: str
    details: dict[str, Any] | None = None


class CommandSuccess(BaseModel, Generic[T]):
    """Successful command result wrapping typed data."""

    model_config = ConfigDict(frozen=True)

    ok: Literal[True] = True
    data: T


class CommandFailure(BaseModel):
    """Failed command result wrapping an ErrorPayload."""

    model_config = ConfigDict(frozen=True)

    ok: Literal[False] = False
    error: ErrorPayload


# Discriminated union on `ok` — Pydantic routes to the right type automatically.
# Usage: CommandResult[MyPayload] for typed success data.
CommandResult = CommandSuccess[T] | CommandFailure


def success(data: T) -> CommandSuccess[T]:
    """Create a successful command result."""
    return CommandSuccess(ok=True, data=data)


def failure(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> CommandFailure:
    """Create a failed command result from error components."""
    return CommandFailure(
        ok=False,
        error=ErrorPayload(code=code, message=message, details=details),
    )


def failure_from_domain_error(exc: Exception) -> CommandFailure:
    """Convert a DomainError exception to a CommandFailure.

    Falls back to INTERNAL_ERROR for non-domain exceptions.
    """
    from senzey_bots.core.errors.domain_errors import DomainError

    if isinstance(exc, DomainError):
        return failure(
            code=exc.code, message=exc.message, details=exc.details
        )
    return failure(
        code="INTERNAL_ERROR",
        message=str(exc),
    )

