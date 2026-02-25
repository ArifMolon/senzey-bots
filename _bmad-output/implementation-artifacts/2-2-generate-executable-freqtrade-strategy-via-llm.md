# Story 2.2: Generate Executable Freqtrade Strategy via LLM

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a strategy developer,
I want the system to convert validated strategy intent into executable Freqtrade Python,
so that I can move from idea to testable strategy quickly.

## Acceptance Criteria

1. **Given** a valid strategy draft
   **When** generation is triggered
   **Then** the LLM agent returns executable strategy code compatible with Freqtrade interfaces
   **And** generation outcome, metadata, and artifacts are versioned for later traceability.

2. **Given** upstream LLM unavailability
   **When** generation exceeds timeout or fails
   **Then** the user is redirected to manual code entry fallback
   **And** failure is surfaced without crashing the workflow.

3. **Given** generated strategy code
   **When** post-generation validation runs
   **Then** code passes AST parsing, forbidden-import check, and Freqtrade interface compliance (IStrategy subclass, required methods, required attributes)
   **And** invalid code is rejected with actionable feedback and status set to "failed".

4. **Given** all new code files
   **When** lint and type checks run
   **Then** `ruff check .` passes with zero errors
   **And** `mypy src/` passes with zero errors
   **And** `pytest tests/unit/core/strategy/ tests/unit/agents/ -v --tb=short` passes with >= 80% line coverage on new modules.

## Tasks / Subtasks

- [ ] Task 1: Extend Strategy model with generation columns + Alembic migration (AC: #1)
  - [ ] 1.1 Update `src/senzey_bots/database/models/strategy.py` — add generation-related columns:
    ```python
    """Strategy model — persists user-provided inputs and LLM-generated code."""

    from __future__ import annotations

    from datetime import datetime

    from sqlalchemy import String, Text
    from sqlalchemy.orm import Mapped, mapped_column

    from senzey_bots.database.base import Base


    class Strategy(Base):
        """Persists strategy drafts and generated code.

        input_type: one of "rules_text", "pinescript", "python_upload"
        status lifecycle: draft → generating → generated → failed
        """

        __tablename__ = "strategies"

        id: Mapped[int] = mapped_column(primary_key=True)
        name: Mapped[str] = mapped_column(String(200), nullable=False)
        input_type: Mapped[str] = mapped_column(String(20), nullable=False)
        input_content: Mapped[str] = mapped_column(Text, nullable=False)
        status: Mapped[str] = mapped_column(
            String(20), nullable=False, default="draft"
        )
        generated_code: Mapped[str | None] = mapped_column(
            Text, nullable=True, default=None
        )
        generation_metadata: Mapped[str | None] = mapped_column(
            Text, nullable=True, default=None
        )
        generation_error: Mapped[str | None] = mapped_column(
            Text, nullable=True, default=None
        )
        created_at: Mapped[datetime] = mapped_column(nullable=False)
        updated_at: Mapped[datetime] = mapped_column(nullable=False)
    ```
    **Column notes:**
    - `generated_code`: Full Python source of the LLM-generated Freqtrade strategy. Stored verbatim.
    - `generation_metadata`: JSON string with `{"model": "...", "input_tokens": N, "output_tokens": N, "duration_ms": N}`. Parsed by application code, not by DB.
    - `generation_error`: Human-readable error message if generation failed (timeout, API error, validation failure).
    - Status lifecycle expands from Story 2.1: `draft → generating → generated → failed`. Story 2.1 only created `draft` rows. Story 2.2 adds the generation transitions.
    - Use `str | None` NOT `Optional[str]` (ruff UP007).
  - [ ] 1.2 Generate Alembic migration:
    ```bash
    PYTHONPATH=src alembic revision --autogenerate -m "add_strategy_generation_columns"
    ```
    **IMPORTANT:** Use `PYTHONPATH=src` prefix — required for Alembic to resolve `senzey_bots` imports. Verify the generated migration adds only `generated_code`, `generation_metadata`, `generation_error` columns (not recreating the table).
  - [ ] 1.3 Apply migration: `PYTHONPATH=src alembic upgrade head` — verify columns exist.
  - [ ] 1.4 Fix migration typing: Auto-generated migration may use `Union`/`Sequence` from `typing` — fix to `collections.abc.Sequence` and `str | None` per ruff UP rules. Same pattern as Story 2.1 migration fix.

- [ ] Task 2: Extend strategy repository with generation operations (AC: #1)
  - [ ] 2.1 Add functions to `src/senzey_bots/database/repositories/strategy_repo.py`:
    ```python
    def update_strategy_status(
        session: Session,
        strategy_id: int,
        status: str,
        *,
        error: str | None = None,
    ) -> Strategy | None:
        """Update strategy status. Optionally set generation_error.

        Returns updated strategy or None if not found.
        """
        strategy = session.get(Strategy, strategy_id)
        if strategy is None:
            return None
        strategy.status = status
        strategy.updated_at = utcnow()
        if error is not None:
            strategy.generation_error = error
        session.commit()
        session.refresh(strategy)
        return strategy


    def update_strategy_generation(
        session: Session,
        strategy_id: int,
        *,
        generated_code: str,
        generation_metadata: str,
    ) -> Strategy | None:
        """Save generated code and metadata, set status to 'generated'.

        Returns updated strategy or None if not found.
        """
        strategy = session.get(Strategy, strategy_id)
        if strategy is None:
            return None
        strategy.generated_code = generated_code
        strategy.generation_metadata = generation_metadata
        strategy.status = "generated"
        strategy.generation_error = None
        strategy.updated_at = utcnow()
        session.commit()
        session.refresh(strategy)
        return strategy
    ```
    **Design decisions:**
    - `update_strategy_status` is generic — handles any status transition with optional error message.
    - `update_strategy_generation` is a specialized "happy path" update — sets code + metadata + status in one atomic operation.
    - Both return `Strategy | None` — same pattern as existing `get_strategy`.
    - Both call `session.commit()` immediately — same pattern as `create_strategy`.

- [ ] Task 3: Create LLM provider abstraction (AC: #1, #2)
  - [ ] 3.1 Add `anthropic` dependency to `pyproject.toml`:
    ```bash
    uv add "anthropic>=0.78.0"
    ```
    Pin minimum version `>=0.78.0` (latest stable is 0.81.0 as of 2026-02-25). The SDK requires Python 3.8+, compatible with our Python 3.11+ requirement.
  - [ ] 3.2 Create `src/senzey_bots/agents/llm/provider.py`:
    ```python
    """LLM provider — abstraction for LLM API calls with timeout and error handling.

    Supports Anthropic Claude as the primary provider.
    Uses environment variable ANTHROPIC_API_KEY for authentication.
    """

    from __future__ import annotations

    import json
    import os
    import time
    from dataclasses import dataclass

    import anthropic

    from senzey_bots.shared.logger import get_logger

    logger = get_logger(__name__)

    _DEFAULT_MODEL = "claude-sonnet-4-6"
    _DEFAULT_MAX_TOKENS = 8192
    _DEFAULT_TIMEOUT_SECONDS = 60  # NFR2: LLM generation timeout <= 60s


    @dataclass(frozen=True)
    class LLMResponse:
        """Result of an LLM API call."""

        content: str
        model: str
        input_tokens: int
        output_tokens: int
        duration_ms: int


    @dataclass(frozen=True)
    class LLMError:
        """Error from an LLM API call."""

        error_type: str  # "timeout", "api_error", "auth_error", "unavailable"
        message: str


    LLMResult = LLMResponse | LLMError


    def generate(
        prompt: str,
        *,
        system_prompt: str | None = None,
        model: str = _DEFAULT_MODEL,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        timeout: float = _DEFAULT_TIMEOUT_SECONDS,
        temperature: float = 0.0,
    ) -> LLMResult:
        """Call the LLM API and return response or error.

        Reads API key from ANTHROPIC_API_KEY environment variable.
        Never raises — returns LLMError on failure.
        """
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return LLMError(
                error_type="auth_error",
                message="ANTHROPIC_API_KEY environment variable is not set. "
                "Please configure your API key in .env file.",
            )

        start_ms = int(time.monotonic() * 1000)
        try:
            client = anthropic.Anthropic(
                api_key=api_key,
                timeout=timeout,
            )

            messages = [{"role": "user", "content": prompt}]
            kwargs: dict[str, object] = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": messages,
                "temperature": temperature,
            }
            if system_prompt is not None:
                kwargs["system"] = system_prompt

            response = client.messages.create(**kwargs)

            elapsed_ms = int(time.monotonic() * 1000) - start_ms

            content = ""
            for block in response.content:
                if block.type == "text":
                    content += block.text

            return LLMResponse(
                content=content,
                model=response.model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                duration_ms=elapsed_ms,
            )

        except anthropic.APITimeoutError:
            elapsed_ms = int(time.monotonic() * 1000) - start_ms
            logger.warning(
                json.dumps({
                    "event": "llm_timeout",
                    "model": model,
                    "timeout_seconds": timeout,
                    "elapsed_ms": elapsed_ms,
                })
            )
            return LLMError(
                error_type="timeout",
                message=f"LLM generation timed out after {timeout:.0f} seconds. "
                "Try simplifying your strategy rules or use manual code entry.",
            )

        except anthropic.AuthenticationError:
            return LLMError(
                error_type="auth_error",
                message="Invalid ANTHROPIC_API_KEY. Please check your API key configuration.",
            )

        except anthropic.APIConnectionError:
            return LLMError(
                error_type="unavailable",
                message="Cannot connect to LLM API. Check network connection "
                "or use manual code entry as fallback.",
            )

        except anthropic.APIError as e:
            logger.warning(
                json.dumps({
                    "event": "llm_api_error",
                    "error": str(e),
                    "model": model,
                })
            )
            return LLMError(
                error_type="api_error",
                message=f"LLM API error: {e}",
            )
    ```
    **Design decisions:**
    - **Never raises exceptions** — returns `LLMResult` (union of `LLMResponse | LLMError`). Same "result, not exception" philosophy as `ValidationResult` from Story 2.1.
    - **Environment variable for API key** (`ANTHROPIC_API_KEY`) — follows `.env` + `python-dotenv` pattern. The secrets store (Story 1.2) stores encrypted keys for long-term persistence; the env var is the runtime delivery mechanism.
    - **60-second timeout** per NFR2. Configurable via parameter for testing.
    - **Temperature 0.0** by default — deterministic code generation. No creativity needed; we want consistent, correct code.
    - **Structured JSON logging** on errors — follows `shared/logger.py` pattern.
    - **`frozen=True` dataclasses** for immutable results — follows established pattern.
    - **Client created per call** — simple, no connection pooling needed for single-user system.

- [ ] Task 4: Create prompt templates for strategy generation (AC: #1, #3)
  - [ ] 4.1 Create `src/senzey_bots/agents/llm/prompts/__init__.py`:
    ```python
    """LLM prompt templates for code generation."""
    ```
  - [ ] 4.2 Create `src/senzey_bots/agents/llm/prompts/strategy_generation.py`:
    ```python
    """Prompt template for Freqtrade strategy generation.

    Builds a structured prompt that instructs the LLM to convert user-provided
    strategy rules/code into an executable Freqtrade IStrategy implementation.
    """

    from __future__ import annotations

    _SYSTEM_PROMPT = """\
    You are an expert Freqtrade strategy developer. You convert trading rules into \
    executable Python code that strictly follows the Freqtrade IStrategy interface.

    RULES:
    - Output ONLY valid Python code. No explanations, no markdown, no code fences.
    - The strategy class MUST inherit from `freqtrade.strategy.IStrategy`.
    - Set `INTERFACE_VERSION = 3`.
    - Implement ALL three required methods: populate_indicators, populate_entry_trend, \
    populate_exit_trend.
    - Set required attributes: timeframe, stoploss, minimal_roi.
    - Use vectorized pandas/talib operations. NEVER use iterrows() or Python loops on DataFrames.
    - Use modern signal column names: enter_long, exit_long (NOT buy/sell).
    - Do NOT use deprecated APIs: no populate_buy_trend, no populate_sell_trend.
    - Use ta-lib for indicator calculations (import as `import talib.abstract as ta`).
    - Include proper type hints on all method signatures.
    - FORBIDDEN: os.system, subprocess, eval, exec, __import__, importlib.import_module, \
    shutil.rmtree. The code must not perform any I/O or shell operations.
    - Always return the dataframe from populate_* methods.
    - Ensure volume > 0 guard in entry/exit conditions to avoid signals on empty candles.\
    """


    def build_strategy_prompt(
        input_type: str,
        input_content: str,
        strategy_name: str,
    ) -> str:
        """Build the user prompt for strategy generation.

        Args:
            input_type: One of "rules_text", "pinescript", "python_upload".
            input_content: The raw user input (rules, PineScript, or Python code).
            strategy_name: Name for the generated strategy class.

        Returns:
            Formatted prompt string for the LLM.
        """
        class_name = _sanitize_class_name(strategy_name)

        type_instructions = _TYPE_INSTRUCTIONS[input_type]

        return f"""\
    {type_instructions}

    Strategy name: {strategy_name}
    Class name: {class_name}

    User input:
    ---
    {input_content}
    ---

    Generate a complete Freqtrade strategy class named `{class_name}` that implements \
    the trading logic described above. The class must inherit from IStrategy with \
    INTERFACE_VERSION = 3.

    Output ONLY the Python source code. No explanations.\
    """


    def get_system_prompt() -> str:
        """Return the system prompt for strategy generation."""
        return _SYSTEM_PROMPT


    _TYPE_INSTRUCTIONS = {
        "rules_text": (
            "Convert the following plain-text trading rules into a Freqtrade strategy. "
            "Interpret indicator names (RSI, MACD, SMA, EMA, etc.) and create "
            "appropriate entry/exit conditions using ta-lib."
        ),
        "pinescript": (
            "Convert the following TradingView PineScript code into an equivalent "
            "Freqtrade strategy. Map PineScript indicators to ta-lib equivalents. "
            "Translate strategy.entry/strategy.close calls to enter_long/exit_long columns."
        ),
        "python_upload": (
            "Refactor the following Python trading strategy code into a valid Freqtrade "
            "IStrategy implementation. Preserve the original trading logic but ensure "
            "it conforms to Freqtrade's interface, uses ta-lib, and follows all conventions."
        ),
    }


    def _sanitize_class_name(name: str) -> str:
        """Convert a strategy name to a valid PascalCase Python class name.

        Examples:
            "RSI Mean Reversion Gold" → "RsiMeanReversionGoldStrategy"
            "my-awesome_strategy" → "MyAwesomeStrategy"
        """
        import re

        # Replace non-alphanumeric with spaces, split, capitalize each word
        words = re.split(r"[^a-zA-Z0-9]+", name.strip())
        pascal = "".join(w.capitalize() for w in words if w)
        if not pascal:
            pascal = "Generated"
        # Ensure it doesn't start with a digit
        if pascal[0].isdigit():
            pascal = "Strategy" + pascal
        # Append "Strategy" suffix if not already present
        if not pascal.endswith("Strategy"):
            pascal += "Strategy"
        return pascal
    ```
    **Design decisions:**
    - **System prompt** encodes all Freqtrade interface rules — the LLM cannot deviate from IStrategy V3.
    - **Separate system + user prompts** — system prompt is stable (Freqtrade rules), user prompt varies (strategy input).
    - **Type-specific instructions** — different guidance for rules_text vs PineScript vs Python upload.
    - **Class name sanitization** — generates valid PascalCase names with "Strategy" suffix.
    - **"Output ONLY code" directive** — prevents markdown/explanation wrapping that would break AST parsing.
    - **Forbidden patterns listed in prompt** — defense in depth alongside post-generation validation.
    - **No Pydantic** at this layer — pure Python for simplicity.

- [ ] Task 5: Create generated code validator (AC: #3)
  - [ ] 5.1 Create `src/senzey_bots/core/strategy/generation_validator.py`:
    ```python
    """Post-generation validation for Freqtrade strategy code.

    Validates that LLM-generated code is a valid Freqtrade IStrategy implementation.
    Checks: AST parsing, forbidden imports, IStrategy inheritance, required methods,
    required class attributes.
    """

    from __future__ import annotations

    import ast
    import re
    from dataclasses import dataclass

    _REQUIRED_METHODS = frozenset({
        "populate_indicators",
        "populate_entry_trend",
        "populate_exit_trend",
    })

    _REQUIRED_ATTRIBUTES = frozenset({
        "timeframe",
        "stoploss",
        "minimal_roi",
    })

    _FORBIDDEN_PATTERNS = re.compile(
        r"\b(os\.system|subprocess|eval\s*\(|exec\s*\(|"
        r"__import__|importlib\.import_module|importlib\.util|shutil\.rmtree)\b"
    )


    @dataclass(frozen=True)
    class GenerationValidationResult:
        """Result of post-generation code validation."""

        valid: bool
        error: str | None = None
        class_name: str | None = None


    def validate_generated_code(code: str) -> GenerationValidationResult:
        """Validate LLM-generated strategy code for Freqtrade compliance.

        Checks in order:
        1. Non-empty code
        2. No forbidden imports/patterns
        3. Valid Python syntax (AST)
        4. Contains class inheriting from IStrategy
        5. Class has required methods
        6. Class has required attributes (INTERFACE_VERSION, timeframe, stoploss, minimal_roi)
        """
        if not code or not code.strip():
            return GenerationValidationResult(
                valid=False,
                error="Generated code is empty.",
            )

        # Security check — forbidden patterns
        forbidden_match = _FORBIDDEN_PATTERNS.search(code)
        if forbidden_match:
            return GenerationValidationResult(
                valid=False,
                error=f"Security violation in generated code: "
                f"forbidden pattern '{forbidden_match.group()}'.",
            )

        # AST parsing
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return GenerationValidationResult(
                valid=False,
                error=f"Generated code has syntax error at line {e.lineno}: {e.msg}.",
            )

        # Find IStrategy subclass
        strategy_class = _find_istrategy_class(tree)
        if strategy_class is None:
            return GenerationValidationResult(
                valid=False,
                error="Generated code must contain a class inheriting from IStrategy.",
            )

        class_name = strategy_class.name

        # Check required methods
        methods = {
            node.name
            for node in ast.walk(strategy_class)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        missing_methods = _REQUIRED_METHODS - methods
        if missing_methods:
            return GenerationValidationResult(
                valid=False,
                error=f"Missing required methods: {', '.join(sorted(missing_methods))}.",
                class_name=class_name,
            )

        # Check required class-level attributes
        class_attrs = _extract_class_attributes(strategy_class)
        missing_attrs = _REQUIRED_ATTRIBUTES - class_attrs
        if missing_attrs:
            return GenerationValidationResult(
                valid=False,
                error=f"Missing required attributes: {', '.join(sorted(missing_attrs))}.",
                class_name=class_name,
            )

        # Check INTERFACE_VERSION is set
        if "INTERFACE_VERSION" not in class_attrs:
            return GenerationValidationResult(
                valid=False,
                error="Missing INTERFACE_VERSION class attribute. Must be set to 3.",
                class_name=class_name,
            )

        return GenerationValidationResult(valid=True, class_name=class_name)


    def _find_istrategy_class(tree: ast.Module) -> ast.ClassDef | None:
        """Find the first class that inherits from IStrategy."""
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for base in node.bases:
                base_name = _get_base_name(base)
                if base_name == "IStrategy":
                    return node
        return None


    def _get_base_name(node: ast.expr) -> str | None:
        """Extract the name from a base class expression."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return None


    def _extract_class_attributes(class_def: ast.ClassDef) -> set[str]:
        """Extract names of class-level attributes from a ClassDef AST node."""
        attrs: set[str] = set()
        for node in class_def.body:
            # Simple assignment: timeframe = '15m'
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        attrs.add(target.id)
            # Annotated assignment: timeframe: str = '15m'
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name):
                    attrs.add(node.target.id)
        return attrs
    ```
    **Design decisions:**
    - **Separate from Story 2.1's `validator.py`** — input validation (user-provided content) and generation validation (LLM output) are different concerns with different checks.
    - **AST-based analysis** — inspects the code structure without executing it. Safe and reliable.
    - **IStrategy detection via base class name** — checks for `IStrategy` in class bases. Works for both `class Foo(IStrategy)` and `class Foo(freqtrade.strategy.IStrategy)`.
    - **Returns `class_name`** on valid results — useful for downstream consumers.
    - **Same `frozen=True` dataclass** pattern as `ValidationResult`.

- [ ] Task 6: Create strategy generator orchestrator (AC: #1, #2, #3)
  - [ ] 6.1 Create `src/senzey_bots/core/strategy/generator.py`:
    ```python
    """Strategy generator — orchestrates LLM-driven code generation.

    Coordinates: status transitions, LLM prompt building, API call,
    post-generation validation, and result persistence.
    """

    from __future__ import annotations

    import json

    from senzey_bots.agents.llm.provider import LLMError, generate
    from senzey_bots.agents.llm.prompts.strategy_generation import (
        build_strategy_prompt,
        get_system_prompt,
    )
    from senzey_bots.core.strategy.generation_validator import (
        validate_generated_code,
    )
    from senzey_bots.database.engine import get_session
    from senzey_bots.database.repositories.strategy_repo import (
        get_strategy,
        update_strategy_generation,
        update_strategy_status,
    )
    from senzey_bots.shared.logger import get_logger

    logger = get_logger(__name__)


    def generate_strategy(strategy_id: int) -> GenerationResult:
        """Generate executable Freqtrade code for a strategy draft.

        Flow:
        1. Load strategy from DB, validate status is "draft"
        2. Set status to "generating"
        3. Build prompt and call LLM
        4. Validate generated code (AST + Freqtrade compliance)
        5. Save result (generated_code + metadata OR error)
        6. Return result

        Never raises — returns GenerationResult with success/failure info.
        """
        # 1. Load and validate strategy
        with get_session() as session:
            strategy = get_strategy(session, strategy_id)
            if strategy is None:
                return GenerationResult(
                    success=False,
                    error="Strategy not found.",
                )
            if strategy.status != "draft":
                return GenerationResult(
                    success=False,
                    error=f"Strategy must be in 'draft' status to generate. "
                    f"Current status: '{strategy.status}'.",
                )
            # Extract fields inside session scope
            name = strategy.name
            input_type = strategy.input_type
            input_content = strategy.input_content

        # 2. Set status to "generating"
        with get_session() as session:
            update_strategy_status(session, strategy_id, "generating")

        # 3. Build prompt and call LLM
        prompt = build_strategy_prompt(input_type, input_content, name)
        system_prompt = get_system_prompt()

        llm_result = generate(prompt, system_prompt=system_prompt)

        # Handle LLM failure
        if isinstance(llm_result, LLMError):
            with get_session() as session:
                update_strategy_status(
                    session, strategy_id, "failed", error=llm_result.message
                )
            return GenerationResult(
                success=False,
                error=llm_result.message,
                error_type=llm_result.error_type,
            )

        # 4. Extract code from response (strip markdown fences if present)
        raw_code = _extract_code(llm_result.content)

        # 5. Validate generated code
        validation = validate_generated_code(raw_code)
        if not validation.valid:
            error_msg = f"Generated code failed validation: {validation.error}"
            with get_session() as session:
                update_strategy_status(
                    session, strategy_id, "failed", error=error_msg
                )
            return GenerationResult(
                success=False,
                error=error_msg,
                error_type="validation_error",
            )

        # 6. Save generated code and metadata
        metadata = json.dumps({
            "model": llm_result.model,
            "input_tokens": llm_result.input_tokens,
            "output_tokens": llm_result.output_tokens,
            "duration_ms": llm_result.duration_ms,
            "class_name": validation.class_name,
        })

        with get_session() as session:
            update_strategy_generation(
                session,
                strategy_id,
                generated_code=raw_code,
                generation_metadata=metadata,
            )

        return GenerationResult(
            success=True,
            generated_code=raw_code,
            class_name=validation.class_name,
            metadata=metadata,
        )


    @dataclass(frozen=True)
    class GenerationResult:
        """Result of strategy generation."""

        success: bool
        generated_code: str | None = None
        class_name: str | None = None
        metadata: str | None = None
        error: str | None = None
        error_type: str | None = None


    def _extract_code(content: str) -> str:
        """Extract Python code from LLM response.

        Handles cases where LLM wraps code in markdown fences despite instructions.
        """
        content = content.strip()
        # Remove markdown code fences if present
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first line (```python or ```)
            lines = lines[1:]
            # Remove last line if it's closing fence
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)
        return content.strip()
    ```
    **Add missing import at top of file:**
    ```python
    from dataclasses import dataclass
    ```
    **Design decisions:**
    - **Never raises** — returns `GenerationResult` with success/failure info.
    - **Session-per-operation** — each DB operation gets its own session scope. Prevents long-lived sessions during the LLM API call.
    - **DetachedInstanceError prevention** — strategy fields are extracted into local variables inside session scope before the LLM call.
    - **Markdown fence stripping** — defensive measure for LLMs that wrap code in ```python fences despite instructions.
    - **Status transitions** are atomic: draft → generating → generated/failed.
    - **`GenerationResult`** carries all info the UI needs: success flag, code, class name, metadata, error.

- [ ] Task 7: Update UI for generation workflow (AC: #1, #2)
  - [ ] 7.1 Update `src/senzey_bots/ui/pages/10_generate.py` — add generation capability to the existing drafts section:
    **Add to the existing drafts section, after the draft info display:**
    - Add a "Generate" button next to each draft with status "draft".
    - On click, call `generate_strategy(strategy_id)`.
    - Show `st.spinner("Generating strategy...")` during the LLM call.
    - On success: display generated code with `st.code(code, language="python")`.
    - On failure: display error with `st.error(error_message)` and show hint: "You can use the Python Upload tab to manually enter strategy code."
    - For drafts with status "generated": show a "View Code" expander with the generated code.
    - For drafts with status "generating": show a spinner/info message.
    - For drafts with status "failed": show error message with option to retry (resets to "draft").
    **Key UI patterns:**
    - Use `st.session_state` for generation-in-progress tracking.
    - All ORM attribute access inside `with get_session()` blocks (DetachedInstanceError prevention).
    - Explicit widget keys on all new buttons/elements.
    - `st.rerun()` after status changes to refresh the display.

  - [ ] 7.2 Add "Retry" functionality for failed strategies:
    ```python
    # Inside the drafts loop, for failed strategies:
    if d["status"] == "failed":
        col_retry, col_error = st.columns([1, 3])
        with col_retry:
            if st.button("Retry", key=f"retry_{d['id']}"):
                with get_session() as session:
                    update_strategy_status(session, d["id"], "draft")
                st.rerun()
        with col_error:
            if d.get("generation_error"):
                st.error(d["generation_error"])
    ```

  - [ ] 7.3 Import new dependencies in `10_generate.py`:
    ```python
    from senzey_bots.core.strategy.generator import generate_strategy
    from senzey_bots.database.repositories.strategy_repo import (
        create_strategy,
        delete_strategy,
        list_strategies,
        update_strategy_status,
    )
    ```

  - [ ] 7.4 Update draft data extraction to include new columns:
    ```python
    draft_data = [
        {
            "id": s.id,
            "name": s.name,
            "input_type": s.input_type,
            "status": s.status,
            "created_at": s.created_at,
            "generated_code": s.generated_code,
            "generation_error": s.generation_error,
        }
        for s in strategies
    ]
    ```

- [ ] Task 8: Write unit tests (AC: #4)
  - [ ] 8.1 Create `tests/unit/agents/__init__.py` (empty).
  - [ ] 8.2 Create `tests/unit/agents/llm/__init__.py` (empty).
  - [ ] 8.3 Create `tests/unit/agents/llm/test_provider.py`:
    - Test `generate` returns `LLMError` when `ANTHROPIC_API_KEY` not set.
    - Test `generate` returns `LLMResponse` on successful API call (mock `anthropic.Anthropic`).
    - Test `generate` returns `LLMError` with `error_type="timeout"` on `APITimeoutError`.
    - Test `generate` returns `LLMError` with `error_type="auth_error"` on `AuthenticationError`.
    - Test `generate` returns `LLMError` with `error_type="unavailable"` on `APIConnectionError`.
    - Test `generate` returns `LLMError` with `error_type="api_error"` on generic `APIError`.
    - Test `LLMResponse` and `LLMError` dataclasses are frozen.
    - **Mock pattern:** Use `monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")` and `monkeypatch.setattr` on `anthropic.Anthropic` to mock API calls.
  - [ ] 8.4 Create `tests/unit/agents/llm/prompts/__init__.py` (empty).
  - [ ] 8.5 Create `tests/unit/agents/llm/prompts/test_strategy_generation.py`:
    - Test `build_strategy_prompt` includes input content.
    - Test `build_strategy_prompt` includes class name from strategy name.
    - Test `build_strategy_prompt` uses correct type instructions for each input type.
    - Test `get_system_prompt` returns non-empty string containing "IStrategy".
    - Test `_sanitize_class_name` with various inputs:
      - "RSI Mean Reversion Gold" → "RsiMeanReversionGoldStrategy"
      - "my-awesome_strategy" → "MyAwesomeStrategy" (already ends with Strategy)
      - "123 numbers first" → "Strategy123NumbersFirstStrategy"
      - "" → "GeneratedStrategy"
      - "simple" → "SimpleStrategy"
  - [ ] 8.6 Create `tests/unit/core/strategy/test_generation_validator.py`:
    - Test `validate_generated_code` with valid Freqtrade strategy code → valid.
    - Test `validate_generated_code` with empty code → invalid.
    - Test `validate_generated_code` with forbidden imports → invalid.
    - Test `validate_generated_code` with syntax error → invalid.
    - Test `validate_generated_code` with no IStrategy subclass → invalid.
    - Test `validate_generated_code` with missing `populate_indicators` → invalid.
    - Test `validate_generated_code` with missing `populate_entry_trend` → invalid.
    - Test `validate_generated_code` with missing `populate_exit_trend` → invalid.
    - Test `validate_generated_code` with missing `INTERFACE_VERSION` → invalid.
    - Test `validate_generated_code` with missing `timeframe` → invalid.
    - Test `validate_generated_code` with missing `stoploss` → invalid.
    - Test `validate_generated_code` with missing `minimal_roi` → invalid.
    - Test `validate_generated_code` returns correct `class_name`.
    - Test `GenerationValidationResult` is frozen.
    - **Use inline strategy code strings** — no file fixtures needed.
  - [ ] 8.7 Create `tests/unit/core/strategy/test_generator.py`:
    - Test `generate_strategy` with non-existent strategy ID → error.
    - Test `generate_strategy` with non-draft status → error.
    - Test `generate_strategy` happy path (mock LLM provider) → success, status=generated.
    - Test `generate_strategy` with LLM timeout → status=failed, error returned.
    - Test `generate_strategy` with LLM API error → status=failed.
    - Test `generate_strategy` with invalid generated code → status=failed.
    - Test `_extract_code` strips markdown fences.
    - Test `_extract_code` passes through clean code.
    - Test `GenerationResult` is frozen.
    - **Mock pattern:** Use `monkeypatch.setattr` on `senzey_bots.core.strategy.generator.generate` (the LLM provider function) to control LLM output.
    - **DB fixture:** Use in-memory SQLite (same `conftest.py` pattern as Story 2.1).
  - [ ] 8.8 Extend `tests/unit/database/repositories/test_strategy_repo.py`:
    - Test `update_strategy_status` updates status and updated_at.
    - Test `update_strategy_status` with error message sets generation_error.
    - Test `update_strategy_status` returns None for non-existent ID.
    - Test `update_strategy_generation` saves code + metadata + sets status to "generated".
    - Test `update_strategy_generation` clears previous generation_error.
    - Test `update_strategy_generation` returns None for non-existent ID.

- [ ] Task 9: Validate all gates pass (AC: #4)
  - [ ] 9.1 Run `ruff check .` — must pass with zero errors.
  - [ ] 9.2 Run `mypy src/` — must pass with zero errors. **Note:** May need `# type: ignore` for `anthropic.Anthropic` constructor kwargs if mypy doesn't have stubs. Prefer `monkeypatch` in tests to avoid suppressing real type errors.
  - [ ] 9.3 Run `pytest tests/unit/core/strategy/ tests/unit/agents/ tests/unit/database/repositories/ -v --tb=short --cov=src/senzey_bots/core/strategy --cov=src/senzey_bots/agents/llm --cov-report=term-missing` — all tests pass with >= 80% line coverage.
  - [ ] 9.4 Run existing tests to confirm no regressions: `pytest tests/ -v --tb=short`.
  - [ ] 9.5 Run `PYTHONPATH=src alembic upgrade head` — migration applies cleanly.
  - [ ] 9.6 Run Streamlit smoke test: `streamlit run src/senzey_bots/ui/main.py` — generation button visible on drafts, generation flow works end-to-end.

## Dev Notes

### CRITICAL CONSTRAINTS

- **DO NOT MODIFY** `freqtrade/` or `trading_ig/` directories. [Source: architecture.md#Architectural Boundaries]
- **DO NOT MODIFY** `src/senzey_bots/app.py` — the Streamlit entry point is `src/senzey_bots/ui/main.py`. [Source: Story 2.1 Dev Notes]
- **DO NOT ADD `[tool.ruff]` to root `pyproject.toml`** — `ruff.toml` is the single source of truth. [Source: Story 1.1 Dev Notes]
- **DO NOT USE `Optional[X]`** — ruff's `UP007` rule flags it. Use `X | None` (Python 3.11+). [Source: Story 1.2 Dev Notes]
- **DO NOT USE `datetime.now()`** directly — use `shared/clock.py`'s `utcnow()` for all timestamps. [Source: Story 1.2 Dev Notes]
- **DO NOT MODIFY existing Story 2.1 test files** — extend, don't rewrite. Add new test cases to existing test files or create new test files.
- **DO NOT MODIFY Story 1.2/1.3 modules** (`security/*`, `core/events/*`, `core/orchestrator/*`, `core/errors/*`) unless adding new error codes.
- **ALEMBIC requires `PYTHONPATH=src`** for all CLI invocations. [Source: Story 1.2 Debug Logs]
- **ALL JSON keys and DB columns MUST be `snake_case`**. [Source: architecture.md#Naming Patterns]
- **DetachedInstanceError prevention** — access ORM attributes INSIDE `with get_session()` blocks. Extract values into plain dicts/variables before the session closes. [Source: Story 2.1 Dev Notes]
- **Streamlit widget keys MUST be explicit** — omitting keys causes widget state reset on reruns. [Source: Story 2.1 Dev Notes]
- **Fernet key must be 32 bytes base64url-encoded (44 chars)** — if touching crypto at all. [Source: Story 1.2 Dev Notes]
- **DO NOT USE `logging.extra` for structured fields** — `shared/logger.py`'s `_JsonFormatter` drops `extra`. Embed fields in JSON message string. [Source: Story 1.2 Dev Notes]
- **LLM timeout MUST be <= 60 seconds** per NFR2. [Source: prd.md#NFR2]
- **LLM fallback MUST activate within 5 seconds** on failure per NFR4. [Source: prd.md#NFR4]
- **Generated code MUST NOT contain forbidden imports** — `os.system`, `subprocess`, `eval`, `exec`, `__import__`, `importlib.import_module`, `shutil.rmtree`. Enforce in both prompt instructions AND post-generation validation.
- **Freqtrade strategy MUST use INTERFACE_VERSION = 3** — V2 APIs (`buy`/`sell` columns, `populate_buy_trend`) are deprecated. [Source: Freqtrade migration docs]

### Architecture Reference

**FR2 Scope:**
- System (LLM Agent) converts user-provided rules into executable Freqtrade Python strategy code.
- [Source: epics.md#Story 2.2, prd.md#FR2]

**Data Flow (architecture.md#Integration Points):**
1. User strategy input → `ui/pages/10_generate.py` (Story 2.1 ✅)
2. LLM generate/validate → `agents/llm/*` + `core/strategy/*` (THIS STORY)
3. Backtest + threshold gate → `core/backtest/*` (Epic 3)

**Component Locations (architecture.md#Project Structure):**
- `agents/llm/provider.py` — LLM API client
- `agents/llm/prompts/` — Prompt templates
- `core/strategy/generator.py` — Generation orchestrator
- `core/strategy/validator.py` — Input validation (Story 2.1 ✅)

**Error Handling (architecture.md#API & Communication Patterns):**
- Typed domain errors: `StrategyValidationError` for code validation failures
- `CommandResult` pattern for service communication (not directly used in UI layer for this story)
- All errors must be user-friendly (no raw stack traces in UI)

**Event System (architecture.md#Communication Patterns):**
- Event names: `domain.action.v1` (e.g., `strategy.generated.v1`)
- Optional for this story — event publishing can be added as enhancement. Core focus is generation + validation.

### Previous Story Context (Story 2.1 — In Review)

**What was built:**
- `database/models/strategy.py` — Strategy model with `id`, `name`, `input_type`, `input_content`, `status`, `created_at`, `updated_at`
- `database/repositories/strategy_repo.py` — CRUD: `create_strategy`, `list_strategies`, `get_strategy`, `delete_strategy`
- `core/strategy/validator.py` — Input validation: `validate_strategy_input` + `ValidationResult`
- `ui/main.py` — Multipage navigation with `st.Page` + `st.navigation`
- `ui/pages/10_generate.py` — Strategy Input Workspace: 3 tabs, draft list, delete
- `database/migrations/versions/29136f6d035f_add_strategies_table.py` — Creates `strategies` table

**Key APIs you WILL use:**
- `from senzey_bots.database.engine import get_session` — context manager yielding `Session`
- `from senzey_bots.database.repositories.strategy_repo import get_strategy, create_strategy, list_strategies, delete_strategy` — existing CRUD
- `from senzey_bots.shared.clock import utcnow` — UTC datetime
- `from senzey_bots.shared.logger import get_logger` — structured JSON logger
- `from senzey_bots.database.base import Base` — DeclarativeBase for models

**Key patterns established:**
- `Mapped[type] = mapped_column(...)` for model fields (SQLAlchemy 2.0)
- In-memory SQLite fixtures in `conftest.py` for test isolation
- `get_session()` is a `contextlib.contextmanager` — use `with get_session() as session:`
- Test functions: `def test_*(...) -> None:` (mypy strict)
- `from __future__ import annotations` at top of every module
- Page file naming: `NN_<feature>.py` (e.g., `10_generate.py`)

**Story 2.1 Debug Lessons:**
- regex `\b` after `(` fails to match `eval('...')` — Story 2.1 fixed by removing trailing `\b`. Generation validator uses same fixed pattern.
- mypy dict type inference: Mixed-type dicts cause `.get()` to return `object`. Use typed tuples or extract to typed variables.
- Alembic migration auto-gen uses `Union`/`Sequence` typing — must fix to `collections.abc.Sequence` and `str | None`.
- ruff N999: Streamlit page files with numeric prefix need `per-file-ignores` in `ruff.toml`. Already configured for `10_generate.py`.

### Story 1.3 Infrastructure Available

Story 1.3 (Messaging Contracts & Typed Errors) provides infrastructure available for use:
- `core/errors/domain_errors.py` — `DomainError`, `StrategyValidationError`, `OrchestratorError`, etc.
- `core/errors/error_codes.py` — `STRATEGY_VALIDATION_ERROR`, `ORCHESTRATOR_ERROR`, etc.
- `core/orchestrator/contracts.py` — `CommandResult`, `success()`, `failure()`, `failure_from_domain_error()`
- `core/events/models.py` — `EventEnvelope` with `domain.action.v1` naming
- `core/events/publisher.py` — `publish_event()` to append-only JSONL audit
- `core/events/correlation.py` — `new_correlation_id()`, `get_correlation_id()`

**Story 2.2 uses Story 1.3's error types** for `StrategyValidationError` if needed, but the primary error communication is through `GenerationResult` (returned to UI). Domain errors are available for future orchestrator integration.

**Optional enhancement (NOT required for AC completion):** Publish `strategy.generation_started.v1`, `strategy.generated.v1`, `strategy.generation_failed.v1` events via `publish_event()`. This adds audit trail but is not part of acceptance criteria.

### Git Intelligence (Recent Commits)

```
68f7118 feat(story-1.3): standardize internal messaging contracts and typed errors
801ef3e feat(story-1.2): implement local authentication and encrypted secrets store
6d31b5c chore(bmad): update story 1.1 artifacts to done + sprint status sync
c701b66 feat(story-1.1): bootstrap modular project skeleton with UV
```

**Commit convention:** `type(scope): description`
- `feat` for new functionality, `chore` for maintenance, `docs` for documentation
- Scope matches story number
- Expected commit for this story: `feat(story-2.2): generate executable freqtrade strategy via llm`

**Uncommitted changes (Story 2.1):** Several new files are in git working tree but not yet committed (story 2.1 is in "review" status). These files ARE on disk and available:
- `src/senzey_bots/core/strategy/validator.py`
- `src/senzey_bots/database/models/strategy.py`
- `src/senzey_bots/database/repositories/strategy_repo.py`
- `src/senzey_bots/ui/pages/10_generate.py`
- `tests/unit/core/strategy/` and `tests/unit/database/`

### Technical Stack (Exact Versions)

| Tool | Version | Purpose |
|---|---|---|
| Streamlit | 1.54.0 (pinned) | UI framework |
| SQLAlchemy | 2.0.47 (pinned) | ORM + session management |
| Alembic | 1.18.4 (pinned) | DB migrations |
| Pydantic | 2.12.5 (pinned) | Schema validation |
| anthropic | >=0.78.0 (NEW) | Anthropic Claude API client |
| Python | 3.11+ | Runtime |
| ruff | >=0.3.0 | Linting |
| mypy | >=1.10.0 | Type checking (strict) |
| pytest | >=8.0.0 | Testing |
| pytest-cov | >=7.0.0 | Coverage reporting |
| pytest-mock | >=3.14.0 | Mock fixtures |

### Freqtrade IStrategy Interface (V3) Reference

Generated strategies MUST conform to this interface:

```python
from freqtrade.strategy import IStrategy
from pandas import DataFrame
import talib.abstract as ta

class MyStrategy(IStrategy):
    INTERFACE_VERSION = 3          # REQUIRED — must be 3
    timeframe = '15m'              # REQUIRED — candle interval
    stoploss = -0.10               # REQUIRED — stop loss ratio
    minimal_roi = {"0": 0.01}      # REQUIRED — min ROI thresholds

    # Optional but recommended for this project's risk management:
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.05

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """REQUIRED — Add technical indicator columns to dataframe."""
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """REQUIRED — Set enter_long/enter_short columns (0 or 1)."""
        dataframe.loc[(dataframe['rsi'] < 30), 'enter_long'] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """REQUIRED — Set exit_long/exit_short columns (0 or 1)."""
        dataframe.loc[(dataframe['rsi'] > 70), 'exit_long'] = 1
        return dataframe
```

**Critical rules:**
- Column names: `enter_long`, `exit_long` (NOT `buy`/`sell` — deprecated V2 names)
- Vectorized pandas operations only — NEVER `iterrows()` or Python loops
- `import talib.abstract as ta` for indicators
- `volume > 0` guard recommended in entry/exit conditions
- Metadata dict contains `{'pair': 'XRP/BTC'}` — accessible via `metadata['pair']`

### Anthropic SDK Usage Pattern

```python
import anthropic

client = anthropic.Anthropic(api_key="...", timeout=60.0)
message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=8192,
    system="System prompt here",
    messages=[{"role": "user", "content": "User prompt here"}],
    temperature=0.0,
)
# Response: message.content[0].text (str), message.usage.input_tokens, message.usage.output_tokens
# Exceptions: APITimeoutError, AuthenticationError, APIConnectionError, APIError
```

### Secrets / API Key Configuration

**For development:** Set `ANTHROPIC_API_KEY` in `.env` file (loaded by `python-dotenv`). Add `ANTHROPIC_API_KEY=` to `.env.example` as a placeholder.

**Runtime flow:**
1. `agents/llm/provider.py` reads `os.environ.get("ANTHROPIC_API_KEY")`
2. If not set → returns `LLMError(error_type="auth_error", ...)`
3. UI displays error: "Please configure your API key in .env file"
4. User falls back to manual code entry (Python Upload tab)

**Future integration:** When auth guard is implemented, the secrets store (Story 1.2) can inject the API key from encrypted DB into environment at session start.

### File Structure for This Story

```
New/modified files:
  src/senzey_bots/database/
    models/
      strategy.py                     ← MODIFY (add generated_code, generation_metadata, generation_error)
    repositories/
      strategy_repo.py                ← MODIFY (add update_strategy_status, update_strategy_generation)
    migrations/
      versions/
        <hash>_add_strategy_generation_columns.py  ← GENERATED by Alembic
  src/senzey_bots/core/
    strategy/
      generator.py                    ← NEW (generation orchestrator)
      generation_validator.py         ← NEW (post-generation Freqtrade compliance check)
  src/senzey_bots/agents/
    llm/
      provider.py                     ← NEW (Anthropic API client)
      prompts/
        __init__.py                   ← NEW (empty)
        strategy_generation.py        ← NEW (prompt templates)
  src/senzey_bots/ui/
    pages/
      10_generate.py                  ← MODIFY (add generation workflow, retry, code display)
  pyproject.toml                      ← MODIFY (add anthropic dependency)
  .env.example                        ← MODIFY (add ANTHROPIC_API_KEY placeholder)
  tests/
    unit/
      agents/
        __init__.py                   ← NEW (empty)
        llm/
          __init__.py                 ← NEW (empty)
          test_provider.py            ← NEW
          prompts/
            __init__.py               ← NEW (empty)
            test_strategy_generation.py ← NEW
      core/
        strategy/
          test_generation_validator.py ← NEW
          test_generator.py           ← NEW
      database/
        repositories/
          test_strategy_repo.py       ← MODIFY (add update tests)
```

### Testing Standards

- Use `tmp_path` fixture for file-system tests if needed.
- Use `monkeypatch` for environment variables and module-level overrides.
- Each test function: `def test_*(...) -> None:` (mypy strict).
- In-memory SQLite via `conftest.py` fixture for DB tests.
- **Mock the Anthropic API** — NEVER make real API calls in tests. Use `monkeypatch.setattr` on `anthropic.Anthropic` class.
- **Mock the LLM provider** in generator tests — patch `senzey_bots.core.strategy.generator.generate` to control LLM output.
- Generation validator tests use inline code strings — no file fixtures needed.
- Prompt tests are pure function tests — no mocking needed.
- Import pattern: `from senzey_bots.agents.llm.provider import generate, LLMResponse, LLMError`
- **New dependency:** `anthropic>=0.78.0` must be added before tests can run.

### What This Story Does NOT Cover (Deferred)

- **Backtest execution** — Epic 3 will run generated strategies through Freqtrade.
- **Strategy file persistence to `freqtrade_user_data/strategies/`** — Story 3.1 will write `.py` files when backtest is requested.
- **Agent-to-agent communication via MCP** — Story 2.3 will display agent communication timeline. The LLM call in this story is a direct API call, not MCP-mediated.
- **Event publishing** for strategy generation lifecycle — available infrastructure from Story 1.3, but not required for AC completion. Can be added as enhancement.
- **UI authentication guard** — deferred cross-cutting concern. No session-level auth check on pages.
- **Multiple LLM providers** — only Anthropic Claude is supported. OpenAI/other providers can be added later via provider abstraction.
- **Advanced static analysis** — Story 3.3 will implement comprehensive static safety checks beyond AST/interface validation.
- **Strategy editing/regeneration** — user can retry (resets to "draft") but cannot edit the generated code in-place.
- **Streaming generation** — LLM response is waited in full. Streaming with real-time display deferred.
- **Cost tracking/budgets** — LLM usage metadata is stored but no enforcement of usage limits.

### Project Structure Notes

- All new files align with the architecture-defined directory structure. [Source: architecture.md#Complete Project Directory Structure]
- `agents/llm/provider.py` matches architecture's agent layer placement. [Source: architecture.md#Project Structure]
- `agents/llm/prompts/strategy_generation.py` follows the `prompts/` directory pattern. [Source: architecture.md#Project Structure]
- `core/strategy/generator.py` matches architecture's core domain placement. [Source: architecture.md#Project Structure]
- `core/strategy/generation_validator.py` is a new file — validation of LLM output is a distinct concern from input validation (Story 2.1's `validator.py`).
- No conflicts detected with existing files or patterns.

### References

- FR2 (LLM strategy generation): [Source: _bmad-output/planning-artifacts/epics.md#Story 2.2]
- NFR2 (LLM timeout 60s): [Source: _bmad-output/planning-artifacts/prd.md#NFR2]
- NFR4 (Graceful degradation): [Source: _bmad-output/planning-artifacts/prd.md#NFR4]
- Epic 2 context: [Source: _bmad-output/planning-artifacts/epics.md#Epic 2]
- Architecture agents: [Source: _bmad-output/planning-artifacts/architecture.md#Project Structure]
- Architecture errors: [Source: _bmad-output/planning-artifacts/architecture.md#API & Communication Patterns]
- Architecture data flow: [Source: _bmad-output/planning-artifacts/architecture.md#Integration Points]
- Story 2.1 context: [Source: _bmad-output/implementation-artifacts/2-1-build-strategy-input-workspace.md]
- Story 1.2 auth/secrets: [Source: _bmad-output/implementation-artifacts/1-2-implement-local-authentication-and-encrypted-secrets-store.md]
- Story 1.3 contracts: [Source: _bmad-output/implementation-artifacts/1-3-standardize-internal-messaging-contracts-and-typed-errors.md]
- Freqtrade IStrategy docs: [Source: freqtrade.io/en/stable/strategy-customization/]
- Freqtrade strategy migration: [Source: freqtrade.io/en/stable/strategy_migration/]
- Anthropic Python SDK: [Source: github.com/anthropics/anthropic-sdk-python]
- Project context: [Source: _bmad-output/project-context.md]

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
