"""Unit tests for domain error hierarchy."""

import pytest

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


def test_domain_error_stores_code_message_details() -> None:
    err = DomainError(code="MY_ERROR", message="something went wrong", details={"k": "v"})
    assert err.code == "MY_ERROR"
    assert err.message == "something went wrong"
    assert err.details == {"k": "v"}
    assert str(err) == "something went wrong"


def test_domain_error_defaults_details_to_none() -> None:
    err = DomainError(code="MY_ERROR", message="oops")
    assert err.details is None


def test_domain_error_with_details() -> None:
    err = DomainError(code="X", message="msg", details={"key": "value"})
    assert err.details == {"key": "value"}


def test_broker_error_code_and_subclass() -> None:
    err = BrokerError(message="connection refused")
    assert err.code == "BROKER_ERROR"
    assert isinstance(err, DomainError)


def test_broker_error_with_details() -> None:
    err = BrokerError(message="rate limited", details={"retry_after": 60})
    assert err.code == "BROKER_ERROR"
    assert err.details == {"retry_after": 60}


def test_strategy_validation_error_code() -> None:
    err = StrategyValidationError(message="invalid indicator")
    assert err.code == "STRATEGY_VALIDATION_ERROR"
    assert isinstance(err, DomainError)


def test_risk_limit_error_code() -> None:
    err = RiskLimitError(message="position too large")
    assert err.code == "RISK_LIMIT_ERROR"
    assert isinstance(err, DomainError)


def test_orchestrator_error_code() -> None:
    err = OrchestratorError(message="coordination failure")
    assert err.code == "ORCHESTRATOR_ERROR"
    assert isinstance(err, DomainError)


def test_validation_error_code() -> None:
    err = ValidationError(message="invalid input")
    assert err.code == "VALIDATION_ERROR"
    assert isinstance(err, DomainError)


def test_authentication_error_backward_compat() -> None:
    err = AuthenticationError("bad credentials")
    assert isinstance(err, Exception)
    assert str(err) == "bad credentials"


def test_secrets_error_backward_compat() -> None:
    err = SecretsError("decrypt failed")
    assert isinstance(err, Exception)
    assert str(err) == "decrypt failed"


def test_domain_errors_catchable_via_base() -> None:
    errors = [
        BrokerError("b"),
        StrategyValidationError("s"),
        RiskLimitError("r"),
        OrchestratorError("o"),
        ValidationError("v"),
    ]
    for err in errors:
        with pytest.raises(DomainError):
            raise err


def test_authentication_error_not_domain_error() -> None:
    err = AuthenticationError("fail")
    assert not isinstance(err, DomainError)
    assert isinstance(err, Exception)


def test_secrets_error_not_domain_error() -> None:
    err = SecretsError("fail")
    assert not isinstance(err, DomainError)
    assert isinstance(err, Exception)
