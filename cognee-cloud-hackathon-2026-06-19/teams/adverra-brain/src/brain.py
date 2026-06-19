"""Company Brain — a thin wrapper around Cognee implementing Karpathy's LLM Wiki.

Three layers (Karpathy):
  - raw/        : immutable source of truth (we read, never mutate)
  - the wiki    : Cognee's knowledge graph (LLM-owned, compiled knowledge)
  - the schema  : my_skills/ + the Ingest / Query+Improve / Lint operations

The same Cognee instance backs both memory tiers:
  - session memory  -> calls passing session_id=...   (fast, per-conversation)
  - permanent graph -> calls without session_id        (durable, cross-session)

By default everything runs locally. Set COGNEE_CLOUD_URL + COGNEE_API_KEY to
target a managed Cognee Cloud instance instead.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import cognee  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw"
SKILLS_DIR = ROOT / "my_skills"

DATASET = "company-brain"


async def connect_cloud_if_configured() -> bool:
    """Point Cognee at the managed Cloud instance if creds are present.

    Returns True if connected to Cloud, False if running locally.
    """
    url = os.getenv("COGNEE_CLOUD_URL", "").strip()
    api_key = os.getenv("COGNEE_API_KEY", "").strip()
    if url and api_key:
        await cognee.serve(url=url, api_key=api_key)
        print(f"[brain] connected to Cognee Cloud: {url}")
        return True
    print("[brain] running locally (no COGNEE_CLOUD_URL / COGNEE_API_KEY set)")
    return False


def result_items(result):
    """Read `.items` defensively — served backend may return a dict."""
    if result is None:
        return []
    if isinstance(result, dict):
        return result.get("items", [])
    return getattr(result, "items", []) or []
