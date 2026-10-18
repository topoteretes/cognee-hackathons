#!/usr/bin/env python3
"""PostToolUse: record useful code changes and explicit tool failures.

Routine reads and successful shell commands repeat information the agent
already has. Sending all of them through synchronous extraction made the
agent wait and produced noisy memories from transient test output.
"""

import difflib
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import _client as c  # noqa: E402

EDIT_TOOLS = {"edit", "multiedit", "write", "notebookedit", "applypatch"}


def _clip(value: object, limit: int) -> str:
    text = value if isinstance(value, str) else str(value)
    return text[:limit]


def _file_name(tool_input: dict) -> str:
    path = tool_input.get("file_path") or tool_input.get("path") or ""
    if not isinstance(path, str):
        return ""
    workspace = os.environ.get("MEMOFF_WORKSPACE")
    if workspace and path:
        try:
            relative = os.path.relpath(path, workspace)
            if relative != ".." and not relative.startswith(".." + os.sep):
                return relative.replace("\\", "/")
        except ValueError:  # different Windows drive
            pass
    return path.replace("\\", "/")[-300:]


def _explicit_error(stdin: dict, response: object) -> bool:
    if stdin.get("is_error") is True:
        return True
    if isinstance(response, dict):
        if response.get("is_error") is True or response.get("isError") is True or response.get("success") is False:
            return True
        for key in ("exit_code", "exitCode"):
            code = response.get(key)
            if isinstance(code, int) and code != 0:
                return True
        return bool(response.get("error"))
    if isinstance(response, str):
        return response.lstrip().lower().startswith(("error:", "failed:", "exit code "))
    return False


def _change_text(tool_input: dict) -> str:
    edits = tool_input.get("edits")
    if isinstance(edits, list):
        return _clip("\n".join(_change_text(edit) for edit in edits if isinstance(edit, dict)), 1600)
    before = tool_input.get("old_string", tool_input.get("oldString", ""))
    after = tool_input.get("new_string", tool_input.get("newString", tool_input.get("content", tool_input.get("new_source", ""))))
    if isinstance(before, str) and isinstance(after, str) and before and after:
        diff = list(difflib.unified_diff(before.splitlines(), after.splitlines(), n=0, lineterm=""))[2:]
        sections: list[list[str]] = []
        section: list[str] = []
        for line in diff:
            if line.startswith("@@"):
                if len(section) > 1:
                    sections.append(section)
                section = [line]
            elif line.startswith(("+", "-")) and line[1:].strip():
                section.append(line)
        if len(section) > 1:
            sections.append(section)
        return _clip("\n".join(line for part in sections for line in part), 1600)
    if after:
        return _clip(after, 1600)
    return _clip(tool_input.get("patch", ""), 1600)


def build_event(stdin: dict) -> tuple[str, str, dict] | None:
    tool_name = str(stdin.get("tool_name", ""))
    tool_input = stdin.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return None
    response = stdin.get("tool_response", stdin.get("tool_result", {})) or {}
    file_name = _file_name(tool_input)
    metadata = {"tool": tool_name, "memory_only": True}
    if file_name:
        metadata["file"] = file_name

    if _explicit_error(stdin, response):
        # Keep the actual diagnostic, not the whole read/edit payload. A
        # keyword appearing inside source code is not evidence of failure.
        if isinstance(response, dict):
            diagnostic = response.get("error") or response.get("stderr") or response.get("stdout") or response
        else:
            diagnostic = response
        command = tool_input.get("command", "")
        content = f"{tool_name} failed for {file_name or _clip(command, 300)}: {_clip(diagnostic, 1400)}"
        return content, "tool_error", metadata

    if tool_name.lower() not in EDIT_TOOLS:
        return None

    change = _change_text(tool_input)
    if not change:
        return None
    return f"Code change in {file_name or 'workspace'}:\n{change}", "code_change", metadata


def main() -> None:
    stdin = c.read_stdin_json()
    event = build_event(stdin)
    if event is not None:
        content, event_type, metadata = event
        c.remember_event(content=content, event_type=event_type, project=c.store_name(), metadata=metadata)
    c.emit_empty()


if __name__ == "__main__":
    main()
