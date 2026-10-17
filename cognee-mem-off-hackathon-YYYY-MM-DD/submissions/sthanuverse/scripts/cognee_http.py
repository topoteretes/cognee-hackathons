"""Stdlib-only HTTP client for this arm's cognee-service.

Shared by wait.sh / wipe.sh / wipe_check.sh (via the small driver scripts
next to this file). The UserPromptSubmit hook does NOT import this module:
plugin/hooks/recall.py carries its own self-contained copy of the same
calls, deliberately, so the one thing that touches the live agent loop has
no dependency outside plugin/ (same "no agent-loop exposure" invariant our
production harness's analyzeMemory.ts enforces by being the only importer
of its own client).
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request

STATE_DIR = os.path.join(os.path.expanduser("~"), ".memoff-cognee")
DEFAULT_SERVICE_URL = "http://127.0.0.1:8057"


def service_url():
    url = os.environ.get("COGNEE_SERVICE_URL")
    if url:
        return url
    try:
        with open(os.path.join(STATE_DIR, "service_url")) as f:
            return f.read().strip()
    except OSError:
        return DEFAULT_SERVICE_URL


def memory_store():
    store = os.environ.get("MEMOFF_MEMORY_STORE")
    if store:
        return store
    try:
        with open(os.path.join(STATE_DIR, "memory_store")) as f:
            return f.read().strip()
    except OSError:
        return None


def _json_request(method, path, payload=None, timeout=30):
    url = service_url() + path
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        return json.loads(body) if body else {}


def remember(dataset_name, raw_data, timeout=180):
    """Write straight to the permanent dataset graph, no session_id.

    /api/v1/remember takes form fields, not JSON (it also accepts file
    uploads) -- see cognee/api/v1/remember/routers/get_remember_router.py.
    Starlette's Form() parsing accepts application/x-www-form-urlencoded as
    well as multipart, so a plain urlencoded POST is enough here; no
    multipart encoder needed for pure text fields.

    run_in_background=False makes this call block until cognify finishes,
    so there is nothing left to poll afterwards -- see remember_diff.py.
    """
    url = service_url() + "/api/v1/remember"
    form = urllib.parse.urlencode({
        "datasetName": dataset_name,
        "raw_data": raw_data,
        "run_in_background": "false",
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=form, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        return json.loads(body) if body else {}


def recall(query, datasets, top_k=5, timeout=20):
    """only_context=True: retrieval only, no LLM completion call and
    nothing written to a session -- see RecallPayloadDTO's docstring."""
    return _json_request("POST", "/api/v1/recall", {
        "query": query,
        "datasets": datasets,
        "top_k": top_k,
        "only_context": True,
    }, timeout=timeout)


def forget_dataset(dataset_name, timeout=30):
    return _json_request("POST", "/api/v1/forget", {
        "dataset": dataset_name,
    }, timeout=timeout)


def list_datasets(timeout=20):
    url = service_url() + "/api/v1/datasets"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())
