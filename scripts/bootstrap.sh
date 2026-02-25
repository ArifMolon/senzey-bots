#!/usr/bin/env bash
# bootstrap.sh — Bootstrap the senzey-bots development environment
# TODO: Implement full bootstrap sequence (Story 1.1 stub)
set -euo pipefail

echo "Bootstrapping senzey-bots..."
uv sync
echo "Bootstrap complete."
