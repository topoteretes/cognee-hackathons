#!/usr/bin/env bash
# One-command setup for the Intro to Cognee tutorial.
# Usage:  bash tutorial/setup.sh
set -euo pipefail

cd "$(dirname "$0")/.."   # repo root

if ! command -v uv >/dev/null 2>&1; then
  echo "uv not found. Install it first: https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi

echo "==> Creating virtualenv (.venv) and installing the tutorial deps"
uv venv
uv pip install -e ".[tutorial]"

if [ ! -f .env ]; then
  echo "==> Creating .env from .env.example"
  cp .env.example .env
fi

if grep -q "^LLM_API_KEY=sk-\.\.\.$" .env 2>/dev/null || ! grep -q "^LLM_API_KEY=" .env; then
  echo
  echo "!!  Set your LLM key in .env before running:"
  echo "      LLM_API_KEY=sk-...   (an OpenAI key works)"
fi

echo
echo "==> Done. Launch the notebook with:"
echo "      source .venv/bin/activate && jupyter lab tutorial/intro_to_cognee.ipynb"
echo "    (or open tutorial/intro_to_cognee.ipynb in Cursor and pick the .venv kernel)"
