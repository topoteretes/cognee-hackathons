#!/usr/bin/env bash
# One-command setup for the Personal Memory / Life Assistant tutorial.
# Usage:  bash setup.sh
set -euo pipefail

cd "$(dirname "$0")"   # folder root

if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found. Install it first: https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi

echo "==> Creating virtualenv (.venv) and installing the tutorial deps"
uv venv
uv pip install -e ".[tutorial]"

echo
echo "!!  Set your LLM key before running, e.g.:"
echo "      export LLM_API_KEY=sk-...   (an OpenAI key works)"
echo
echo "==> Done. Launch the notebook with:"
echo "      source .venv/bin/activate && jupyter lab tutorial/personal_memory_life_assistant.ipynb"
echo
echo "    To also run the dlt-based ingestion template:"
echo "      uv pip install -e \".[personal-assistant]\""
