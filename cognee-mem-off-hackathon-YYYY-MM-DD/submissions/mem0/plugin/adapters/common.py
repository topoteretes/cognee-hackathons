"""Shared Mem Off scoping and audit helpers for the Mem0 wrapper plugin."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

SAFE_COMPONENT = re.compile(r"[^A-Za-z0-9_.-]+")


def submission_root() -> Path:
    return Path(__file__).resolve().parents[2]


def upstream_plugin_root() -> Path:
    override = os.environ.get("MEMOFF_MEM0_UPSTREAM")
    if override:
        return Path(override).expanduser().resolve()
    return submission_root() / ".runtime" / "mem0" / "integrations" / "claude-code-plugin"


def memory_store() -> str:
    return os.environ.get("MEMOFF_MEMORY_STORE", "memoff_unscoped").strip() or "memoff_unscoped"


def safe_store_name() -> str:
    value = SAFE_COMPONENT.sub("_", memory_store())[:120]
    if value in {"", ".", ".."}:
        digest = hashlib.sha256(memory_store().encode("utf-8")).hexdigest()[:16]
        return f"store_{digest}"
    return value


def data_dir() -> Path:
    root = Path(os.environ.get("MEMOFF_MEM0_DATA_ROOT", Path.home() / ".mem0-memoff"))
    return root.expanduser() / safe_store_name()


def configure_mem0_environment() -> None:
    """Map one Mem Off repeat onto one isolated Mem0 user/project namespace."""
    store = memory_store()
    os.environ["MEM0_PROJECT_ID"] = store
    os.environ["MEM0_USER_ID"] = store
    os.environ["MEM0_CODE_DATA_DIR"] = str(data_dir())
    os.environ.setdefault("MEM0_CODE_SEARCH_ONCE_PER_SESSION", "true")
    os.environ.setdefault("MEM0_TELEMETRY", "false")


def injected_contexts(output: str) -> list[str]:
    contexts: list[str] = []
    for line in output.splitlines():
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        hook_output = payload.get("hookSpecificOutput") if isinstance(payload, dict) else None
        context = hook_output.get("additionalContext") if isinstance(hook_output, dict) else None
        if isinstance(context, str) and context:
            contexts.append(context)
    return contexts


def audit_injected_context(output: str) -> list[Path]:
    """Copy exactly what Mem0 injected; do not add headings or metadata to the files."""
    root_value = os.environ.get("MEMOFF_INJECTED_DIR")
    if not root_value:
        return []
    root = Path(root_value)
    root.mkdir(parents=True, exist_ok=True)
    session = SAFE_COMPONENT.sub("_", os.environ.get("MEMOFF_SESSION_ID", "unknown"))
    written: list[Path] = []
    for index, context in enumerate(injected_contexts(output), start=1):
        digest = hashlib.sha256(context.encode("utf-8")).hexdigest()[:12]
        path = root / f"mem0-{session}-{index:02d}-{digest}.txt"
        path.write_text(context, encoding="utf-8")
        written.append(path)
    return written
