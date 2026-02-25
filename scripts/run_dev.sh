#!/usr/bin/env bash
# run_dev.sh — Start the senzey-bots Streamlit development server
# TODO: Expand with environment setup (Story 1.1 stub)
set -euo pipefail

uv run streamlit run src/senzey_bots/ui/main.py
