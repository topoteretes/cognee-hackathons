"""Helper for receipt.sh. stdlib only -- runs with any python3, not just
the engine's venv.

Prints the Best-Recall-Story evidence: for the most relevant retrieval this
issue, which memories were injected, their rank, and why -- ids and reasons
only, never memory content (CONTRACT.md: "no bodies").
"""

import json
import os
import sys
import urllib.request

BASE_URL = os.environ.get("CROWMEM_BASE_URL", "http://127.0.0.1:8765")
STORE = os.environ.get("MEMOFF_MEMORY_STORE", "manual-test")
STATE_DIR = os.environ.get("MEMOFF_STATE_DIR", "")


def _get(path: str) -> dict | list:
    with urllib.request.urlopen(f"{BASE_URL}{path}", timeout=30) as resp:
        return json.load(resp)


def _stashed_retrieval_id() -> str | None:
    if not STATE_DIR:
        return None
    path = os.path.join(STATE_DIR, "retrieval_id")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        return f.read().strip() or None


def main() -> None:
    retrieval_id = _stashed_retrieval_id()
    if retrieval_id:
        log = _get(f"/recall/{retrieval_id}")
    else:
        recent = _get(f"/recall?project_id={STORE}&limit=1")
        if not recent:
            print(json.dumps([]))
            return
        log = recent[0]

    ranked_ids = log["returned_memory_ids"]
    reasons_by_id = log["scores_and_reasons"]

    receipt = [
        {
            "id": memory_id,
            "rank": rank + 1,
            "reasons": reasons_by_id.get(memory_id, {}).get("reasons", []),
        }
        for rank, memory_id in enumerate(ranked_ids)
    ]
    print(json.dumps(receipt))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 -- receipt.sh is optional evidence, never fatal
        print(f"[crowmem] receipt helper failed: {exc}", file=sys.stderr)
        print(json.dumps([]))
