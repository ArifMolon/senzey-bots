---
stepsCompleted:
  - step-01-init
  - step-02-context
  - step-03-starter
  - step-04-decisions
  - step-05-patterns
  - step-06-structure
  - step-07-validation
  - step-08-complete
inputDocuments:
  - _bmad-output/planning-artifacts/prd.md
  - _bmad-output/planning-artifacts/ux-design-specification.md
  - _bmad-output/project-context.md
  - _bmad-output/freqtrade/project-context.md
workflowType: 'architecture'
project_name: 'trading-ig'
user_name: 'Senzey'
date: '2026-02-25'
lastStep: 8
status: 'complete'
completedAt: '2026-02-25'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._


## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
Sistem, kullanıcının strateji kurallarını (metin veya kod) işleyerek çalıştırılabilir Freqtrade stratejilerine dönüştüren bir LLM Ajan orkestrasyonudur. Bu orkestrasyon, backtestleri çalıştırır, hataları otonom (max 3 iterasyon sınırı olan bir 'circuit breaker' ile) düzeltir, başarılı testleri IG Broker üzerinden canlıya alır. Entegre Streamlit arayüzü; ajan iletişimini, "Kill-Switch" acil durum düğmesini, kar yönetimi (Profit Locking) ve marjin kontrollerini barındırır. Yeni stratejiler için zorunlu 14 günlük 'dry_run' kalite geçitleri mevcuttur.

**Non-Functional Requirements:**
- İşlem gecikmesi < 500ms, LLM yanıtı < 60sn.
- 30sn içinde otomatik yeniden bağlanma (Auto-reconnect).
- API Key'ler için AES-256 şifreleme, yerel depolama ve in-memory ifşa sürelerinin en aza indirilmesi.
- Kesin IG API Limitleri (30 req/min, 10 order/min).
- Katı risk kuralları: -%5 DD'da durdurma, -%10 DD'da "Kill-Switch", sıkı backtest eşikleri (Sharpe ≥ 0.5, Max DD ≤ %25).

**Scale & Complexity:**
Proje, finansal risk taşıyan, gerçek zamanlı hata toleransı gerektiren ve farklı 3. parti motorları (Freqtrade, IG) entegre eden yüksek karmaşıklıkta bir otonom ajan sistemidir.
- Primary domain: Fintech / AI Orchestration
- Complexity level: High
- Estimated architectural components: Streamlit UI, Agent Orchestration Layer (MCP), Freqtrade Engine Bridge, Broker API Wrapper, Local Encrypted DB, Immutable Audit Logger.

### Technical Constraints & Dependencies
- `freqtrade` ve `trading-ig` çekirdek kodları kesinlikle değiştirilemez (Strict Separation of Concerns). Stratejiler yalnızca `user_data` klasöründe yer alacaktır.
- Streamlit ve ajanlar arası iletişim standart Model Context Protocol (MCP) kullanılarak sağlanacaktır.

### Cross-Cutting Concerns Identified
- **Security & Secrets:** API anahtarlarının AES-256 ile şifrelenmesi, yerel ağ erişim güvenliği ve bellekte (in-memory) tutulma süresinin minimuma indirilmesi.
- **Resiliency & Recovery:** Ağ kesintilerinde otomatik toparlanma, LLM iterasyon sınırlamaları, acil durum Kill-Switch mekanizması ve kalite geçitleri (dry_run).
- **Auditability:** Kararların ve emirlerin zaman damgalı değişmez (immutable) loglara kaydedilmesi.
- **Rate & Risk Limiting:** Borsa API limitlerine ve marjin/drawdown risk kurallarına tam uyum.

## Starter Template Evaluation

### Primary Technology Domain

**AI Orchestration & Web UI (Python)** based on project requirements analysis. Sistem, arkada BMAD/MCP ajanları çalıştıran ve Streamlit ile kullanıcı etkileşimi sağlayan Python tabanlı bir yapıdır.

### Starter Options Considered

Bu proje standart bir web uygulaması (örn. Next.js veya React) olmadığı ve mevcut `freqtrade` ile `trading-ig` motorlarına dışarıdan sıkı entegrasyon gerektirdiği için genel geçer boilerplate'ler yerine, modüler Python + Streamlit mimarisi değerlendirilmiştir.

- `pmareke/streamlit-boilerplate` (2024, public template): test, Docker, CI ve `uv` tabanlı modern Python akışı sunuyor.
- `ArthurVerrez/structured-streamlit-template` (2025): sade bir Streamlit organizasyonu sağlıyor ancak ileri düzey test/CI altyapısı sınırlı.

### Selected Starter: Modular Streamlit AI Starter (UV-based, customized)

**Rationale for Selection:**
Projenin MCP tabanlı ajan orkestrasyonu, AES-256 şifreli SQLite ve sıkı Freqtrade/IG entegrasyonu gibi özel ihtiyaçları var. Bu nedenle, hazır bir kalıbı birebir almak yerine `uv` merkezli modüler bir başlangıç (clean boundaries: `ui/`, `core/`, `agents/`, `database/`) daha uygun.

**Initialization Command:**

```bash
uv init senzey-bots
cd senzey-bots
uv add streamlit pandas numpy ruff mypy pytest pytest-mock responses python-dotenv
```

**Architectural Decisions Provided by Starter:**

**Language & Runtime:**
Python 3.11+ ve `uv` ile bağımlılık/ortam yönetimi.

**Styling Solution:**
Streamlit native UI + gerektiğinde custom CSS.

**Build Tooling:**
`uv` + lint/type/test pipeline (Ruff, Mypy, Pytest).

**Testing Framework:**
`pytest`, `pytest-mock`, `responses`.

**Code Organization:**
- `ui/`: Streamlit sayfaları ve bileşenleri
- `core/`: iş kuralları, risk/limit yönetimi
- `agents/`: MCP ve LLM orchestration
- `database/`: şifreleme, persistence, repository katmanı
- `freqtrade_user_data/`: strateji/hyperopt çıktıları

**Development Experience:**
Hızlı local setup, güçlü lint/type gates ve test odaklı iterasyon.

**Note:** Project initialization using this command should be the first implementation story.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
1. Data persistence stack: SQLite + SQLAlchemy 2.0.46 + Alembic 1.18.4
2. Secrets/auth baseline: local single-user auth with Argon2 (argon2-cffi 25.1.0) + AES-256 at-rest encryption boundary
3. Service communication model: MCP (stdio/SSE) for agents, adapter boundary for IG/Freqtrade, unified error taxonomy
4. Audit model: append-only immutable event log for strategy lifecycle, order events, and risk actions

**Important Decisions (Shape Architecture):**
1. Validation layer: Pydantic 2.12.5 request/config schemas
2. Rate/risk enforcement location: centralized Risk Guard service before broker/order path
3. Deployment baseline: Dockerized local deployment with explicit env profiles (dev/sim/live)

**Deferred Decisions (Post-MVP):**
1. Multi-user RBAC (current scope: single user)
2. Distributed queue/event bus (initially in-process orchestrator + durable DB/event log)
3. External observability stack (start with structured logs + alerts, evolve later)

### Data Architecture

- **Primary DB:** SQLite (local, encrypted storage boundary)
- **ORM:** SQLAlchemy 2.0.46
- **Migrations:** Alembic 1.18.4
- **Schema Validation:** Pydantic 2.12.5
- **Modeling Approach:**
  - `strategies`, `backtests`, `deployments`, `orders`, `risk_events`, `agent_runs`, `secrets_metadata`
- **Caching Strategy:** conservative in-memory TTL cache for non-critical computed views; no cache bypass for risk checks

### Authentication & Security

- **Auth Method:** single-user local login (password hash: argon2-cffi 25.1.0)
- **Authorization:** role simplification (owner-only in MVP)
- **Secrets Handling:** API keys encrypted at rest (AES-256), minimized in-memory residency, explicit zeroization lifecycle where possible
- **Security Middleware:** request/session guard, brute-force throttle, local-network hardening option

### API & Communication Patterns

- **Internal Communication:** MCP-based agent communication (stdio/SSE)
- **External Integrations:** adapter layer for IG + Freqtrade boundaries
- **Error Handling Standard:** typed domain errors (BrokerError, StrategyValidationError, RiskLimitError, OrchestratorError)
- **Rate Limiting:** centralized token-bucket + broker-specific guardrails

### Frontend Architecture

- **UI Framework:** Streamlit 1.54.0
- **State Management:** `st.session_state` + explicit workflow-state objects
- **Component Strategy:** page modules (`Generate`, `Backtest`, `Deploy`, `Monitor`, `Emergency`)
- **Performance Strategy:** async-safe background tasks + incremental rendering for logs/metrics

### Infrastructure & Deployment

- **Runtime Model:** local-first dockerized services (app + worker + db volume)
- **Environment Profiles:** `dev`, `dry_run`, `live`
- **Monitoring & Logging:** structured JSON logs, immutable append-only audit stream, heartbeat alerts
- **Scalability:** vertical-first scaling, horizontal/event-bus deferred to post-MVP

### Decision Impact Analysis

**Implementation Sequence:**
1. Data models + migrations
2. Secrets/auth + risk guard
3. MCP orchestration contracts
4. UI workflow pages
5. Deployment/ops hardening

**Cross-Component Dependencies:**
- Risk Guard sits on broker path and depends on normalized strategy/backtest artifacts.
- Audit logging is cross-cutting and mandatory for all agent/order flows.
- Secrets lifecycle policy affects UI, orchestrator, and integration adapters together.

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:** 24
Bu alanlar netleştirilmezse ajanlar farklı naming/format/structure kararları verip entegrasyon kırılmalarına yol açabilir.

### Naming Patterns

**Database Naming Conventions:**
- Tables: `snake_case_plural` (örn: `agent_runs`, `risk_events`)
- Columns: `snake_case` (örn: `created_at`, `strategy_id`)
- PK: `id` (UUID veya integer, tablo bazında tutarlı)
- FK: `<referenced_singular>_id` (örn: `strategy_id`)
- Indexes: `idx_<table>_<column_list>`

**API Naming Conventions:**
- Internal service methods: `snake_case`
- External REST paths (varsa): lowercase + plural (`/strategies`, `/orders`)
- Query params: `snake_case`
- Headers: standard HTTP casing, custom için `X-...`

**Code Naming Conventions:**
- Python module/function/variable: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Streamlit page files: `NN_<feature>.py` (örn: `10_generate.py`)

### Structure Patterns

**Project Organization:**
- `ui/`: Streamlit pages/components
- `core/`: domain services (risk, strategy, orchestration contracts)
- `agents/`: MCP agents, prompts, adapterlar
- `integrations/`: IG/Freqtrade boundary adapterları
- `database/`: models, repositories, migrations
- `tests/`: `unit/`, `integration/`, `e2e/`

**File Structure Patterns:**
- Config: `config/` + `.env` + `.env.example`
- Migration scripts: `database/migrations/versions/`
- Immutable logs: `var/audit/YYYY/MM/DD/*.jsonl`
- Docs: `docs/architecture/`, `docs/runbooks/`

### Format Patterns

**API/Service Response Formats:**
- Internal command result:
  - success: `{ "ok": true, "data": ... }`
  - fail: `{ "ok": false, "error": { "code": "RISK_LIMIT", "message": "...", "details": {...} } }`

**Data Exchange Formats:**
- JSON keys: `snake_case`
- Datetime: ISO-8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`)
- Money/ratio: explicit decimal precision (float yerine Decimal domain layer'da)
- Nullability: schema ile açık tanım (Pydantic)

### Communication Patterns

**Event System Patterns:**
- Event names: `domain.action.v1` (örn: `strategy.generated.v1`, `order.opened.v1`)
- Event envelope:
  - `event_id`, `event_name`, `occurred_at`, `source`, `correlation_id`, `payload`
- Versioning: breaking change → `v2` event adı

**State Management Patterns:**
- Streamlit state key prefixleri: `session.<module>.<name>`
- Immutable update-first yaklaşımı; kritik risk state'i yalnız `core/risk_guard` üzerinden güncellenir
- UI sadece command/request tetikler, karar `core` içinde verilir

### Process Patterns

**Error Handling Patterns:**
- Domain exceptions zorunlu tipli (`RiskLimitError`, `BrokerError`, `ValidationError`)
- Kullanıcı mesajı ve teknik log ayrılır
- Her hata logunda `correlation_id` bulunur

**Loading State Patterns:**
- Long-running görevlerde durumlar: `queued` → `running` → `succeeded|failed`
- UI polling interval standardı belirli ve merkezi config'den okunur
- Retry politikası kategori bazlı (broker/network/llm)

### Enforcement Guidelines

**All AI Agents MUST:**
- `snake_case` JSON + Python naming standardına uymak
- Tüm order/risk aksiyonlarında `correlation_id` üretmek ve taşımak
- Risk Guard bypass etmemek (tek zorunlu geçiş noktası)
- `freqtrade` / `trading-ig` core dosyalarını değiştirmemek

**Pattern Enforcement:**
- PR checklist + automated lint/type/test gates
- Pattern ihlali: `docs/runbooks/pattern-violations.md`
- Değişiklik süreci: ADR + reviewer onayı

### Pattern Examples

**Good Examples:**
- `event_name="risk.halt_triggered.v1"`
- `error.code="BROKER_RATE_LIMIT"`
- `table="agent_runs"`, `column="started_at"`

**Anti-Patterns:**
- `camelCase` JSON keys ile `snake_case` payload karıştırmak
- UI katmanından doğrudan broker order çağrısı yapmak
- correlation_id olmadan order/log yazmak

## Project Structure & Boundaries

### Complete Project Directory Structure

```
senzey-bots/
├── README.md
├── pyproject.toml
├── uv.lock
├── Makefile
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── ruff.toml
├── mypy.ini
├── pytest.ini
├── docker-compose.yml
├── Dockerfile
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── security.yml
├── config/
│   ├── app.toml
│   ├── risk.toml
│   ├── broker.toml
│   └── logging.toml
├── docs/
│   ├── architecture/
│   │   ├── adr/
│   │   └── decisions-index.md
│   ├── runbooks/
│   │   ├── emergency-kill-switch.md
│   │   ├── pattern-violations.md
│   │   └── incident-response.md
│   └── api/
├── scripts/
│   ├── bootstrap.sh
│   ├── run_dev.sh
│   └── rotate_audit_logs.sh
├── var/
│   └── audit/
│       └── YYYY/MM/DD/
│           └── events.jsonl
├── src/
│   └── senzey_bots/
│       ├── __init__.py
│       ├── app.py
│       ├── ui/
│       │   ├── main.py
│       │   ├── components/
│       │   │   ├── agent_flow.py
│       │   │   ├── risk_panel.py
│       │   │   └── order_table.py
│       │   └── pages/
│       │       ├── 10_generate.py
│       │       ├── 20_backtest.py
│       │       ├── 30_deploy.py
│       │       ├── 40_monitor.py
│       │       └── 50_emergency.py
│       ├── core/
│       │   ├── orchestrator/
│       │   │   ├── coordinator.py
│       │   │   ├── contracts.py
│       │   │   └── workflow_state.py
│       │   ├── risk/
│       │   │   ├── risk_guard.py
│       │   │   ├── drawdown_rules.py
│       │   │   └── margin_rules.py
│       │   ├── strategy/
│       │   │   ├── generator.py
│       │   │   ├── validator.py
│       │   │   └── deploy_policy.py
│       │   ├── backtest/
│       │   │   ├── runner.py
│       │   │   └── threshold_gate.py
│       │   ├── events/
│       │   │   ├── models.py
│       │   │   ├── publisher.py
│       │   │   └── correlation.py
│       │   └── errors/
│       │       ├── domain_errors.py
│       │       └── error_mapper.py
│       ├── agents/
│       │   ├── mcp/
│       │   │   ├── transport.py
│       │   │   ├── message_schema.py
│       │   │   └── registry.py
│       │   ├── llm/
│       │   │   ├── provider.py
│       │   │   ├── prompts/
│       │   │   └── auto_fix_loop.py
│       │   └── policies/
│       │       └── iteration_limits.py
│       ├── integrations/
│       │   ├── freqtrade/
│       │   │   ├── adapter.py
│       │   │   ├── user_data_gateway.py
│       │   │   └── protections.py
│       │   ├── ig/
│       │   │   ├── adapter.py
│       │   │   ├── rate_limit_guard.py
│       │   │   └── order_gateway.py
│       │   └── notifications/
│       │       ├── telegram.py
│       │       └── email.py
│       ├── database/
│       │   ├── engine.py
│       │   ├── models/
│       │   │   ├── strategy.py
│       │   │   ├── backtest.py
│       │   │   ├── deployment.py
│       │   │   ├── order.py
│       │   │   ├── risk_event.py
│       │   │   ├── agent_run.py
│       │   │   └── secret_metadata.py
│       │   ├── repositories/
│       │   │   ├── strategy_repo.py
│       │   │   ├── order_repo.py
│       │   │   └── audit_repo.py
│       │   └── migrations/
│       │       ├── env.py
│       │       └── versions/
│       ├── security/
│       │   ├── crypto_service.py
│       │   ├── secrets_store.py
│       │   ├── auth_service.py
│       │   └── password_hasher.py
│       └── shared/
│           ├── config_loader.py
│           ├── clock.py
│           └── logger.py
├── freqtrade_user_data/
│   ├── strategies/
│   ├── hyperopts/
│   └── config/
└── tests/
    ├── unit/
    │   ├── core/
    │   ├── agents/
    │   ├── integrations/
    │   └── security/
    ├── integration/
    │   ├── ig_adapter/
    │   ├── freqtrade_adapter/
    │   └── risk_guard/
    ├── e2e/
    │   ├── generate_to_backtest/
    │   └── deploy_and_killswitch/
    └── fixtures/
        ├── broker_responses/
        ├── strategy_samples/
        └── risk_scenarios/
```

### Architectural Boundaries

**API Boundaries:**
- UI hiçbir zaman IG/Freqtrade adapterlarını doğrudan çağırmaz; tüm çağrılar `core/orchestrator` üzerinden akar.
- `integrations/ig/*` sadece broker erişimi, `integrations/freqtrade/*` sadece engine erişimi sağlar.

**Component Boundaries:**
- `ui/` render + user input
- `core/` business decisions + risk gate
- `agents/` LLM/MCP orchestration
- `database/` persistence
- `security/` auth + crypto

**Service Boundaries:**
- `risk_guard` broker order yolunda zorunlu “pre-trade” kontrol noktasıdır.
- `threshold_gate` backtest sonuç eşiği geçmeden deploy akışına izin vermez.

**Data Boundaries:**
- Secret plaintext sadece en kısa yaşam süresiyle memory'de tutulur.
- Audit events append-only JSONL + repository katmanı üzerinden yazılır.

### Requirements to Structure Mapping

**Feature/FR Mapping:**
- FR1–FR4 (generate/backtest/auto-fix): `core/strategy`, `core/backtest`, `agents/llm`, `ui/pages/10_*`,`20_*`
- FR5–FR7 (live trade/kill-switch): `integrations/ig`, `core/risk`, `ui/pages/30_*`,`50_*`
- FR8–FR10 (agent logs, tasking, encrypted keys): `core/events`, `agents/mcp`, `security/*`, `database/models/secret_metadata.py`
- FR11–FR16 (profit lock, drawdown, capital & margin controls): `core/risk/*`, `integrations/ig/rate_limit_guard.py`

**Cross-Cutting Concerns:**
- Correlation ID: `core/events/correlation.py` + `shared/logger.py`
- Error taxonomy: `core/errors/domain_errors.py`
- Immutable audit trail: `database/repositories/audit_repo.py` + `var/audit/...`

### Integration Points

**Internal Communication:**
- `ui -> core/orchestrator -> core/services -> integrations/database/security`
- Agent events: `agents/* -> core/events/publisher`

**External Integrations:**
- IG Broker: `integrations/ig/adapter.py`
- Freqtrade Engine: `integrations/freqtrade/adapter.py`
- Notifications: `integrations/notifications/*`

**Data Flow:**
1. User strategy input → `ui/pages/10_generate.py`
2. LLM generate/validate → `agents/llm/*` + `core/strategy/*`
3. Backtest + threshold gate → `core/backtest/*`
4. Deploy intent → `core/risk/risk_guard.py`
5. Broker order + audit append → `integrations/ig/*` + `database/repositories/audit_repo.py`

### File Organization Patterns

**Configuration Files:**
- Runtime config `config/*.toml`
- Secrets via `.env` + encrypted local store

**Source Organization:**
- Domain-first under `core/`
- Adapter boundaries under `integrations/`

**Test Organization:**
- Unit tests close to domain area
- Integration tests per external adapter
- E2E tests for business-critical user journeys

**Asset Organization:**
- Streamlit static assets under `ui/components` and optional `assets/`

### Development Workflow Integration

**Development Server Structure:**
- Streamlit app entry: `src/senzey_bots/ui/main.py`
- Background workers initialized from `core/orchestrator/coordinator.py`

**Build Process Structure:**
- `ruff`, `mypy`, `pytest` pipeline
- migration checks via Alembic before release

**Deployment Structure:**
- Docker compose profiles (`dev`, `dry_run`, `live`)
- Audit volume mount read-only archive policy

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
Seçilen teknoloji seti (Streamlit + SQLAlchemy + Alembic + Pydantic + argon2-cffi + MCP adapter boundaries) birbirini teknik olarak destekliyor. Kararlar arasında çelişki bulunmadı.

**Pattern Consistency:**
Naming, format, communication ve process patternleri; step-04'te alınan çekirdek kararlarla hizalı. Özellikle `snake_case`, event envelope ve Risk Guard zorunlu geçiş kuralı tutarlı.

**Structure Alignment:**
Step-06'daki klasör yapısı; kararları fiziksel olarak doğru sınırlara ayırıyor (UI/Core/Agents/Integrations/Database/Security). Entegrasyon noktaları açık.

### Requirements Coverage Validation ✅

**Functional Requirements Coverage:**
FR1–FR16'nın tamamı belirli modül/sınırlarla eşlendi. Strateji üretim, backtest, live deploy, kill-switch, risk limitleri ve dry-run geçitleri kapsanıyor.

**Non-Functional Requirements Coverage:**
- Performans: latency/timeout hedefleri için orchestrator + rate/risk guards tanımlı.
- Güvenlik: Argon2 hash + AES-256 at-rest + secrets lifecycle kuralları mevcut.
- Güvenilirlik: retry/reconnect, immutable audit, correlation id ve hata sınıfları tanımlı.
- Uyum: kişisel kullanım + broker sınırlarına uyum mimari seviyede ele alındı.

### Implementation Readiness Validation ✅

**Decision Completeness:**
Kritik kararlar sürüm doğrulamalarıyla birlikte belgelendi.

**Structure Completeness:**
Uygulama, test, migration, runbook ve CI katmanları dahil detaylı dizin yapısı hazır.

**Pattern Completeness:**
AI ajanları arasında çakışma yaratabilecek ana alanlar için zorunlu kurallar ve anti-pattern örnekleri yazıldı.

### Gap Analysis Results

**Critical Gaps:**
- Yok (implementation blocking gap tespit edilmedi).

**Important Gaps (Post-step refinements):**
1. `crypto_service.py` içinde anahtar döndürme (key rotation) prosedürünün ADR olarak detaylandırılması.
2. `dry_run -> live` geçişinde otomatik rollback koşullarının runbook'a daha detaylı yazılması.
3. `alert routing` (Telegram/e-mail) öncelik matrisinin netleştirilmesi.

**Nice-to-Have Gaps:**
- Observability dashboard standardı (post-MVP).
- Event schema registry otomasyonu (v2).

### Validation Issues Addressed

Doğrulama sırasında kritik çelişki bulunmadı. Önemli iyileştirme alanları implementation öncesi checklist'e eklendi.

### Architecture Completeness Checklist

**✅ Requirements Analysis**
- [x] Project context analyzed
- [x] Scale/complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped

**✅ Architectural Decisions**
- [x] Critical decisions documented with versions
- [x] Integration patterns defined
- [x] Security/performance constraints mapped

**✅ Implementation Patterns**
- [x] Naming/structure/communication/process patterns defined
- [x] Enforcement and anti-pattern guidance included

**✅ Project Structure**
- [x] Complete directory tree defined
- [x] Component/service/data boundaries mapped
- [x] FR-to-structure mapping completed

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION

**Confidence Level:** High

**Key Strengths:**
- Güçlü sınır tanımı (core vs integrations)
- Risk Guard merkezli güvenli trade akışı
- AI ajanları için deterministik pattern seti
- Denetlenebilir (immutable) audit tasarımı

**Areas for Future Enhancement:**
- Key rotation automation
- Alert escalation matrix
- Post-MVP distributed event infrastructure

### Implementation Handoff

**AI Agent Guidelines:**
- Bu dokümandaki karar ve patternleri birebir takip et
- `freqtrade` ve `trading-ig` core dosyalarını değiştirme
- Tüm kritik akışlarda `correlation_id` taşı
- Risk Guard bypass etme

**First Implementation Priority:**
1. `uv` ile proje bootstrap
2. DB models + Alembic migration baseline
3. Risk Guard ve secrets katmanı
4. MCP orchestration contractları
