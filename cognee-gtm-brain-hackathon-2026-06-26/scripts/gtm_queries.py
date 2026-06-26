#!/usr/bin/env python3
"""Demo recall queries over the unified GTM brain.

Run after ``scripts/run_gtm_ingest.py``. Each query deliberately spans
more than one source — a good answer can only come from the *merged*
graph (a deal CSV + a calendar invite + a meeting transcript + an email
thread + an account deep-dive all about the same Company).

    python scripts/gtm_queries.py
"""

from __future__ import annotations

import asyncio

from gtm_brain.env import load_project_env

QUERIES = [
    # account ↔ deal ↔ meeting ↔ email ↔ deep-dive (all "Clay")
    "What is the status of the Clay sponsorship and what did Bruno want instead of a booth?",
    # speaker recruiting ↔ do-not-approach constraint ↔ transcript
    "Can we pitch Pavilion a sponsorship, and what did Sam Jacobs agree to?",
    # Warsaw debrief ↔ past sponsors ↔ renewal deals
    "Which Warsaw 2026 sponsors should we renew for London, and why?",
    # calendar ↔ account ↔ person
    "What meetings are on the calendar in the next 24h and which accounts are they about?",
    # ICP ↔ scoring ↔ signals
    "Who is the highest-fit sponsor prospect and what 'why now' signal supports approaching them?",
]


async def _run() -> None:
    from gtm_brain.cognee_client import connect, recall

    await connect()
    for q in QUERIES:
        print("\n" + "=" * 80)
        print("Q:", q)
        print("-" * 80)
        try:
            results = await recall(q, top_k=5)
        except Exception as exc:  # pragma: no cover - demo convenience
            print(f"[recall error: {type(exc).__name__}: {exc}]")
            continue
        for r in results:
            print("•", r if isinstance(r, str) else str(r)[:500])


def main() -> None:
    load_project_env()
    asyncio.run(_run())


if __name__ == "__main__":
    main()
