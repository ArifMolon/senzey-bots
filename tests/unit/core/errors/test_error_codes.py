"""Unit tests for canonical error code constants."""

import re

from senzey_bots.core.errors import error_codes


def _get_all_codes() -> list[str]:
    return [
        v
        for k, v in vars(error_codes).items()
        if not k.startswith("_") and isinstance(v, str)
    ]


def test_all_error_codes_are_non_empty_strings() -> None:
    codes = _get_all_codes()
    assert len(codes) > 0
    for code in codes:
        assert isinstance(code, str)
        assert len(code) > 0, f"Error code must not be empty: {code!r}"


def test_all_error_codes_are_upper_snake_case() -> None:
    pattern = re.compile(r"^[A-Z][A-Z0-9_]*$")
    for code in _get_all_codes():
        assert pattern.match(code), f"Error code not UPPER_SNAKE_CASE: {code!r}"


def test_no_duplicate_error_code_values() -> None:
    codes = _get_all_codes()
    assert len(codes) == len(set(codes)), "Duplicate error code values found"


def test_expected_error_codes_exist() -> None:
    from senzey_bots.core.errors.error_codes import (
        AUTHENTICATION_ERROR,
        BROKER_ERROR,
        ORCHESTRATOR_ERROR,
        RISK_LIMIT_ERROR,
        SECRETS_ERROR,
        STRATEGY_VALIDATION_ERROR,
        VALIDATION_ERROR,
    )

    assert AUTHENTICATION_ERROR == "AUTHENTICATION_ERROR"
    assert SECRETS_ERROR == "SECRETS_ERROR"
    assert BROKER_ERROR == "BROKER_ERROR"
    assert STRATEGY_VALIDATION_ERROR == "STRATEGY_VALIDATION_ERROR"
    assert RISK_LIMIT_ERROR == "RISK_LIMIT_ERROR"
    assert ORCHESTRATOR_ERROR == "ORCHESTRATOR_ERROR"
    assert VALIDATION_ERROR == "VALIDATION_ERROR"
