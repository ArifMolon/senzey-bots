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
        placeholder="e.g., Buy when RSI(14) < 30 and price above SMA(200)\nSell when RSI(14) > 70",
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
        placeholder="//@version=5\nstrategy('My Strategy', ...)",
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
            file_content: str | None = None
            try:
                file_content = uploaded_file.read().decode("utf-8")
            except UnicodeDecodeError:
                st.error("File is not valid UTF-8 text. Please upload a plain-text .py file.")
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
                        sid = strategy.id
                        sname = strategy.name
                        st.success(f"Strategy '{sname}' saved as draft (ID: {sid}).")

# --- Existing Drafts Section ---
st.divider()
st.subheader("Existing Strategy Drafts")

with get_session() as session:
    strategies = list_strategies(session)
    # Extract display data INSIDE session scope to avoid DetachedInstanceError
    # Use tuples (id, name, input_type, status, created_str) for clean typing
    draft_rows: list[tuple[int, str, str, str, str]] = [
        (s.id, s.name, s.input_type, s.status, f"{s.created_at:%Y-%m-%d %H:%M}")
        for s in strategies
    ]

if not draft_rows:
    st.info("No strategy drafts yet. Create one above.")
else:
    for strategy_id, s_name, s_input_type, s_status, s_created in draft_rows:
        col_info, col_actions = st.columns([4, 1])
        with col_info:
            st.markdown(
                f"**{s_name}** — `{s_input_type}` | Status: `{s_status}` | "
                f"Created: {s_created}"
            )
        with col_actions:
            if st.button("Delete", key=f"delete_{strategy_id}"):
                with get_session() as del_session:
                    delete_strategy(del_session, strategy_id)
                st.rerun()
