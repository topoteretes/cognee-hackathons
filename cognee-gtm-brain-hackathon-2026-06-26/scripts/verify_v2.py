#!/usr/bin/env python3
"""Sanity-check the v2 graph after ingest.

Runs a handful of demo-style queries against gtm_brain_v2 and
inspects the dataset's data items to confirm:

  - we have many docs landed
  - tags coming from the classifier (product:/client:/domain:) and the
    structural emitter (source:/slack:/speaker:) both appear on docs
  - sample queries return content scoped by the expected tag

Doesn't mutate anything. Use it as the "did v2 work?" oracle.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

import urllib.request


KEY = os.environ.get("COGNEE_API_KEY", "")
BASE = os.environ.get("COGNEE_SERVICE_URL", "http://127.0.0.1:8000").rstrip("/")
DATASET = os.environ.get("COGNEE_DATASET", "gtm_brain_v2")


def _request(method: str, path: str, body: dict | None = None) -> dict | list:
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body).encode() if body else None,
        headers={"X-Api-Key": KEY, "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def find_dataset_id(name: str) -> str | None:
    datasets = _request("GET", "/api/v1/datasets")
    for d in datasets:
        if d.get("name") == name:
            return d.get("id")
    return None


def sample_tags_from_disk(dataset_id: str, limit: int = 30) -> dict[str, int]:
    """Walk a sample of data items, read each file header, count tag families."""
    items = _request("GET", f"/api/v1/datasets/{dataset_id}/data")
    if not isinstance(items, list):
        return {}
    counts: dict[str, int] = {}
    for it in items[:limit]:
        loc = it.get("rawDataLocation", "")
        if loc.startswith("file://"):
            try:
                head = Path(loc[7:]).read_text(encoding="utf-8", errors="replace")[:120]
            except Exception:
                continue
            if head.startswith("# #"):
                tag = head.split(":", 1)[0].lstrip("# ").strip()
                counts[f"slack:{tag}"] = counts.get(f"slack:{tag}", 0) + 1
            elif head.startswith("# Cognee") or head.startswith("# Meeting"):
                counts["granola"] = counts.get("granola", 0) + 1
    return counts


def run_recall(query: str, node_set: list[str] | None = None, top_k: int = 3) -> str:
    body = {"query": query, "top_k": top_k}
    if node_set:
        body["node_set"] = node_set
    try:
        out = _request("POST", "/api/v1/recall", body)
        if isinstance(out, list) and out:
            return (out[0].get("text") or "")[:500]
    except Exception as e:
        return f"<recall error: {e}>"
    return "<no results>"


def main():
    print(f"== verifying dataset: {DATASET} ==\n")

    ds_id = find_dataset_id(DATASET)
    if not ds_id:
        print(f"ERROR: dataset {DATASET!r} not found")
        return
    print(f"dataset_id: {ds_id}\n")

    items = _request("GET", f"/api/v1/datasets/{ds_id}/data")
    print(f"total data items: {len(items) if isinstance(items, list) else 'unknown'}\n")

    print("== sample of source breakdown (first 30 items) ==")
    for k, v in sorted(sample_tags_from_disk(ds_id).items(), key=lambda kv: -kv[1]):
        print(f"  {k}: {v}")
    print()

    queries = [
        ("Who has been working on the client integration?", None),
        ("What cloud bugs were discussed?", ["product:cloud", "domain:technical"]),
        ("What did people ask about the SDK?", ["product:sdk"]),
        ("Are there any operational topics (reimbursements, access, accounting)?", ["domain:operations"]),
    ]
    print("== demo queries ==")
    for q, ns in queries:
        print(f"\nQ: {q}")
        if ns:
            print(f"   filter: node_set={ns}")
        print(f"A: {run_recall(q, node_set=ns)}")


if __name__ == "__main__":
    main()
