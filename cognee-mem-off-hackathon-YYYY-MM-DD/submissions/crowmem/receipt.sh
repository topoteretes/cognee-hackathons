#!/bin/sh
# Prints a JSON injection receipt for the last session (Best Recall Story
# evidence): ids, ranks, reasons -- no bodies. Optional per the contract.
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/_common.sh"

export CROWMEM_BASE_URL

PYTHON_BIN="$CROWMEM_VENV/bin/python"
[ -x "$PYTHON_BIN" ] || PYTHON_BIN="$(command -v python3)"

"$PYTHON_BIN" "$SCRIPT_DIR/_receipt.py"
