#!/usr/bin/env python3
"""Driver for receipt.sh. Prints the remember/recall receipts for this
issue, found via cognee_http.issue_state_dir -- the one place that knows
how to locate the hook's real per-issue directory even when
MEMOFF_STATE_DIR itself was never passed to this script."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import cognee_http  # noqa: E402


def load(path):
    try:
        with open(path) as f:
            return json.load(f)
    except OSError:
        return None


def main():
    issue = os.environ.get("MEMOFF_ISSUE", "unknown")
    state_dir = cognee_http.issue_state_dir(issue)
    remember = load(os.path.join(state_dir, "remember_receipt.json"))
    recall = load(os.path.join(state_dir, "recall_receipt.json"))
    print(json.dumps({"remember": remember, "recall": recall}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
