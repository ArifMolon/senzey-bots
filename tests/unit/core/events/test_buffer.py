"""Unit tests for the in-memory event buffer."""

from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta

import pytest

from senzey_bots.core.events.buffer import (
    BufferedEvent,
    _MAX_BUFFER_SIZE,
    _buffer,
    clear_buffer,
    get_events,
    push_event,
)


def _make_event(
    event_name: str = "agent.started.v1",
    correlation_id: str = "corr-1",
    occurred_at: datetime | None = None,
) -> BufferedEvent:
    return BufferedEvent(
        event_name=event_name,
        occurred_at=occurred_at or datetime.now(tz=UTC),
        source="test.source",
        correlation_id=correlation_id,
        payload_summary={"step": "test"},
    )


class TestPushEvent:
    def test_push_adds_to_buffer(self) -> None:
        event = _make_event()
        push_event(event)
        events = get_events()
        assert len(events) == 1
        assert events[0] is event

    def test_push_multiple_events(self) -> None:
        for i in range(5):
            push_event(_make_event(event_name=f"agent.progress.v{i}"))
        assert len(get_events()) == 5


class TestGetEvents:
    def test_returns_all_events_without_filter(self) -> None:
        push_event(_make_event(correlation_id="a"))
        push_event(_make_event(correlation_id="b"))
        events = get_events()
        assert len(events) == 2

    def test_filter_by_correlation_id(self) -> None:
        push_event(_make_event(correlation_id="a"))
        push_event(_make_event(correlation_id="b"))
        push_event(_make_event(correlation_id="a"))
        events = get_events(correlation_id="a")
        assert len(events) == 2
        assert all(e.correlation_id == "a" for e in events)

    def test_filter_returns_empty_for_unknown_correlation_id(self) -> None:
        push_event(_make_event(correlation_id="known"))
        events = get_events(correlation_id="unknown")
        assert events == []

    def test_filter_by_since(self) -> None:
        t0 = datetime.now(tz=UTC)
        old = _make_event(occurred_at=t0 - timedelta(seconds=10))
        new = _make_event(occurred_at=t0 + timedelta(seconds=5))
        push_event(old)
        push_event(new)
        events = get_events(since=t0)
        assert len(events) == 1
        assert events[0] is new

    def test_filter_since_excludes_exact_time(self) -> None:
        t0 = datetime.now(tz=UTC)
        exact = _make_event(occurred_at=t0)
        push_event(exact)
        # since filters strictly greater than, not >=
        events = get_events(since=t0)
        assert len(events) == 0

    def test_combined_filters(self) -> None:
        t0 = datetime.now(tz=UTC)
        push_event(_make_event(correlation_id="a", occurred_at=t0 - timedelta(seconds=5)))
        push_event(_make_event(correlation_id="a", occurred_at=t0 + timedelta(seconds=1)))
        push_event(_make_event(correlation_id="b", occurred_at=t0 + timedelta(seconds=1)))
        events = get_events(correlation_id="a", since=t0)
        assert len(events) == 1


class TestClearBuffer:
    def test_clear_empties_buffer(self) -> None:
        push_event(_make_event())
        push_event(_make_event())
        clear_buffer()
        assert get_events() == []


class TestBufferBounded:
    def test_buffer_bounded_at_max_size(self) -> None:
        for i in range(_MAX_BUFFER_SIZE + 50):
            push_event(_make_event(event_name=f"agent.progress.v1", correlation_id=str(i)))
        events = get_events()
        assert len(events) == _MAX_BUFFER_SIZE


class TestBufferedEventFrozen:
    def test_buffered_event_is_frozen(self) -> None:
        event = _make_event()
        with pytest.raises((TypeError, AttributeError)):
            event.event_name = "other"  # type: ignore[misc]


class TestThreadSafety:
    def test_concurrent_push_and_get(self) -> None:
        errors: list[Exception] = []

        def pusher() -> None:
            try:
                for _ in range(50):
                    push_event(_make_event())
            except Exception as e:
                errors.append(e)

        def getter() -> None:
            try:
                for _ in range(50):
                    get_events()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=pusher) for _ in range(5)]
        threads += [threading.Thread(target=getter) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Thread safety errors: {errors}"
