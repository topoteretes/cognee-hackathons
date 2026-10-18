"""Shared HTTP client + helpers for the Crowmem hook bundle. stdlib only
(urllib) -- hooks run in whatever Python Claude Code's host environment
provides, not necessarily a Python with httpx installed.

Mirrors mcp_server/client.py's role for the MCP surface, but synchronous
and minimal: hooks are short-lived, read-stdin/write-stdout processes.
"""

import json
import os
import urllib.error
import urllib.request

BASE_URL = os.environ.get("CROWMEM_BASE_URL", "http://127.0.0.1:8765")


def _request(method: str, path: str, payload: dict | None = None) -> dict | list | None:
    url = f"{BASE_URL}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read()
            return json.loads(body) if body else None
    except urllib.error.URLError:
        # The engine being unreachable must never crash the agent's turn --
        # memory is an enhancement, not a dependency of the agent working.
        return None


def recall(query: str, project: str, task: str | None = None, environment: str | None = None, active_tools=None) -> dict | None:
    goal_state = {"project": project, "task": task, "environment": environment, "active_tools": active_tools or []}
    return _request("POST", "/recall", {"query": query, "goal_state": goal_state})


def remember_event(content: str, event_type: str, project: str, metadata: dict | None = None) -> dict | None:
    return _request(
        "POST", "/events", {"content": content, "event_type": event_type, "project_id": project, "metadata": metadata or {}}
    )


def report_outcome(retrieval_id: str, outcome: str, used_memory_ids: list[str]) -> dict | None:
    return _request(
        "POST", "/outcomes", {"retrieval_id": retrieval_id, "outcome": outcome, "used_memory_ids": used_memory_ids}
    )


def get_retrieval(retrieval_id: str) -> dict | None:
    return _request("GET", f"/recall/{retrieval_id}")


def store_name() -> str:
    return os.environ.get("MEMOFF_MEMORY_STORE", "manual-test")


def issue_task() -> str:
    issue = os.environ.get("MEMOFF_ISSUE", "unknown")
    return f"issue-{issue}"


def state_dir() -> str | None:
    return os.environ.get("MEMOFF_STATE_DIR") or None


def injected_dir() -> str | None:
    return os.environ.get("MEMOFF_INJECTED_DIR") or None


def stash_retrieval_id(retrieval_id: str) -> None:
    directory = state_dir()
    if not directory:
        return
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, "retrieval_id"), "w", encoding="utf-8") as f:
        f.write(retrieval_id)


def read_stashed_retrieval_ids() -> list[str]:
    directory = state_dir()
    if not directory:
        return []
    path = os.path.join(directory, "retrieval_ids_seen")
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def append_seen_retrieval_id(retrieval_id: str) -> None:
    directory = state_dir()
    if not directory:
        return
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, "retrieval_ids_seen"), "a", encoding="utf-8") as f:
        f.write(retrieval_id + "\n")


def write_injected_context(working_memory: list[dict]) -> None:
    """One file per injection in $MEMOFF_INJECTED_DIR, per CONTRACT.md --
    the runner counts characters there. The agent only actually sees this
    content through hookSpecificOutput.additionalContext; this is purely
    the measurement side-channel."""
    directory = injected_dir()
    if not directory:
        return
    os.makedirs(directory, exist_ok=True)
    for item in working_memory:
        path = os.path.join(directory, f"{item['id']}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(item["content"])


def format_context(working_memory: list[dict]) -> str:
    if not working_memory:
        return ""
    lines = ["Prior implementation notes from memory. Verify them against the current task; newer requirements take precedence:"]
    for item in working_memory:
        lines.append(f"- {item['content']}")
    return "\n".join(lines)


def emit_additional_context(hook_event_name: str, context: str) -> None:
    output = {"hookSpecificOutput": {"hookEventName": hook_event_name, "additionalContext": context}}
    print(json.dumps(output))


def emit_empty() -> None:
    print(json.dumps({}))


def read_stdin_json() -> dict:
    import sys

    raw = sys.stdin.read()
    return json.loads(raw) if raw.strip() else {}
