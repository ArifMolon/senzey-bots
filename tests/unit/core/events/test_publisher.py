"""Unit tests for the append-only event publisher."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import BaseModel

import senzey_bots.core.events.publisher as publisher_module
from senzey_bots.core.events.models import EventEnvelope
from senzey_bots.core.events.publisher import publish_event


class _TestPayload(BaseModel):
    action: str


def _make_envelope(source: str = "test") -> EventEnvelope[_TestPayload]:
    return EventEnvelope[_TestPayload](
        event_name="order.opened.v1",
        source=source,
        correlation_id=str(uuid.uuid4()),
        payload=_TestPayload(action="buy"),
        occurred_at=datetime(2026, 2, 25, 12, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def isolated_audit_base(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect _AUDIT_BASE to a temp directory for test isolation."""
    audit_base = tmp_path / "audit"
    monkeypatch.setattr(publisher_module, "_AUDIT_BASE", audit_base)
    return audit_base


def test_publish_event_creates_directory_structure(
    isolated_audit_base: Path,
) -> None:
    envelope = _make_envelope()
    publish_event(envelope)
    expected_dir = isolated_audit_base / "2026" / "02" / "25"
    assert expected_dir.exists()
    assert expected_dir.is_dir()


def test_publish_event_writes_single_jsonl_line(
    isolated_audit_base: Path,
) -> None:
    envelope = _make_envelope()
    publish_event(envelope)
    audit_file = isolated_audit_base / "2026" / "02" / "25" / "events.jsonl"
    assert audit_file.exists()
    lines = audit_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1


def test_publish_event_appends_not_overwrites(
    isolated_audit_base: Path,
) -> None:
    env1 = _make_envelope(source="service_a")
    env2 = _make_envelope(source="service_b")
    publish_event(env1)
    publish_event(env2)
    audit_file = isolated_audit_base / "2026" / "02" / "25" / "events.jsonl"
    lines = audit_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2


def test_written_jsonl_is_valid_json(
    isolated_audit_base: Path,
) -> None:
    envelope = _make_envelope()
    publish_event(envelope)
    audit_file = isolated_audit_base / "2026" / "02" / "25" / "events.jsonl"
    line = audit_file.read_text(encoding="utf-8").strip()
    parsed = json.loads(line)
    assert isinstance(parsed, dict)
    assert "event_name" in parsed
    assert parsed["event_name"] == "order.opened.v1"
    assert "correlation_id" in parsed
    assert "event_id" in parsed


def test_written_jsonl_is_deserializable_to_event_envelope(
    isolated_audit_base: Path,
) -> None:
    """JSONL round-trip: written line must parse back into a typed EventEnvelope."""
    envelope = _make_envelope()
    publish_event(envelope)
    audit_file = isolated_audit_base / "2026" / "02" / "25" / "events.jsonl"
    line = audit_file.read_text(encoding="utf-8").strip()
    # Deserialize back to a typed EventEnvelope — this verifies the serialisation
    # format is model-compatible, not just valid JSON.
    restored = EventEnvelope[_TestPayload].model_validate_json(line)
    assert restored.event_name == envelope.event_name
    assert restored.event_id == envelope.event_id
    assert restored.correlation_id == envelope.correlation_id
    assert restored.payload.action == envelope.payload.action


def test_publish_event_logs_correlation_id(
    isolated_audit_base: Path,
) -> None:
    """Logger emits event_published JSON with correlation_id and all key fields."""
    from unittest.mock import patch

    envelope = _make_envelope()
    with patch.object(publisher_module, "logger") as mock_logger:
        publish_event(envelope)

    mock_logger.info.assert_called_once()
    logged_msg: str = mock_logger.info.call_args[0][0]
    parsed = json.loads(logged_msg)
    assert parsed["event"] == "event_published"
    assert parsed["correlation_id"] == envelope.correlation_id
    assert parsed["event_id"] == envelope.event_id
    assert parsed["event_name"] == envelope.event_name
