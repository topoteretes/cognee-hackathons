#!/usr/bin/env python3
"""Mem Off lifecycle commands for the pinned Mem0 Claude Code plugin."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "plugin" / "adapters"))

from common import configure_mem0_environment, data_dir, upstream_plugin_root

ACTIVE_STATUSES = {"prepared", "semantic-queued"}
SUCCESS_STATUSES = {"semantic-succeeded", "explicitly-stored", "nothing-to-flush"}
FAILURE_STATUSES = {
    "error",
    "gave-up",
    "semantic-failed",
    "semantic-missing",
    "semantic-timeout",
}


def is_smoke() -> bool:
    return os.environ.get("MEMOFF_SMOKE") == "1"


def require_live_key() -> None:
    if not os.environ.get("MEM0_API_KEY") and not is_smoke():
        raise RuntimeError("MEM0_API_KEY is required for a live Mem Off run")


def load_upstream():
    configure_mem0_environment()
    upstream = upstream_plugin_root()
    core = upstream / "core"
    if not (core / "memory_core.py").is_file():
        raise RuntimeError(f"run install.sh first; Mem0 runtime missing at {upstream}")
    sys.path.insert(0, str(core))
    import memory_core

    memory_core.configure_harness(
        "claude-code", data_dir_name="mem0-memoff", source_tag="mem0_memoff_plugin"
    )
    return memory_core


def workspace() -> Path:
    value = os.environ.get("MEMOFF_WORKSPACE")
    if not value:
        raise RuntimeError("MEMOFF_WORKSPACE is required")
    return Path(value).resolve()


def local_counts(db_path: Path) -> dict[str, int]:
    if not db_path.is_file():
        return {"events": 0, "flushes": 0, "retrievals": 0}
    connection = sqlite3.connect(db_path)
    try:
        counts = {}
        for table in ("events", "flushes", "retrievals"):
            try:
                counts[table] = int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            except sqlite3.Error:
                counts[table] = 0
        return counts
    finally:
        connection.close()


def remote_ids(memory_core) -> list[str]:
    key = memory_core.api_key()
    if not key:
        return []
    repo = memory_core.resolve_repo(str(workspace()))
    url = os.environ.get("MEM0_API_URL", memory_core.DEFAULT_API_URL).rstrip("/")
    return memory_core._scoped_memory_ids(
        url,
        key,
        memory_core.user_id(),
        repo,
        True,
    )


def do_wipe() -> int:
    configure_mem0_environment()
    require_live_key()
    if not is_smoke():
        memory_core = load_upstream()
        repo = memory_core.resolve_repo(str(workspace()))
        result = memory_core.forget_remote_repo(repo, include_project_memory=True)
        if result.get("status") in {"error", "partial"}:
            print(json.dumps(result), file=sys.stderr)
            return 1
        print(json.dumps({"remote": result}, sort_keys=True))
    shutil.rmtree(data_dir(), ignore_errors=True)
    return 0


def do_wipe_check() -> int:
    configure_mem0_environment()
    counts = local_counts(data_dir() / "evidence.sqlite3")
    if any(counts.values()):
        print(json.dumps({"local_not_empty": counts}), file=sys.stderr)
        return 1
    if is_smoke():
        return 0
    require_live_key()
    ids = remote_ids(load_upstream())
    if ids:
        print(json.dumps({"remote_not_empty": len(ids)}), file=sys.stderr)
        return 1
    return 0


def flush_statuses(db_path: Path, session: str | None = None) -> list[str]:
    if not db_path.is_file():
        return []
    connection = sqlite3.connect(db_path)
    try:
        try:
            if session:
                rows = connection.execute(
                    "SELECT status FROM flushes WHERE session_id = ? ORDER BY created_at",
                    (session,),
                ).fetchall()
            else:
                rows = connection.execute("SELECT status FROM flushes ORDER BY created_at").fetchall()
        except sqlite3.Error:
            return []
        return [str(row[0]) for row in rows]
    finally:
        connection.close()


def do_wait() -> int:
    configure_mem0_environment()
    if is_smoke():
        return 0
    require_live_key()
    root = data_dir()
    session = os.environ.get("MEMOFF_SESSION_ID")
    deadline = time.monotonic() + float(os.environ.get("MEMOFF_WAIT_SECONDS", "600"))
    while time.monotonic() < deadline:
        pending = root / "pending"
        queued = list(pending.glob("*.json")) if pending.is_dir() else []
        running = list(pending.glob("*.running")) if pending.is_dir() else []
        statuses = flush_statuses(root / "evidence.sqlite3", session)
        failures = [status for status in statuses if status in FAILURE_STATUSES]
        if failures:
            print(json.dumps({"failed_flushes": failures}), file=sys.stderr)
            return 1
        active = any(status in ACTIVE_STATUSES for status in statuses)
        succeeded = any(status in SUCCESS_STATUSES for status in statuses)
        # The upstream worker writes the terminal DB status before flushing
        # telemetry. If telemetry stalls, its .running file may linger even
        # though the memory is already durable and queryable.
        if not queued and not active and (not running or succeeded):
            print(json.dumps({"status": "idle", "flushes": statuses}), flush=True)
            return 0
        time.sleep(0.25)
    print("Mem0 background extraction did not finish before MEMOFF_WAIT_SECONDS", file=sys.stderr)
    return 1


def do_receipt() -> int:
    configure_mem0_environment()
    session = os.environ.get("MEMOFF_SESSION_ID", "")
    result = {
        "session": session,
        "system": "mem0",
        "trigger": "first-prompt-search",
        "items": [],
        "recall_ms": None,
    }
    db_path = data_dir() / "evidence.sqlite3"
    if db_path.is_file() and session:
        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row
        try:
            rows = connection.execute(
                """SELECT memory_id, rank, score, context_chars
                   FROM retrievals WHERE session_id = ?
                   ORDER BY COALESCE(rank, 2147483647), injected_at, memory_id""",
                (session,),
            ).fetchall()
            result["items"] = [
                {
                    "id": row["memory_id"],
                    "rank": row["rank"],
                    "score": row["score"],
                    "context_chars": row["context_chars"],
                    "reason": "first-prompt-search",
                }
                for row in rows
            ]
            operation = connection.execute(
                """SELECT duration_ms FROM operations
                   WHERE session_id = ? AND operation = 'first-prompt-search'
                   ORDER BY id DESC LIMIT 1""",
                (session,),
            ).fetchone()
            if operation:
                result["recall_ms"] = operation["duration_ms"]
        except sqlite3.Error:
            pass
        finally:
            connection.close()
    print(json.dumps(result, sort_keys=True))
    return 0


def do_usage() -> int:
    session = os.environ.get("MEMOFF_SESSION_ID", "unknown")
    print(
        json.dumps(
            [
                {
                    "id": f"mem0-platform:{session}",
                    "source": "server",
                    "token_basis": "unmeasured: Mem0 Platform does not expose per-event model or embedding tokens",
                    "cost_basis": "unmeasured: Mem0 Platform does not expose per-event extraction cost",
                }
            ]
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("wipe", "wipe-check", "wait", "receipt", "usage"))
    args = parser.parse_args()
    actions = {
        "wipe": do_wipe,
        "wipe-check": do_wipe_check,
        "wait": do_wait,
        "receipt": do_receipt,
        "usage": do_usage,
    }
    try:
        return actions[args.action]()
    except Exception as exc:
        print(f"mem0_control: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
