"""Ingest — pull raw company knowledge into the brain (the LLM wiki).

Reads every file under raw/ and remembers it into the permanent knowledge graph
(no session_id => durable tier). Also ingests my_skills/ as skills so the agent
can be steered and self-improved later.

Run:
    python -m src.ingest          # from the project root, venv activated
"""

from __future__ import annotations

import asyncio

import cognee

from .brain import (
    DATASET,
    RAW_DIR,
    SKILLS_DIR,
    connect_cloud_if_configured,
    result_items,
)


async def ingest(fresh: bool = True) -> list[str]:
    await connect_cloud_if_configured()

    if fresh:
        # Start from a clean slate so the demo is reproducible.
        await cognee.prune.prune_data()
        await cognee.prune.prune_system(metadata=True)
        try:
            from cognee.modules.engine.operations.setup import setup

            await setup()
        except Exception as exc:  # setup is best-effort on some builds
            print(f"[ingest] setup skipped: {exc}")

    # 1. Ingest every raw source into the permanent graph (the wiki).
    raw_files = sorted(p for p in RAW_DIR.rglob("*.md") if p.is_file())
    print(f"[ingest] remembering {len(raw_files)} raw sources into '{DATASET}'...")
    for path in raw_files:
        text = path.read_text(encoding="utf-8")
        await cognee.remember(text, dataset_name=DATASET)
        print(f"   + {path.relative_to(RAW_DIR)}")

    # 2. Ingest the skills so the answerer/linter can be selected at query time.
    print(f"[ingest] remembering skills from {SKILLS_DIR} ...")
    remembered = await cognee.remember(
        str(SKILLS_DIR),
        dataset_name=DATASET,
        content_type="skills",
    )
    skill_names = [
        item["name"]
        for item in result_items(remembered)
        if item.get("kind") == "skill"
    ]
    print(f"[ingest] skills ingested: {skill_names or '(names not returned by backend)'}")

    print("[ingest] done — the wiki is built.")
    return skill_names


if __name__ == "__main__":
    asyncio.run(ingest())
