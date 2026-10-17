#!/usr/bin/env python3
"""Driver for usage.sh. Rough usage ESTIMATE from the remember receipt's
character count (chars / 4 as a token proxy) -- cognee's REST API has no
public per-call usage endpoint we could find. Found via the same
cognee_http.issue_state_dir resolution receipt.sh uses."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import cognee_http  # noqa: E402


def main():
    issue = os.environ.get("MEMOFF_ISSUE", "unknown")
    state_dir = cognee_http.issue_state_dir(issue)
    try:
        with open(os.path.join(state_dir, "remember_receipt.json")) as f:
            receipt = json.load(f)
    except OSError:
        receipt = {}

    chars = receipt.get("chars_written", 0)
    est_tokens = max(1, chars // 4)

    print(json.dumps([{
        "id": f"cognee-diffmem:{receipt.get('issue', issue)}",
        "source": "server",
        "tokens_in": est_tokens,
        "tokens_out": 0,
        "cost_usd": None,
        "token_basis": "estimate_chars_div_4_not_measured",
        "cost_basis": "unmeasured",
    }]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
