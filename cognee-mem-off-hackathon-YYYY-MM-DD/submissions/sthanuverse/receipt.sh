#!/bin/sh
# Prints the JSON receipts for the last issue: what wait.sh wrote when it
# remembered the diff, and what the UserPromptSubmit hook recorded when it
# recalled for this issue's prompt (if it ran). No bodies -- ids, counts,
# reasons only, per the entrant contract.
set -eu
STATE_DIR="${MEMOFF_STATE_DIR:-$HOME/.memoff-cognee}"
REMEMBER="$STATE_DIR/remember_receipt.json"
RECALL="$STATE_DIR/recall_receipt.json"

python3 - "$REMEMBER" "$RECALL" <<'PY'
import json
import sys

remember_path, recall_path = sys.argv[1], sys.argv[2]


def load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except OSError:
        return None


print(json.dumps({"remember": load(remember_path), "recall": load(recall_path)}))
PY
