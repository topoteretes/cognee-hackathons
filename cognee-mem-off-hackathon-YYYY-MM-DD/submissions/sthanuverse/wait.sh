#!/bin/sh
# Blocks until this issue's diff has been written into the shared dataset's
# knowledge graph. There is no session cache to poll afterwards: remember()
# (called with no session_id -- see scripts/cognee_http.py) already blocks
# on cognify when run_in_background=false, so "wait" here just *is* that
# one blocking call. Non-zero exit on failure or timeout, per the contract.
set -eu
DIR="$(dirname "$0")"
python3 "$DIR/scripts/remember_diff.py"
