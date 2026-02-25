"""Domain-specific exception types for senzey_bots."""


class AuthenticationError(Exception):
    """Raised when authentication fails."""


class SecretsError(Exception):
    """Raised on encrypted secrets operation failure."""
