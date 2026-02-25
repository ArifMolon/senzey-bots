"""Unit tests for strategy input validator."""

import pytest

from senzey_bots.core.strategy.validator import ValidationResult, validate_strategy_input


# ---------------------------------------------------------------------------
# ValidationResult immutability
# ---------------------------------------------------------------------------


def test_validation_result_is_frozen() -> None:
    result = ValidationResult(valid=True)
    with pytest.raises((AttributeError, TypeError)):
        result.valid = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# rules_text
# ---------------------------------------------------------------------------


def test_validate_rules_text_valid() -> None:
    result = validate_strategy_input("rules_text", "Buy when RSI < 30, Sell when RSI > 70")
    assert result.valid is True
    assert result.error is None


def test_validate_rules_text_empty() -> None:
    result = validate_strategy_input("rules_text", "")
    assert result.valid is False
    assert result.error is not None


def test_validate_rules_text_too_short() -> None:
    result = validate_strategy_input("rules_text", "short")
    assert result.valid is False
    assert "too short" in result.error  # type: ignore[operator]


def test_validate_rules_text_too_large() -> None:
    large_input = "x" * 500_001
    result = validate_strategy_input("rules_text", large_input)
    assert result.valid is False
    assert "too large" in result.error  # type: ignore[operator]


# ---------------------------------------------------------------------------
# Invalid input_type
# ---------------------------------------------------------------------------


def test_validate_invalid_input_type() -> None:
    result = validate_strategy_input("unknown_type", "some valid content here")
    assert result.valid is False
    assert "Unsupported input type" in result.error  # type: ignore[operator]


# ---------------------------------------------------------------------------
# pinescript
# ---------------------------------------------------------------------------


def test_validate_pinescript_valid_with_version() -> None:
    pine = "//@version=5\nstrategy('My Strat', overlay=true)\n"
    result = validate_strategy_input("pinescript", pine)
    assert result.valid is True


def test_validate_pinescript_valid_with_indicator() -> None:
    pine = "indicator('RSI', shorttitle='RSI', overlay=false)\n"
    result = validate_strategy_input("pinescript", pine)
    assert result.valid is True


def test_validate_pinescript_missing_markers() -> None:
    result = validate_strategy_input("pinescript", "this is not pinescript code here")
    assert result.valid is False
    assert "PineScript" in result.error  # type: ignore[operator]


# ---------------------------------------------------------------------------
# python_upload
# ---------------------------------------------------------------------------


def test_validate_python_upload_valid() -> None:
    code = "def strategy():\n    return 'buy'\n"
    result = validate_strategy_input("python_upload", code)
    assert result.valid is True


def test_validate_python_upload_syntax_error() -> None:
    code = "def strategy(\n    return 'buy'\n"
    result = validate_strategy_input("python_upload", code)
    assert result.valid is False
    assert "syntax error" in result.error.lower()  # type: ignore[union-attr]


def test_validate_python_upload_forbidden_subprocess() -> None:
    code = "import subprocess\nsubprocess.run(['ls'])\n"
    result = validate_strategy_input("python_upload", code)
    assert result.valid is False
    assert "Security violation" in result.error  # type: ignore[operator]


def test_validate_python_upload_forbidden_eval() -> None:
    code = "x = eval('1 + 1')\n"
    result = validate_strategy_input("python_upload", code)
    assert result.valid is False
    assert "Security violation" in result.error  # type: ignore[operator]


def test_validate_python_upload_forbidden_exec() -> None:
    code = "exec('print(1)')\n"
    result = validate_strategy_input("python_upload", code)
    assert result.valid is False
    assert "Security violation" in result.error  # type: ignore[operator]


def test_validate_python_upload_forbidden_os_system() -> None:
    code = "import os\nos.system('rm -rf /')\n"
    result = validate_strategy_input("python_upload", code)
    assert result.valid is False
    assert "Security violation" in result.error  # type: ignore[operator]


def test_validate_python_upload_non_py_filename() -> None:
    code = "def strategy():\n    return 'buy'\n"
    result = validate_strategy_input("python_upload", code, file_name="strategy.txt")
    assert result.valid is False
    assert ".py" in result.error  # type: ignore[operator]


def test_validate_python_upload_py_filename_accepted() -> None:
    code = "def strategy():\n    return 'buy'\n"
    result = validate_strategy_input("python_upload", code, file_name="my_strategy.py")
    assert result.valid is True
