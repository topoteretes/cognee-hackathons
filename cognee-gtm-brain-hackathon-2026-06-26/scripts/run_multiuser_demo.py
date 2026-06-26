#!/usr/bin/env python3
"""Per-user isolation + sharing demo for the GTM brain.

Tells a four-act story on top of cognee's multi-user access control:

  1. INGEST   — two users each get their own isolated brain:
                  • User A (artur@gtm-week.com)  -> dataset "gtm_brain_warsaw"
                  • User B (dana@devtools-day.com) -> dataset "gtm_brain_berlin"
  2. ISOLATE  — each user can only recall their own data.
  3. SHARE    — A grants B read access to the Warsaw brain.
  4. SEE      — B can now recall (and visualize) the Warsaw brain too.

Run after installing the package. Needs LLM_API_KEY (cognify + recall).

    python scripts/run_multiuser_demo.py

All cognee storage is forced INTO this project (.cognee_system / .data_storage
/ .cognee_cache, all gitignored) and wiped at start, so the demo is fully
isolated and reproducible — it never touches any other cognee install.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent

# --- isolate storage BEFORE importing cognee (env wins over defaults) -------
for _d in (".cognee_system", ".data_storage", ".cognee_cache"):
    shutil.rmtree(PROJECT / _d, ignore_errors=True)
os.environ["SYSTEM_ROOT_DIRECTORY"] = str(PROJECT / ".cognee_system")
os.environ["DATA_ROOT_DIRECTORY"] = str(PROJECT / ".data_storage")
os.environ["CACHE_ROOT_DIRECTORY"] = str(PROJECT / ".cognee_cache")
os.environ["ENABLE_BACKEND_ACCESS_CONTROL"] = "true"  # multi-user mode ON

import asyncio  # noqa: E402
import logging  # noqa: E402

from gtm_brain.env import load_project_env  # noqa: E402

DATA = PROJECT / "sample_data"
OUT = PROJECT / "tutorial"

USER_A_EMAIL = "artur@gtm-week.com"
USER_B_EMAIL = "dana@devtools-day.com"
DS_A = "gtm_brain_warsaw"
DS_B = "gtm_brain_berlin"


def _short(results, n: int = 320) -> str:
    if not results:
        return "<no results>"
    r = results[0]
    for attr in ("text", "answer", "content"):
        v = getattr(r, attr, None)
        if v:
            return " ".join(str(v).split())[:n]
    return str(r)[:n]


async def _run() -> None:
    from cognee.modules.engine.operations.setup import setup

    from gtm_brain.multiuser import (
        get_or_create_user,
        ingest_brain_for_user,
        list_readable_datasets,
        recall_as,
        share_dataset,
        visualize_user_dataset,
    )

    await setup()  # create relational/vector tables in the fresh local store

    print("\n=== ACT 1 — INGEST (two isolated brains) ===")
    user_a = await get_or_create_user(USER_A_EMAIL)
    user_b = await get_or_create_user(USER_B_EMAIL)
    a = await ingest_brain_for_user(DATA / "gtm_brain", DS_A, user_a)
    b = await ingest_brain_for_user(DATA / "gtm_brain_user_b", DS_B, user_b)
    print(f"  A ({USER_A_EMAIL}): {DS_A} -> companies={a.companies} deals={a.deals} threads={a.threads} fail={a.failures}")
    print(f"  B ({USER_B_EMAIL}): {DS_B} -> companies={b.companies} deals={b.deals} threads={b.threads} fail={b.failures}")

    print("\n=== ACT 2 — ISOLATE (each user sees only their own) ===")
    print("  A can read:", await list_readable_datasets(user_a))
    print("  B can read:", await list_readable_datasets(user_b))

    q_clay = "What is the status of the Clay sponsorship and what did Bruno want?"
    q_vercel = "What did Lee Robinson from Vercel want for the Berlin event?"
    print("\n  [A asks about Clay — A owns the Warsaw brain]")
    print("   ->", _short(await recall_as(user_a, q_clay, [DS_A])))
    print("\n  [B asks the Warsaw brain about Clay BEFORE share — isolated]")
    blocked = await recall_as(user_b, q_clay, [DS_A])
    print("   ->", _short(blocked) if blocked else "<no access — isolated, empty result>")
    print("\n  [B asks about Vercel — B owns the Berlin brain]")
    print("   ->", _short(await recall_as(user_b, q_vercel, [DS_B])))

    print("\n=== ACT 3 — SHARE (A grants B read on the Warsaw brain) ===")
    await share_dataset(user_a, user_b, DS_A, permission="read")
    print("  B can now read:", await list_readable_datasets(user_b))

    print("\n=== ACT 4 — SEE (B recalls the shared Warsaw brain) ===")
    print("  [B asks about Clay AFTER share — same query, now answered]")
    print("   ->", _short(await recall_as(user_b, q_clay, [DS_A])))

    print("\n=== VISUALIZE ===")
    OUT.mkdir(exist_ok=True)

    async def _viz(coro, label):
        try:
            path = await coro
            print(f"  wrote: {Path(path).name}  ({label})")
        except Exception as exc:
            print(f"  skipped {label}: {type(exc).__name__}: {str(exc)[:120]}")

    # Each user's own brain (isolation, visually).
    await _viz(visualize_user_dataset(str(OUT / "graph_user_a_warsaw.html"), DS_A, user_a),
               "A: Warsaw brain")
    await _viz(visualize_user_dataset(str(OUT / "graph_user_b_berlin.html"), DS_B, user_b),
               "B: Berlin brain")
    # After the share, B can now render the Warsaw graph too (sharing, visually).
    await _viz(visualize_user_dataset(str(OUT / "graph_user_b_sees_warsaw.html"), DS_A, user_b),
               "B sees Warsaw AFTER share")


def main() -> None:
    load_project_env()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s — %(message)s")
    asyncio.run(_run())


if __name__ == "__main__":
    main()
