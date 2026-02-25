# Story 2.1: Build Strategy Input Workspace

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a strategy developer,
I want a unified workspace to enter rule text, paste PineScript, or upload Python strategy code,
so that I can start strategy creation from my preferred input format.

## Acceptance Criteria

1. **Given** the strategy generation page
   **When** the user navigates to it
   **Then** a tabbed workspace is displayed with three input modes: Rule Text, PineScript, and Python Upload
   **And** the multipage Streamlit app navigation is functional with the "Generate" page active.

2. **Given** the Rule Text input tab
   **When** the user enters plain-text strategy rules (e.g., "Buy when RSI < 30, Sell when RSI > 70")
   **Then** the input is validated as non-empty and within size limits
   **And** the user can assign a strategy name and submit.

3. **Given** the PineScript input tab
   **When** the user pastes TradingView PineScript code
   **Then** the input is validated for basic PineScript syntax markers (e.g., `//@version`, `strategy(` or `indicator(`)
   **And** invalid input is rejected with actionable feedback explaining what's expected.

4. **Given** the Python Upload tab
   **When** the user uploads a `.py` file
   **Then** the file is validated: correct extension, parseable Python (AST check), reasonable size (< 500 KB)
   **And** files with forbidden imports (e.g., `os.system`, `subprocess`, `eval`, `exec`) are rejected with a security warning.

5. **Given** any valid strategy input
   **When** the user submits the form
   **Then** a `strategies` row is created with `status = "draft"`, `input_type` matching the selected tab, and `input_content` containing the raw input
   **And** the user sees a success confirmation with the strategy name and ID.

6. **Given** a previously saved draft
   **When** the user returns to the strategy generation page
   **Then** existing drafts are listed with name, input type, status, and creation date
   **And** the user can view or delete drafts.

7. **Given** all new code files
   **When** lint and type checks run
   **Then** `ruff check .` passes with zero errors
   **And** `mypy src/` passes with zero errors
   **And** `pytest tests/unit/core/strategy/ tests/unit/ui/ tests/unit/database/ -v --tb=short` passes with >= 80% line coverage on new modules.

## Tasks / Subtasks

- [x] Task 1: Create Strategy database model and migration (AC: #5)
  - [x] 1.1 Create `src/senzey_bots/database/models/strategy.py`:
    ```python
    """Strategy draft model — persists user-provided strategy inputs."""

    from __future__ import annotations

    from datetime import datetime

    from sqlalchemy import String, Text
    from sqlalchemy.orm import Mapped, mapped_column

    from senzey_bots.database.base import Base


    class Strategy(Base):
        """Persists strategy drafts created from the input workspace.

        input_type: one of "rules_text", "pinescript", "python_upload"
        status lifecycle: draft → validated → generating → generated → failed
        """

        __tablename__ = "strategies"

        id: Mapped[int] = mapped_column(primary_key=True)
        name: Mapped[str] = mapped_column(String(200), nullable=False)
        input_type: Mapped[str] = mapped_column(String(20), nullable=False)
        input_content: Mapped[str] = mapped_column(Text, nullable=False)
        status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
        created_at: Mapped[datetime] = mapped_column(nullable=False)
        updated_at: Mapped[datetime] = mapped_column(nullable=False)
    ```
    **Column notes:**
    - `name`: user-given strategy name. Max 200 chars, required.
    - `input_type`: enum-like string. Valid values: `"rules_text"`, `"pinescript"`, `"python_upload"`. Enforce at application layer, NOT via DB CHECK constraint (keeps migrations simple).
    - `input_content`: the raw text/code. Stored verbatim — no transformation at persistence layer.
    - `status`: lifecycle state. Story 2.1 only creates `"draft"` rows. Story 2.2 will add `"generating"`, `"generated"`, `"failed"`.
    - Use `Mapped[type] = mapped_column(...)` — same pattern as Story 1.2's models.
    - Use `str | None` NOT `Optional[str]` (ruff UP007).
  - [x] 1.2 Update `src/senzey_bots/database/models/__init__.py` — add `Strategy` to exports:
    ```python
    from senzey_bots.database.models.auth_config import AuthConfig
    from senzey_bots.database.models.secret_metadata import SecretMetadata
    from senzey_bots.database.models.strategy import Strategy

    __all__ = ["AuthConfig", "SecretMetadata", "Strategy"]
    ```
  - [x] 1.3 Generate Alembic migration:
    ```bash
    PYTHONPATH=src alembic revision --autogenerate -m "add_strategies_table"
    ```
    Verify the generated migration creates the `strategies` table with correct columns.
    **IMPORTANT:** Use `PYTHONPATH=src` prefix — required for Alembic to resolve `senzey_bots` imports (learned from Story 1.2).
  - [x] 1.4 Apply migration: `PYTHONPATH=src alembic upgrade head` — verify table exists with correct schema.

- [x] Task 2: Create strategy repository (AC: #5, #6)
  - [x] 2.1 Create `src/senzey_bots/database/repositories/strategy_repo.py`:
    ```python
    """Strategy repository — CRUD operations for strategy drafts."""

    from __future__ import annotations

    from sqlalchemy.orm import Session

    from senzey_bots.database.models.strategy import Strategy
    from senzey_bots.shared.clock import utcnow
    from senzey_bots.shared.logger import get_logger

    logger = get_logger(__name__)


    def create_strategy(
        session: Session,
        *,
        name: str,
        input_type: str,
        input_content: str,
    ) -> Strategy:
        """Create a new strategy draft."""
        now = utcnow()
        strategy = Strategy(
            name=name,
            input_type=input_type,
            input_content=input_content,
            status="draft",
            created_at=now,
            updated_at=now,
        )
        session.add(strategy)
        session.commit()
        session.refresh(strategy)
        return strategy


    def list_strategies(session: Session) -> list[Strategy]:
        """Return all strategies ordered by creation date descending."""
        return list(
            session.query(Strategy).order_by(Strategy.created_at.desc()).all()
        )


    def get_strategy(session: Session, strategy_id: int) -> Strategy | None:
        """Get a single strategy by ID. Returns None if not found."""
        return session.get(Strategy, strategy_id)


    def delete_strategy(session: Session, strategy_id: int) -> bool:
        """Delete a strategy by ID. Returns True if deleted, False if not found."""
        strategy = session.get(Strategy, strategy_id)
        if strategy is None:
            return False
        session.delete(strategy)
        session.commit()
        return True
    ```
    **Design decisions:**
    - Module-level functions with `Session` param — matches the pattern from Story 1.2 (`auth_service.py`, `secrets_store.py`).
    - Session is passed in (injected), not created internally — allows callers to manage transaction boundaries.
    - `create_strategy` commits immediately — strategy creation is a single atomic operation.
    - Uses `shared/clock.py`'s `utcnow()` for all timestamps (pattern from Story 1.2).
    - Returns `Strategy | None` for get operations (not raising exceptions for "not found" — that's a UI concern).

- [x] Task 3: Create strategy input validator (AC: #2, #3, #4)
  - [x] 3.1 Create `src/senzey_bots/core/strategy/validator.py`:
    ```python
    """Strategy input validation — validates user-provided strategy inputs before persistence.

    Validates three input types: rules_text, pinescript, python_upload.
    Returns structured validation results, never raises exceptions for invalid input.
    """

    from __future__ import annotations

    import ast
    import re
    from dataclasses import dataclass

    VALID_INPUT_TYPES = frozenset({"rules_text", "pinescript", "python_upload"})

    _MAX_INPUT_SIZE = 500_000  # 500 KB in characters
    _MIN_INPUT_LENGTH = 10  # Minimum meaningful input

    # PineScript markers — at least one must be present
    _PINESCRIPT_MARKERS = (
        "//@version",
        "strategy(",
        "indicator(",
        "study(",
        "plot(",
        "hline(",
    )

    # Forbidden Python imports/calls — security blocklist
    # NOTE: `importlib` is intentionally scoped to `importlib.import_module` and `importlib.util`
    # because `importlib.metadata` is a legitimate stdlib usage (e.g., version checking).
    _FORBIDDEN_PATTERNS = re.compile(
        r"\b(os\.system|subprocess|eval\s*\(|exec\s*\(|__import__|importlib\.import_module|importlib\.util|shutil\.rmtree)\b"
    )


    @dataclass(frozen=True)
    class ValidationResult:
        """Result of input validation."""

        valid: bool
        error: str | None = None


    def validate_strategy_input(
        input_type: str,
        input_content: str,
        file_name: str | None = None,
    ) -> ValidationResult:
        """Validate strategy input based on type.

        Returns ValidationResult with valid=True or valid=False with error message.
        """
        if input_type not in VALID_INPUT_TYPES:
            return ValidationResult(
                valid=False,
                error=f"Unsupported input type: '{input_type}'. Must be one of: {', '.join(sorted(VALID_INPUT_TYPES))}.",
            )

        if len(input_content) > _MAX_INPUT_SIZE:
            return ValidationResult(
                valid=False,
                error=f"Input too large ({len(input_content):,} chars). Maximum is {_MAX_INPUT_SIZE:,} chars.",
            )

        if len(input_content.strip()) < _MIN_INPUT_LENGTH:
            return ValidationResult(
                valid=False,
                error="Input is too short. Please provide meaningful strategy content.",
            )

        if input_type == "rules_text":
            return _validate_rules_text(input_content)
        if input_type == "pinescript":
            return _validate_pinescript(input_content)
        return _validate_python_upload(input_content, file_name)


    def _validate_rules_text(content: str) -> ValidationResult:
        """Validate plain-text strategy rules."""
        # Rules text just needs to be non-empty and not too short (already checked above)
        return ValidationResult(valid=True)


    def _validate_pinescript(content: str) -> ValidationResult:
        """Validate PineScript code has expected markers."""
        content_lower = content.lower()
        has_marker = any(marker.lower() in content_lower for marker in _PINESCRIPT_MARKERS)
        if not has_marker:
            return ValidationResult(
                valid=False,
                error="Input doesn't look like PineScript. Expected markers like '//@version', 'strategy(', or 'indicator('.",
            )
        return ValidationResult(valid=True)


    def _validate_python_upload(content: str, file_name: str | None) -> ValidationResult:
        """Validate uploaded Python strategy code."""
        if file_name and not file_name.endswith(".py"):
            return ValidationResult(
                valid=False,
                error=f"File must be a Python file (.py). Got: '{file_name}'.",
            )

        # Check for forbidden patterns (security)
        forbidden_match = _FORBIDDEN_PATTERNS.search(content)
        if forbidden_match:
            return ValidationResult(
                valid=False,
                error=f"Security violation: forbidden pattern '{forbidden_match.group()}' detected. "
                "Strategy code must not use os.system, subprocess, eval, exec, or __import__.",
            )

        # Verify parseable Python via AST
        try:
            ast.parse(content)
        except SyntaxError as e:
            return ValidationResult(
                valid=False,
                error=f"Python syntax error at line {e.lineno}: {e.msg}. Please fix and re-upload.",
            )

        return ValidationResult(valid=True)
    ```
    **Design decisions:**
    - Returns `ValidationResult` dataclass (not exceptions) — validation is a query, not an error path. The UI layer decides how to present results.
    - `frozen=True` dataclass — immutable result, matches architecture's immutability preference.
    - PineScript validation is lenient — checks for common markers but doesn't parse full syntax (that's the LLM's job in Story 2.2).
    - Python security check uses regex for forbidden patterns — a reasonable first pass. Static analysis tools (AST-level) can be added in Story 3.3 (static safety gate).
    - `ast.parse()` verifies syntactic correctness without executing the code.
    - No Pydantic dependency at this layer — keeping validation pure Python for simplicity and testability.
  - [x] 3.2 Update `src/senzey_bots/core/strategy/__init__.py`:
    ```python
    """Strategy domain — validation and lifecycle management."""
    ```
    Keep minimal — just a docstring. Don't re-export internals until the module grows.

- [x] Task 4: Set up multipage Streamlit app navigation (AC: #1)
  - [x] 4.1 Update `src/senzey_bots/ui/main.py` — replace the stub with multipage navigation:
    ```python
    """Streamlit multipage app entry point.

    Run: streamlit run src/senzey_bots/ui/main.py
    """

    from __future__ import annotations

    import streamlit as st

    st.set_page_config(
        page_title="senzey-bots",
        page_icon=":robot_face:",
        layout="wide",
    )

    generate_page = st.Page(
        "pages/10_generate.py",
        title="Generate",
        icon=":gear:",
        default=True,
    )

    pg = st.navigation([generate_page])

    st.sidebar.title("senzey-bots")

    pg.run()
    ```
    **IMPORTANT:**
    - `st.set_page_config` must be the first Streamlit command.
    - `st.Page` paths are relative to `ui/` directory (where `main.py` lives).
    - Only `10_generate.py` is registered now. Future stories add more pages here.
    - `default=True` makes Generate the landing page.
    - The `layout="wide"` gives more horizontal space for code input.
    - **NOTE on Streamlit page resolution:** `st.Page("pages/10_generate.py", ...)` resolves relative to the script's directory. Since `main.py` is at `src/senzey_bots/ui/main.py`, the page file must be at `src/senzey_bots/ui/pages/10_generate.py`.

- [x] Task 5: Create the strategy input page (AC: #1, #2, #3, #4, #5, #6)
  - [x] 5.1 Create `src/senzey_bots/ui/pages/10_generate.py`:
    ```python
    """Strategy Input Workspace — create strategy drafts from text, PineScript, or Python files."""

    from __future__ import annotations

    import streamlit as st

    from senzey_bots.core.strategy.validator import validate_strategy_input
    from senzey_bots.database.engine import get_session
    from senzey_bots.database.repositories.strategy_repo import (
        create_strategy,
        delete_strategy,
        list_strategies,
    )

    st.header("Strategy Input Workspace")
    st.caption("Create a new strategy draft from rules, PineScript, or Python code.")

    # --- Input Section ---
    strategy_name = st.text_input(
        "Strategy Name",
        placeholder="e.g., RSI Mean Reversion Gold",
        key="strategy_name_input",
    )

    tab_rules, tab_pine, tab_python = st.tabs(
        ["Rule Text", "PineScript", "Python Upload"]
    )

    with tab_rules:
        rules_text = st.text_area(
            "Enter your trading rules in plain text",
            height=300,
            placeholder="e.g., Buy when RSI(14) < 30 and price above SMA(200)\\nSell when RSI(14) > 70",
            key="rules_text_input",
        )
        if st.button("Submit Rules", key="submit_rules"):
            if not strategy_name.strip():
                st.error("Please enter a strategy name.")
            else:
                result = validate_strategy_input("rules_text", rules_text)
                if not result.valid:
                    st.error(result.error)
                else:
                    with get_session() as session:
                        strategy = create_strategy(
                            session,
                            name=strategy_name.strip(),
                            input_type="rules_text",
                            input_content=rules_text,
                        )
                        # Access ORM attributes INSIDE session scope to avoid DetachedInstanceError
                        st.success(f"Strategy '{strategy.name}' saved as draft (ID: {strategy.id}).")

    with tab_pine:
        pine_code = st.text_area(
            "Paste your PineScript code",
            height=300,
            placeholder="//@version=5\\nstrategy('My Strategy', ...)",
            key="pinescript_input",
        )
        if st.button("Submit PineScript", key="submit_pine"):
            if not strategy_name.strip():
                st.error("Please enter a strategy name.")
            else:
                result = validate_strategy_input("pinescript", pine_code)
                if not result.valid:
                    st.error(result.error)
                else:
                    with get_session() as session:
                        strategy = create_strategy(
                            session,
                            name=strategy_name.strip(),
                            input_type="pinescript",
                            input_content=pine_code,
                        )
                        st.success(f"Strategy '{strategy.name}' saved as draft (ID: {strategy.id}).")

    with tab_python:
        uploaded_file = st.file_uploader(
            "Upload a Python strategy file (.py)",
            type=["py"],
            key="python_upload_input",
        )
        if st.button("Submit Python File", key="submit_python"):
            if not strategy_name.strip():
                st.error("Please enter a strategy name.")
            elif uploaded_file is None:
                st.error("Please upload a .py file first.")
            else:
                try:
                    file_content = uploaded_file.read().decode("utf-8")
                except UnicodeDecodeError:
                    st.error("File is not valid UTF-8 text. Please upload a plain-text .py file.")
                    file_content = None
                if file_content is not None:
                    result = validate_strategy_input(
                        "python_upload", file_content, file_name=uploaded_file.name
                    )
                    if not result.valid:
                        st.error(result.error)
                    else:
                        with get_session() as session:
                            strategy = create_strategy(
                                session,
                                name=strategy_name.strip(),
                                input_type="python_upload",
                                input_content=file_content,
                            )
                            st.success(f"Strategy '{strategy.name}' saved as draft (ID: {strategy.id}).")

    # --- Existing Drafts Section ---
    st.divider()
    st.subheader("Existing Strategy Drafts")

    with get_session() as session:
        strategies = list_strategies(session)
        # Extract display data INSIDE session scope to avoid DetachedInstanceError
        draft_data = [
            {"id": s.id, "name": s.name, "input_type": s.input_type,
             "status": s.status, "created_at": s.created_at}
            for s in strategies
        ]

    if not draft_data:
        st.info("No strategy drafts yet. Create one above.")
    else:
        for d in draft_data:
            col_info, col_actions = st.columns([4, 1])
            with col_info:
                st.markdown(
                    f"**{d['name']}** — `{d['input_type']}` | Status: `{d['status']}` | "
                    f"Created: {d['created_at']:%Y-%m-%d %H:%M}"
                )
            with col_actions:
                if st.button("Delete", key=f"delete_{d['id']}"):
                    with get_session() as del_session:
                        delete_strategy(del_session, d["id"])
                    st.rerun()
    ```
    **KEY IMPLEMENTATION NOTES:**
    - **DetachedInstanceError prevention:** All ORM attribute access happens INSIDE `with get_session()` blocks. For the draft list, attributes are extracted into plain dicts before the session closes. For create operations, `st.success()` is called inside the session scope. SQLAlchemy 2.0's default `expire_on_commit=True` expires all ORM attributes after commit — accessing them on detached objects raises `DetachedInstanceError`.
    - All widget keys are explicit — required by Streamlit 1.54+ key-based identity system.
    - `get_session()` context manager from `database/engine.py` is used for all DB operations — same pattern as Story 1.2.
    - File upload uses `type=["py"]` restriction — Streamlit enforces at browser level.
    - `uploaded_file.read().decode("utf-8")` — wrapped in try/except for non-UTF-8 files (e.g., accidentally uploaded `.pyc`).
    - `st.rerun()` after delete to refresh the list — Streamlit standard pattern.
    - No authentication check — UI-level auth (session guard) is a cross-cutting concern deferred to a later story. Strategy persistence itself doesn't involve secrets.

- [x] Task 6: Write unit tests (AC: #7)
  - [x] 6.1 Create `tests/unit/core/strategy/__init__.py` (empty). Note: `tests/unit/core/__init__.py` may already exist from Story 1.3 — create only the `strategy/` subdirectory if so.
  - [x] 6.2 Create `tests/unit/core/strategy/test_validator.py`:
    - Test `validate_strategy_input` with valid `rules_text`.
    - Test `validate_strategy_input` with empty `rules_text` → invalid.
    - Test `validate_strategy_input` with too-short input → invalid.
    - Test `validate_strategy_input` with too-large input → invalid.
    - Test `validate_strategy_input` with invalid `input_type` → invalid.
    - Test `validate_strategy_input` with valid PineScript (has `//@version`).
    - Test `validate_strategy_input` with PineScript missing markers → invalid.
    - Test `validate_strategy_input` with valid Python code.
    - Test `validate_strategy_input` with Python syntax error → invalid.
    - Test `validate_strategy_input` with forbidden Python imports (e.g., `subprocess`) → invalid.
    - Test `validate_strategy_input` with non-.py filename → invalid.
    - Test `ValidationResult` is frozen (immutable).
  - [x] 6.3 Create `tests/unit/database/repositories/__init__.py` (empty).
  - [x] 6.4 Create `tests/unit/database/repositories/test_strategy_repo.py`:
    - Use in-memory SQLite fixture (same `conftest.py` pattern as Story 1.2's `tests/unit/security/conftest.py`).
    - Test `create_strategy` returns a `Strategy` with correct fields.
    - Test `create_strategy` sets `status = "draft"` and timestamps.
    - Test `list_strategies` returns strategies ordered by `created_at` desc.
    - Test `list_strategies` returns empty list when no strategies exist.
    - Test `get_strategy` returns strategy by ID.
    - Test `get_strategy` returns `None` for non-existent ID.
    - Test `delete_strategy` removes the strategy.
    - Test `delete_strategy` returns `False` for non-existent ID.
  - [x] 6.5 Create `tests/unit/database/repositories/conftest.py` — shared DB fixture:
    ```python
    from collections.abc import Generator

    import pytest
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from senzey_bots.database.base import Base


    @pytest.fixture
    def db_session() -> Generator[Session, None, None]:
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            yield session
        Base.metadata.drop_all(engine)
    ```
    **NOTE:** Same fixture pattern as `tests/unit/security/conftest.py` (Story 1.2). In-memory SQLite for test isolation. Use `Generator[Session, None, None]` return type — matches the established pattern and satisfies mypy strict without `# type: ignore` suppression.
  - [x] 6.6 Create `tests/unit/database/__init__.py` (empty) — this directory does NOT exist yet on disk, so you MUST create both `tests/unit/database/` and `tests/unit/database/repositories/` directories with their `__init__.py` files.
  - [x] 6.7 (Optional) Create `tests/unit/ui/__init__.py` — UI page testing is optional for this story. Streamlit pages are difficult to unit test without `streamlit-testing-library`. The core logic (validator + repository) carries the test burden. If desired, create smoke tests using `unittest.mock` to verify import paths work.

- [x] Task 7: Validate all gates pass (AC: #7)
  - [x] 7.1 Run `ruff check .` — must pass with zero errors. **Note:** `ruff.toml` excludes the `tests/` directory, so ruff will NOT lint test files. Follow ruff conventions manually in test code (use `X | None` not `Optional[X]`, correct import ordering per `I` rules, `snake_case` naming).
  - [x] 7.2 Run `mypy src/` — must pass with zero errors.
  - [x] 7.3 Run `pytest tests/unit/core/strategy/ tests/unit/database/repositories/ -v --tb=short --cov=src/senzey_bots/core/strategy --cov=src/senzey_bots/database/repositories --cov-report=term-missing` — all tests pass with >= 80% line coverage.
  - [x] 7.4 Run existing tests to confirm no regressions: `pytest tests/unit/security/ -v --tb=short`.
  - [x] 7.5 Run `PYTHONPATH=src alembic upgrade head` — migration applies cleanly.
  - [x] 7.6 Run Streamlit smoke test: `streamlit run src/senzey_bots/ui/main.py` — page loads without errors, tabs are visible, form elements render.

## Dev Notes

### CRITICAL CONSTRAINTS

- **DO NOT MODIFY** `freqtrade/` or `trading_ig/` directories. [Source: architecture.md#Architectural Boundaries]
- **DO NOT MODIFY** `src/senzey_bots/app.py` — this is a Python-only entry point stub (guarded by `if __name__ == "__main__":`) separate from the Streamlit UI. The Streamlit entry point is `src/senzey_bots/ui/main.py`. Editing the wrong file will produce a blank Streamlit page.
- **DO NOT ADD `[tool.ruff]` to root `pyproject.toml`** — `ruff.toml` is the single source of truth. [Source: Story 1.1 Dev Notes]
- **DO NOT USE `Optional[X]`** — ruff's `UP007` rule flags it. Use `X | None` (Python 3.11+). [Source: Story 1.2 Dev Notes]
- **DO NOT USE `logging.extra` for `correlation_id`** — `shared/logger.py`'s `_JsonFormatter` silently drops `extra` fields. Embed `correlation_id` in JSON message string. [Source: Story 1.2 Dev Notes]
- **DO NOT USE `datetime.now()`** directly — use `shared/clock.py`'s `utcnow()` for all timestamps. [Source: Story 1.2 Dev Notes]
- **DO NOT MODIFY existing models** (`AuthConfig`, `SecretMetadata`) — they belong to Story 1.2 and are in production use.
- **Fernet key must be 32 bytes base64url-encoded (44 chars)** — if touching crypto at all. [Source: Story 1.2 Dev Notes]
- **ALEMBIC requires `PYTHONPATH=src`** for all CLI invocations — Alembic cannot resolve `senzey_bots` imports without it. [Source: Story 1.2 Debug Logs]
- **ALL JSON keys and DB columns MUST be `snake_case`**. [Source: architecture.md#Naming Patterns]
- **Streamlit widget keys MUST be explicit** — Streamlit 1.54+ uses key-based identity. Omitting keys causes widget state reset on reruns.
- **DetachedInstanceError prevention** — SQLAlchemy 2.0 default `expire_on_commit=True` expires all ORM attributes after `session.commit()`. Access ORM object attributes INSIDE the `with get_session()` block, or extract values into plain dicts/variables before the session closes. Accessing `.name`, `.id` etc. on a detached ORM object outside the session scope will raise `DetachedInstanceError`.
- **UTF-8 file upload safety** — Always wrap `uploaded_file.read().decode("utf-8")` in a try/except for `UnicodeDecodeError`. Users may accidentally upload `.pyc` or non-UTF-8 encoded files.

### Architecture Reference

**Frontend Architecture (architecture.md#Frontend Architecture):**
- UI Framework: Streamlit 1.54.0
- State Management: `st.session_state` + explicit workflow-state objects
- Component Strategy: page modules (`Generate`, `Backtest`, `Deploy`, `Monitor`, `Emergency`)
- Page file naming: `NN_<feature>.py` (e.g., `10_generate.py`)
- Performance: async-safe background tasks + incremental rendering

**Data Architecture (architecture.md#Data Architecture):**
- DB: SQLite + SQLAlchemy 2.0.47 + Alembic 1.18.4
- Modeling: `strategies`, `backtests`, `deployments`, `orders`, `risk_events`, `agent_runs`, `secrets_metadata`
- Naming: `snake_case_plural` tables, `snake_case` columns, PK = `id`, FK = `<ref>_id`

**Data Flow (architecture.md#Integration Points):**
1. User strategy input → `ui/pages/10_generate.py`
2. LLM generate/validate → `agents/llm/*` + `core/strategy/*` (Story 2.2)
3. Backtest + threshold gate → `core/backtest/*` (Epic 3)

**FR1 Scope:**
- User can input TradingView/PineScript rules or plain-text rules via UI
- User can upload ready Python strategy code
- [Source: epics.md#Story 2.1, prd.md#FR1]

### Previous Story Context (Story 1.2 — Last Completed)

**What was built:**
- `database/engine.py` — SQLite singleton: `get_engine() -> Engine`, `get_session() -> Generator[Session]` (contextmanager)
- `database/base.py` — `DeclarativeBase` subclass for all ORM models
- `database/models/auth_config.py` — `AuthConfig` model
- `database/models/secret_metadata.py` — `SecretMetadata` model
- `database/migrations/` — Alembic configured with baseline migration
- `security/*` — Full auth + secrets infrastructure
- `core/errors/domain_errors.py` — `AuthenticationError`, `SecretsError`
- All shared utilities: `logger.py`, `clock.py`, `config_loader.py`

**Key APIs you WILL use:**
- `from senzey_bots.database.engine import get_session` — context manager yielding `Session`
- `from senzey_bots.shared.clock import utcnow` — returns `datetime(tzinfo=timezone.utc)`
- `from senzey_bots.shared.logger import get_logger` — returns `logging.Logger` with JSON output
- `from senzey_bots.database.base import Base` — DeclarativeBase for new models

**Key patterns established:**
- Use `Mapped[type] = mapped_column(...)` for model fields (SQLAlchemy 2.0 declarative style)
- Use in-memory SQLite fixtures in `conftest.py` for test isolation
- `get_session()` is a `contextlib.contextmanager` — use `with get_session() as session:`
- All test functions: `def test_*(...) -> None:` (mypy strict requires return type)

**Code-Review lessons from Story 1.2:**
- `.gitignore` had a `*_config.*` pattern that silently excluded `auth_config.py` — fixed with `!src/**/*_config.py` negation. Verify new files aren't accidentally gitignored.
- Coverage was 88% → 100% after code review added missing upsert/rehash tests. Aim for >= 80% from the start.
- Alembic migration had `Union`/`Sequence` typing imports — fix to use `collections.abc.Sequence` and `X | Y` per ruff UP rules.

### Story 1.3 Relationship

Story 1.3 (Messaging Contracts & Typed Errors) is in `review` status and provides:
- Extended domain errors: `DomainError` base, `StrategyValidationError`, `BrokerError`, `RiskLimitError`, `OrchestratorError`, `ValidationError` in `core/errors/domain_errors.py`
- Orchestrator contracts: `CommandResult`, `success()`, `failure()` in `core/orchestrator/contracts.py`
- Event infrastructure: `EventEnvelope`, `publish_event()`, `correlation.py` in `core/events/`

**Story 2.1 deliberately does NOT use Story 1.3's infrastructure.** This story keeps validation self-contained via its own `ValidationResult` dataclass. Reasons:
- Strategy input validation is a UI-level concern — `ValidationResult` is simpler and more appropriate than `CommandResult` for form validation.
- Event publishing for strategy creation can be added as a follow-up enhancement.
- Do NOT import from `core/orchestrator/contracts.py` or `core/events/models.py` in this story.

**Optional enhancement (NOT required for AC completion):** Story 1.3's event infrastructure is fully implemented and available right now (`publish_event`, `get_correlation_id`, `EventEnvelope` are all live in `core/events/`). If you want to add an audit trail, you MAY optionally publish a `strategy.draft_created.v1` event after `create_strategy()` succeeds — no Story 1.3 merge is needed. This is deferred to Story 2.3's scope and is NOT part of this story's acceptance criteria.

### Git Intelligence (Recent Commits)

```
801ef3e feat(story-1.2): implement local authentication and encrypted secrets store
6d31b5c chore(bmad): update story 1.1 artifacts to done + sprint status sync
c701b66 feat(story-1.1): bootstrap modular project skeleton with UV
```

**Commit convention:** `type(scope): description`
- `feat` for new functionality
- `chore` for maintenance
- `docs` for documentation
- Scope matches story number
- Expected commit for this story: `feat(story-2.1): build strategy input workspace`

### Technical Stack (Exact Versions)

| Tool | Version | Purpose |
|---|---|---|
| Streamlit | 1.54.0 (pinned) | UI framework |
| SQLAlchemy | 2.0.47 (pinned) | ORM + session management |
| Alembic | 1.18.4 (pinned) | DB migrations |
| Pydantic | 2.12.5 (pinned) | Schema validation (not directly used in this story) |
| Python | 3.11+ | Runtime |
| ruff | >=0.3.0 | Linting |
| mypy | >=1.10.0 | Type checking (strict) |
| pytest | >=8.0.0 | Testing |
| pytest-cov | >=7.0.0 | Coverage reporting |

### Streamlit 1.54.0 Specifics

- **Multipage apps:** Use `st.Page` + `st.navigation` for programmatic page control (recommended over `pages/` auto-discovery for complex apps with explicit ordering).
- **Widget keys:** Always provide explicit `key` parameter — Streamlit 1.54+ uses key-based identity. Omitting keys causes widget reset on parameter changes.
- **File uploader:** `st.file_uploader(type=["py"])` restricts file types at browser level. Uploaded files are `BytesIO`-like objects — use `.read().decode("utf-8")` for text content.
- **Tabs:** `st.tabs(["Tab1", "Tab2", "Tab3"])` creates a tab interface. Use `with tab:` context manager for content.
- **`st.rerun()`:** Use after state-changing operations (like delete) to refresh the page.
- **`st.set_page_config`:** Must be the FIRST Streamlit command in the entry point. Cannot be called from page files.
- **Page resolution:** `st.Page("pages/10_generate.py")` resolves relative to the entry script's directory.
- **Removed APIs:** `st.experimental_query_params` and `st.experimental_user` are removed — do not use.

### File Structure for This Story

```
New/modified files:
  src/senzey_bots/database/
    models/
      __init__.py                    ← UPDATE (add Strategy export)
      strategy.py                    ← NEW
    repositories/
      __init__.py                    ← EXISTS (empty stub from Story 1.1)
      strategy_repo.py              ← NEW
    migrations/
      versions/
        <hash>_add_strategies_table.py  ← GENERATED by Alembic
  src/senzey_bots/core/
    strategy/
      __init__.py                    ← UPDATE (add docstring)
      validator.py                   ← NEW
  src/senzey_bots/ui/
    main.py                          ← REPLACE (stub → multipage navigation)
    pages/
      10_generate.py                 ← NEW
  tests/
    unit/
      core/
        strategy/
          __init__.py                ← NEW
          test_validator.py          ← NEW
      database/
        __init__.py                  ← NEW (if not existing)
        repositories/
          __init__.py                ← NEW
          conftest.py                ← NEW (shared DB fixture)
          test_strategy_repo.py      ← NEW
```

### Testing Standards

- Use `tmp_path` fixture for file-system tests if needed.
- Use `monkeypatch` for module-level overrides.
- Each test function: `def test_*(...) -> None:` (mypy strict).
- In-memory SQLite via `conftest.py` fixture for DB tests.
- Validator tests are pure functions — no fixtures needed.
- Streamlit UI tests are optional (hard to unit test without `streamlit-testing-library`).
- Import pattern: `from senzey_bots.core.strategy.validator import validate_strategy_input, ValidationResult`
- No new dependencies required — all deps are already installed.

### What This Story Does NOT Cover (Deferred)

- **LLM strategy generation** — Story 2.2 will implement the LLM agent that converts drafts into executable Freqtrade code.
- **Strategy versioning** — `version` column or `generated_code` column will be added by Story 2.2 via a new migration.
- **UI authentication guard** — Session-level auth check on pages is a cross-cutting concern for a future story.
- **Strategy editing** — Draft editing (updating input_content) is not in scope. Users create new drafts or delete existing ones.
- **Advanced static analysis** — Story 3.3 will implement comprehensive static safety checks (AST-level analysis, import whitelisting, etc.).
- **Event publishing for strategy creation** — Can be added when Story 1.3's event infrastructure is available.
- **Real-time agent timeline** — Story 2.3 will add the agent communication display.

### Project Structure Notes

- All new files align with the architecture-defined directory structure. [Source: architecture.md#Complete Project Directory Structure]
- `ui/pages/10_generate.py` matches the `NN_<feature>.py` naming convention. [Source: architecture.md#Code Naming Conventions]
- `database/models/strategy.py` follows the established model pattern from Story 1.2. [Source: Story 1.2 File List]
- `database/repositories/strategy_repo.py` is the first repository — establishes the CRUD pattern for future repos. [Source: architecture.md#Project Structure]
- No conflicts detected with existing files or patterns.

### References

- FR1 (Strategy input): [Source: _bmad-output/planning-artifacts/epics.md#Story 2.1]
- Epic 2 context: [Source: _bmad-output/planning-artifacts/epics.md#Epic 2]
- Architecture frontend: [Source: _bmad-output/planning-artifacts/architecture.md#Frontend Architecture]
- Architecture data: [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture]
- Architecture structure: [Source: _bmad-output/planning-artifacts/architecture.md#Complete Project Directory Structure]
- Architecture naming: [Source: _bmad-output/planning-artifacts/architecture.md#Naming Patterns]
- Architecture data flow: [Source: _bmad-output/planning-artifacts/architecture.md#Integration Points]
- Story 1.1 bootstrap: [Source: _bmad-output/implementation-artifacts/1-1-bootstrap-modular-project-skeleton-with-uv.md]
- Story 1.2 auth/secrets: [Source: _bmad-output/implementation-artifacts/1-2-implement-local-authentication-and-encrypted-secrets-store.md]
- Story 1.3 contracts: [Source: _bmad-output/implementation-artifacts/1-3-standardize-internal-messaging-contracts-and-typed-errors.md]
- Streamlit 1.54.0 docs: [Source: docs.streamlit.io/develop/quick-reference/release-notes/2026]
- Project context: [Source: _bmad-output/project-context.md]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- **regex trailing `\b` bug (validator.py):** Story spec's `_FORBIDDEN_PATTERNS` regex had trailing `\b` after `eval\s*\(` and `exec\s*\(`. Because `(` is a non-word character, `\b` after it only matches when followed by a word character — `eval('...')` (followed by `'`) failed to match. Fixed by removing trailing `\b` from the entire pattern. The leading `\b` still prevents false positives on substring matches.
- **Streamlit emoji shortcode rejection (main.py):** Streamlit 1.54.0 does not support emoji shortcodes (`:gear:`, `:robot_face:`) in `st.Page(icon=)` and `st.set_page_config(page_icon=)`. Smoke test discovered `StreamlitAPIException: The value ":gear:" is not a valid emoji. Shortcodes are not allowed, please use a single character instead.` Fixed by replacing shortcodes with actual Unicode emoji characters: `:robot_face:` → `🤖`, `:gear:` → `⚙️`.
- **mypy dict type inference (10_generate.py):** Mixed-type `dict[str, ...]` comprehension caused `d["id"]` to be inferred as `object`, incompatible with `delete_strategy(session, int)`. Replaced dict list with typed tuple list `list[tuple[int, str, str, str, str]]`.
- **mypy `file_content = None` (10_generate.py):** Variable inferred as `str` from try block, then `None` assignment in except block caused type mismatch. Fixed by pre-declaring `file_content: str | None = None` before the try block.
- **ruff N999 (10_generate.py):** Streamlit page files use numeric prefixes (`10_generate.py`) by convention. Added `per-file-ignores` to `ruff.toml` to suppress N999 for this file.
- **ruff E501 (validator.py, 10_generate.py):** Several long string error messages exceeded 100 chars. Fixed by extracting to local variables or using string concatenation.
- **Alembic migration style:** Auto-generated migration used `from typing import Union, Sequence` and `Union[str, None]` style — violates ruff UP007/UP035. Manually fixed to use `from collections.abc import Sequence` and `str | None` syntax (same as baseline migration pattern).

### Completion Notes List

- Implemented all 7 tasks covering AC #1–7 completely.
- `Strategy` ORM model created with `strategies` table, Alembic migration `29136f6d035f` generated and applied.
- `strategy_repo.py` provides CRUD: `create_strategy`, `list_strategies`, `get_strategy`, `delete_strategy` — all function-style with injected `Session`, following Story 1.2 patterns.
- `validator.py` validates three input types: `rules_text` (length checks), `pinescript` (marker detection), `python_upload` (`.py` extension, AST parse, forbidden pattern regex). Returns frozen `ValidationResult` dataclass — never raises.
- `ui/main.py` replaced stub with `st.Page` + `st.navigation` multipage setup; `10_generate.py` page registered as default.
- `10_generate.py` implements full Strategy Input Workspace: three tabs (Rule Text, PineScript, Python Upload), draft list with delete, all ORM attribute access inside session scope (DetachedInstanceError prevention).
- 27 unit tests: 17 for validator (including frozen dataclass, all forbidden patterns, all input types), 10 for repository (CRUD + ordering). 100% line coverage on both modules.
- All quality gates: `ruff check .` ✅, `mypy src/` ✅ (52 files), 27/27 new tests ✅, 26/26 regression tests ✅, migration applied ✅.
- Task 7.6 Streamlit smoke test completed via Playwright browser automation: all three tabs (Rule Text, PineScript, Python Upload) visible and functional, form elements render correctly, Strategy Name input and Existing Strategy Drafts section display properly. Fixed emoji shortcode bug discovered during smoke test: `:gear:` → `⚙️`, `:robot_face:` → `🤖` in `main.py` (Streamlit 1.54.0 rejects shortcodes in `st.Page(icon=)` and `st.set_page_config(page_icon=)`). All quality gates re-confirmed: `ruff check .` ✅, `mypy src/` ✅ (52 files).

### File List

- `src/senzey_bots/database/models/strategy.py` (NEW)
- `src/senzey_bots/database/models/__init__.py` (MODIFIED — added Strategy export)
- `src/senzey_bots/database/migrations/versions/29136f6d035f_add_strategies_table.py` (NEW)
- `src/senzey_bots/database/repositories/strategy_repo.py` (NEW)
- `src/senzey_bots/core/strategy/__init__.py` (MODIFIED — updated docstring)
- `src/senzey_bots/core/strategy/validator.py` (NEW)
- `src/senzey_bots/ui/main.py` (MODIFIED — stub replaced with multipage navigation; emoji shortcodes fixed: `:robot_face:` → `🤖`, `:gear:` → `⚙️`)
- `src/senzey_bots/ui/pages/10_generate.py` (NEW)
- `tests/unit/core/strategy/__init__.py` (NEW)
- `tests/unit/core/strategy/test_validator.py` (NEW)
- `tests/unit/database/__init__.py` (NEW)
- `tests/unit/database/repositories/__init__.py` (NEW)
- `tests/unit/database/repositories/conftest.py` (NEW)
- `tests/unit/database/repositories/test_strategy_repo.py` (NEW)
- `ruff.toml` (MODIFIED — added per-file-ignores for N999 on Streamlit page files)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (MODIFIED — status: review)

## Change Log

- feat(story-2.1): implement Strategy Input Workspace — model, migration, repository, validator, multipage Streamlit UI with three-tab input workspace (Date: 2026-02-25)
- fix(story-2.1): replace emoji shortcodes with Unicode chars in main.py — Streamlit 1.54.0 rejects `:gear:`/`:robot_face:` shortcodes in st.Page(icon) and st.set_page_config(page_icon) (Date: 2026-02-25)
