#!/usr/bin/env python3
"""SessionEnd: report the outcome of every recall made during this issue.
Credit assignment is deliberately conservative -- on a self-reported
success, every memory this issue's recalls returned is marked used; on
anything else, none are (the engine's own 'retrieved but unused' penalty
applies instead, per reinforcement_service). No attempt is made to guess
which specific memory helped.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import _client as c  # noqa: E402

OUTCOME_MAP = {"implemented": "success", "not_implemented": "failure"}


def _read_status() -> str:
    directory = c.state_dir()
    if not directory:
        return "unknown"
    path = os.path.join(directory, "status")
    if not os.path.isfile(path):
        return "unknown"
    with open(path, encoding="utf-8") as f:
        return f.read().strip() or "unknown"


def main() -> None:
    c.read_stdin_json()  # SessionEnd only carries `reason`; no outcome signal.
    outcome = OUTCOME_MAP.get(_read_status(), "neutral")

    for retrieval_id in c.read_stashed_retrieval_ids():
        log = c.get_retrieval(retrieval_id)
        if log is None:
            continue
        returned_ids = log.get("returned_memory_ids", [])
        used = returned_ids if outcome == "success" else []
        c.report_outcome(retrieval_id, outcome, used)

    c.emit_empty()


if __name__ == "__main__":
    main()
