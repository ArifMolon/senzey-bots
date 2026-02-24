---
project_name: 'senzey-bots'
user_name: 'Senzey'
date: '2026-02-25'
sections_completed: ['technology_stack', 'language_rules', 'framework_rules', 'testing_rules', 'quality_rules', 'workflow_rules', 'anti_patterns', 'prd_validation']
status: 'complete'
rule_count: 32
optimized_for_llm: true
---

# Project Context for AI Agents: senzey-bots (Agentic Trading System)

_This file contains critical rules and patterns that AI agents must follow when implementing code in this project. Focus on unobvious details that agents might otherwise miss._

**System Architecture Overview:**
`senzey-bots` is an overarching Agentic Trading System. It orchestrates AI agents to generate strategies, run backtests, and execute trades. It utilizes two major existing/3rd-party projects as its foundation:
1. **freqtrade**: Used purely as the trading engine, backtesting framework, and machine learning (FreqAI) provider.
2. **trading-ig**: Used as the broker API wrapper to communicate with IG (REST and Streaming).

---

## Technology Stack & Versions

- **senzey-bots (Core System)**: Python >= 3.11, LLM Orchestration frameworks (BMAD, LangChain/OpenAI, etc.).
- **Broker Integration (3rd Party - trading-ig)**: Python ^3.9, `requests` ^2.24, `requests-cache` ^0.5, `lightstreamer-client-lib` ^1.0.3, `pandas` ^2.
- **Trading Engine (3rd Party - freqtrade)**: Python >= 3.11, `pandas`==2.3.3, `numpy`==2.4.2, `ccxt`==4.5.39, `freqai`, `hyperopt`, `fastapi`==0.129.0, `SQLAlchemy`==2.0.46.

---

## Critical Implementation Rules

### Integration Boundaries & Workflow Rules

- **Strict Separation of Concerns:** DO NOT modify the core source code of `freqtrade` (`freqtrade/freqtrade/...`) or `trading-ig` (`trading_ig/...`) unless fixing a critical bug. Treat them as external libraries/engines.
- **Extensions Only:** All Freqtrade custom logic (strategies, hyperopts, FreqAI models) MUST be contained within the `freqtrade/user_data/` directory.
- **Agentic Logic:** All higher-level AI orchestration, agent logic, and system coordination MUST be placed in dedicated `senzey-bots` directories, kept separate from the underlying engine cores.
- **Configuration Management:** Do not check in `config.json` containing real API keys for IG or CCXT exchanges. Use `.env` or template files.

### Language-Specific Rules

- **Data Formatting (trading-ig):** Parse responses using `self.parse_response(response.text)` for consistent `errorCode` handling.
- **Typing & Interfaces (Freqtrade):** Maintain strict Python type hints (`-> DataFrame`, `dict`, `bool`) in strategy methods (`populate_indicators`, `populate_entry_trend`, `populate_exit_trend`).
- **Exception Handling:** Raise appropriate custom exceptions (`IGException`, `OperationalException`, `StrategyError`). Use `response.raise_for_status()` before parsing IG API errors.
- **Optional Dependencies (trading-ig):** Use `_HAS_PANDAS` feature flags before using optional dependencies like `pandas`.

### Framework-Specific Rules

- **REST & Streaming (trading-ig):** Use `self._req()` for automatic rate-limiting and session management. Follow `LightstreamerClient` patterns for WebSocket subscriptions.
- **Strategy Implementation (Freqtrade):** All custom trading strategies MUST inherit from `IStrategy`.
- **DataFrame Mutations (Freqtrade):** Strictly use Pandas `DataFrame` operations (`df['trend'] = ...`). NEVER use `iterrows()` or loops.
- **Timeframes & Data (Freqtrade):** Always use `dp.get_pair_dataframe()` to access historical data cleanly without Look-ahead bias.
- **Hyperopt Optimization:** Implement spaces using `IntParameter`, `DecimalParameter`, or `CategoricalParameter` within the strategy class. Prefer JSON configurations over hardcoded values.

### Testing Rules

- **Framework & Location:** Use `pytest` for all tests. Test files go in `tests/` with `test_{module}.py` naming.
- **Mocking:** Heavily utilize the `responses` library for REST API mocks, and `pytest-mock` (mocker fixture) for ccxt and Telegram API stubs. Never make live API calls.
- **Fixture Reusability:** Utilize `conftest.py` for global fixtures (mock configurations, fake exchanges).

### Code Quality & Style Rules

- **Formatting & Linting:** Enforce `Ruff` and `isort` for Freqtrade extensions and new `senzey-bots` code. Use `black` and `flake8` for `trading-ig` core.
- **Type Checking:** Strict type hints are enforced via `Mypy`.
- **Naming Conventions:** `snake_case` for modules, variables, and functions. `PascalCase` for classes. `UPPER_SNAKE_CASE` for constants.
- **Clean Code:** ALWAYS adhere strictly to Clean Code and SOLID principles.

### Critical Don't-Miss Rules (Anti-Patterns)

- **No Iterating Over DataFrames:** NEVER use `df.iterrows()`, `df.apply()`, or `for` loops on candlestick data within `populate_indicators()`. This destroys backtesting performance.
- **Lookahead Bias Prevention:** NEVER use `df.shift(-1)` or any future data reference to calculate current signals. `shift()` must only be positive (`df.shift(1)`).
- **Rate-Limiter Integrity:** Never bypass or override `trading_rate_limit_pause_or_pass` under `IGService`.
- **Safe API Limits:** Do not spam exchange APIs. Rely strictly on freqtrade's internal `DataProvider` caching.
- **No Global State Mutability:** Do not store trading state in global variables. Use the `Trade` model or `Wallets` objects in Freqtrade.
- **Pagination Edge Cases:** For IG account history API operations, carefully handle `pageSize` vs `pageData["totalPages"]` across different API versions.

---

## Usage Guidelines

**For AI Agents:**
- Read this file before implementing any code.
- Acknowledge that `freqtrade` and `trading-ig` are tools for the `senzey-bots` system.
- Follow ALL rules exactly as documented.
- When in doubt, prefer the more restrictive option.

**For Humans:**
- Keep this file lean and focused on agent needs.
- Review quarterly for outdated rules.

Last Updated: 2026-02-25
