#!/usr/bin/env python3
"""UserPromptSubmit hook: the only part of this arm that touches the live
agent loop. Deliberately self-contained (no import of ../../scripts/
cognee_http.py) -- see that module's docstring for why.

Reads the new issue's prompt from stdin, recalls from the shared dataset,
and injects the result as additionalContext. Fails open on any error: a
down or slow cognee-service must never block the benchmark run -- on
failure this issue just runs with the same behaviour a no-memory arm
would have.
"""
import json
import os
import sys
import urllib.request

MAX_INJECT_CHARS = 8000  # stays under Claude Code's ~10,000-char hook-output stub cutoff
DEFAULT_SERVICE_URL = "http://127.0.0.1:8057"
STATE_DIR = os.path.join(os.path.expanduser("~"), ".memoff-cognee")


def _service_url():
    url = os.environ.get("COGNEE_SERVICE_URL")
    if url:
        return url
    try:
        with open(os.path.join(STATE_DIR, "service_url")) as f:
            return f.read().strip()
    except OSError:
        return DEFAULT_SERVICE_URL


def _memory_store():
    store = os.environ.get("MEMOFF_MEMORY_STORE")
    if store:
        return store
    try:
        with open(os.path.join(STATE_DIR, "memory_store")) as f:
            return f.read().strip()
    except OSError:
        return None


def _recall(query, dataset, timeout_s):
    # only_context=True: retrieval only, no extra LLM completion call and
    # nothing written to a session -- see RecallPayloadDTO's docstring in
    # cognee's own recall router.
    url = _service_url() + "/api/v1/recall"
    payload = json.dumps({
        "query": query,
        "datasets": [dataset],
        "top_k": 5,
        "only_context": True,
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        body = resp.read()
        return json.loads(body) if body else []


def _write(path, text):
    try:
        with open(path, "w") as f:
            f.write(text)
    except OSError:
        pass


def _issue_state_dir(issue):
    # Same resolution as scripts/cognee_http.py.issue_state_dir -- kept as
    # its own copy here deliberately (see this file's module docstring).
    # MEMOFF_STATE_DIR reaches this hook subprocess reliably in the harness
    # we tested against (confirmed), but a different runner might not set it
    # for the hook either -- MEMOFF_INJECTED_DIR is the one value every
    # script, including this hook, is guaranteed to get, so it is the
    # fallback anchor rather than inventing an unrelated directory.
    state_dir = os.environ.get("MEMOFF_STATE_DIR")
    if state_dir:
        return state_dir

    injected_dir = os.environ.get("MEMOFF_INJECTED_DIR")
    if injected_dir:
        root = os.path.dirname(os.path.dirname(injected_dir))  # .../<arm>/r<rep>
        fallback = os.path.join(root, "state", _issue_tag(issue))
    else:
        fallback = os.path.join(STATE_DIR, _issue_tag(issue))
    try:
        os.makedirs(fallback, exist_ok=True)
    except OSError:
        pass
    return fallback


def _issue_tag(issue):
    try:
        return f"issue-{int(issue):02d}"
    except (TypeError, ValueError):
        return f"issue-{issue}"


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # malformed stdin: never block the prompt over this

    prompt = payload.get("prompt", "")
    if not prompt:
        return 0

    dataset = _memory_store()
    if not dataset:
        return 0  # no store configured yet (e.g. issue 1, nothing written)

    try:
        timeout_s = float(os.environ.get("MEMOFF_RECALL_TIMEOUT_S", "20"))
        results = _recall(prompt, dataset, timeout_s)
    except Exception as exc:
        print(f"recall.py: recall failed, continuing without memory: {exc}", file=sys.stderr)
        return 0

    if not results:
        return 0

    chunks = [item.get("text") or item.get("context") or "" for item in results]
    chunks = [c for c in chunks if c]
    if not chunks:
        return 0

    context = "\n\n---\n\n".join(chunks)[:MAX_INJECT_CHARS]

    injected_dir = os.environ.get("MEMOFF_INJECTED_DIR")
    issue = os.environ.get("MEMOFF_ISSUE", "unknown")
    if injected_dir:
        _write(os.path.join(injected_dir, f"issue-{issue}.txt"), context)

    state_dir = _issue_state_dir(issue)
    receipt = {
        "issue": issue,
        "dataset": dataset,
        "items_recalled": len(results),
        "chars_injected": len(context),
    }
    _write(os.path.join(state_dir, "recall_receipt.json"), json.dumps(receipt))

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": context,
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
