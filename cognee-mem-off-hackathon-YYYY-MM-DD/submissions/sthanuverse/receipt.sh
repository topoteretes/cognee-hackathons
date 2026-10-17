#!/bin/sh
# Prints the JSON receipts for the last issue: what wait.sh wrote when it
# remembered the diff, and what the UserPromptSubmit hook recorded when it
# recalled for this issue's prompt (if it ran). No bodies -- ids, counts,
# reasons only, per the entrant contract.
#
# The actual directory lookup lives in scripts/cognee_http.py's
# issue_state_dir(), not here: a real harness run (2026-10-17) showed
# MEMOFF_STATE_DIR never reaches this script at all (only the hook, inside
# the claude subprocess, gets it), so the lookup has to reconstruct the
# hook's real per-issue directory from MEMOFF_INJECTED_DIR instead --
# logic worth keeping in one place rather than duplicated in shell.
set -eu
DIR="$(dirname "$0")"
python3 "$DIR/scripts/print_receipt.py"
