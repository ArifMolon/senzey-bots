# Story 1.2: Implement Local Authentication and Encrypted Secrets Store

Status: done

## Story

As a platform owner,
I want local authentication and encrypted API key storage,
so that broker and LLM credentials are protected at rest and access is restricted to authenticated sessions.

## Acceptance Criteria

**Given** first-time setup
**When** the owner password is configured
**Then** the password is stored as an Argon2 hash in the local SQLite database
**And** authentication is required before any secret management actions are permitted.

**Given** broker/LLM API keys are entered
**When** secrets are persisted
**Then** values are encrypted with Fernet (AES-128-CBC + HMAC-SHA256, project-approved equivalent of AES-256) before database write
**And** plaintext is never stored in the `secrets_metadata` persistence table.

**Given** an authenticated session
**When** a secret is retrieved for use (e.g., to pass to IG adapter)
**Then** the plaintext is decrypted in-memory, used, and not persisted
**And** in-memory residency is explicitly minimized (no lingering via module-level variables or caches).

**Given** an unauthenticated caller
**When** any secrets write or read action is attempted
**Then** an `AuthenticationError` is raised
**And** the attempt is written to the structured JSON audit log with a `correlation_id`.

More specifically:
1. `src/senzey_bots/database/engine.py` is fully implemented: creates/connects to SQLite (`var/db/senzey_bots.db`), exposes `get_engine()` and `get_session()` context-manager.
2. Alembic is configured (`database/migrations/env.py`) with at minimum one baseline migration that creates the `auth_config` and `secrets_metadata` tables.
3. `auth_config` table stores: `id`, `password_hash` (Argon2), `fernet_salt` (base64-encoded, for PBKDF2 key derivation), `created_at`, `updated_at`.
4. `secrets_metadata` table stores: `id`, `key_name`, `encrypted_value` (AES-256/Fernet ciphertext), `description`, `created_at`, `updated_at`. **No plaintext column exists in this table.**
5. `security/password_hasher.py` implements `hash_password(plain: str) -> str`, `verify_password(plain: str, hashed: str) -> bool`, and `check_needs_rehash(hashed: str) -> bool` using `argon2-cffi`.
6. `security/crypto_service.py` implements `encrypt(plaintext: str, master_key: bytes) -> str` and `decrypt(ciphertext: str, master_key: bytes) -> str` using `cryptography.fernet.Fernet` (AES-128-CBC + HMAC-SHA256 under the hood — Fernet is the approved AES-equivalent for local secrets in this architecture).
7. `security/auth_service.py` implements `setup_password(plain: str) -> None` (generates fernet_salt + Argon2 hash, persists both), `authenticate(plain: str) -> bytes` (verifies password, returns derived Fernet master_key), and `is_configured() -> bool`; uses `shared/clock.py` for timestamps; raises typed `AuthenticationError` on failure.
8. `security/secrets_store.py` implements `store_secret(key_name: str, plaintext: str, master_key: bytes)` and `get_secret(key_name: str, master_key: bytes) -> str`; internally calls `crypto_service`.
9. `ruff check .` and `mypy src/` continue to pass with zero errors after all new files are added.
10. Unit tests cover: password hash/verify, encrypt/decrypt round-trip, auth_service success + `AuthenticationError` failure. Minimum 80% line coverage on security module.

## Tasks / Subtasks

- [x] Task 1: Implement database engine and session factory (AC: #1)
  - [x] 1.1 Update `src/senzey_bots/database/engine.py` — replace stub with full implementation (current stub has `get_engine(database_url: str) -> Engine`; the new singleton drops that parameter entirely — old signature is intentionally removed):
    - Create SQLite engine pointing to `var/db/senzey_bots.db` (create parent dirs if not exist using `pathlib.Path.mkdir(parents=True, exist_ok=True)`).
    - Expose `get_engine() -> Engine` (module-level singleton, lazy-init).
    - Expose `get_session()` as a `contextlib.contextmanager` returning `Session` (SQLAlchemy 2.0 style: `with Session(engine) as session:`).
    - Use `connect_args={"check_same_thread": False}` for SQLite thread-safety in Streamlit context.
  - [x] 1.2 Create `src/senzey_bots/database/base.py` — shared declarative base for all model files:
    ```python
    from sqlalchemy.orm import DeclarativeBase

    class Base(DeclarativeBase):
        """Shared declarative base for all ORM models."""
        pass
    ```
    **IMPORTANT:** Use `DeclarativeBase` subclass (SQLAlchemy 2.0 modern pattern), NOT the legacy `declarative_base()` factory. This is required for `Mapped[]` + `mapped_column()` annotated mappings and mypy strict compatibility.

- [x] Task 2: Create SQLAlchemy models (AC: #3, #4)
  - [x] 2.1 Create `src/senzey_bots/database/models/auth_config.py`:
    ```python
    class AuthConfig(Base):
        __tablename__ = "auth_config"
        id: Mapped[int] = mapped_column(primary_key=True)
        password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
        fernet_salt: Mapped[str] = mapped_column(String(44), nullable=False)  # base64-encoded 16 bytes, for PBKDF2 key derivation
        created_at: Mapped[datetime] = mapped_column(nullable=False)
        updated_at: Mapped[datetime] = mapped_column(nullable=False)
    ```
    **CRITICAL:** The `fernet_salt` column is required for Fernet master key derivation via PBKDF2. This salt is separate from the Argon2 salt (which is embedded in the password_hash string). Generated once via `os.urandom(16)` during `setup_password()`, stored as `base64.urlsafe_b64encode(salt).decode()`.
  - [x] 2.2 Create `src/senzey_bots/database/models/secret_metadata.py`:
    ```python
    class SecretMetadata(Base):
        __tablename__ = "secrets_metadata"
        id: Mapped[int] = mapped_column(primary_key=True)
        key_name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
        encrypted_value: Mapped[str] = mapped_column(Text, nullable=False)
        description: Mapped[str | None] = mapped_column(Text, nullable=True)
        created_at: Mapped[datetime] = mapped_column(nullable=False)
        updated_at: Mapped[datetime] = mapped_column(nullable=False)
    ```
    **Note:** Use `str | None` (Python 3.11+), NOT `Optional[str]` — ruff's `UP007` rule flags `Optional[X]` as a lint error with the project's `UP` ruleset enabled.
  - [x] 2.3 Update `src/senzey_bots/database/models/__init__.py` to export `AuthConfig`, `SecretMetadata`.

- [x] Task 3: Configure Alembic and create baseline migration (AC: #2)
  - [x] 3.1 Manually create Alembic files — **do NOT run `alembic init`**: `database/migrations/` already has `__init__.py` from Story 1.1; `alembic init` will fail on a non-empty directory. Create these files manually:
    - `database/migrations/env.py` — configure `target_metadata = Base.metadata`, use `DATABASE_URL` from env or default to `sqlite:///var/db/senzey_bots.db`.
    - `database/migrations/script.py.mako` — standard Alembic migration template (copy from Alembic source or any boilerplate).
    - **NOTE**: The `alembic.ini` should be at project root pointing `script_location = src/senzey_bots/database/migrations`.
  - [x] 3.2 Generate initial migration: `alembic revision --autogenerate -m "baseline_auth_and_secrets"` — verify it creates both `auth_config` and `secrets_metadata` tables.
  - [x] 3.3 Run `alembic upgrade head` to apply migration locally; verify `var/db/senzey_bots.db` is created with correct schema.
  - [x] 3.4 Add `var/db/` to `.gitignore` (do NOT commit the SQLite database file — only `.gitkeep` if needed).

- [x] Task 4: Implement password hasher (AC: #5)
  - [x] 4.1 Update `src/senzey_bots/security/password_hasher.py`:
    ```python
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError

    _hasher = PasswordHasher()  # argon2-cffi defaults: Argon2id, RFC 9106 LOW_MEMORY profile

    def hash_password(plain: str) -> str:
        return _hasher.hash(plain)

    def verify_password(plain: str, hashed: str) -> bool:
        # IMPORTANT: argon2 verify() arg order is (hash, password) — hash FIRST
        try:
            return _hasher.verify(hashed, plain)
        except VerifyMismatchError:
            return False

    def check_needs_rehash(hashed: str) -> bool:
        """Check if hash needs upgrading to current PasswordHasher parameters."""
        return _hasher.check_needs_rehash(hashed)
    ```
    **Note:** `check_needs_rehash()` enables transparent parameter upgrades — if you later increase `time_cost` or `memory_cost`, existing hashes can be re-hashed after successful login.
  - [x] 4.2 Confirm `argon2-cffi==25.1.0` is already pinned in `src/senzey_bots/pyproject.toml` ✅ (done in Story 1.1).

- [x] Task 5: Implement crypto service (AC: #6)
  - [x] 5.1 Update `src/senzey_bots/security/crypto_service.py`:
    - Use `cryptography.fernet.Fernet` for symmetric encryption (AES-128-CBC + HMAC-SHA256; architecture-approved for local secrets).
    - `encrypt(plaintext: str, master_key: bytes) -> str` — returns URL-safe base64 Fernet token string.
    - `decrypt(ciphertext: str, master_key: bytes) -> str` — returns plain string.
    - `derive_master_key(password: str, salt: bytes) -> bytes` — use `PBKDF2HMAC(SHA256, length=32, iterations=480000)` then `base64.urlsafe_b64encode(key)` to produce Fernet-compatible key.
    - IMPORTANT: master_key passed in/out as `bytes`; never stored to disk.
  - [x] 5.2 Ensure `cryptography>=43.0.0` already pinned ✅ (Story 1.1).

- [x] Task 6: Implement auth service (AC: #7)
  - [x] 6.1 Create `src/senzey_bots/core/errors/domain_errors.py` — `core/errors/__init__.py` already exists (stub from Story 1.1); do NOT recreate the directory or overwrite `__init__.py`, just add this new file:
    ```python
    class AuthenticationError(Exception):
        """Raised when authentication fails."""
    class SecretsError(Exception):
        """Raised on encrypted secrets operation failure."""
    ```
    Keep minimal — Story 1.3 will add `RiskLimitError`, `BrokerError`, `ValidationError`, `OrchestratorError`. Do not pre-add those here.
  - [x] 6.2 Update `src/senzey_bots/security/auth_service.py`:
    - `setup_password(plain: str) -> None`:
      1. Hash password with `password_hasher.hash_password(plain)`.
      2. Generate fernet_salt: `base64.urlsafe_b64encode(os.urandom(16)).decode()`.
      3. Upsert `AuthConfig` row with `password_hash`, `fernet_salt`, timestamps.
      4. Return value: `None`. The fernet_salt is persisted in DB, not returned.
    - `authenticate(plain: str) -> bytes`:
      1. Load `AuthConfig` row from DB.
      2. If no row exists, raise `AuthenticationError("No password configured")`.
      3. Call `verify_password(plain, row.password_hash)`.
      4. On mismatch: raise `AuthenticationError`; log attempt with `correlation_id`.
      5. On success: derive and return master_key via `crypto_service.derive_master_key(plain, base64.urlsafe_b64decode(row.fernet_salt))`.
      6. Optionally: if `check_needs_rehash(row.password_hash)` is True, re-hash and update DB.
    - `is_configured() -> bool` — checks if `auth_config` table has a row (for first-time setup detection).
    - Import `shared/clock.py` for `created_at`/`updated_at`.
    - Import `shared/logger.py` for structured logging.
    - **CRITICAL:** `authenticate()` returns `bytes` (the derived master_key) so the caller can use it for secret operations without re-deriving. The caller must NOT persist this key.
    - **CRITICAL:** `correlation_id` logging pattern — `shared/logger.py`'s `_JsonFormatter` only serializes `{timestamp, level, logger, message}`; it does NOT include `logging.extra` fields in JSON. Generate `correlation_id` with `import uuid; correlation_id = str(uuid.uuid4())` and embed it directly in the message string:
      ```python
      import json, uuid
      correlation_id = str(uuid.uuid4())
      logger.warning(json.dumps({"event": "auth_failed", "correlation_id": correlation_id}))
      ```
      Do NOT use `logger.warning("msg", extra={"correlation_id": ...})` — the extra dict is silently dropped by the current formatter.

- [x] Task 7: Implement secrets store (AC: #8)
  - [x] 7.1 Update `src/senzey_bots/security/secrets_store.py`:
    - `store_secret(key_name: str, plaintext: str, master_key: bytes) -> None` — calls `crypto_service.encrypt`, upserts `SecretMetadata`.
    - `get_secret(key_name: str, master_key: bytes) -> str` — loads `SecretMetadata.encrypted_value`, calls `crypto_service.decrypt`, returns plaintext (caller is responsible for not persisting the return value).
    - `list_secret_names() -> list[str]` — returns all `key_name` values (no encrypted values exposed).
    - `delete_secret(key_name: str) -> None` — removes from DB.

- [x] Task 8: Write unit tests (AC: #10)
  - [x] 8.1 Create `tests/unit/security/` directory with `__init__.py`.
  - [x] 8.1a Create `tests/unit/security/conftest.py` with shared in-memory DB fixture (pytest auto-injects this without import boilerplate in test files):
    ```python
    import pytest
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from senzey_bots.database.base import Base

    @pytest.fixture
    def db_session() -> Session:  # type: ignore[misc]
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            yield session
        Base.metadata.drop_all(engine)
    ```
    Use `db_session` fixture directly in test function signatures — no import needed.
  - [x] 8.2 Create `tests/unit/security/test_password_hasher.py`:
    - Test `hash_password` returns a non-empty string, not equal to plaintext.
    - Test `verify_password` returns `True` for correct plain, `False` for wrong plain.
    - Test `check_needs_rehash` returns `False` for a freshly created hash.
    - Test hash output starts with `$argon2id$` (confirms Argon2id variant).
  - [x] 8.3 Create `tests/unit/security/test_crypto_service.py`:
    - Test round-trip: `decrypt(encrypt(text, key), key) == text`.
    - Test tampering detection: modified ciphertext raises `InvalidToken` (cryptography.fernet).
    - Test `derive_master_key` returns 44-byte base64 string (Fernet-compatible).
    - Test `derive_master_key` is deterministic: same password + same salt → same key.
    - Test `derive_master_key` with different salt → different key.
  - [x] 8.4 Create `tests/unit/security/test_auth_service.py` with an in-memory SQLite DB fixture:
    - Test `setup_password` + `authenticate` success path returns `bytes` (master_key).
    - Test wrong password raises `AuthenticationError`.
    - Test `is_configured()` returns `False` before setup, `True` after.
    - Test `authenticate` before any setup raises `AuthenticationError("No password configured")`.
  - [x] 8.5 Create `tests/unit/security/test_secrets_store.py` with in-memory SQLite DB fixture:
    - Test `store_secret` + `get_secret` round-trip.
    - Test `list_secret_names` returns stored key names.
    - Test `delete_secret` removes the entry.
    - Test `get_secret` with wrong key_name raises `SecretsError`.
  - [x] 8.6 Use `tests/unit/security/conftest.py` (see 8.1a) for shared fixture — do NOT create a separate `tests/fixtures/db_fixture.py` module (requires manual imports in every test file).

- [x] Task 9: Validate all AC gates pass (AC: #9, #10)
  - [x] 9.0 Add `pytest-cov` to dev deps (required for AC #10 coverage check — NOT in Story 1.1 deps):
    ```
    uv add --dev pytest-cov
    ```
  - [x] 9.1 Run `ruff check .` — must pass with zero errors. Note: ruff `UP007` rule will flag `Optional[X]` — use `X | None` in all new files.
  - [x] 9.2 Run `mypy src/` — must pass with zero errors.
  - [x] 9.3 Run `pytest tests/unit/security/ -v --tb=short --cov=src/senzey_bots/security --cov-report=term-missing` — all new tests pass with ≥80% line coverage on the security module.
  - [x] 9.4 Run `alembic upgrade head` on clean state — migration applies cleanly.

## Dev Notes

### CRITICAL CONSTRAINTS

- **DO NOT MODIFY** `freqtrade/` or `trading_ig/` directories. [Source: architecture.md#Architectural Boundaries]
- **DO NOT STORE PLAINTEXT** in any database column. The `secrets_metadata.encrypted_value` column must only ever hold Fernet ciphertext. [Source: architecture.md#Authentication & Security]
- **DO NOT MODULE-CACHE SECRETS**: Never store decrypted API keys in module-level variables, class attributes, or `st.session_state` beyond the immediate operation. [Source: architecture.md#Authentication & Security]
- **DO NOT ADD `[tool.ruff]` to root `pyproject.toml`** — `ruff.toml` is the single source of truth. [Source: Story 1.1 Dev Notes]
- **DO NOT RUN `alembic init`** — `database/migrations/__init__.py` already exists from Story 1.1; the command fails on non-empty directories. Manually create `env.py` and `script.py.mako` only.
- **DO NOT USE `logging.extra` for `correlation_id`** — `shared/logger.py`'s formatter silently drops extra fields. Embed `correlation_id` directly in the message JSON string.
- **Fernet key must be 32 bytes base64url-encoded (44 chars)**. Use `base64.urlsafe_b64encode(os.urandom(32))` or PBKDF2-derived key. Do NOT pass raw bytes to `Fernet()`.
- **Fernet vs AES-256**: Fernet uses AES-128-CBC + HMAC-SHA256 internally (NOT AES-256). The architecture specifies AES-256; Fernet is the project-approved implementation — do NOT substitute with raw `cryptography.hazmat` AES-256 primitives. [Source: architecture.md#Authentication & Security]
- **BRUTE-FORCE PROTECTION DEFERRED**: `authenticate()` raises `AuthenticationError` immediately without rate limiting. Throttling will be added in a future story when the Streamlit session layer is implemented. Do not add rate-limiting logic here.

### Architecture Reference

**Security Module (architecture.md#Authentication & Security):**
- Auth: single-user local login, argon2-cffi 25.1.0 hash
- Secrets: AES-256 at-rest, minimized in-memory residency, explicit zeroization lifecycle where possible
- Files: `security/crypto_service.py`, `security/secrets_store.py`, `security/auth_service.py`, `security/password_hasher.py`

**Database Layer (architecture.md#Data Architecture):**
- Stack: SQLite + SQLAlchemy 2.0.47 + Alembic 1.18.4
- Tables this story: `auth_config`, `secrets_metadata`
- Future tables (other stories): `strategies`, `backtests`, `deployments`, `orders`, `risk_events`, `agent_runs`
- Naming: `snake_case_plural` tables, `snake_case` columns, PK = `id` (integer), FK = `<ref>_id`

**Cross-Cutting (architecture.md#Cross-Cutting Concerns):**
- All auth failures must log with `correlation_id` via `shared/logger.py`
- `shared/clock.py` provides `utcnow()` for all timestamps (do NOT use `datetime.now()` directly)

### Previous Story Context (Story 1.1)

- `shared/logger.py` is available — actual API: `get_logger(name: str, level: int = logging.INFO) -> logging.Logger`
  - Outputs structured JSON to stdout only
  - `_JsonFormatter` fields: `{timestamp, level, logger, message}` — no extra fields
  - Usage: `logger = get_logger(__name__)`
- `shared/clock.py` is available — actual API: `utcnow() -> datetime` (timezone-aware UTC, `tzinfo=timezone.utc`)
  - Usage: `from senzey_bots.shared.clock import utcnow; ts = utcnow()`
- `shared/config_loader.py` is available — `load_config(path: str) -> dict[str, object]`
- `core/errors/__init__.py` exists (empty stub from Story 1.1) — do NOT recreate or overwrite
- `database/engine.py` is a stub (`get_engine(database_url: str) -> Engine`) — this story replaces it with a no-arg singleton; old signature is dropped
- `security/__init__.py` exists (empty stub)
- `database/models/__init__.py` exists (empty stub)
- `database/migrations/__init__.py` exists (empty stub) — alembic init will fail; manually create env.py
- `argon2-cffi==25.1.0` and `cryptography>=43.0.0` already pinned in `src/senzey_bots/pyproject.toml` ✅
- `pytest-cov` is NOT installed — must add via `uv add --dev pytest-cov` in Task 9.0
- `pytest.ini` has `pythonpath = . src` and `testpaths = tests`

### Technical Stack (Exact Versions)

| Tool | Version | Purpose |
|---|---|---|
| argon2-cffi | 25.1.0 (pinned) | Password hashing |
| cryptography | >=43.0.0 (pinned) | Fernet/AES crypto |
| SQLAlchemy | 2.0.47 (pinned) | ORM + session management |
| Alembic | 1.18.4 (pinned) | DB migrations |
| Python | 3.11+ | f-string, tomllib, match support |

### Fernet Key Derivation Pattern (Required)

```python
import base64
import os
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.fernet import Fernet

def derive_master_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480_000,
    )
    raw_key = kdf.derive(password.encode())
    return base64.urlsafe_b64encode(raw_key)  # Fernet-compatible 44-byte key
```

**Salt management:** Argon2 embeds its own salt in the hash string automatically — no separate salt column needed for password verification. However, a **separate `fernet_salt`** column IS required in `auth_config` for PBKDF2 key derivation. This salt is generated once via `os.urandom(16)` during `setup_password()` and stored as `base64.urlsafe_b64encode(salt).decode()` in the `auth_config.fernet_salt` column. During `authenticate()`, it is loaded from DB and decoded back to `bytes` for `derive_master_key()`.

### Alembic Configuration Pattern

```
# alembic.ini (project root)
script_location = src/senzey_bots/database/migrations
sqlalchemy.url = sqlite:///var/db/senzey_bots.db
```

```python
# database/migrations/env.py — critical section
from senzey_bots.database.base import Base
from senzey_bots.database.models import auth_config, secret_metadata  # noqa: F401
target_metadata = Base.metadata
```

### DB Location

- File: `var/db/senzey_bots.db`
- `var/db/` must be in `.gitignore`
- Create parent dir in `get_engine()` using `Path("var/db").mkdir(parents=True, exist_ok=True)`

### File Structure for This Story

```
New/modified files:
  src/senzey_bots/database/
    base.py                          ← NEW
    engine.py                        ← REPLACE stub
    models/
      __init__.py                    ← UPDATE (export models)
      auth_config.py                 ← NEW
      secret_metadata.py             ← NEW
    migrations/
      __init__.py                    ← EXISTS (from Story 1.1, do NOT overwrite)
      env.py                         ← NEW (manually created — do NOT run alembic init)
      script.py.mako                 ← NEW (Alembic template, manually created)
      versions/
        <hash>_baseline_auth_and_secrets.py  ← GENERATED
  src/senzey_bots/security/
    password_hasher.py               ← REPLACE stub
    crypto_service.py                ← REPLACE stub
    auth_service.py                  ← REPLACE stub
    secrets_store.py                 ← REPLACE stub
  src/senzey_bots/core/errors/
    domain_errors.py                 ← NEW (AuthenticationError, SecretsError)
  tests/unit/security/
    __init__.py                      ← NEW
    conftest.py                      ← NEW (shared in-memory DB fixture for all tests)
    test_password_hasher.py          ← NEW
    test_crypto_service.py           ← NEW
    test_auth_service.py             ← NEW
    test_secrets_store.py            ← NEW
  alembic.ini                        ← NEW (project root)
  .gitignore                         ← UPDATE (add var/db/)
```

### Testing Standards

- Test directory: `tests/unit/security/`
- Use pytest fixtures for in-memory SQLite engine isolation
- In-memory SQLite for test DB: `create_engine("sqlite:///:memory:")`
- Run `Base.metadata.create_all(engine)` in fixture setup
- All test functions: `def test_*(...) -> None:` (mypy strict requires return type)
- Mock `shared/clock.py` where needed for deterministic timestamps

### References

- Auth/crypto decisions: [Source: _bmad-output/planning-artifacts/architecture.md#Authentication & Security]
- Database stack decisions: [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture]
- Security module file locations: [Source: _bmad-output/planning-artifacts/architecture.md#Complete Project Directory Structure]
- FR10 (encrypted key management): [Source: _bmad-output/planning-artifacts/epics.md#Story 1.2]
- NFR5 (AES-256 at-rest enforcement): [Source: _bmad-output/planning-artifacts/epics.md#NonFunctional Requirements]
- Naming standards: [Source: _bmad-output/planning-artifacts/architecture.md#Naming Patterns]
- Story 1.1 learnings: [Source: _bmad-output/implementation-artifacts/1-1-bootstrap-modular-project-skeleton-with-uv.md#Dev Agent Record]

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

- Alembic needed `PYTHONPATH=src` to resolve `senzey_bots` imports; fixed by using that env var for all `alembic` CLI invocations.
- Generated migration file had `Union`/`Sequence` from `typing` — fixed to use `collections.abc.Sequence` and `X | Y` union syntax per ruff UP rules.
- `auth_service.get_session()` is patched via monkeypatch in tests to avoid touching the real SQLite file during unit tests.

### Completion Notes List

- Implemented full SQLite engine singleton with `contextlib` session factory (Task 1)
- Created SQLAlchemy 2.0 `DeclarativeBase` and models: `AuthConfig`, `SecretMetadata` (Tasks 1.2, 2)
- Configured Alembic manually (no `alembic init`), generated and applied baseline migration (Task 3)
- `password_hasher.py`: Argon2id via argon2-cffi, exposes hash/verify/check_needs_rehash (Task 4)
- `crypto_service.py`: Fernet + PBKDF2HMAC key derivation, 480k iterations (Task 5)
- `domain_errors.py`: `AuthenticationError`, `SecretsError` (Task 6.1)
- `auth_service.py`: setup_password, authenticate (returns bytes master_key), is_configured; correlation_id embedded in JSON log message (Task 6.2)
- `secrets_store.py`: store/get/list/delete with no plaintext persistence (Task 7)
- 26 unit tests across 4 test files, 100% coverage on security module (Task 8 + code-review fixes)
- All AC gates pass: ruff ✅ mypy ✅ pytest 26/26 ✅ alembic upgrade ✅ (Task 9)

**Code-Review Fixes Applied (claude-sonnet-4-6):**
- [CRITICAL] `.gitignore`: added `!src/**/*_config.py` negation — pre-existing `*_config.*` pattern was silently gitignoring `auth_config.py`, which would have broken the app on any fresh clone
- [HIGH] `test_auth_service.py`: added `test_setup_password_update_replaces_existing_row` — covers the upsert path in `setup_password()` (was uncovered at lines 33–35)
- [HIGH] `test_auth_service.py`: added `test_authenticate_rehashes_when_needed` — covers the re-hash branch in `authenticate()` (was uncovered at lines 70–76)
- [HIGH] `test_secrets_store.py`: added `test_store_secret_updates_existing_value` — covers the upsert path in `store_secret()` (was uncovered at lines 22–23)
- Coverage improved from 88% → 100% on security module

### File List

**New files:**
- `src/senzey_bots/database/base.py`
- `src/senzey_bots/database/models/auth_config.py`
- `src/senzey_bots/database/models/secret_metadata.py`
- `src/senzey_bots/database/migrations/env.py`
- `src/senzey_bots/database/migrations/script.py.mako`
- `src/senzey_bots/database/migrations/versions/__init__.py`
- `src/senzey_bots/database/migrations/versions/d02486ca3209_baseline_auth_and_secrets.py`
- `src/senzey_bots/security/password_hasher.py`
- `src/senzey_bots/security/crypto_service.py`
- `src/senzey_bots/security/auth_service.py`
- `src/senzey_bots/security/secrets_store.py`
- `src/senzey_bots/core/errors/domain_errors.py`
- `tests/unit/__init__.py`
- `tests/unit/security/__init__.py`
- `tests/unit/security/conftest.py`
- `tests/unit/security/test_password_hasher.py`
- `tests/unit/security/test_crypto_service.py`
- `tests/unit/security/test_auth_service.py`
- `tests/unit/security/test_secrets_store.py`
- `alembic.ini`

**Modified files:**
- `src/senzey_bots/database/engine.py` (replaced stub with singleton implementation)
- `src/senzey_bots/database/models/__init__.py` (added AuthConfig, SecretMetadata exports)
- `src/senzey_bots/pyproject.toml` (added pytest-cov to dev deps)
- `.gitignore` (added `.auto-claude/` exclusion; added `!src/**/*_config.py` negation to un-ignore `auth_config.py` from pre-existing `*_config.*` pattern — code-review fix)
- `uv.lock` (updated by `uv add --dev pytest-cov`)
