"""Agent flow timeline component — renders agent events in chronological order.

Reusable Streamlit component that displays a timeline of agent communication
events. Used on the Generate page and future pages (Backtest, Deploy).
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from senzey_bots.core.events.buffer import BufferedEvent, get_events

_EVENT_ICONS = {
    "agent.started": ":rocket:",
    "agent.progress": ":hourglass_flowing_sand:",
    "agent.completed": ":white_check_mark:",
    "agent.failed": ":x:",
}


def render_timeline(
    correlation_id: str,
    *,
    title: str = "Agent Activity",
) -> None:
    """Render the event timeline for a specific agent run.

    Args:
        correlation_id: Filter events to this correlation ID.
        title: Section title.
    """
    events = get_events(correlation_id=correlation_id)
    if not events:
        st.info("No agent events yet.")
        return

    st.subheader(title)
    for event in events:
        _render_event(event)


def render_live_status(
    correlation_id: str,
    status_container: Any,  # st.status() container — typed as Any for mypy compatibility
) -> None:
    """Update a st.status() container with the latest events.

    SYNC NOTE: Generation is synchronous in the Streamlit thread, so this function
    cannot be called mid-generation for true real-time updates. Instead, call it
    AFTER generation completes to show the full event log inside a status block.
    Future enhancement: background thread generation would enable true mid-run polling.

    Usage (post-generation display inside an already-finished st.status block):
        with st.status("Done", expanded=True) as status:
            result = generate_strategy(strategy_id)
            render_live_status(result.correlation_id, status)

    Args:
        correlation_id: Filter events to this correlation ID.
        status_container: The st.status() container to write to.
    """
    events = get_events(correlation_id=correlation_id)
    for event in events:
        icon = _get_icon(event.event_name)
        timestamp = event.occurred_at.strftime("%H:%M:%S")
        msg = event.payload_summary.get("message", event.event_name)
        status_container.write(f"{icon} `{timestamp}` — {msg}")


def _render_event(event: BufferedEvent) -> None:
    """Render a single event as a Streamlit element."""
    icon = _get_icon(event.event_name)
    timestamp = event.occurred_at.strftime("%H:%M:%S.%f")[:-3]
    source = event.source

    col_time, col_content = st.columns([1, 4])
    with col_time:
        st.caption(f"`{timestamp}`")
    with col_content:
        st.markdown(f"{icon} **{event.event_name}** — *{source}*")
        # Show payload summary as expandable detail
        summary = event.payload_summary
        if summary:
            filtered = {
                k: v for k, v in summary.items()
                if k not in ("data",) and v is not None
            }
            if filtered:
                with st.expander("Details", expanded=False):
                    for k, v in filtered.items():
                        st.text(f"  {k}: {v}")


def _get_icon(event_name: str) -> str:
    """Get icon for an event based on its name prefix."""
    prefix = ".".join(event_name.split(".")[:2])
    return _EVENT_ICONS.get(prefix, ":information_source:")
