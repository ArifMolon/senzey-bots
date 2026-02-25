"""Canonical domain error code constants.

Every error code is a string constant matching the architecture error taxonomy.
Use these constants in ErrorPayload.code — never hard-code raw strings elsewhere.
"""

AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
SECRETS_ERROR = "SECRETS_ERROR"
BROKER_ERROR = "BROKER_ERROR"
STRATEGY_VALIDATION_ERROR = "STRATEGY_VALIDATION_ERROR"
RISK_LIMIT_ERROR = "RISK_LIMIT_ERROR"
ORCHESTRATOR_ERROR = "ORCHESTRATOR_ERROR"
VALIDATION_ERROR = "VALIDATION_ERROR"
INTERNAL_ERROR = "INTERNAL_ERROR"
