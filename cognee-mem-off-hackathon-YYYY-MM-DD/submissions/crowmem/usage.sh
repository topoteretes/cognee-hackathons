#!/bin/sh
# Prints JSON usage records for this engine's own model/embedding spend
# since the last call. Optional per the contract, but without it spend is
# unmeasured (null), never zero.
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/_common.sh"

export CROWMEM_BASE_URL CROWMEM_HOME

PYTHON_BIN="$CROWMEM_VENV/bin/python"
[ -x "$PYTHON_BIN" ] || PYTHON_BIN="$(command -v python3)"

"$PYTHON_BIN" "$SCRIPT_DIR/_usage.py"
