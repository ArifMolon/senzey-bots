# Story 1.3: Standardize Internal Messaging Contracts and Typed Errors

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a platform owner,
I want standardized service messaging schemas and typed domain errors,
so that agents/services exchange tasks and failures in a reliable, diagnosable way.

## Acceptance Criteria

1. **Given** orchestrator-to-service communication
   **When** commands and results are exchanged
   **Then** payloads follow a consistent schema with `snake_case` keys
   **And** failure responses use typed domain error categories with `code`, `message`, and optional `details` fields.

2. **Given** critical execution paths
   **When** events and errors are logged
   **Then** each record includes a `correlation_id` (UUID v4)
   **And** records remain append-only compatible for immutable auditing (JSONL format).

3. **Given** domain error payloads
   **When** serialized for transport or logging
   **Then** each error includes a `Literal` discriminator `code` field from the defined error taxonomy
   **And** Pydantic validation enforces schema correctness.

4. **Given** event envelope payloads
   **When** events are published
   **Then** each envelope contains `event_id`, `event_name` (matching `domain.action.v1` regex), `occurred_at` (ISO-8601 UTC), `source`, `correlation_id`, and typed `payload`
   **And** the envelope is serializable to JSON with `snake_case` keys.

5. **Given** command result payloads (success or failure)
   **When** services return results
   **Then** success returns `{"ok": true, "data": {...}}`
   **And** failure returns `{"ok": false, "error": {"code": "...", "message": "...", "details": {...}}}`
   **And** `ok` field serves as Pydantic discriminator between success and failure types.

6. **Given** correlation ID propagation requirements
   **When** a new request enters the system
   **Then** a `correlation_id` is generated or inherited via `contextvars.ContextVar`
   **And** the correlation ID is accessible throughout the async call chain.

7. **Given** all new code files
   **When** lint and type checks run
   **Then** `ruff check .` passes with zero errors
   **And** `mypy src/` passes with zero errors
   **And** `pytest tests/unit/core/ -v --tb=short --cov=src/senzey_bots/core --cov-report=term-missing` achieves >= 80% line coverage on the `core/errors`, `core/events`, and `core/orchestrator` modules.

More specifically:
1. `core/errors/domain_errors.py` is extended with `DomainError` base, `BrokerError`, `StrategyValidationError`, `RiskLimitError`, `OrchestratorError`, `ValidationError` — all carrying typed `ErrorPayload` instances.
2. `core/errors/error_codes.py` defines the canonical error code constants (`BROKER_ERROR`, `RISK_LIMIT_ERROR`, etc.) as `UPPER_SNAKE_CASE` string constants.
3. `core/orchestrator/contracts.py` defines Pydantic models: `ErrorPayload`, `CommandSuccess[T]`, `CommandFailure`, `CommandResult` discriminated union, plus `success()` / `failure()` factory functions.
4. `core/events/models.py` defines Pydantic models: `EventEnvelope[PayloadT]` (generic, frozen), with `event_name` regex validation (`domain.action.v1`).
5. `core/events/correlation.py` provides `get_correlation_id()`, `set_correlation_id()`, `new_correlation_id()` using `contextvars.ContextVar`.
6. `core/events/publisher.py` provides `publish_event()` that writes events as append-only JSONL to `var/audit/YYYY/MM/DD/events.jsonl`.
7. Unit tests cover all modules with >= 80% line coverage.

## Tasks / Subtasks

- [x] Task 1: Extend domain error hierarchy (AC: #1, #3)
  - [x] 1.1 Create `src/senzey_bots/core/errors/error_codes.py`:
    ```python
    """Canonical domain error code constants.

    Every error code is a string constant matching the architecture error taxonomy.
    Use these constants in ErrorPayload.code — never hard-code raw strings elsewhere.
    """

    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    SECRETS_ERROR = "SECRETS_ERROR"
    BROKER_ERROR = "BROKER_ERROR"
    STRATEGY_VALIDATION_ERROR = "STRATEGY_VALIDATION_ERROR"
    RISK_LIMIT_ERROR = "RISK_LIMIT_ERROR"
    ORCHESTRATOR_ERROR = "ORCHESTRATOR_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    ```
  - [x] 1.2 Update `src/senzey_bots/core/errors/domain_errors.py` — extend the existing file (which has `AuthenticationError` and `SecretsError` from Story 1.2). Add a `DomainError` base class and new typed exceptions. **Do NOT remove `AuthenticationError` or `SecretsError`** — they are used by Story 1.2 security modules.
    ```python
    """Domain-specific exception types for senzey_bots.

    Each exception carries a typed ErrorPayload for serialization/transport.
    AuthenticationError and SecretsError (Story 1.2) are preserved as-is for
    backward compatibility and will be migrated to carry payloads in a future story.
    """

    from __future__ import annotations

    from typing import TYPE_CHECKING, Any

    if TYPE_CHECKING:
        pass


    class AuthenticationError(Exception):
        """Raised when authentication fails."""


    class SecretsError(Exception):
        """Raised on encrypted secrets operation failure."""


    class DomainError(Exception):
        """Base domain exception carrying a typed error payload.

        All new domain exceptions must subclass this and pass an ErrorPayload
        (from core.orchestrator.contracts) at construction time.
        """

        def __init__(
            self,
            code: str,
            message: str,
            details: dict[str, Any] | None = None,
        ) -> None:
            super().__init__(message)
            self.code = code
            self.message = message
            self.details = details


    class BrokerError(DomainError):
        """Raised on broker API failures (IG adapter, connection, rate limit)."""

        def __init__(
            self, message: str, details: dict[str, Any] | None = None
        ) -> None:
            from senzey_bots.core.errors.error_codes import BROKER_ERROR

            super().__init__(code=BROKER_ERROR, message=message, details=details)


    class StrategyValidationError(DomainError):
        """Raised when strategy code fails static analysis or schema validation."""

        def __init__(
            self, message: str, details: dict[str, Any] | None = None
        ) -> None:
            from senzey_bots.core.errors.error_codes import STRATEGY_VALIDATION_ERROR

            super().__init__(
                code=STRATEGY_VALIDATION_ERROR, message=message, details=details
            )


    class RiskLimitError(DomainError):
        """Raised when a risk guard rule rejects an action."""

        def __init__(
            self, message: str, details: dict[str, Any] | None = None
        ) -> None:
            from senzey_bots.core.errors.error_codes import RISK_LIMIT_ERROR

            super().__init__(code=RISK_LIMIT_ERROR, message=message, details=details)


    class OrchestratorError(DomainError):
        """Raised on orchestration/coordination failures."""

        def __init__(
            self, message: str, details: dict[str, Any] | None = None
        ) -> None:
            from senzey_bots.core.errors.error_codes import ORCHESTRATOR_ERROR

            super().__init__(code=ORCHESTRATOR_ERROR, message=message, details=details)


    class ValidationError(DomainError):
        """Raised on general input/schema validation failures (non-strategy)."""

        def __init__(
            self, message: str, details: dict[str, Any] | None = None
        ) -> None:
            from senzey_bots.core.errors.error_codes import VALIDATION_ERROR

            super().__init__(code=VALIDATION_ERROR, message=message, details=details)
    ```
    **IMPORTANT:** Lazy imports (`from ... import` inside `__init__`) prevent circular imports between `domain_errors.py` and `error_codes.py`. Each exception stores `code`, `message`, `details` directly as attributes — no dependency on Pydantic at the exception layer.
  - [x] 1.3 Update `src/senzey_bots/core/errors/__init__.py` to re-export all exceptions and error codes:
    ```python
    """Domain error types and error code constants."""

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
    from senzey_bots.core.errors.error_codes import (
        AUTHENTICATION_ERROR,
        BROKER_ERROR,
        ORCHESTRATOR_ERROR,
        RISK_LIMIT_ERROR,
        SECRETS_ERROR,
        STRATEGY_VALIDATION_ERROR,
        VALIDATION_ERROR,
    )

    __all__ = [
        "AuthenticationError",
        "BrokerError",
        "DomainError",
        "OrchestratorError",
        "RiskLimitError",
        "SecretsError",
        "StrategyValidationError",
        "ValidationError",
        "AUTHENTICATION_ERROR",
        "BROKER_ERROR",
        "ORCHESTRATOR_ERROR",
        "RISK_LIMIT_ERROR",
        "SECRETS_ERROR",
        "STRATEGY_VALIDATION_ERROR",
        "VALIDATION_ERROR",
    ]
    ```

- [x] Task 2: Create command/result contracts (AC: #1, #5)
  - [x] 2.1 Create `src/senzey_bots/core/orchestrator/contracts.py`:
    ```python
    """Orchestrator command/result contracts — Pydantic models for service communication.

    All payloads use snake_case keys. Command results are discriminated on the `ok` field.
    """

    from __future__ import annotations

    from typing import Any, Generic, Literal, TypeVar

    from pydantic import BaseModel, ConfigDict, Field

    T = TypeVar("T", bound=BaseModel)


    class ErrorPayload(BaseModel):
        """Serializable error payload for transport/logging."""

        model_config = ConfigDict(frozen=True, populate_by_name=True)

        code: str
        message: str
        details: dict[str, Any] | None = None


    class CommandSuccess(BaseModel, Generic[T]):
        """Successful command result wrapping typed data."""

        model_config = ConfigDict(frozen=True)

        ok: Literal[True] = True
        data: T


    class CommandFailure(BaseModel):
        """Failed command result wrapping an ErrorPayload."""

        model_config = ConfigDict(frozen=True)

        ok: Literal[False] = False
        error: ErrorPayload


    # Discriminated union on `ok` — Pydantic routes to the right type automatically.
    # Usage: CommandResult[MyPayload] for typed success data.
    CommandResult = CommandSuccess[T] | CommandFailure


    def success(data: T) -> CommandSuccess[T]:
        """Create a successful command result."""
        return CommandSuccess(ok=True, data=data)


    def failure(
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> CommandFailure:
        """Create a failed command result from error components."""
        return CommandFailure(
            ok=False,
            error=ErrorPayload(code=code, message=message, details=details),
        )


    def failure_from_domain_error(exc: Exception) -> CommandFailure:
        """Convert a DomainError exception to a CommandFailure.

        Falls back to INTERNAL_ERROR for non-domain exceptions.
        """
        from senzey_bots.core.errors.domain_errors import DomainError

        if isinstance(exc, DomainError):
            return failure(
                code=exc.code, message=exc.message, details=exc.details
            )
        return failure(
            code="INTERNAL_ERROR",
            message=str(exc),
        )
    ```
    **KEY DESIGN DECISIONS:**
    - `frozen=True` on all payloads — command results are immutable once created.
    - `CommandResult = CommandSuccess[T] | CommandFailure` — union type. Callers can discriminate on `ok` field. Pydantic 2.12 handles `Literal[True] | Literal[False]` discrimination automatically.
    - `failure_from_domain_error()` bridges the exception hierarchy (Task 1) to the serializable contract layer.
    - No `ConfigDict(extra="allow")` — our internal contracts are strict; extra fields are rejected.
  - [x] 2.2 Update `src/senzey_bots/core/orchestrator/__init__.py`:
    ```python
    """Orchestrator package — command/result contracts and coordination."""

    from senzey_bots.core.orchestrator.contracts import (
        CommandFailure,
        CommandResult,
        CommandSuccess,
        ErrorPayload,
        failure,
        failure_from_domain_error,
        success,
    )

    __all__ = [
        "CommandFailure",
        "CommandResult",
        "CommandSuccess",
        "ErrorPayload",
        "failure",
        "failure_from_domain_error",
        "success",
    ]
    ```

- [x] Task 3: Create correlation ID utility (AC: #2, #6)
  - [x] 3.1 Create `src/senzey_bots/core/events/correlation.py`:
    ```python
    """Correlation ID propagation via contextvars.

    Provides request-scoped correlation IDs that propagate correctly across
    asyncio task boundaries. Every critical flow (orders, risk checks, agent runs)
    must carry a correlation_id.
    """

    from __future__ import annotations

    import contextvars
    import uuid

    _correlation_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
        "correlation_id", default=None
    )


    def new_correlation_id() -> str:
        """Generate a new UUID v4 correlation ID and set it in context."""
        cid = str(uuid.uuid4())
        _correlation_id.set(cid)
        return cid


    def get_correlation_id() -> str:
        """Return the current correlation ID, creating one if absent."""
        cid = _correlation_id.get()
        if cid is None:
            return new_correlation_id()
        return cid


    def set_correlation_id(cid: str) -> contextvars.Token[str | None]:
        """Explicitly set a correlation ID (e.g., from an incoming request).

        Returns a Token that can restore the previous value via .reset().
        """
        return _correlation_id.set(cid)
    ```
    **NOTE:** `contextvars.ContextVar` propagates correctly across `asyncio` boundaries. For Streamlit's threading model, each thread gets its own context copy — this is the correct behavior.

- [x] Task 4: Create event envelope model (AC: #2, #4)
  - [x] 4.1 Create `src/senzey_bots/core/events/models.py`:
    ```python
    """Event envelope model — typed, validated, audit-compatible.

    Events follow the domain.action.v1 naming convention and are serializable
    to append-only JSONL for immutable audit trails.
    """

    from __future__ import annotations

    import re
    import uuid
    from datetime import datetime, timezone
    from typing import Any, Generic, TypeVar

    from pydantic import BaseModel, ConfigDict, Field, field_validator

    PayloadT = TypeVar("PayloadT", bound=BaseModel)

    _EVENT_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*\.v\d+$")


    class EventEnvelope(BaseModel, Generic[PayloadT]):
        """Typed event envelope for domain events.

        Validates event_name against domain.action.v1 pattern.
        Serializes to JSON with snake_case keys for JSONL audit logs.
        """

        model_config = ConfigDict(frozen=True)

        event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
        event_name: str
        occurred_at: datetime = Field(
            default_factory=lambda: datetime.now(tz=timezone.utc)
        )
        source: str
        correlation_id: str
        payload: PayloadT

        @field_validator("event_name")
        @classmethod
        def validate_event_name(cls, v: str) -> str:
            """Enforce domain.action.v1 naming convention."""
            if not _EVENT_NAME_RE.match(v):
                msg = (
                    f"event_name must match 'domain.action.vN' pattern, got '{v}'"
                )
                raise ValueError(msg)
            return v
    ```
    **DESIGN DECISIONS:**
    - `frozen=True` — events are immutable facts.
    - `Generic[PayloadT]` — allows typed payloads like `EventEnvelope[TradeExecutedPayload]`.
    - `event_name` regex validation enforces the architecture naming convention at construction time.
    - `default_factory` for `event_id` and `occurred_at` — auto-generated if not provided.
    - Uses `datetime.now(tz=timezone.utc)` directly (same pattern as `shared/clock.py`'s `utcnow()`). For testability in event-publishing code, the caller should pass `occurred_at` explicitly in tests rather than mocking the field default.

- [x] Task 5: Create event publisher (AC: #2)
  - [x] 5.1 Create `src/senzey_bots/core/events/publisher.py`:
    ```python
    """Append-only event publisher — writes EventEnvelopes to JSONL audit files.

    File path: var/audit/YYYY/MM/DD/events.jsonl
    Each line is a single JSON object (one event envelope).
    """

    from __future__ import annotations

    import json
    from pathlib import Path
    from typing import Any

    from senzey_bots.core.events.correlation import get_correlation_id
    from senzey_bots.core.events.models import EventEnvelope
    from senzey_bots.shared.logger import get_logger

    logger = get_logger(__name__)

    _AUDIT_BASE = Path("var/audit")


    def publish_event(envelope: EventEnvelope[Any]) -> None:
        """Write an event envelope as a single JSONL line to the daily audit file.

        Creates parent directories if they do not exist.
        Logs the event via structured logger for operational visibility.
        """
        ts = envelope.occurred_at
        day_dir = _AUDIT_BASE / f"{ts.year:04d}" / f"{ts.month:02d}" / f"{ts.day:02d}"
        day_dir.mkdir(parents=True, exist_ok=True)

        audit_file = day_dir / "events.jsonl"
        line = envelope.model_dump_json()

        with audit_file.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

        logger.info(
            json.dumps(
                {
                    "event": "event_published",
                    "event_name": envelope.event_name,
                    "event_id": envelope.event_id,
                    "correlation_id": envelope.correlation_id,
                }
            )
        )
    ```
    **IMPORTANT:**
    - Append mode (`"a"`) ensures existing events are never overwritten — append-only audit requirement.
    - `model_dump_json()` produces a single-line JSON string (Pydantic 2.x).
    - Correlation ID is logged via embedded JSON in message string — NOT via `logging.extra` (which is silently dropped by `shared/logger.py`'s `_JsonFormatter`).
    - File path follows architecture pattern: `var/audit/YYYY/MM/DD/events.jsonl`.
  - [x] 5.2 Update `src/senzey_bots/core/events/__init__.py`:
    ```python
    """Events package — envelope models, correlation IDs, and publishing."""

    from senzey_bots.core.events.correlation import (
        get_correlation_id,
        new_correlation_id,
        set_correlation_id,
    )
    from senzey_bots.core.events.models import EventEnvelope
    from senzey_bots.core.events.publisher import publish_event

    __all__ = [
        "EventEnvelope",
        "get_correlation_id",
        "new_correlation_id",
        "publish_event",
        "set_correlation_id",
    ]
    ```

- [x] Task 6: Write unit tests (AC: #7)
  - [x] 6.1 Create `tests/unit/core/__init__.py` (empty).
  - [x] 6.2 Create `tests/unit/core/errors/__init__.py` (empty).
  - [x] 6.3 Create `tests/unit/core/errors/test_domain_errors.py`:
    - Test `DomainError` stores `code`, `message`, `details` attributes.
    - Test `BrokerError` has `code == "BROKER_ERROR"` and is a `DomainError` subclass.
    - Test `StrategyValidationError` has `code == "STRATEGY_VALIDATION_ERROR"`.
    - Test `RiskLimitError` has `code == "RISK_LIMIT_ERROR"`.
    - Test `OrchestratorError` has `code == "ORCHESTRATOR_ERROR"`.
    - Test `ValidationError` has `code == "VALIDATION_ERROR"`.
    - Test `DomainError` with `details=None` (default).
    - Test `DomainError` with `details={"key": "value"}`.
    - Test `AuthenticationError` still works (backward compatibility).
    - Test `SecretsError` still works (backward compatibility).
    - Test all exceptions are catchable via `except DomainError` (except `AuthenticationError` and `SecretsError` which are plain `Exception`).
  - [x] 6.4 Create `tests/unit/core/errors/test_error_codes.py`:
    - Test all error code constants are non-empty strings.
    - Test all error code constants are `UPPER_SNAKE_CASE`.
    - Test no duplicate values in the error code set.
  - [x] 6.5 Create `tests/unit/core/orchestrator/__init__.py` (empty).
  - [x] 6.6 Create `tests/unit/core/orchestrator/test_contracts.py`:
    - Test `ErrorPayload` creation with `code`, `message`, `details`.
    - Test `ErrorPayload` is frozen (raises on attribute assignment).
    - Test `ErrorPayload` with `details=None` (default).
    - Test `success(data)` returns `CommandSuccess` with `ok=True`.
    - Test `CommandSuccess` serialization produces `{"ok": true, "data": {...}}` with `snake_case` keys.
    - Test `failure(code, message, details)` returns `CommandFailure` with `ok=False`.
    - Test `CommandFailure` serialization produces `{"ok": false, "error": {"code": "...", "message": "...", "details": ...}}`.
    - Test `failure_from_domain_error()` with `BrokerError` produces correct `CommandFailure`.
    - Test `failure_from_domain_error()` with non-domain `Exception` produces `INTERNAL_ERROR` code.
    - Test `CommandSuccess` is frozen.
    - Test `CommandFailure` is frozen.
  - [x] 6.7 Create `tests/unit/core/events/__init__.py` (empty).
  - [x] 6.8 Create `tests/unit/core/events/test_correlation.py`:
    - Test `new_correlation_id()` returns a valid UUID v4 string.
    - Test `get_correlation_id()` returns the same ID when called twice in same context.
    - Test `get_correlation_id()` creates a new ID when none exists.
    - Test `set_correlation_id()` overrides the current context value.
    - Test `set_correlation_id()` returns a token that can restore previous value.
    - **IMPORTANT:** Each test function must reset context state. Use `set_correlation_id()` + token reset, or run in separate threads/tasks to isolate context.
  - [x] 6.9 Create `tests/unit/core/events/test_models.py`:
    - Test `EventEnvelope` creation with valid `event_name` (e.g., `"strategy.generated.v1"`).
    - Test `EventEnvelope` rejects invalid `event_name` (e.g., `"NotValid"`, `"no_version"`, `"UPPER.case.v1"`).
    - Test `EventEnvelope` auto-generates `event_id` (UUID) and `occurred_at` (datetime).
    - Test `EventEnvelope` is frozen (raises on attribute assignment).
    - Test `EventEnvelope` serialization to JSON produces `snake_case` keys.
    - Test `EventEnvelope` with typed payload (create a simple test payload model).
    - Test `EventEnvelope.model_dump_json()` produces valid JSON string.
  - [x] 6.10 Create `tests/unit/core/events/test_publisher.py`:
    - Test `publish_event()` creates directory structure `var/audit/YYYY/MM/DD/`.
    - Test `publish_event()` writes a single JSONL line.
    - Test multiple `publish_event()` calls append (not overwrite).
    - Test written JSONL is valid JSON and deserializable back to `EventEnvelope`.
    - Use `tmp_path` fixture to override `_AUDIT_BASE` (monkeypatch `publisher._AUDIT_BASE`).
    - Mock logger to verify correlation_id appears in log output.

- [x] Task 7: Validate all gates pass (AC: #7)
  - [x] 7.1 Run `ruff check .` — must pass with zero errors.
  - [x] 7.2 Run `mypy src/` — must pass with zero errors.
  - [x] 7.3 Run `pytest tests/unit/core/ -v --tb=short --cov=src/senzey_bots/core/errors --cov=src/senzey_bots/core/events --cov=src/senzey_bots/core/orchestrator --cov-report=term-missing` — all tests pass with >= 80% line coverage on `core/errors`, `core/events`, and `core/orchestrator` modules.
  - [x] 7.4 Run existing security tests to confirm no regressions: `pytest tests/unit/security/ -v --tb=short`.

## Dev Notes

### CRITICAL CONSTRAINTS

- **DO NOT MODIFY** `freqtrade/` or `trading_ig/` directories. [Source: architecture.md#Architectural Boundaries]
- **DO NOT REMOVE** `AuthenticationError` or `SecretsError` from `domain_errors.py` — they are actively used by Story 1.2's `auth_service.py` and `secrets_store.py`. [Source: Story 1.2 implementation]
- **DO NOT USE `logging.extra` for `correlation_id`** — `shared/logger.py`'s `_JsonFormatter` only serializes `{timestamp, level, logger, message}` and silently drops `extra` fields. Embed correlation_id directly in the message JSON string. [Source: Story 1.2 Dev Notes, shared/logger.py implementation]
- **DO NOT USE `Optional[X]`** — ruff's `UP007` rule flags it. Use `X | None` (Python 3.11+). [Source: ruff.toml lint rules, Story 1.2 Dev Notes]
- **DO NOT ADD `[tool.ruff]` to root `pyproject.toml`** — `ruff.toml` is the single source of truth. [Source: Story 1.1 Dev Notes]
- **ALL JSON KEYS MUST BE `snake_case`** — architecture mandates this for all internal/external payloads. No `camelCase`. [Source: architecture.md#Format Patterns]
- **Pydantic `frozen=True`** on all contract/event models — immutable payloads prevent accidental mutation.
- **`contextvars`** for correlation_id — NOT thread-local storage. `contextvars` propagates correctly in asyncio; `threading.local` does not. [Source: Python docs]
- **Event publisher uses file append mode** — never truncate or overwrite existing audit logs. [Source: architecture.md#Audit model]

### Architecture Reference

**Error Taxonomy (architecture.md#API & Communication Patterns):**
- `BrokerError` — broker API failure (IG adapter, connection, rate limit)
- `StrategyValidationError` — strategy code fails static analysis or schema
- `RiskLimitError` — risk guard rejection (pre-trade)
- `OrchestratorError` — orchestration/coordination failure
- `ValidationError` — general input/schema validation failure
- `AuthenticationError` — auth failure (Story 1.2, preserved)
- `SecretsError` — secrets operation failure (Story 1.2, preserved)

**Internal Command Result Format (architecture.md#Format Patterns):**
```json
// Success:
{ "ok": true, "data": { ... } }
// Failure:
{ "ok": false, "error": { "code": "RISK_LIMIT", "message": "...", "details": {...} } }
```

**Event Envelope (architecture.md#Communication Patterns):**
```json
{
  "event_id": "uuid",
  "event_name": "domain.action.v1",
  "occurred_at": "2026-02-25T18:00:00Z",
  "source": "service_name",
  "correlation_id": "uuid",
  "payload": { ... }
}
```

**Event Name Convention:** `domain.action.v1` (e.g., `strategy.generated.v1`, `order.opened.v1`, `risk.halt_triggered.v1`). Breaking changes require version bump to `v2`.

**Correlation ID Pattern:**
```python
import json, uuid
correlation_id = str(uuid.uuid4())
logger.warning(json.dumps({"event": "some_event", "correlation_id": correlation_id}))
```

### Previous Story Context (Story 1.2)

**What was built:**
- `database/engine.py` — SQLite singleton with `get_engine()` and `get_session()` context manager.
- `database/base.py` — `DeclarativeBase` subclass for all ORM models.
- `database/models/auth_config.py` — `AuthConfig` model (Argon2 hash + Fernet salt).
- `database/models/secret_metadata.py` — `SecretMetadata` model (encrypted values).
- `security/password_hasher.py` — `hash_password()`, `verify_password()`, `check_needs_rehash()`.
- `security/crypto_service.py` — `encrypt()`, `decrypt()`, `derive_master_key()` using Fernet.
- `security/auth_service.py` — `setup_password()`, `authenticate()`, `is_configured()`.
- `security/secrets_store.py` — `store_secret()`, `get_secret()`, `list_secret_names()`, `delete_secret()`.
- `core/errors/domain_errors.py` — `AuthenticationError`, `SecretsError` (minimal, no payload).
- `tests/unit/security/` — Full test suite with in-memory SQLite fixtures.

**Key patterns established:**
- Use `shared/clock.py`'s `utcnow()` for all timestamps.
- Use `shared/logger.py`'s `get_logger(__name__)` for structured JSON logging.
- Embed `correlation_id` directly in JSON message strings (not `logging.extra`).
- Use `str | None` not `Optional[str]`.
- Use `Mapped[type] = mapped_column(...)` for SQLAlchemy models.
- Use `conftest.py` with in-memory SQLite fixtures for test isolation.
- `mypy strict = True` — all functions need return type annotations, no implicit `Any`.

**Existing imports to be aware of:**
- `security/auth_service.py` imports `AuthenticationError` from `senzey_bots.core.errors.domain_errors`.
- If you rename or restructure `domain_errors.py`, those imports will break.

### Git Intelligence (Recent Commits)

```
6d31b5c chore(bmad): update story 1.1 artifacts to done + sprint status sync
c701b66 feat(story-1.1): bootstrap modular project skeleton with UV
```
- Commit convention: `type(scope): description`
- Types used: `feat`, `chore`, `docs`
- Scope matches story number or area

### Technical Stack (Exact Versions)

| Tool | Version | Purpose |
|---|---|---|
| Pydantic | 2.12.5 (pinned) | Schema validation, discriminated unions |
| SQLAlchemy | 2.0.47 (pinned) | ORM (not directly used in this story, but must coexist) |
| Python | 3.11+ | `contextvars`, `str | None` syntax, `tomllib` |
| ruff | >=0.3.0 | Linting (UP007 enforces `X | None`) |
| mypy | >=1.10.0 | Type checking (strict mode) |
| pytest | >=8.0.0 | Testing |
| pytest-cov | >=7.0.0 | Coverage reporting (installed in Story 1.2) |

### Pydantic 2.12.5 Specifics

- **Discriminated unions:** Use `Literal` field discriminator for `CommandSuccess[T] | CommandFailure` on `ok` field. Pydantic routes directly to the right type — no tag functions needed for simple cases.
- **`frozen=True`:** Models are immutable. `model_config = ConfigDict(frozen=True)`.
- **`model_dump_json()`:** Produces single-line JSON — use for JSONL audit output.
- **`model_validate_json()`:** Parse JSON bytes/str directly into model — faster than `model_validate(json.loads(...))`.
- **Generic models:** `EventEnvelope[PayloadT]` works with `Generic[PayloadT]` — TypeVar must be `bound=BaseModel`.
- **`field_validator`:** Use `@classmethod` decorator pattern for field validators.
- **`from __future__ import annotations`:** Required in all Pydantic model files for forward reference support and performance.
- **Instance-method form for `@model_validator(mode='after')`** — classmethod form is deprecated in 2.12.

### File Structure for This Story

```
New/modified files:
  src/senzey_bots/core/
    errors/
      __init__.py                    ← UPDATE (re-export all errors + codes)
      domain_errors.py               ← UPDATE (extend with DomainError hierarchy)
      error_codes.py                 ← NEW
    events/
      __init__.py                    ← UPDATE (re-export)
      correlation.py                 ← NEW
      models.py                      ← NEW
      publisher.py                   ← NEW
    orchestrator/
      __init__.py                    ← UPDATE (re-export)
      contracts.py                   ← NEW
  tests/unit/core/
    __init__.py                      ← NEW
    errors/
      __init__.py                    ← NEW
      test_domain_errors.py          ← NEW
      test_error_codes.py            ← NEW
    events/
      __init__.py                    ← NEW
      test_correlation.py            ← NEW
      test_models.py                 ← NEW
      test_publisher.py              ← NEW
    orchestrator/
      __init__.py                    ← NEW
      test_contracts.py              ← NEW
```

### Testing Standards

- Use `tmp_path` fixture for file-system tests (event publisher).
- Use `monkeypatch` to override module-level paths (e.g., `publisher._AUDIT_BASE`).
- Each test function: `def test_*(... ) -> None:` (mypy strict requires return type).
- For `contextvars` tests: reset context in each test to avoid cross-test contamination.
- For frozen model tests: assert `ValidationError` is raised on attribute assignment (`with pytest.raises(ValidationError)`). Note: Pydantic raises its own `ValidationError` for frozen model mutations — this is different from our `core.errors.ValidationError`.
- Import pattern for tests: `from senzey_bots.core.errors import BrokerError, BROKER_ERROR`
- No new dependencies required — Pydantic, pytest, pytest-cov, pytest-mock already installed.

### What This Story Does NOT Cover (Deferred)

- **MCP transport implementation** — Story 2.x will implement `agents/mcp/transport.py` and `registry.py` using these contracts.
- **Database audit_repo** — `database/repositories/audit_repo.py` will query JSONL files in a future story.
- **Streamlit UI integration** — UI pages will use `CommandResult` types in Epic 2+.
- **Concrete event payloads** — Story 1.3 provides the `EventEnvelope[T]` generic framework. Specific payload types (e.g., `TradeExecutedPayload`, `RiskLimitBreachedPayload`) will be defined in their respective domain stories.
- **Error mapper** — `core/errors/error_mapper.py` (mapping external exceptions to domain errors) is deferred to integration stories.
- **Workflow state** — `core/orchestrator/workflow_state.py` is deferred to Epic 2.

### References

- Error taxonomy and command format: [Source: _bmad-output/planning-artifacts/architecture.md#API & Communication Patterns]
- Event envelope and naming: [Source: _bmad-output/planning-artifacts/architecture.md#Communication Patterns]
- Correlation ID requirement: [Source: _bmad-output/planning-artifacts/architecture.md#Cross-Cutting Concerns]
- Append-only audit model: [Source: _bmad-output/planning-artifacts/architecture.md#Core Architectural Decisions]
- FR9 (standardized tasking): [Source: _bmad-output/planning-artifacts/epics.md#Story 1.3]
- Naming conventions: [Source: _bmad-output/planning-artifacts/architecture.md#Naming Patterns]
- File structure: [Source: _bmad-output/planning-artifacts/architecture.md#Complete Project Directory Structure]
- Story 1.2 implementation: [Source: _bmad-output/implementation-artifacts/1-2-implement-local-authentication-and-encrypted-secrets-store.md]
- Pydantic 2.12 discriminated unions: [Source: docs.pydantic.dev/latest/concepts/unions/]
- MCP SDK error patterns: [Source: mcp Python SDK v1.21.0 — shared/exceptions.py]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

No blocking issues encountered. One minor ruff fix: `timezone.utc` → `UTC` (UP017) in `models.py`.

### Completion Notes List

- ✅ Task 1: Created `error_codes.py` with 7 canonical error code constants. Extended `domain_errors.py` with `DomainError` base class and 5 typed subclasses (`BrokerError`, `StrategyValidationError`, `RiskLimitError`, `OrchestratorError`, `ValidationError`). `AuthenticationError` and `SecretsError` preserved for backward compatibility. Updated `errors/__init__.py` to re-export all types.
- ✅ Task 2: Created `orchestrator/contracts.py` with `ErrorPayload`, `CommandSuccess[T]`, `CommandFailure`, `CommandResult` discriminated union, and `success()` / `failure()` / `failure_from_domain_error()` factory functions. All models are frozen (immutable).
- ✅ Task 3: Created `events/correlation.py` with `get_correlation_id()`, `set_correlation_id()`, `new_correlation_id()` using `contextvars.ContextVar` — correct asyncio-safe propagation.
- ✅ Task 4: Created `events/models.py` with `EventEnvelope[PayloadT]` generic frozen model, `event_name` regex validator enforcing `domain.action.v1` pattern.
- ✅ Task 5: Created `events/publisher.py` with `publish_event()` — append-only JSONL write to `var/audit/YYYY/MM/DD/events.jsonl`. Updated `events/__init__.py` to re-export all public API.
- ✅ Task 6: 55 unit tests written across 5 test files covering all modules at 100% line coverage (51 original + 4 code-review fixes).
- ✅ Task 7: All gates passed — `ruff check .` 0 errors, `mypy src/` 0 errors, 55 new tests all pass at 100% coverage, 26 security regression tests all pass.

**Code-Review Fixes Applied (claude-sonnet-4-6):**
- [HIGH] `events/models.py`: added `validate_correlation_id` field_validator enforcing UUID v4 format on `EventEnvelope.correlation_id` (AC#2 mandates UUID v4; model previously accepted any string)
- [HIGH] `test_publisher.py`: added `test_written_jsonl_is_deserializable_to_event_envelope` — verifies the written JSONL can be parsed back via `EventEnvelope[PayloadT].model_validate_json()` (task 6.10 required round-trip but test only checked `json.loads()`)
- [HIGH] `test_models.py`: added 3 tests covering the new UUID v4 validator (rejects non-UUID, rejects non-v4 UUID, accepts valid v4 UUID)
- [LOW] `test_correlation.py`: corrected `reset_correlation_context` fixture return type from `-> None` to `-> Generator[None, None, None]`, removed `# type: ignore[misc]` suppression

### File List

**New files:**
- src/senzey_bots/core/errors/error_codes.py
- src/senzey_bots/core/orchestrator/contracts.py
- src/senzey_bots/core/events/correlation.py
- src/senzey_bots/core/events/models.py
- src/senzey_bots/core/events/publisher.py
- tests/unit/core/__init__.py
- tests/unit/core/errors/__init__.py
- tests/unit/core/errors/test_domain_errors.py
- tests/unit/core/errors/test_error_codes.py
- tests/unit/core/orchestrator/__init__.py
- tests/unit/core/orchestrator/test_contracts.py
- tests/unit/core/events/__init__.py
- tests/unit/core/events/test_correlation.py
- tests/unit/core/events/test_models.py
- tests/unit/core/events/test_publisher.py

**Modified files:**
- src/senzey_bots/core/errors/domain_errors.py
- src/senzey_bots/core/errors/__init__.py
- src/senzey_bots/core/events/__init__.py
- src/senzey_bots/core/orchestrator/__init__.py

## Change Log

- 2026-02-25: Story 1.3 implemented — standardized internal messaging contracts and typed errors. Added domain error hierarchy (`DomainError` + 5 subclasses), canonical error codes, Pydantic command result contracts (`CommandSuccess[T]` / `CommandFailure` discriminated union), `EventEnvelope[T]` model with `domain.action.v1` validation, correlation ID propagation via `contextvars`, and append-only JSONL event publisher. 51 unit tests added with 100% coverage. All lint/type/test gates pass.
