---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/architecture.md
  - _bmad-output/planning-artifacts/ux-design-specification.md
---

# trading-ig - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for trading-ig, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: User can input TradingView/PineScript rules or plain-text rules via UI, or upload ready Python strategy code.
FR2: System (LLM Agent) converts user-provided rules into executable Freqtrade Python strategy code.
FR3: User can start Freqtrade backtests for selected strategies and view summarized results (e.g., ROI, WinRate).
FR4: System (Analysis Agent) can read failed backtest logs, detect issues, and propose/fix with an iteration cap of 3.
FR5: User can deploy test-passing strategies to live production on IG Broker.
FR6: System automatically enforces Stop-Loss and Drawdown constraints for live strategies.
FR7: User can monitor live trades on dashboard and use emergency Kill-Switch to close all positions.
FR8: User can view real-time inter-agent communication logs from the UI.
FR9: System can assign tasks and pass results among internal services/agents via standard protocols.
FR10: User can register API keys in UI; system stores keys encrypted in local DB with password/IP-restricted access.
FR11: System enforces dynamic profit-taking (trailing stop) and time-based ROI realization per strategy; profitable positions must not fall below break-even.
FR12: System can enable automatic circuit-breakers through Freqtrade protection plugins (e.g., MaxDrawdown, StoplossGuard).
FR13: User can define per-strategy maximum capital allocation; system rejects orders exceeding this limit.
FR14: LLM-generated strategies must pass static code safety checks and mandatory backtest threshold validation before live deployment.
FR15: New strategies must complete a mandatory minimum 14-day dry_run period before full-capital live deployment.
FR16: System monitors IG free margin and blocks opening new positions when margin falls below critical threshold.

### NonFunctional Requirements

NFR1: Live deployment command-to-broker dispatch latency (excluding network) must stay below 500ms, validated via APM/log analysis.
NFR2: LLM strategy generation timeout must be <= 60 seconds, verified by integration test timing.
NFR3: In temporary network failures, Freqtrade engine and agents must attempt auto-reconnect up to 5 times within 30 seconds, measurable via logs.
NFR4: If LLM API is unavailable, system must fall back to manual code-entry UI within 5 seconds without crash, validated via integration tests.
NFR5: All API keys must be encrypted at rest in local DB with AES-256 (or equivalent), verified via code audit.
NFR6: System must never exceed IG request limits (aligned to max 30 req/min) and must prove compliance with API usage logs.
NFR7: If daily drawdown exceeds -5%, system enforces 24h new-order halt; if exceeds -10%, system closes all open positions via emergency market orders.
NFR8: Broker-side stoploss protection (IG on-exchange stop) must be enabled to protect positions during system outages.
NFR9: Unfilled orders must auto-cancel after 10 minutes for buy orders and 30 minutes for sell orders.
NFR10: Before going live, strategy backtests must satisfy thresholds: Sharpe >= 0.5, Max Drawdown <= 25%, Win Rate >= 35%.
NFR11: System must emit heartbeat every 60 seconds and send emergency Telegram/email alert when heartbeat is absent for 120 seconds.
NFR12: System must enforce IG order rate limit of max 10 orders/min and prevent duplicate orders from the same signal.

### Additional Requirements

- **Starter Template Requirement (Critical):** Architecture mandates a modular Streamlit AI starter (UV-based, customized), not a generic web boilerplate.
- **First Implementation Story Constraint:** Project bootstrap using `uv init` and baseline dependency setup must be the first implementation story in Epic 1.
- **Strict Boundary Rule:** `freqtrade` and `trading-ig` core code must not be modified; strategies stay under `user_data`/adapter boundaries.
- **Infrastructure/Runtime Profiles:** Dockerized local deployment with explicit `dev`, `dry_run`, and `live` profiles.
- **Data Persistence Stack:** SQLite + SQLAlchemy + Alembic with defined domain tables (`strategies`, `backtests`, `deployments`, `orders`, `risk_events`, `agent_runs`, `secrets_metadata`).
- **Security Baseline:** Single-user local auth with Argon2 hash and AES-256 encrypted secrets at rest; minimize in-memory plaintext residency.
- **Communication Model:** MCP-based agent communication (stdio/SSE) with typed domain errors and clear adapter boundaries.
- **Auditability Requirement:** Append-only immutable audit event log for strategy lifecycle, order events, and risk actions.
- **Risk Gate Placement:** Centralized Risk Guard must be enforced pre-trade on broker order path; no bypass allowed.
- **Integration Requirements:** IG broker adapter and Freqtrade adapter integration through orchestrator contracts.
- **Monitoring & Logging:** Structured JSON logs, correlation IDs in critical flows, heartbeat + alerting (Telegram/email).
- **API Compatibility/Versioning:** Event naming/versioning (`domain.action.v1`) and error taxonomy consistency required across services.
- **Quality Gate Requirements:** Backtest threshold gate and dry-run-to-live transition controls are mandatory before deployment.
- **UX-Sourced Additions:** UX specification file currently contains no detailed UX requirements beyond placeholder metadata/content shell.

### FR Coverage Map

FR1: Epic 2 - Strategy rule/code input from UI
FR2: Epic 2 - LLM conversion to executable Freqtrade strategy
FR3: Epic 3 - Backtest execution and result visibility
FR4: Epic 3 - Backtest log auto-fix loop (max 3 iterations)
FR5: Epic 4 - Live deployment to IG broker
FR6: Epic 4 - Automated stop-loss and drawdown enforcement
FR7: Epic 5 - Live monitoring and emergency kill-switch actions
FR8: Epic 2 - Real-time agent communication visibility
FR9: Epic 1 - Standardized inter-service task/result communication foundation
FR10: Epic 1 - Encrypted API key management with local access controls
FR11: Epic 4 - Dynamic profit lock and break-even protection rules
FR12: Epic 4 - Circuit-breaker protections via Freqtrade plugins
FR13: Epic 4 - Per-strategy capital cap enforcement
FR14: Epic 3 - Static analysis + backtest threshold quality gate
FR15: Epic 3 - Mandatory 14-day dry_run promotion gate
FR16: Epic 4 - IG free-margin threshold guard for new positions

## Epic List

### Epic 1: Secure Platform Foundation & Bootstrap
User can initialize and operate the platform on a secure local baseline with encrypted secrets and standardized service communication, enabling all downstream capabilities safely.
**FRs covered:** FR9, FR10

### Epic 2: Strategy Authoring & AI Generation
User can provide strategy intent/code and obtain executable Freqtrade strategies from the LLM workflow while observing agent interactions in real time.
**FRs covered:** FR1, FR2, FR8

### Epic 3: Backtest, Auto-Fix & Promotion Gates
User can validate strategy quality through backtesting, leverage bounded auto-fix loops, and enforce strict promotion criteria before live use.
**FRs covered:** FR3, FR4, FR14, FR15

### Epic 4: Live Deployment with Risk-Protected Execution
User can deploy validated strategies to IG while the system enforces capital, margin, drawdown, profit-locking, and circuit-breaker protections automatically.
**FRs covered:** FR5, FR6, FR11, FR12, FR13, FR16

### Epic 5: Live Operations Monitoring & Emergency Control
User can monitor live trading operations and rapidly neutralize risk through emergency controls when needed.
**FRs covered:** FR7

## Epic 1: Secure Platform Foundation & Bootstrap

Establish a secure, runnable project foundation with enforced boundaries, protected credentials, and standardized internal communication so all later capabilities can be implemented safely and consistently.

### Story 1.1: Bootstrap Modular Project Skeleton with UV

**FRs implemented:** FR9

As a platform owner,
I want to initialize the modular project skeleton with uv and baseline tooling,
So that all subsequent features are built on a consistent, enforceable architecture.

**Acceptance Criteria:**

**Given** a clean repository state
**When** project bootstrap is executed with uv and baseline dependencies/tooling are configured
**Then** the modular structure (`ui/`, `core/`, `agents/`, `integrations/`, `database/`, `security/`) exists and is runnable
**And** lint/type/test commands execute without configuration errors.

### Story 1.2: Implement Local Authentication and Encrypted Secrets Store

**FRs implemented:** FR10

As a platform owner,
I want local authentication and encrypted API key storage,
So that broker and LLM credentials are protected at rest and access is restricted.

**Acceptance Criteria:**

**Given** first-time setup
**When** the owner password is configured
**Then** the password is stored as an Argon2 hash
**And** authentication is required before secret management actions.

**Given** broker/LLM API keys are entered
**When** secrets are persisted
**Then** values are encrypted with AES-256 (or equivalent) before database write
**And** plaintext is never stored in persistence tables.

### Story 1.3: Standardize Internal Messaging Contracts and Typed Errors

**FRs implemented:** FR9

As a platform owner,
I want standardized service messaging schemas and typed domain errors,
So that agents/services exchange tasks and failures in a reliable, diagnosable way.

**Acceptance Criteria:**

**Given** orchestrator-to-service communication
**When** commands and results are exchanged
**Then** payloads follow a consistent schema with `snake_case` keys
**And** failure responses use typed domain error categories.

**Given** critical execution paths
**When** events and errors are logged
**Then** each record includes a correlation identifier
**And** records remain append-only compatible for immutable auditing.

## Epic 2: Strategy Authoring & AI Generation

Enable the user to author strategy intent/code and obtain executable Freqtrade strategies from the LLM workflow, with transparent agent activity visibility.

### Story 2.1: Build Strategy Input Workspace

**FRs implemented:** FR1

As a strategy developer,
I want a unified workspace to enter rule text, paste PineScript, or upload Python strategy code,
So that I can start strategy creation from my preferred input format.

**Acceptance Criteria:**

**Given** the strategy generation page
**When** the user provides rule text, PineScript, or a Python file
**Then** the input is validated and persisted as a strategy draft
**And** invalid or unsupported input is rejected with actionable feedback.

### Story 2.2: Generate Executable Freqtrade Strategy via LLM

**FRs implemented:** FR2

As a strategy developer,
I want the system to convert validated strategy intent into executable Freqtrade Python,
So that I can move from idea to testable strategy quickly.

**Acceptance Criteria:**

**Given** a valid strategy draft
**When** generation is triggered
**Then** the LLM agent returns executable strategy code compatible with Freqtrade interfaces
**And** generation outcome, metadata, and artifacts are versioned for later traceability.

**Given** upstream LLM unavailability
**When** generation exceeds timeout or fails
**Then** the user is redirected to manual code entry fallback
**And** failure is surfaced without crashing the workflow.

### Story 2.3: Display Real-Time Agent Communication Timeline

**FRs implemented:** FR8

As a strategy developer,
I want to observe real-time agent orchestration logs in the UI,
So that I can understand system progress and diagnose generation issues early.

**Acceptance Criteria:**

**Given** an active generation or analysis run
**When** agents exchange messages
**Then** the timeline shows events in near real time with timestamps and source context
**And** sensitive payload fields are masked according to security policy.

## Epic 3: Backtest, Auto-Fix & Promotion Gates

Provide a reliable quality pipeline where strategies are backtested, auto-corrected within guardrails, and promoted only when objective safety/performance gates are passed.

### Story 3.1: Run Backtests and Present Decision-Ready Results

**FRs implemented:** FR3

As a strategy developer,
I want to run backtests from the UI and view ROI/WinRate and core metrics,
So that I can evaluate strategy viability before deployment.

**Acceptance Criteria:**

**Given** a generated or uploaded strategy
**When** backtest execution is requested
**Then** the system runs the backtest through the Freqtrade adapter
**And** presents normalized summary metrics and links to detailed artifacts.

### Story 3.2: Execute Bounded Auto-Fix Loop from Backtest Logs

**FRs implemented:** FR4

As a strategy developer,
I want failed backtests to trigger automated diagnosis-and-fix cycles,
So that recoverable strategy issues are resolved with minimal manual effort.

**Acceptance Criteria:**

**Given** a failed backtest with parse/runtime errors
**When** auto-fix is enabled
**Then** the analysis agent proposes and applies fixes iteratively
**And** the loop stops at a maximum of 3 attempts with complete attempt history.

### Story 3.3: Enforce Static Safety and Backtest Threshold Gate

**FRs implemented:** FR14

As a platform owner,
I want pre-live strategies to pass static safety checks and quantitative thresholds,
So that unsafe or weak strategies cannot progress to deployment.

**Acceptance Criteria:**

**Given** a strategy eligible for promotion
**When** gate validation runs
**Then** static checks block forbidden imports/patterns
**And** the strategy must satisfy Sharpe >= 0.5, Max Drawdown <= 25%, Win Rate >= 35%.

### Story 3.4: Apply Mandatory 14-Day Dry-Run Promotion Policy

**FRs implemented:** FR15

As a platform owner,
I want every new strategy to complete a minimum dry-run observation period,
So that production capital is protected from unproven behavior.

**Acceptance Criteria:**

**Given** a strategy that passed static and backtest gates
**When** promotion to live is requested
**Then** the system enforces a minimum 14-day dry-run requirement
**And** promotion is blocked until dry-run completion criteria are met.

## Epic 4: Live Deployment with Risk-Protected Execution

Enable live trading on IG only through a risk-governed execution path that enforces capital, margin, drawdown, profit-lock, and circuit-breaker controls by default.

### Story 4.1: Deploy Approved Strategies to IG Through Orchestrated Adapter Path

**FRs implemented:** FR5

As a strategy developer,
I want approved strategies deployed to IG via orchestrator-controlled adapters,
So that live execution remains compliant with architecture boundaries.

**Acceptance Criteria:**

**Given** a strategy approved by all promotion gates
**When** live deployment is initiated
**Then** orders are routed through orchestrator -> risk guard -> IG adapter path
**And** no direct UI-to-broker execution path is available.

### Story 4.2: Enforce Pre-Trade Risk Guardrails and Circuit Breakers

**FRs implemented:** FR6, FR12

As a platform owner,
I want all live orders screened by centralized risk policies,
So that stop-loss, drawdown, and protection rules are never bypassed.

**Acceptance Criteria:**

**Given** an incoming order intent
**When** risk evaluation is performed
**Then** stop-loss, drawdown thresholds, and configured protections are applied before broker submission
**And** blocked actions return typed `RiskLimitError` responses with auditable reason codes.

### Story 4.3: Apply Capital Caps, Margin Thresholds, and Profit-Locking Controls

**FRs implemented:** FR11, FR13, FR16

As a platform owner,
I want per-strategy capital limits, margin guards, and profit-lock logic enforced automatically,
So that profitable and capital-safe behavior is maintained in volatile conditions.

**Acceptance Criteria:**

**Given** strategy-level risk configuration
**When** new positions are evaluated
**Then** orders exceeding configured capital caps are rejected
**And** new positions are blocked when IG free margin falls below critical threshold.

**Given** a profitable open position
**When** price evolves after profit-lock activation
**Then** trailing/time-based rules are enforced
**And** break-even floor protection prevents profit reversion below allowed boundary.

### Story 4.4: Enforce Broker/API Rate and Order Lifecycle Controls

**FRs implemented:** FR6, FR12

As a platform owner,
I want strict request/order limits and stale-order cancellation,
So that broker compatibility and operational safety are preserved.

**Acceptance Criteria:**

**Given** live order flow
**When** requests and orders are issued
**Then** IG-compatible limits are enforced (request and order budgets)
**And** duplicate-order prevention is active per signal identity.

**Given** pending orders
**When** timeout thresholds are reached
**Then** stale buy orders are auto-cancelled at 10 minutes and sell orders at 30 minutes
**And** cancellation events are written to immutable audit logs.

## Epic 5: Live Operations Monitoring & Emergency Control

Provide operational visibility and immediate emergency actions so the user can monitor system health and neutralize exposure within seconds.

### Story 5.1: Build Live Operations and Health Monitoring Dashboard

**FRs implemented:** FR7

As a platform operator,
I want a real-time dashboard for positions, risk state, agent activity, and system heartbeat,
So that I can detect anomalies quickly and operate with confidence.

**Acceptance Criteria:**

**Given** active strategy deployments
**When** dashboard views are opened or refreshed
**Then** live positions, risk signals, and heartbeat status are displayed with timestamps
**And** alert conditions (heartbeat miss, risk halt) are visibly emphasized.

### Story 5.2: Implement Emergency Kill-Switch Workflow

**FRs implemented:** FR7

As a platform operator,
I want a single kill-switch action to close open positions and halt new trades,
So that I can immediately reduce risk during market emergencies.

**Acceptance Criteria:**

**Given** emergency conditions or manual operator decision
**When** kill-switch is triggered
**Then** all open positions are closed via market orders as fast as broker constraints allow
**And** new order creation is blocked until explicit recovery procedures are executed.

**Given** kill-switch execution
**When** the action completes
**Then** immutable audit logs capture trigger source, timestamps, and resulting actions
**And** user-facing notifications summarize emergency outcome.
