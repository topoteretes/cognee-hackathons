#!/usr/bin/env python3
"""SessionStart: prime context before the agent sees the issue text.
A thin wrapper around /recall -- see memoff/README.md for what's verified
about the hook stdin/stdout contract this relies on."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import _client as c  # noqa: E402


def main() -> None:
    c.read_stdin_json()  # SessionStart's fields (source, model, ...) aren't needed here.
    store = c.store_name()

    result = c.recall(query="", project=store, task=c.issue_task())
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
        c.emit_additional_context("SessionStart", context)
    else:
        c.emit_empty()


if __name__ == "__main__":
    main()
