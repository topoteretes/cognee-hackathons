#!/bin/sh
# Rough usage ESTIMATE from request/response character counts (chars / 4 as
# a token proxy) -- cognee's REST API has no public per-call usage endpoint
# we could find. Better partial accounting than reporting nothing; the
# numbers are explicitly NOT real token counts (see memory.yml's notes and
# SUBMISSION.md's known-gaps entry).
set -eu
STATE_DIR="${MEMOFF_STATE_DIR:-$HOME/.memoff-cognee}"
REMEMBER="$STATE_DIR/remember_receipt.json"

python3 - "$REMEMBER" <<'PY'
import json
import sys

path = sys.argv[1]
try:
    with open(path) as f:
        receipt = json.load(f)
except OSError:
    receipt = {}

chars = receipt.get("chars_written", 0)
est_tokens = max(1, chars // 4)

print(json.dumps([{
    "id": f"cognee-diffmem:{receipt.get('issue', 'unknown')}",
    "source": "server",
    "tokens_in": est_tokens,
    "tokens_out": 0,
    "cost_usd": None,
    "token_basis": "estimate_chars_div_4_not_measured",
    "cost_basis": "unmeasured",
}]))
PY
