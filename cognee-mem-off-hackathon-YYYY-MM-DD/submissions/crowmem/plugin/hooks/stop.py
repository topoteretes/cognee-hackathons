#!/usr/bin/env python3
"""Stop: the only point in the hook lifecycle that sees the agent's own
self-report. SessionEnd carries no outcome signal at all (just a `reason`
per the confirmed hook schema), so this stashes the STATUS line for
SessionEnd to pick up -- a best-effort proxy for the private grader's
verdict, not the verdict itself. See memoff/memory.yml's `notes`.
"""

import os
import re
import sys
import hashlib

sys.path.insert(0, os.path.dirname(__file__))
import _client as c  # noqa: E402

STATUS_RE = re.compile(r"STATUS:\s*(implemented|not_implemented)", re.IGNORECASE)


def main() -> None:
    stdin = c.read_stdin_json()
    message = stdin.get("last_assistant_message", "") or ""
    match = STATUS_RE.search(message)
    status = match.group(1).lower() if match else "unknown"

    directory = c.state_dir()
    if directory:
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, "status"), "w", encoding="utf-8") as f:
            f.write(status)

    # The agent can use Bash for every successful edit, leaving PostToolUse
    # with nothing selected to send. Record its final summary once per issue
    # so the next issue has a memory candidate. This is explicitly an agent
    # self-report, not the private grader's verdict.
    if isinstance(message, str) and message.strip():
        summary = message.strip()[:2400]
        marker = hashlib.sha256(summary.encode("utf-8")).hexdigest()
        marker_path = os.path.join(directory, "summary_hash") if directory else None
        previous = ""
        if marker_path and os.path.isfile(marker_path):
            with open(marker_path, encoding="utf-8") as f:
                previous = f.read().strip()
        if previous != marker:
            title = ""
            if directory:
                title_path = os.path.join(directory, "issue_title")
                if os.path.isfile(title_path):
                    with open(title_path, encoding="utf-8") as f:
                        title = f.read().strip()
            content = f"Agent self-report for {c.issue_task()} ({title}):\n{summary}"
            result = c.remember_event(
                content=content,
                event_type="code_change" if status == "implemented" else "observation",
                project=c.store_name(),
                metadata={"tool": "Stop", "task": c.issue_task(), "memory_only": True, "self_reported": True},
            )
            if marker_path and result is not None:
                with open(marker_path, "w", encoding="utf-8") as f:
                    f.write(marker)

    c.emit_empty()


if __name__ == "__main__":
    main()
