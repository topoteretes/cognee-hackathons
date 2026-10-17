#!/bin/sh
# Rough usage ESTIMATE from request/response character counts (chars / 4 as
# a token proxy) -- cognee's REST API has no public per-call usage endpoint
# we could find. Better partial accounting than reporting nothing; the
# numbers are explicitly NOT real token counts (see memory.yml's notes and
# SUBMISSION.md's known-gaps entry).
#
# Same directory-lookup reasoning as receipt.sh: the logic lives in
# scripts/cognee_http.py's issue_state_dir(), not duplicated here.
set -eu
DIR="$(dirname "$0")"
python3 "$DIR/scripts/print_usage.py"
