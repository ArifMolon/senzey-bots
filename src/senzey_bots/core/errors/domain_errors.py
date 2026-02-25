"""Domain-specific exception types for senzey_bots.

Each exception carries a typed ErrorPayload for serialization/transport.
AuthenticationError and SecretsError (Story 1.2) are preserved as-is for
backward compatibility and will be migrated to carry payloads in a future story.
"""

from __future__ import annotations

from typing import Any


class AuthenticationError(Exception):
    """Raised when authentication fails."""


class SecretsError(Exception):
    """Raised on encrypted secrets operation failure."""


class DomainError(Exception):
    """Base domain exception carrying a typed error payload.

    All new domain exceptions must subclass this and pass an ErrorPayload
    (from core.orchestrator.contracts) at construction time.
    """

    def __init__(
        self,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


class BrokerError(DomainError):
    """Raised on broker API failures (IG adapter, connection, rate limit)."""

    def __init__(
        self, message: str, details: dict[str, Any] | None = None
    ) -> None:
        from senzey_bots.core.errors.error_codes import BROKER_ERROR

        super().__init__(code=BROKER_ERROR, message=message, details=details)


class StrategyValidationError(DomainError):
    """Raised when strategy code fails static analysis or schema validation."""

    def __init__(
        self, message: str, details: dict[str, Any] | None = None
    ) -> None:
        from senzey_bots.core.errors.error_codes import STRATEGY_VALIDATION_ERROR

        super().__init__(
            code=STRATEGY_VALIDATION_ERROR, message=message, details=details
        )


class RiskLimitError(DomainError):
    """Raised when a risk guard rule rejects an action."""

    def __init__(
        self, message: str, details: dict[str, Any] | None = None
    ) -> None:
        from senzey_bots.core.errors.error_codes import RISK_LIMIT_ERROR

        super().__init__(code=RISK_LIMIT_ERROR, message=message, details=details)


class OrchestratorError(DomainError):
    """Raised on orchestration/coordination failures."""

    def __init__(
        self, message: str, details: dict[str, Any] | None = None
    ) -> None:
        from senzey_bots.core.errors.error_codes import ORCHESTRATOR_ERROR

        super().__init__(code=ORCHESTRATOR_ERROR, message=message, details=details)


class ValidationError(DomainError):
    """Raised on general input/schema validation failures (non-strategy)."""

    def __init__(
        self, message: str, details: dict[str, Any] | None = None
    ) -> None:
        from senzey_bots.core.errors.error_codes import VALIDATION_ERROR

        super().__init__(code=VALIDATION_ERROR, message=message, details=details)
