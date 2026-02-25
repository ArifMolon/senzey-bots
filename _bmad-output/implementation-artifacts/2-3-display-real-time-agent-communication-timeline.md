# Story 2.3: Display Real-Time Agent Communication Timeline

Status: in-progress

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a strategy developer,
I want to observe real-time agent orchestration logs in the UI,
so that I can understand system progress and diagnose generation issues early.

## Acceptance Criteria

1. **Given** an active generation or analysis run
   **When** agents exchange messages
   **Then** the timeline shows events in near real time with timestamps and source context
   **And** sensitive payload fields are masked according to security policy.

2. **Given** a completed generation run
   **When** the user views the timeline
   **Then** the full event history for that run is displayed with correlation ID, event type, and duration
   **And** events are grouped by the agent run that produced them.

3. **Given** an event payload containing sensitive data (API keys, secrets, tokens)
   **When** the timeline renders the payload
   **Then** sensitive fields are replaced with masked values (e.g., `"sk-***..."`)
   **And** no sensitive data appears in the rendered UI.

4. **Given** all new code files
   **When** lint and type checks run
   **Then** `ruff check .` passes with zero errors
   **And** `mypy src/` passes with zero errors
   **And** `pytest tests/unit/core/events/ tests/unit/ui/ tests/unit/database/repositories/ -v --tb=short` passes with >= 80% line coverage on new modules.

## Tasks / Subtasks

> **🚫 BLOCKING PREREQUISITE — Story 2.2 Must Be Implemented First**
> `src/senzey_bots/core/strategy/generator.py` does **not exist** yet (confirmed in codebase).
> Story 2.3 modifies `generator.py` to add event emission hooks (Task 6.2).
> **DO NOT start Task 6.2 until Story 2.2 is complete** and `generator.py` exists with
> `generate_strategy(strategy_id: int) -> GenerationResult` implemented.
> If implementing Stories 2.2 and 2.3 concurrently, coordinate on `generator.py` ownership.

- [x] Task 1: Create AgentRun database model + Alembic migration (AC: #2)
  - [x] 1.1 Create `src/senzey_bots/database/models/agent_run.py`:
    ```python
    """AgentRun model — tracks agent execution sessions for timeline display."""

    from __future__ import annotations

    from datetime import datetime

    from sqlalchemy import ForeignKey, String, Text
    from sqlalchemy.orm import Mapped, mapped_column

    from senzey_bots.database.base import Base


    class AgentRun(Base):
        """Tracks individual agent execution sessions.

        run_type: "strategy_generation", "backtest", "auto_fix", etc.
        status lifecycle: running → completed | failed
        """

        __tablename__ = "agent_runs"

        id: Mapped[int] = mapped_column(primary_key=True)
        correlation_id: Mapped[str] = mapped_column(
            String(36), nullable=False, unique=True
        )
        run_type: Mapped[str] = mapped_column(String(50), nullable=False)
        status: Mapped[str] = mapped_column(
            String(20), nullable=False, default="running"
        )
        strategy_id: Mapped[int | None] = mapped_column(
            ForeignKey("strategies.id"), nullable=True
        )
        metadata_json: Mapped[str | None] = mapped_column(
            Text, nullable=True, default=None
        )
        started_at: Mapped[datetime] = mapped_column(nullable=False)
        ended_at: Mapped[datetime | None] = mapped_column(
            nullable=True, default=None
        )
    ```
    **Column notes:**
    - `correlation_id`: UUID v4 string linking all events for this run. Unique constraint enforces one-run-per-correlation.
    - `run_type`: free-form string categorizing the run. Story 2.3 uses `"strategy_generation"`. Future stories add `"backtest"`, `"auto_fix"`, etc.
    - `strategy_id`: nullable FK to `strategies.id`. Links the run to a specific strategy. Nullable because future run types may not be strategy-related.
    - `metadata_json`: JSON string for run-specific metadata (e.g., `{"model": "claude-sonnet-4-6", "input_type": "rules_text"}`).
    - `status`: `running` → `completed` | `failed`. Simple lifecycle.
    - Use `str | None` NOT `Optional[str]` (ruff UP007).
  - [x] 1.2 Update `src/senzey_bots/database/models/__init__.py` — add `AgentRun` to exports:
    ```python
    from senzey_bots.database.models.agent_run import AgentRun
    from senzey_bots.database.models.auth_config import AuthConfig
    from senzey_bots.database.models.secret_metadata import SecretMetadata
    from senzey_bots.database.models.strategy import Strategy

    __all__ = ["AgentRun", "AuthConfig", "SecretMetadata", "Strategy"]
    ```
  - [x] 1.3 Generate Alembic migration:
    ```bash
    PYTHONPATH=src alembic revision --autogenerate -m "add_agent_runs_table"
    ```
    **IMPORTANT:** Use `PYTHONPATH=src`. Verify the migration creates `agent_runs` table with FK to `strategies`. Fix auto-generated `Union`/`Sequence` typing to `collections.abc.Sequence` and `str | None`.
    **FK DEPENDENCY:** The `agent_runs` table has `strategy_id FK → strategies.id`. Alembic auto-generate resolves this automatically when both models are imported, but verify the generated migration lists `strategies` table as a dependency (check `depends_on` or table creation order). The `strategies` table must be created BEFORE `agent_runs` in the migration chain. If the migration order is wrong, manually add `depends_on = ('<strategies_migration_revision>',)` to the migration file.
  - [x] 1.4 Apply migration: `PYTHONPATH=src alembic upgrade head`

- [x] Task 2: Create agent event payload models (AC: #1)
  - [x] 2.1 Create `src/senzey_bots/core/events/payloads.py`:
    ```python
    """Agent event payload models — typed payloads for agent communication events.

    These Pydantic models define the payload structure for events published
    during agent runs. Used with EventEnvelope[PayloadT] for type-safe event creation.
    """

    from __future__ import annotations

    from pydantic import BaseModel, ConfigDict


    class AgentStartedPayload(BaseModel):
        """Payload for agent.started.v1 events."""

        model_config = ConfigDict(frozen=True)

        run_type: str
        strategy_id: int | None = None
        strategy_name: str | None = None
        input_type: str | None = None


    class AgentProgressPayload(BaseModel):
        """Payload for agent.progress.v1 events."""

        model_config = ConfigDict(frozen=True)

        step: str  # e.g., "llm_call_started", "llm_call_completed", "validation_started"
        message: str
        details: dict[str, object] | None = None


    class AgentCompletedPayload(BaseModel):
        """Payload for agent.completed.v1 events."""

        model_config = ConfigDict(frozen=True)

        run_type: str
        duration_ms: int
        result_summary: str | None = None


    class AgentFailedPayload(BaseModel):
        """Payload for agent.failed.v1 events."""

        model_config = ConfigDict(frozen=True)

        run_type: str
        error_type: str
        error_message: str
        duration_ms: int
    ```
    **Design decisions:**
    - `frozen=True` — immutable payloads matching `EventEnvelope` pattern.
    - Payload types are generic enough for all agent run types (generation, backtest, auto-fix).
    - `AgentProgressPayload.step` is a free-form string — different run types define their own step names.
    - `details` is `dict[str, object] | None` — allows arbitrary structured data (e.g., token counts, model info).

- [x] Task 3: Create in-memory event buffer for real-time streaming (AC: #1)
  - [x] 3.1 Create `src/senzey_bots/core/events/buffer.py`:
    ```python
    """In-memory event buffer — thread-safe buffer for real-time UI streaming.

    Events published via publish_event() are also pushed to this buffer.
    The UI polls the buffer to display events in near real time.
    Buffer is bounded (maxlen) to prevent unbounded memory growth.
    """

    from __future__ import annotations

    import threading
    from collections import deque
    from dataclasses import dataclass, field
    from datetime import datetime
    from typing import Any


    @dataclass(frozen=True)
    class BufferedEvent:
        """Lightweight event record for UI display."""

        event_name: str
        occurred_at: datetime
        source: str
        correlation_id: str
        payload_summary: dict[str, Any]


    _MAX_BUFFER_SIZE = 500
    _lock = threading.Lock()
    _buffer: deque[BufferedEvent] = deque(maxlen=_MAX_BUFFER_SIZE)


    def push_event(event: BufferedEvent) -> None:
        """Add an event to the buffer (thread-safe)."""
        with _lock:
            _buffer.append(event)


    def get_events(
        correlation_id: str | None = None,
        since: datetime | None = None,
    ) -> list[BufferedEvent]:
        """Get events from buffer, optionally filtered.

        Args:
            correlation_id: Filter to events matching this correlation ID.
            since: Filter to events after this timestamp.

        Returns:
            List of matching events in chronological order.
        """
        with _lock:
            events = list(_buffer)

        if correlation_id is not None:
            events = [e for e in events if e.correlation_id == correlation_id]
        if since is not None:
            events = [e for e in events if e.occurred_at > since]

        return events


    def clear_buffer() -> None:
        """Clear all events from the buffer (for testing)."""
        with _lock:
            _buffer.clear()
    ```
    **Design decisions:**
    - **Thread-safe** via `threading.Lock` — generation may run in a thread while UI polls.
    - **Bounded** via `deque(maxlen=500)` — prevents memory leaks for long-running sessions.
    - **`BufferedEvent`** is a lightweight dataclass (not full `EventEnvelope`) — carries only what the UI needs.
    - **`payload_summary`** is a pre-processed dict (already masked) — no raw payloads in the buffer.
    - Module-level singleton pattern — same as `database/engine.py`.

- [x] Task 4: Create event masking utility (AC: #3)
  - [x] 4.1 Create `src/senzey_bots/core/events/masking.py`:
    ```python
    """Event payload masking — masks sensitive fields before UI display.

    Applies pattern-based masking to prevent exposure of API keys, secrets,
    and other sensitive data in the agent communication timeline.
    """

    from __future__ import annotations

    import re
    from typing import Any

    # Field name patterns that indicate sensitive data
    _SENSITIVE_PATTERNS = re.compile(
        r"(api_key|secret|password|token|credential|auth|private_key|"
        r"encrypted|master_key|fernet)",
        re.IGNORECASE,
    )


    def mask_payload(payload: dict[str, Any]) -> dict[str, Any]:
        """Recursively mask sensitive fields in a payload dict.

        Sensitive fields (matching _SENSITIVE_PATTERNS) have their values
        replaced with a masked preview showing only the first 4 characters.

        Args:
            payload: The raw payload dictionary to mask.

        Returns:
            New dictionary with sensitive values masked.
        """
        masked: dict[str, Any] = {}
        for key, value in payload.items():
            if _SENSITIVE_PATTERNS.search(key):
                masked[key] = _mask_value(value)
            elif isinstance(value, dict):
                masked[key] = mask_payload(value)
            else:
                masked[key] = value
        return masked


    def _mask_value(value: Any) -> str:
        """Mask a sensitive value, showing only a short prefix."""
        s = str(value)
        if len(s) <= 4:
            return "***"
        return f"{s[:4]}***"
    ```
    **Design decisions:**
    - **Regex-based field name matching** — catches `api_key`, `secret_key`, `auth_token`, etc.
    - **Recursive masking** — handles nested payload dicts.
    - **Short prefix preserved** — shows first 4 chars for identification (e.g., `"sk-p***"`) without exposing the full value.
    - **New dict returned** — never mutates the original payload.

- [x] Task 5: Create agent run repository (AC: #2)
  - [x] 5.1 Create `src/senzey_bots/database/repositories/agent_run_repo.py`:
    ```python
    """Agent run repository — CRUD operations for agent execution tracking."""

    from __future__ import annotations

    from sqlalchemy.orm import Session

    from senzey_bots.database.models.agent_run import AgentRun
    from senzey_bots.shared.clock import utcnow
    from senzey_bots.shared.logger import get_logger

    logger = get_logger(__name__)


    def create_agent_run(
        session: Session,
        *,
        correlation_id: str,
        run_type: str,
        strategy_id: int | None = None,
        metadata_json: str | None = None,
    ) -> AgentRun:
        """Create a new agent run record with status 'running'."""
        run = AgentRun(
            correlation_id=correlation_id,
            run_type=run_type,
            status="running",
            strategy_id=strategy_id,
            metadata_json=metadata_json,
            started_at=utcnow(),
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        return run


    def complete_agent_run(
        session: Session,
        correlation_id: str,
        *,
        status: str = "completed",
    ) -> AgentRun | None:
        """Mark an agent run as completed or failed.

        Returns updated AgentRun or None if not found.
        """
        run = _get_by_correlation(session, correlation_id)
        if run is None:
            return None
        run.status = status
        run.ended_at = utcnow()
        session.commit()
        session.refresh(run)
        return run


    def get_agent_run(
        session: Session, correlation_id: str
    ) -> AgentRun | None:
        """Get an agent run by correlation ID."""
        return _get_by_correlation(session, correlation_id)


    def list_recent_agent_runs(
        session: Session, *, limit: int = 20
    ) -> list[AgentRun]:
        """Return recent agent runs ordered by started_at descending."""
        return list(
            session.query(AgentRun)
            .order_by(AgentRun.started_at.desc())
            .limit(limit)
            .all()
        )


    def list_agent_runs_for_strategy(
        session: Session, strategy_id: int
    ) -> list[AgentRun]:
        """Return all agent runs for a specific strategy."""
        return list(
            session.query(AgentRun)
            .filter(AgentRun.strategy_id == strategy_id)
            .order_by(AgentRun.started_at.desc())
            .all()
        )


    def _get_by_correlation(
        session: Session, correlation_id: str
    ) -> AgentRun | None:
        """Internal helper to find agent run by correlation_id."""
        return session.query(AgentRun).filter(
            AgentRun.correlation_id == correlation_id
        ).first()
    ```
    **Design decisions:**
    - Module-level functions with `Session` param — matches `strategy_repo.py` pattern.
    - Keyed on `correlation_id` (not integer ID) — correlation IDs are the primary lookup key for timeline display.
    - `list_recent_agent_runs` with configurable limit — bounded result set for UI display.
    - `list_agent_runs_for_strategy` — allows showing all runs for a specific strategy.

- [ ] Task 6: Hook event emission into the generation flow (AC: #1)
  - [x] 6.1 Create `src/senzey_bots/core/strategy/generation_events.py`:
    ```python
    """Event emission hooks for strategy generation — publishes events during generation.

    Provides helper functions that wrap EventEnvelope creation and publishing
    for common generation lifecycle events.
    """

    from __future__ import annotations

    from typing import Any

    from pydantic import BaseModel, ConfigDict

    from senzey_bots.core.events.buffer import BufferedEvent, push_event
    from senzey_bots.core.events.masking import mask_payload
    from senzey_bots.core.events.models import EventEnvelope
    from senzey_bots.core.events.publisher import publish_event


    class _DictPayload(BaseModel):
        """Module-level payload wrapper for dict-based events.

        Defined at module level (not inside emit_event) to avoid mypy strict
        mode issues with locally-defined classes and prevent class re-creation
        on every call.
        """

        model_config = ConfigDict(frozen=True)

        data: dict[str, Any]


    def emit_event(
        event_name: str,
        source: str,
        correlation_id: str,
        payload: dict[str, Any],
    ) -> None:
        """Publish an event to both audit trail (JSONL) and in-memory buffer.

        This is the primary entry point for emitting agent events.
        The payload is masked before buffering for UI display.
        """
        envelope: EventEnvelope[_DictPayload] = EventEnvelope(
            event_name=event_name,
            source=source,
            correlation_id=correlation_id,
            payload=_DictPayload(data=payload),
        )

        # Publish to audit trail (JSONL)
        publish_event(envelope)

        # Push masked event to UI buffer
        push_event(BufferedEvent(
            event_name=event_name,
            occurred_at=envelope.occurred_at,
            source=source,
            correlation_id=correlation_id,
            payload_summary=mask_payload(payload),
        ))
    ```
    **Design decisions:**
    - **Dual-publish**: writes to JSONL audit trail AND in-memory buffer.
    - **Masking applied before buffering** — sensitive data never enters the UI buffer.
    - **Dict-based payloads** — simpler than requiring callers to create typed Pydantic models for every event. The typed payloads in `core/events/payloads.py` (Task 2) are designed for future use when callers want compile-time type safety (e.g., when building a typed MCP transport layer). For this story, `emit_event()` with raw dicts is sufficient.
    - **`_DictPayload` at module level** — avoids mypy strict mode issues with locally-defined Pydantic classes and prevents class re-creation on every `emit_event()` call.

  - [ ] 6.2 [BLOCKED: Story 2.2 prerequisite] Update `src/senzey_bots/core/strategy/generator.py` — add event emission to the generation flow:

    **Step A — Extend `GenerationResult` dataclass** (add `correlation_id` field):
    ```python
    @dataclass(frozen=True)
    class GenerationResult:
        """Result of strategy generation."""

        success: bool
        generated_code: str | None = None
        class_name: str | None = None
        metadata: str | None = None
        error: str | None = None
        error_type: str | None = None
        correlation_id: str | None = None  # ← Added by Story 2.3 for timeline filtering
    ```
    This field allows the UI to call `render_timeline(result.correlation_id)` after generation.

    **Step B — Add imports** at top of `generator.py`:
    ```python
    from senzey_bots.core.events.correlation import new_correlation_id
    from senzey_bots.core.strategy.generation_events import emit_event
    from senzey_bots.database.engine import get_session
    from senzey_bots.database.repositories.agent_run_repo import (
        complete_agent_run,
        create_agent_run,
    )
    ```

    **Step C — Modify `generate_strategy()` skeleton** (integrate event emission):
    ```python
    def generate_strategy(strategy_id: int) -> GenerationResult:
        """Generate executable Freqtrade code for a strategy draft."""
        correlation_id = new_correlation_id()
        source = "core.strategy.generator"

        # 1. Load strategy + create AgentRun record
        with get_session() as session:
            strategy = get_strategy(session, strategy_id)
            if strategy is None:
                return GenerationResult(
                    success=False,
                    error="Strategy not found",
                    error_type="not_found",
                    correlation_id=correlation_id,
                )
            # Extract fields before session closes (DetachedInstanceError prevention)
            s_id = strategy.id
            s_name = strategy.name
            s_input_type = strategy.input_type
            s_input_content = strategy.input_content

        with get_session() as session:
            create_agent_run(
                session,
                correlation_id=correlation_id,
                run_type="strategy_generation",
                strategy_id=s_id,
                metadata_json=None,
            )

        emit_event(
            "agent.started.v1", source, correlation_id,
            {"run_type": "strategy_generation", "strategy_id": s_id, "strategy_name": s_name},
        )

        try:
            # 2. LLM call
            emit_event("agent.progress.v1", source, correlation_id,
                       {"step": "llm_call_started", "message": "Calling LLM..."})
            llm_result = _call_llm(s_input_type, s_input_content, s_name)  # existing logic
            emit_event("agent.progress.v1", source, correlation_id,
                       {"step": "llm_call_completed", "message": "LLM responded"})

            if isinstance(llm_result, LLMError):  # existing error handling
                with get_session() as session:
                    complete_agent_run(session, correlation_id, status="failed")
                emit_event("agent.failed.v1", source, correlation_id,
                           {"run_type": "strategy_generation", "error_type": llm_result.error_type,
                            "error_message": llm_result.message, "duration_ms": 0})
                return GenerationResult(success=False, error=llm_result.message,
                                        error_type=llm_result.error_type, correlation_id=correlation_id)

            # 3. Validation
            emit_event("agent.progress.v1", source, correlation_id,
                       {"step": "validation_started", "message": "Validating generated code..."})
            val_result = validate_generated_code(llm_result.content)  # existing logic

            if not val_result.valid:
                with get_session() as session:
                    complete_agent_run(session, correlation_id, status="failed")
                emit_event("agent.failed.v1", source, correlation_id,
                           {"run_type": "strategy_generation", "error_type": "validation_error",
                            "error_message": val_result.error or "Validation failed", "duration_ms": 0})
                return GenerationResult(success=False, error=val_result.error,
                                        error_type="validation_error", correlation_id=correlation_id)

            # 4. Success
            with get_session() as session:
                complete_agent_run(session, correlation_id, status="completed")
            emit_event("agent.completed.v1", source, correlation_id,
                       {"run_type": "strategy_generation", "duration_ms": llm_result.duration_ms,
                        "result_summary": f"Generated {val_result.class_name}"})
            return GenerationResult(
                success=True,
                generated_code=llm_result.content,
                class_name=val_result.class_name,
                correlation_id=correlation_id,
            )

        except Exception as exc:  # noqa: BLE001
            with get_session() as session:
                complete_agent_run(session, correlation_id, status="failed")
            emit_event("agent.failed.v1", source, correlation_id,
                       {"run_type": "strategy_generation", "error_type": "unexpected_error",
                        "error_message": str(exc), "duration_ms": 0})
            return GenerationResult(success=False, error=str(exc),
                                    error_type="unexpected_error", correlation_id=correlation_id)
    ```
    **IMPORTANT:** The skeleton above shows the event emission integration pattern. Adapt it to Story 2.2's actual implementation — preserve all existing LLM call logic, retry handling, timeout logic, and DB update calls (`update_strategy_status`, `update_strategy_generation`). Do not remove any Story 2.2 functionality; only add the `emit_event()` and `create_agent_run()`/`complete_agent_run()` calls at the designated lifecycle points.

- [x] Task 7: Create timeline UI component (AC: #1, #3)
  - [x] 7.1 Create `src/senzey_bots/ui/components/agent_flow.py`:
    ```python
    """Agent flow timeline component — renders agent events in chronological order.

    Reusable Streamlit component that displays a timeline of agent communication
    events. Used on the Generate page and future pages (Backtest, Deploy).
    """

    from __future__ import annotations

    from datetime import datetime
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
    ```
    **Design decisions:**
    - **Reusable component** — `render_timeline()` can be called from any page.
    - **`render_live_status()`** for real-time display inside `st.status()` during synchronous operations.
    - **Icon mapping** based on event name prefix — visual distinction between started/progress/completed/failed.
    - **Expandable details** — payload summary shown in collapsible sections to keep timeline clean.
    - **Millisecond timestamps** — `%H:%M:%S.%f` truncated to ms for precision without clutter.

- [ ] Task 8: Integrate timeline into Generate page (AC: #1, #2) [BLOCKED: requires Task 6.2 / Story 2.2]
  - [ ] 8.1 [BLOCKED] Update `src/senzey_bots/ui/pages/10_generate.py` — add timeline display:
    **After the generation flow (when user clicks "Generate"):**

    Story 2.2 changes the draft row loop from tuple unpacking to dict-based iteration.
    In Story 2.2's updated `10_generate.py`, the drafts loop uses `d` as a dict with keys
    `id`, `name`, `input_type`, `status`, `created_at`, etc. If Story 2.2 hasn't changed
    this yet, adapt to whatever loop variable holds `strategy_id`.

    ```python
    from senzey_bots.core.strategy.generator import generate_strategy
    from senzey_bots.ui.components.agent_flow import render_timeline

    # Inside the drafts loop (Story 2.2 uses dict d; adapt if still tuple-unpacking):
    # strategy_id = d["id"]  ← dict access (Story 2.2 pattern)
    # strategy_id = strategy_id  ← tuple variable (Story 2.1 pattern)

    if st.button("Generate", key=f"gen_{strategy_id}"):
        with st.status("Generating strategy...", expanded=True) as status:
            result = generate_strategy(strategy_id)
            if result.success:
                status.update(label="Generation complete!", state="complete")
            else:
                status.update(label="Generation failed", state="error")

        # Persist correlation_id across reruns for timeline display
        st.session_state[f"session.generate.last_correlation_{strategy_id}"] = result.correlation_id

        # Show timeline for the completed run
        if result.correlation_id:
            render_timeline(result.correlation_id, title="Generation Timeline")
        st.rerun()
    ```

    **For previously completed runs (cross-rerun persistence):**
    ```python
    last_correlation = st.session_state.get(f"session.generate.last_correlation_{strategy_id}")
    if last_correlation:
        with st.expander("View Last Generation Timeline", expanded=False):
            render_timeline(last_correlation, title="Generation Timeline")
    ```
    **Note:** `result.correlation_id` is available because Story 2.3 Task 6.2 adds this field to `GenerationResult`.

  - [ ] 8.2 [BLOCKED] Update `src/senzey_bots/ui/pages/10_generate.py` — extend draft data extraction:
    Add `generated_code`, `generation_error` to the draft data dict (Story 2.2 columns). Also display generation status badges.

  - [ ] 8.3 [BLOCKED] Session state persistence is handled in Task 8.1 above.
    State key convention confirmed: `session.generate.last_correlation_{strategy_id}`.
    Prefix pattern `session.<module>.<name>` per architecture.md#State Management Patterns.

- [x] Task 9: Write unit tests (AC: #4)
  - [x] 9.0 Create `tests/unit/core/events/conftest.py` — shared buffer-clearing fixture:
    ```python
    """Shared fixtures for core/events unit tests."""

    import pytest

    from senzey_bots.core.events.buffer import clear_buffer


    @pytest.fixture(autouse=True)
    def _clear_event_buffer() -> None:
        """Clear the in-memory event buffer before each test to prevent state leakage."""
        clear_buffer()
        yield  # type: ignore[misc]
        clear_buffer()
    ```
    **Note:** `tests/unit/core/events/__init__.py` already exists (created by Story 1.3). Do NOT
    recreate it. The autouse fixture here applies to all tests in this directory automatically —
    individual test files do NOT need their own `clear_buffer()` calls.

  - [x] 9.1 Create `tests/unit/core/events/test_payloads.py`:
    - Test each payload model validates correctly.
    - Test payload models are frozen (immutable).
    - Test models serialize to JSON with `snake_case` keys.
  - [x] 9.2 Create `tests/unit/core/events/test_buffer.py`:
    - Test `push_event` adds event to buffer.
    - Test `get_events` returns all events.
    - Test `get_events` with `correlation_id` filter.
    - Test `get_events` with `since` filter.
    - Test `clear_buffer` empties the buffer.
    - Test buffer is bounded (maxlen=500).
    - Test thread safety (concurrent push/get).
    - Test `BufferedEvent` is frozen.
    - **State isolation handled by `conftest.py`** (Task 9.0) — `clear_buffer()` runs automatically before each test via `autouse=True`.
  - [x] 9.3 Create `tests/unit/core/events/test_masking.py`:
    - Test `mask_payload` masks `api_key` field.
    - Test `mask_payload` masks `secret` field.
    - Test `mask_payload` masks `password` field.
    - Test `mask_payload` masks `token` field.
    - Test `mask_payload` is case-insensitive.
    - Test `mask_payload` handles nested dicts.
    - Test `mask_payload` preserves non-sensitive fields.
    - Test `_mask_value` shows first 4 chars + `***`.
    - Test `_mask_value` with short values returns `***`.
  - [x] 9.4 Create `tests/unit/core/strategy/test_generation_events.py`:
    - Test `emit_event` publishes to audit trail (mock `publish_event`).
    - Test `emit_event` pushes to buffer (check buffer after call).
    - Test buffered event has masked payload.
    - Test buffered event has correct event_name, source, correlation_id.
  - [x] 9.5 Create `tests/unit/database/repositories/test_agent_run_repo.py`:
    - Test `create_agent_run` creates record with correct fields.
    - Test `create_agent_run` sets status="running" and started_at.
    - Test `complete_agent_run` updates status and ended_at.
    - Test `complete_agent_run` returns None for non-existent correlation_id.
    - Test `get_agent_run` returns run by correlation_id.
    - Test `get_agent_run` returns None for non-existent.
    - Test `list_recent_agent_runs` returns runs ordered by started_at desc.
    - Test `list_recent_agent_runs` respects limit.
    - Test `list_agent_runs_for_strategy` filters by strategy_id.
    - Use in-memory SQLite fixture (same pattern as Story 2.1).

    **⚠️ FK DEPENDENCY — CRITICAL:** `AgentRun.strategy_id` references `strategies.id`. For the
    in-memory SQLite fixture to create both tables, both models must be registered with
    `Base.metadata` before `create_all()` is called. Add this import to your test file (or to
    `tests/unit/database/repositories/conftest.py`):
    ```python
    # Force-import both models so Base.metadata registers both tables
    from senzey_bots.database.models.agent_run import AgentRun  # noqa: F401
    from senzey_bots.database.models.strategy import Strategy  # noqa: F401
    ```
    Without this, the existing `conftest.py` fixture only creates tables that have been
    imported transitively — and `strategies` table may be absent, causing an FK error.
  - [x] 9.6 Create `tests/unit/ui/__init__.py` (if not exists).
  - [x] 9.7 Create `tests/unit/ui/components/__init__.py`.
  - [x] 9.8 Create `tests/unit/ui/components/test_agent_flow.py`:
    - Test `_get_icon` returns correct icons for known event types.
    - Test `_get_icon` returns default icon for unknown types.
    - Test `_render_event` internal logic (mock st calls via `unittest.mock`).
    - **Note:** Full Streamlit rendering tests are difficult without `streamlit-testing-library`. Focus on pure logic functions.

- [ ] Task 10: Validate all gates pass (AC: #4)
  - [x] 10.1 Run `ruff check .` — zero errors.
  - [x] 10.2 Run `mypy src/` — zero errors.
  - [x] 10.3 Run full new-module coverage check:
    ```bash
    pytest tests/unit/core/events/ \
           tests/unit/core/strategy/test_generation_events.py \
           tests/unit/database/repositories/ \
           tests/unit/ui/components/ \
           -v --tb=short \
           --cov=src/senzey_bots/core/events \
           --cov=src/senzey_bots/core/strategy/generation_events \
           --cov=src/senzey_bots/database/repositories/agent_run_repo \
           --cov=src/senzey_bots/ui/components/agent_flow \
           --cov-report=term-missing
    ```
    All tests must pass and each module must show >= 80% line coverage.
  - [x] 10.4 Run full test suite to check for regressions:
    ```bash
    pytest tests/ -v --tb=short
    ```
    No regressions allowed — all pre-existing Story 1.x and 2.1 tests must still pass.
  - [x] 10.5 Run `PYTHONPATH=src alembic upgrade head` — migration applies cleanly.
  - [ ] 10.6 [DEFERRED] Streamlit smoke test: `streamlit run src/senzey_bots/ui/main.py` — timeline renders during/after generation (requires Story 2.2 for end-to-end flow).

## Dev Notes

### CRITICAL CONSTRAINTS

- **DO NOT MODIFY** `freqtrade/` or `trading_ig/` directories. [Source: architecture.md#Architectural Boundaries]
- **DO NOT MODIFY** `src/senzey_bots/app.py` — Streamlit entry is `ui/main.py`. [Source: Story 2.1]
- **DO NOT ADD `[tool.ruff]` to root `pyproject.toml`** — `ruff.toml` is source of truth. [Source: Story 1.1]
- **DO NOT USE `Optional[X]`** — use `X | None`. [Source: ruff UP007]
- **DO NOT USE `datetime.now()`** — use `shared/clock.utcnow()`. [Source: Story 1.2]
- **DO NOT USE `logging.extra`** — embed fields in JSON message string. [Source: Story 1.2]
- **DO NOT MODIFY** Story 1.2/1.3 core modules (`security/*`, `core/errors/*`, `core/orchestrator/*`).
- **DO NOT MODIFY** Story 2.1's `validator.py` or existing test files — extend only.
- **ALEMBIC requires `PYTHONPATH=src`** for all CLI invocations. [Source: Story 1.2]
- **ALL JSON keys and DB columns MUST be `snake_case`**. [Source: architecture.md#Naming Patterns]
- **DetachedInstanceError prevention** — access ORM attributes INSIDE `with get_session()` blocks. [Source: Story 2.1]
- **Streamlit widget keys MUST be explicit**. [Source: Story 2.1]
- **Streamlit state key prefixes**: `session.<module>.<name>`. [Source: architecture.md#State Management Patterns]
- **Event names MUST match `domain.action.v1` pattern** — enforced by `EventEnvelope` validator. [Source: Story 1.3]
- **Correlation IDs MUST be UUID v4** — enforced by `EventEnvelope` validator. [Source: Story 1.3]
- **Sensitive data MUST be masked before UI display** — required by AC #3 and security policy. [Source: epics.md#Story 2.3]
- **Thread safety** — the event buffer MUST be thread-safe since generation may run in the main Streamlit thread while UI polls.
- **Typed payloads vs raw dict** — `core/events/payloads.py` (Task 2) defines `AgentStartedPayload`, etc. for future compile-time type safety. This story uses `emit_event()` with raw dicts (simpler). Use typed payloads in a future story when building a strict MCP transport or when the caller needs Pydantic validation at the call site. Do NOT use typed payloads inside `generate_strategy()` for this story — raw dicts keep the code readable.

### Architecture Reference

**FR8 Scope:**
- User can view real-time inter-agent communication logs from the UI.
- [Source: epics.md#Story 2.3, prd.md#FR8]

**Component Locations (architecture.md#Project Structure):**
- `ui/components/agent_flow.py` — agent flow timeline component
- `core/events/models.py` — event envelope (Story 1.3 ✅)
- `core/events/publisher.py` — event publisher to JSONL (Story 1.3 ✅)
- `core/events/correlation.py` — correlation IDs (Story 1.3 ✅)
- `database/models/agent_run.py` — agent run tracking model
- `agents/mcp/` — MCP scaffolding (empty, for future use)

**Event System (architecture.md#Communication Patterns):**
- Event names: `domain.action.v1` pattern
- Event envelope: `event_id`, `event_name`, `occurred_at`, `source`, `correlation_id`, `payload`
- Event publishing: append-only JSONL at `var/audit/YYYY/MM/DD/events.jsonl`
- Story 2.3 adds: in-memory buffer for real-time UI streaming

**Data Flow (architecture.md#Integration Points):**
- Agent events: `agents/* -> core/events/publisher`
- Story 2.3 adds: `core/events/publisher -> core/events/buffer -> ui/components/agent_flow`

**Cross-Cutting Concerns (architecture.md):**
- Correlation ID: `core/events/correlation.py` + `shared/logger.py` — every agent run MUST carry correlation_id
- Immutable audit trail: `database/repositories/audit_repo.py` + `var/audit/...` — events written to JSONL are immutable
- Security: sensitive payload fields masked before UI display

### Previous Story Context

**Story 2.1 (In Review) — Built:**
- Strategy model, repository, input validator, Streamlit Generate page
- Key APIs: `get_session()`, `create_strategy()`, `list_strategies()`, `get_strategy()`, `delete_strategy()`
- 27 unit tests, 100% coverage
- Streamlit multipage nav with `st.Page` + `st.navigation`

**Story 2.2 (Ready-for-Dev) — Will Build:**
- Strategy generation via LLM (Anthropic API)
- LLM provider (`agents/llm/provider.py`), prompt templates, generation validator
- Strategy model extended: `generated_code`, `generation_metadata`, `generation_error` columns
- Repository extended: `update_strategy_status()`, `update_strategy_generation()`
- `GenerationResult` dataclass returned by `generate_strategy()`
- **CRITICAL DEPENDENCY:** Story 2.3 hooks INTO Story 2.2's `generate_strategy()` to emit events. If Story 2.2 is implemented first, Story 2.3 modifies `generator.py` to add event emission. If implemented concurrently, both stories must coordinate on `generator.py`.

**Story 1.3 (Done) — Infrastructure Available:**
- `EventEnvelope[PayloadT]` — typed, validated, immutable event envelope
- `publish_event(envelope)` — writes to JSONL audit trail
- `new_correlation_id()` / `get_correlation_id()` / `set_correlation_id()` — contextvars-based propagation
- `DomainError` subclasses — `OrchestratorError`, `StrategyValidationError`, etc.
- `CommandResult` = `CommandSuccess[T] | CommandFailure` — discriminated union
- `ErrorPayload` — serializable error transport

**Key patterns from previous stories:**
- `Mapped[type] = mapped_column(...)` for model fields (SQLAlchemy 2.0)
- In-memory SQLite fixtures in `conftest.py` for test isolation
- `get_session()` context manager — use `with get_session() as session:`
- Test functions: `def test_*(...) -> None:` (mypy strict)
- `from __future__ import annotations` at top of every module

**Debug lessons from previous stories:**
- regex `\b` after `(` fails — use Story 2.1's fixed pattern
- mypy dict type inference — use typed tuples or extract to typed variables
- Alembic migration auto-gen uses `Union`/`Sequence` — fix to `collections.abc.Sequence` and `str | None`
- ruff N999 for numeric-prefix page files — already configured in `ruff.toml`

### Git Intelligence

```
74bd650 review(story-1.3): fix 4 medium issues from adversarial code review
68f7118 feat(story-1.3): standardize internal messaging contracts and typed errors
801ef3e feat(story-1.2): implement local authentication and encrypted secrets store
c701b66 feat(story-1.1): bootstrap modular project skeleton with UV
```

**Commit convention:** `type(scope): description`
- Expected commit: `feat(story-2.3): display real-time agent communication timeline`

### Technical Stack (Exact Versions)

| Tool | Version | Purpose |
|---|---|---|
| Streamlit | 1.54.0 (pinned) | UI framework |
| SQLAlchemy | 2.0.47 (pinned) | ORM + session management |
| Alembic | 1.18.4 (pinned) | DB migrations |
| Pydantic | 2.12.5 (pinned) | Schema validation |
| Python | 3.11+ | Runtime |
| ruff | >=0.3.0 | Linting |
| mypy | >=1.10.0 | Type checking (strict) |
| pytest | >=8.0.0 | Testing |
| pytest-cov | >=7.0.0 | Coverage reporting |
| No new dependencies | — | All needed packages already installed |

### Streamlit Real-Time Display Patterns

**`st.status()` for synchronous progress:**
```python
with st.status("Processing...", expanded=True) as status:
    st.write("Step 1: Starting...")
    # ... synchronous operation ...
    st.write("Step 2: Completed.")
    status.update(label="Done!", state="complete")
```
`st.status()` updates render immediately during the synchronous call. This is the recommended approach for showing generation progress.

**`st.empty()` for dynamic content:**
```python
placeholder = st.empty()
placeholder.markdown("Current status: running")
# ... later ...
placeholder.markdown("Current status: completed")
```

**`st.rerun()` after state changes:**
After generation completes, call `st.rerun()` to refresh the page and display the final timeline.

**Session state for cross-rerun persistence:**
```python
if "session.generate.last_correlation" not in st.session_state:
    st.session_state["session.generate.last_correlation"] = None
```

### File Structure for This Story

```
New/modified files:
  src/senzey_bots/database/
    models/
      __init__.py                       ← MODIFY (add AgentRun export)
      agent_run.py                      ← NEW
    repositories/
      agent_run_repo.py                 ← NEW
    migrations/
      versions/
        <hash>_add_agent_runs_table.py  ← GENERATED by Alembic
  src/senzey_bots/core/
    events/
      payloads.py                       ← NEW (agent event payload models)
      buffer.py                         ← NEW (in-memory event buffer)
      masking.py                        ← NEW (sensitive field masking)
    strategy/
      generation_events.py              ← NEW (event emission helpers)
      generator.py                      ← MODIFY (add event emission hooks)
  src/senzey_bots/ui/
    components/
      __init__.py                       ← NEW (Python package marker — required!)
      agent_flow.py                     ← NEW (timeline component)
    pages/
      10_generate.py                    ← MODIFY (integrate timeline display)
  tests/
    unit/
      core/
        events/
          conftest.py                   ← NEW (autouse clear_buffer fixture)
          test_payloads.py              ← NEW
          test_buffer.py                ← NEW
          test_masking.py               ← NEW
        strategy/
          test_generation_events.py     ← NEW
      database/
        repositories/
          test_agent_run_repo.py        ← NEW
      ui/
        __init__.py                     ← NEW (if not exists)
        components/
          __init__.py                   ← NEW
          test_agent_flow.py            ← NEW
```

### Testing Standards

- Use `monkeypatch` for module-level overrides and environment variables.
- Each test function: `def test_*(...) -> None:` (mypy strict).
- In-memory SQLite via `conftest.py` fixture for DB tests.
- **Clear event buffer** in test fixtures (`autouse=True`) to prevent state leakage.
- Mock `publish_event` in generation_events tests — test buffer behavior independently.
- Streamlit component tests mock `st.*` calls via `unittest.mock` — test pure logic only.
- No new dependencies required.

### What This Story Does NOT Cover (Deferred)

- **MCP transport implementation** — `agents/mcp/transport.py` remains empty. Story 2.3 hooks into the generation flow directly via event emission helpers, not through MCP.
- **WebSocket/SSE real-time streaming** — uses Streamlit's `st.status()` for synchronous rendering. True push-based streaming deferred to future enhancement.
- **Event persistence to database** — events are buffered in-memory for UI and persisted to JSONL audit trail. A dedicated `agent_events` table is not needed for MVP.
- **Timeline filtering/search** — initial implementation shows all events for a correlation ID. Advanced filtering (by time, source, type) deferred.
- **Multi-run timeline** — shows one run at a time. Cross-run comparison deferred.
- **Notification integration** — Telegram/email alerts for agent failures deferred to Epic 5.
- **Background thread generation** — generation is synchronous in Streamlit thread. Background execution for true real-time polling deferred.

### Project Structure Notes

- All new files align with the architecture-defined directory structure. [Source: architecture.md#Complete Project Directory Structure]
- `ui/components/agent_flow.py` matches architecture's component layer. [Source: architecture.md#Project Structure]
- `database/models/agent_run.py` matches architecture's `agent_runs` table. [Source: architecture.md#Data Architecture]
- `core/events/buffer.py` and `core/events/masking.py` extend the events package with UI-facing capabilities.
- `core/strategy/generation_events.py` bridges the strategy domain with the events system.
- No conflicts detected with existing files or patterns.

### References

- FR8 (Agent communication visibility): [Source: _bmad-output/planning-artifacts/epics.md#Story 2.3]
- Epic 2 context: [Source: _bmad-output/planning-artifacts/epics.md#Epic 2]
- Architecture events: [Source: _bmad-output/planning-artifacts/architecture.md#Communication Patterns]
- Architecture components: [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure]
- Architecture state management: [Source: _bmad-output/planning-artifacts/architecture.md#State Management Patterns]
- Story 2.1 context: [Source: _bmad-output/implementation-artifacts/2-1-build-strategy-input-workspace.md]
- Story 2.2 context: [Source: _bmad-output/implementation-artifacts/2-2-generate-executable-freqtrade-strategy-via-llm.md]
- Story 1.3 events: [Source: _bmad-output/implementation-artifacts/1-3-standardize-internal-messaging-contracts-and-typed-errors.md]
- Project context: [Source: _bmad-output/project-context.md]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6 (dev-story pass — 2026-02-25)

### Debug Log References

- Pydantic v2 frozen model raises `ValidationError` on attribute assignment (not `TypeError`/`AttributeError`) — test expects `(TypeError, AttributeError, PydanticValidationError)`.
- `conftest.py` autouse fixture scoped to its directory only — `test_generation_events.py` needed its own `_clear_buffer` fixture since it lives in `tests/unit/core/strategy/` not `tests/unit/core/events/`.
- `_make_event(..., payload_summary={})` — empty dict is falsy; use `if ... is None` not `or {}` pattern.
- `st.caption()` in `_render_event` is called on module-level `st`, not the column context manager mock.
- Alembic auto-generated migration uses `Union`/`Sequence` from `typing` — fixed to `collections.abc.Sequence` and `str | None`.
- ruff I001 import-sort: `import sqlalchemy as sa` must follow `from alembic import op` alphabetically; fixed with `ruff check --fix`.

### Completion Notes List

- **Tasks 1-5, 7, 9, 10.1-10.5 complete** — all implemented, tested, and validated.
- **Task 6.1 complete** — `generation_events.py` created with `emit_event()` supporting dual-publish (JSONL + buffer) with masking.
- **Task 6.2 BLOCKED** — `src/senzey_bots/core/strategy/generator.py` does not exist (Story 2.2 not yet implemented). Cannot hook event emission until Story 2.2 creates `generate_strategy()`.
- **Task 8 BLOCKED** — `10_generate.py` Generate button integration requires `generator.py` (Story 2.2).
- **Quality gates passed**: ruff ✅ 0 errors, mypy ✅ 0 errors (60 files), pytest ✅ 195/195 pass, 100% coverage on all new modules.
- **Alembic migration** `6acd432aa9a7_add_agent_runs_table` applied cleanly; FK to `strategies.id` verified.

### File List

- `src/senzey_bots/database/models/agent_run.py` — NEW
- `src/senzey_bots/database/models/__init__.py` — MODIFIED (added AgentRun export)
- `src/senzey_bots/database/migrations/versions/6acd432aa9a7_add_agent_runs_table.py` — GENERATED
- `src/senzey_bots/database/repositories/agent_run_repo.py` — NEW
- `src/senzey_bots/core/events/payloads.py` — NEW
- `src/senzey_bots/core/events/buffer.py` — NEW
- `src/senzey_bots/core/events/masking.py` — NEW
- `src/senzey_bots/core/strategy/generation_events.py` — NEW
- `src/senzey_bots/ui/components/agent_flow.py` — NEW
- `tests/unit/core/events/conftest.py` — NEW
- `tests/unit/core/events/test_payloads.py` — NEW
- `tests/unit/core/events/test_buffer.py` — NEW
- `tests/unit/core/events/test_masking.py` — NEW
- `tests/unit/core/strategy/test_generation_events.py` — NEW
- `tests/unit/database/repositories/test_agent_run_repo.py` — NEW
- `tests/unit/ui/__init__.py` — NEW
- `tests/unit/ui/components/__init__.py` — NEW
- `tests/unit/ui/components/test_agent_flow.py` — NEW
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — MODIFIED (status: in-progress)

## Change Log

- 2026-02-25: Implemented Tasks 1-7, 9, 10.1-10.5. Created AgentRun model + migration, event payload models, in-memory thread-safe buffer, masking utility, agent run repository, generation_events emit helper, and agent_flow timeline UI component. 66 new unit tests added (195 total), 100% coverage on new modules, ruff/mypy clean. Tasks 6.2, 8.x blocked pending Story 2.2 (generator.py).
