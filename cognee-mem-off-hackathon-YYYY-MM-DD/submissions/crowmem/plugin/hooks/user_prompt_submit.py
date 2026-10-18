#!/usr/bin/env python3
"""UserPromptSubmit: the real goal-conditioned recall, keyed off the actual
issue text rather than SessionStart's empty priming query."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import _client as c  # noqa: E402


def main() -> None:
    stdin = c.read_stdin_json()
    user_input = stdin.get("prompt", stdin.get("user_input", ""))
    store = c.store_name()

    # Keep the public issue title for the end-of-issue observation. Claude
    # sometimes makes every edit through Bash, so PostToolUse may have no
    # selected code-change event to remember.
    directory = c.state_dir()
    if directory and isinstance(user_input, str):
        title = next((line.strip().lstrip("# ").strip() for line in user_input.splitlines() if line.strip()), "")
        if title:
            os.makedirs(directory, exist_ok=True)
            with open(os.path.join(directory, "issue_title"), "w", encoding="utf-8") as f:
                f.write(title[:200])

    result = c.recall(query=user_input, project=store, task=c.issue_task())
    if not result:
        c.emit_empty()
        return

    working_memory = result.get("working_memory", [])
    c.write_injected_context(working_memory)
    retrieval_id = result.get("retrieval_id")
    if retrieval_id:
        c.stash_retrieval_id(retrieval_id)
        c.append_seen_retrieval_id(retrieval_id)

    context = c.format_context(working_memory)
    if context:
        c.emit_additional_context("UserPromptSubmit", context)
    else:
        c.emit_empty()


if __name__ == "__main__":
    main()
