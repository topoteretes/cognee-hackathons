#!/usr/bin/env python3
"""Driver for wait.sh: computes this issue's diff and writes it to the
shared dataset. No session_id is used (see cognee_http.remember) -- direct
dataset writes make the call itself block until cognify finishes, so there
is nothing left to poll for afterwards.

Unlike the UserPromptSubmit hook (plugin/hooks/recall.py), this script does
NOT fail open: wait.sh is a harness-invoked script, not something touching
a live agent turn, and the contract expects a non-zero exit when post-
session processing genuinely did not complete.
"""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
import cognee_http  # noqa: E402

MAX_DIFF_CHARS = 20000


def git_diff(workspace):
    # Issues are committed one at a time by the sequencer, so HEAD~1..HEAD
    # is normally the right range. If this is the very first commit in the
    # workspace (no parent) or nothing was committed (verify failed before
    # commit), fall back to the working-tree diff so we still remember
    # whatever changed.
    for rev_range in (["HEAD~1", "HEAD"], []):
        try:
            stat_out = subprocess.run(
                ["git", "-C", workspace, "diff", "--stat", *rev_range],
                capture_output=True, text=True, timeout=30,
            )
            full_out = subprocess.run(
                ["git", "-C", workspace, "diff", *rev_range],
                capture_output=True, text=True, timeout=30,
            )
            stat, full = stat_out.stdout.strip(), full_out.stdout.strip()
            if stat or full:
                return stat, full
        except Exception:
            continue
    return "", ""


def main():
    workspace = os.environ.get("MEMOFF_WORKSPACE")
    issue = os.environ.get("MEMOFF_ISSUE", "unknown")
    state_dir = os.environ.get("MEMOFF_STATE_DIR", cognee_http.STATE_DIR)
    timeout_s = float(os.environ.get("MEMOFF_WAIT_SECONDS", "600"))

    store = cognee_http.memory_store()
    if not workspace or not store:
        print(
            "remember_diff: MEMOFF_WORKSPACE or the memory store name is "
            "unavailable -- cannot remember this issue",
            file=sys.stderr,
        )
        return 1

    stat, full = git_diff(workspace)
    if not stat and not full:
        print(f"remember_diff: no diff found for issue {issue}, nothing to remember")
        return 0

    text = f"Issue {issue}:\n{stat}\n\n{full}"[:MAX_DIFF_CHARS]

    started = time.time()
    try:
        result = cognee_http.remember(store, text, timeout=timeout_s)
    except Exception as exc:
        print(f"remember_diff: remember() failed for issue {issue}: {exc}", file=sys.stderr)
        return 1
    elapsed = time.time() - started

    receipt = {
        "issue": issue,
        "dataset": store,
        "chars_written": len(text),
        "elapsed_s": round(elapsed, 2),
        "remember_status": result.get("status"),
    }
    try:
        with open(os.path.join(state_dir, "remember_receipt.json"), "w") as f:
            json.dump(receipt, f)
    except OSError:
        pass

    print(
        f"remember_diff: wrote {len(text)} chars for issue {issue} in "
        f"{elapsed:.1f}s (status={result.get('status')})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
