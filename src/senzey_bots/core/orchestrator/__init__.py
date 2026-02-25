"""Orchestrator package — command/result contracts and coordination."""

from senzey_bots.core.orchestrator.contracts import (
    CommandFailure,
    CommandResult,
    CommandSuccess,
    ErrorPayload,
    failure,
    failure_from_domain_error,
    success,
)

__all__ = [
    "CommandFailure",
    "CommandResult",
    "CommandSuccess",
    "ErrorPayload",
    "failure",
    "failure_from_domain_error",
    "success",
]
