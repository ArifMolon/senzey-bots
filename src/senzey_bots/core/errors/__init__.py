"""Domain error types and error code constants."""

from senzey_bots.core.errors.domain_errors import (
    AuthenticationError,
    BrokerError,
    DomainError,
    OrchestratorError,
    RiskLimitError,
    SecretsError,
    StrategyValidationError,
    ValidationError,
)
from senzey_bots.core.errors.error_codes import (
    AUTHENTICATION_ERROR,
    BROKER_ERROR,
    INTERNAL_ERROR,
    ORCHESTRATOR_ERROR,
    RISK_LIMIT_ERROR,
    SECRETS_ERROR,
    STRATEGY_VALIDATION_ERROR,
    VALIDATION_ERROR,
)

__all__ = [
    "AuthenticationError",
    "BrokerError",
    "DomainError",
    "OrchestratorError",
    "RiskLimitError",
    "SecretsError",
    "StrategyValidationError",
    "ValidationError",
    "AUTHENTICATION_ERROR",
    "BROKER_ERROR",
    "INTERNAL_ERROR",
    "ORCHESTRATOR_ERROR",
    "RISK_LIMIT_ERROR",
    "SECRETS_ERROR",
    "STRATEGY_VALIDATION_ERROR",
    "VALIDATION_ERROR",
]
