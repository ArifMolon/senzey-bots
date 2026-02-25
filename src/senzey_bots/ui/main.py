"""Streamlit multipage app entry point.

Run: streamlit run src/senzey_bots/ui/main.py
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="senzey-bots",
    page_icon="🤖",
    layout="wide",
)

generate_page = st.Page(
    "pages/10_generate.py",
    title="Generate",
    icon="⚙️",
    default=True,
)

pg = st.navigation([generate_page])

st.sidebar.title("senzey-bots")

pg.run()
