"""Unit tests for the agent flow timeline UI component."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, call, patch

import pytest

from senzey_bots.core.events.buffer import BufferedEvent
from senzey_bots.ui.components.agent_flow import (
    _EVENT_ICONS,
    _get_icon,
    _render_event,
    render_live_status,
    render_timeline,
)


def _make_event(
    event_name: str = "agent.started.v1",
    correlation_id: str = "test-corr",
    payload_summary: dict | None = None,
) -> BufferedEvent:
    return BufferedEvent(
        event_name=event_name,
        occurred_at=datetime(2026, 2, 25, 10, 30, 45, 123000, tzinfo=UTC),
        source="core.strategy.generator",
        correlation_id=correlation_id,
        payload_summary={"message": "Test event"} if payload_summary is None else payload_summary,
    )


class TestGetIcon:
    def test_started_event_gets_rocket_icon(self) -> None:
        assert _get_icon("agent.started.v1") == ":rocket:"

    def test_progress_event_gets_hourglass_icon(self) -> None:
        assert _get_icon("agent.progress.v1") == ":hourglass_flowing_sand:"

    def test_completed_event_gets_checkmark_icon(self) -> None:
        assert _get_icon("agent.completed.v1") == ":white_check_mark:"

    def test_failed_event_gets_x_icon(self) -> None:
        assert _get_icon("agent.failed.v1") == ":x:"

    def test_unknown_event_gets_default_icon(self) -> None:
        assert _get_icon("unknown.event.v1") == ":information_source:"

    def test_all_known_prefixes_in_event_icons(self) -> None:
        for prefix in _EVENT_ICONS:
            assert _get_icon(f"{prefix}.v1") == _EVENT_ICONS[prefix]


class TestRenderEvent:
    def test_render_event_calls_columns(self) -> None:
        event = _make_event()
        with patch("senzey_bots.ui.components.agent_flow.st") as mock_st:
            mock_col1 = MagicMock()
            mock_col2 = MagicMock()
            mock_st.columns.return_value = (mock_col1, mock_col2)
            mock_col1.__enter__ = MagicMock(return_value=mock_col1)
            mock_col1.__exit__ = MagicMock(return_value=False)
            mock_col2.__enter__ = MagicMock(return_value=mock_col2)
            mock_col2.__exit__ = MagicMock(return_value=False)

            _render_event(event)

            mock_st.columns.assert_called_once_with([1, 4])

    def test_render_event_shows_timestamp(self) -> None:
        event = _make_event()
        with patch("senzey_bots.ui.components.agent_flow.st") as mock_st:
            mock_col = MagicMock()
            mock_st.columns.return_value = (mock_col, mock_col)
            mock_col.__enter__ = MagicMock(return_value=mock_col)
            mock_col.__exit__ = MagicMock(return_value=False)

            _render_event(event)

            # st.caption is called on the module-level st (not the column mock)
            caption_calls = mock_st.caption.call_args_list
            assert any("10:30:45" in str(c) for c in caption_calls)


class TestRenderTimeline:
    def test_render_timeline_shows_info_when_empty(self) -> None:
        with patch("senzey_bots.ui.components.agent_flow.get_events", return_value=[]):
            with patch("senzey_bots.ui.components.agent_flow.st") as mock_st:
                render_timeline("non-existent-corr")
                mock_st.info.assert_called_once()

    def test_render_timeline_shows_subheader_when_events_exist(self) -> None:
        events = [_make_event()]
        with patch("senzey_bots.ui.components.agent_flow.get_events", return_value=events):
            with patch("senzey_bots.ui.components.agent_flow.st") as mock_st:
                mock_col = MagicMock()
                mock_st.columns.return_value = (mock_col, mock_col)
                mock_col.__enter__ = MagicMock(return_value=mock_col)
                mock_col.__exit__ = MagicMock(return_value=False)

                render_timeline("test-corr", title="My Timeline")

                mock_st.subheader.assert_called_once_with("My Timeline")

    def test_render_timeline_default_title(self) -> None:
        events = [_make_event()]
        with patch("senzey_bots.ui.components.agent_flow.get_events", return_value=events):
            with patch("senzey_bots.ui.components.agent_flow.st") as mock_st:
                mock_col = MagicMock()
                mock_st.columns.return_value = (mock_col, mock_col)
                mock_col.__enter__ = MagicMock(return_value=mock_col)
                mock_col.__exit__ = MagicMock(return_value=False)

                render_timeline("test-corr")

                mock_st.subheader.assert_called_once_with("Agent Activity")


class TestRenderLiveStatus:
    def test_writes_each_event_to_container(self) -> None:
        events = [
            _make_event("agent.started.v1", payload_summary={"message": "Starting"}),
            _make_event("agent.progress.v1", payload_summary={"step": "s", "message": "Progress"}),
        ]
        container = MagicMock()
        with patch(
            "senzey_bots.ui.components.agent_flow.get_events", return_value=events
        ):
            render_live_status("test-corr", container)

        assert container.write.call_count == 2

    def test_uses_event_name_as_fallback_when_no_message(self) -> None:
        # Pass an explicit empty dict (not None) to avoid the default
        event = _make_event("agent.completed.v1", payload_summary={})
        container = MagicMock()
        with patch(
            "senzey_bots.ui.components.agent_flow.get_events", return_value=[event]
        ):
            render_live_status("test-corr", container)

        write_args = container.write.call_args[0][0]
        # payload_summary.get("message", event.event_name) falls back to event_name
        assert "agent.completed.v1" in write_args

    def test_empty_events_no_writes(self) -> None:
        container = MagicMock()
        with patch(
            "senzey_bots.ui.components.agent_flow.get_events", return_value=[]
        ):
            render_live_status("test-corr", container)

        container.write.assert_not_called()
