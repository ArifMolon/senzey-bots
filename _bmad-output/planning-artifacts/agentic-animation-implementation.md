# Agentic Flow Animation Implementation Guide

This guide translates the approved dashboard concept into implementable UI behavior for a Streamlit-based interface.

## Design Tokens

Use these as CSS variables in Streamlit custom styles:

- `--background`: `#020204`
- `--surface`: `#101218`
- `--surface-2`: `#161A23`
- `--foreground`: `#FAFAFB`
- `--muted-foreground`: `#9A9DA1`
- `--border`: `#50545A`
- `--border-soft`: `#828084`
- `--accent-active`: `#E53935`
- `--accent-info`: `#3AA8FF`
- `--accent-success`: `#4CAF50`
- `--accent-warning`: `#FFB020`

## Agent State Model

Each node should map to one of these states:

- `waiting`: muted look, no glow
- `active`: red accent, glow + pulse
- `done`: green accent, soft glow
- `error`: amber/red accent, stronger pulse

Example state payload:

```json
{
  "input": "done",
  "codegen": "active",
  "freqtrade": "waiting",
  "backtest": "waiting",
  "analysis": "waiting"
}
```

## CSS: Node + Connector Animations

```css
:root {
  --background: #020204;
  --surface: #101218;
  --surface2: #161A23;
  --fg: #FAFAFB;
  --muted: #9A9DA1;
  --border: #50545A;
  --active: #E53935;
  --success: #4CAF50;
  --info: #3AA8FF;
  --warn: #FFB020;
}

.agent-node {
  border: 1px solid var(--border);
  color: var(--fg);
  background: var(--surface2);
  border-radius: 999px;
  transition: all 220ms ease;
}

.agent-node.waiting {
  border-color: #828084;
  box-shadow: none;
  opacity: 0.92;
}

.agent-node.active {
  border: 2px solid var(--active);
  box-shadow:
    0 0 8px rgba(229, 57, 53, 0.45),
    0 0 24px rgba(229, 57, 53, 0.35);
  animation: pulse 1.6s ease-in-out infinite;
}

.agent-node.done {
  border: 2px solid var(--success);
  box-shadow: 0 0 14px rgba(76, 175, 80, 0.35);
}

.agent-node.error {
  border: 2px solid var(--warn);
  box-shadow: 0 0 22px rgba(255, 176, 32, 0.45);
  animation: pulse-fast 0.9s ease-in-out infinite;
}

.connector {
  stroke: #828084;
  stroke-width: 2;
}

.connector.active {
  stroke: var(--active);
  stroke-dasharray: 10 8;
  animation: flow 1.2s linear infinite;
}

.connector.done {
  stroke: var(--success);
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.03); }
}

@keyframes pulse-fast {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.04); opacity: 0.86; }
}

@keyframes flow {
  from { stroke-dashoffset: 0; }
  to { stroke-dashoffset: -36; }
}
```

## Streamlit Integration Pattern

Use a small state machine and rerender the flow section only.

```python
import streamlit as st
import time

if "flow_state" not in st.session_state:
    st.session_state.flow_state = "state_01"

states = [
    {"input": "active", "codegen": "waiting", "freqtrade": "waiting", "backtest": "waiting", "analysis": "waiting"},
    {"input": "done", "codegen": "active", "freqtrade": "waiting", "backtest": "waiting", "analysis": "waiting"},
    {"input": "done", "codegen": "done", "freqtrade": "done", "backtest": "done", "analysis": "active"},
]

placeholder = st.empty()
for s in states:
    with placeholder.container():
        st.write("Render node classes from state:", s)
    time.sleep(1.2)
```

## Recommended Motion Timing

- Node glow fade-in: `180-260ms`
- Active pulse cycle: `1.4-1.8s`
- Connector flow cycle: `1.0-1.4s`
- State handoff delay: `350-500ms`
- Error pulse: `700-950ms`

## UI Consistency Rules

- Only one `active` node at a time.
- `done` nodes stay green until a full reset.
- Never animate all nodes simultaneously.
- Use muted text (`#9A9DA1`) for helper copy, and white (`#FAFAFB`) for primary labels.
