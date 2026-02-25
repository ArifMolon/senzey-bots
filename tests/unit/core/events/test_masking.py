"""Unit tests for event payload masking."""

from __future__ import annotations

from senzey_bots.core.events.masking import _mask_value, mask_payload


class TestMaskPayload:
    def test_masks_api_key_field(self) -> None:
        result = mask_payload({"api_key": "sk-abc123"})
        assert result["api_key"] == "sk-a***"

    def test_masks_secret_field(self) -> None:
        result = mask_payload({"secret": "mysecretvalue"})
        assert result["secret"] == "myse***"

    def test_masks_password_field(self) -> None:
        result = mask_payload({"password": "hunter2"})
        assert result["password"] == "hunt***"

    def test_masks_token_field(self) -> None:
        result = mask_payload({"token": "Bearer abc123"})
        assert result["token"] == "Bear***"

    def test_case_insensitive_field_matching(self) -> None:
        result = mask_payload({"API_KEY": "sk-abc123", "Secret": "hidden"})
        assert result["API_KEY"] == "sk-a***"
        assert result["Secret"] == "hidd***"

    def test_masks_nested_dicts(self) -> None:
        payload = {
            "config": {
                "api_key": "sk-abc",
                "model": "claude",
            }
        }
        result = mask_payload(payload)
        assert result["config"]["api_key"] == "sk-a***"
        assert result["config"]["model"] == "claude"

    def test_preserves_non_sensitive_fields(self) -> None:
        result = mask_payload({"step": "llm_call", "duration_ms": 1200})
        assert result["step"] == "llm_call"
        assert result["duration_ms"] == 1200

    def test_does_not_mutate_original(self) -> None:
        original = {"api_key": "sk-abc123", "step": "start"}
        original_copy = dict(original)
        mask_payload(original)
        assert original == original_copy

    def test_empty_payload(self) -> None:
        assert mask_payload({}) == {}

    def test_masks_credential_field(self) -> None:
        result = mask_payload({"credential": "cred_abc123"})
        assert result["credential"] == "cred***"

    def test_masks_auth_field(self) -> None:
        result = mask_payload({"auth": "Basic dXNlcjpwYXNz"})
        assert result["auth"] == "Basi***"

    def test_masks_private_key_field(self) -> None:
        result = mask_payload({"private_key": "-----BEGIN"})
        assert result["private_key"] == "----***"

    def test_masks_fernet_field(self) -> None:
        result = mask_payload({"fernet_key": "gAAAAAB..."})
        assert result["fernet_key"] == "gAAA***"


class TestMaskValue:
    def test_shows_first_4_chars_plus_stars(self) -> None:
        assert _mask_value("abcdefgh") == "abcd***"

    def test_short_value_returns_stars(self) -> None:
        assert _mask_value("abc") == "***"

    def test_exactly_4_chars_returns_stars(self) -> None:
        assert _mask_value("abcd") == "***"

    def test_converts_non_string_to_string(self) -> None:
        result = _mask_value(12345678)
        assert result == "1234***"

    def test_empty_string_returns_stars(self) -> None:
        assert _mask_value("") == "***"
