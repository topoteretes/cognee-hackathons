#!/usr/bin/env python3
"""Run the pinned Mem0 Claude Code hook and audit every injected context string."""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys

from common import audit_injected_context, configure_mem0_environment, upstream_plugin_root


def forwarded_hook_input(raw_input: str) -> str:
    """Replace Claude's ephemeral id with the trial id used by Mem Off receipts."""
    try:
        hook_input = json.loads(raw_input)
        memoff_session = os.environ.get("MEMOFF_SESSION_ID")
        if isinstance(hook_input, dict) and memoff_session:
            hook_input["session_id"] = memoff_session
        return json.dumps(hook_input)
    except (json.JSONDecodeError, TypeError):
        return raw_input


def main() -> int:
    configure_mem0_environment()

    # Claude generates its own session id, while Mem Off assigns the stable id
    # used by receipts. Feed the latter to Mem0 so capture and retrieval rows
    # can be joined to the harness trial without changing the upstream core.
    forwarded_input = forwarded_hook_input(sys.stdin.read())

    upstream = upstream_plugin_root()
    core = upstream / "core"
    claude_adapter = upstream / "adapters" / "claude"
    if not (core / "memory_core.py").is_file():
        print(f"mem0-memoff: upstream runtime missing at {upstream}", file=sys.stderr)
        return 0

    sys.path.insert(0, str(core))
    sys.path.insert(0, str(claude_adapter))

    import hook_runner
    import telemetry
    from memory_core import configure_harness, record_tool
    from transcript import record_stop

    configure_harness(
        "claude-code",
        data_dir_name="mem0-memoff",
        source_tag="mem0_memoff_plugin",
    )
    telemetry.init(harness="claude-code", source_tag="MEM0_MEMOFF_PLUGIN")

    captured = io.StringIO()
    original_stdin = sys.stdin
    try:
        sys.stdin = io.StringIO(forwarded_input)
        with contextlib.redirect_stdout(captured):
            status = hook_runner.run(
                record_stop_fn=record_stop,
                extra_actions={
                    "post-tool-failure": lambda store, payload: record_tool(
                        store, payload, failed=True
                    )
                },
                data_dir_env="MEM0_CODE_DATA_DIR",
                automatic_flush_reasons={"session-end", "pre-compact"},
            )
    except Exception as exc:
        print(f"mem0-memoff hook failed open: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 0
    finally:
        sys.stdin = original_stdin

    output = captured.getvalue()
    audit_injected_context(output)
    if output:
        sys.stdout.write(output)
    return int(status or 0)


if __name__ == "__main__":
    raise SystemExit(main())
