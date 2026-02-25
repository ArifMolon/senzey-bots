# Wireframe Specification — trading-ig

**Author:** Senzey  
**Date:** 2026-02-25  
**Source Inputs:** `architecture.md`, `prd.md`

## 1) App Information Architecture

- 10_generate (Strategy Generate)
- 20_backtest (Backtest + Auto-fix Loop)
- 30_deploy (Dry-run / Live Deploy)
- 40_monitor (PnL, Risk, Orders, Agent Logs)
- 50_emergency (Kill-Switch + Recovery)

Primary navigation pattern: **left sidebar + top status strip + main content panel**.

## 2) Shared Layout Shell (All Screens)

```
+---------------------------------------------------------------+
| TOP STRIP: env | broker status | freqtrade status | latency   |
+---------------------+-----------------------------------------+
| SIDEBAR NAV         | MAIN CONTENT                            |
| - Generate          |                                         |
| - Backtest          |                                         |
| - Deploy            |                                         |
| - Monitor           |                                         |
| - Emergency         |                                         |
|                     |                                         |
+---------------------+-----------------------------------------+
| FOOTER: correlation_id | audit stream indicator | version      |
+---------------------------------------------------------------+
```

## 3) Screen Wireframes

### A. 10_generate

Purpose: Strategy prompt/code input, generation, validation preview.

```
+---------------------------------------------------------------+
| Strategy Input (textarea / code editor)                      |
| [Template Selector] [Risk Preset] [Generate Strategy]        |
+---------------------------------------------------------------+
| Generation Output (read-only code preview)                   |
| Validation Panel: syntax | constraints | warnings             |
+---------------------------------------------------------------+
| Actions: [Save Draft] [Send to Backtest]                     |
+---------------------------------------------------------------+
```

### B. 20_backtest

Purpose: Backtest run, threshold gate (Sharpe/DD), auto-fix iterations.

```
+---------------------------------------------------------------+
| Backtest Config: pair | timeframe | timerange | fees          |
| [Run Backtest] [Auto-fix Toggle]                             |
+---------------------------------------------------------------+
| Metrics Cards: Sharpe | MaxDD | Winrate | Net Profit         |
| Equity Curve (chart)                                          |
+---------------------------------------------------------------+
| Agent Iteration Log (max 3) + Error Classification            |
+---------------------------------------------------------------+
| Gate Result: PASS/FAIL  |  Actions: [Re-run] [Promote to Deploy] |
+---------------------------------------------------------------+
```

### C. 30_deploy

Purpose: Dry-run/live rollout with strict risk + margin checks.

```
+---------------------------------------------------------------+
| Deploy Mode: ( ) dry_run  ( ) live                            |
| Pre-Deploy Checklist: thresholds | capital | margin | API caps |
+---------------------------------------------------------------+
| Risk Guard Preview:                                          |
| - max drawdown policy                                        |
| - profit lock policy                                         |
| - order/min + req/min limits                                 |
+---------------------------------------------------------------+
| Actions: [Start Dry Run] [Promote to Live] [Abort]           |
+---------------------------------------------------------------+
```

### D. 40_monitor

Purpose: Real-time observability for orders, risk events, and agents.

```
+---------------------------------------------------------------+
| KPI: Equity | Open PnL | Closed PnL | Margin Usage | DD       |
+---------------------------------------------------------------+
| Left: Order Table              | Right: Risk & Alerts         |
| - order id, symbol, side, qty  | - threshold warnings          |
| - status, sl/tp, correlation   | - reconnect / API events      |
+---------------------------------------------------------------+
| Agent Timeline + Immutable Audit Feed (append-only)          |
+---------------------------------------------------------------+
```

### E. 50_emergency

Purpose: Fast kill-switch and controlled recovery.

```
+---------------------------------------------------------------+
| CRITICAL ACTIONS                                               |
| [KILL-SWITCH - CLOSE ALL]  [STOP NEW ORDERS]                  |
+---------------------------------------------------------------+
| Incident Context: reason | timestamp | operator               |
| Recovery Checklist: broker sync | exposure check | restart     |
+---------------------------------------------------------------+
| Actions: [Generate Incident Report] [Enter Recovery Mode]     |
+---------------------------------------------------------------+
```

## 4) Interaction Rules (Wireframe Level)

- Every critical action shows `correlation_id` and writes audit event.
- Deploy actions are disabled until backtest gate = PASS.
- Live mode requires explicit confirmation dialog + risk summary.
- Kill-Switch is globally accessible from top strip and emergency page.

## 5) Accessibility Baseline

- Keyboard navigable sidebar/actions.
- Color + icon redundancy for risk states (not color-only).
- Minimum contrast target equivalent to WCAG AA.

## 6) Handoff to UI Implementation

Implementation targets inferred from architecture:

- `src/senzey_bots/ui/main.py` (shell)
- `src/senzey_bots/ui/pages/10_generate.py`
- `src/senzey_bots/ui/pages/20_backtest.py`
- `src/senzey_bots/ui/pages/30_deploy.py`
- `src/senzey_bots/ui/pages/40_monitor.py`
- `src/senzey_bots/ui/pages/50_emergency.py`

This wireframe spec is low-fidelity and ready for component-level UI task breakdown.
