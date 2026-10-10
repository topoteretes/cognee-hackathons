"""Load the seed corpus into Cognee with the two-tier split + distillation rule.

Split:
  - Per-email raw record → session memory (session_id=prospect_xxx).
  - Cross-prospect patterns → permanent graph (no session_id),
    BUT only when a pattern fires across >=3 prospects with avg score >=0.7.

The distillation rule is what makes our brain different from "dump everything".
"""

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import cognee

from . import config


PROMOTION_MIN_PROSPECTS = 3
PROMOTION_MIN_AVG_SCORE = 0.7


async def ingest_skills() -> dict[str, str]:
    """Ingest writer + critic skills individually.

    Cognee Cloud canonicalizes skill names (e.g. 'cognee-skills-xxxx') so we
    return a role→canonical_name mapping, e.g. {'writer': 'cognee-skills-abc',
    'critic': 'cognee-skills-def'}, by uploading one SKILL.md at a time.
    """
    mapping: dict[str, str] = {}
    for role in ("writer", "critic"):
        skill_path = config.SKILLS_DIR / role / "SKILL.md"
        if not skill_path.exists():
            print(f"[ingest] WARN missing skill file: {skill_path}")
            continue
        remembered = await cognee.remember(
            str(skill_path),
            dataset_name=config.DATASET,
            content_type="skills",
        )
        items = _items(remembered)
        canonical = next((it["name"] for it in items if it.get("kind") == "skill"), role)
        mapping[role] = canonical
        print(f"[ingest] {role:6s} -> {canonical}")
    return mapping


async def ingest_corpus(seed_path: Path | None = None) -> dict[str, Any]:
    """Load real + synthetic emails. Per-email raw → session. Promoted patterns → graph."""
    path = seed_path or config.SEED_PATH
    if not path.exists():
        raise FileNotFoundError(f"Seed corpus not found at {path}. Run scripts/build_seed.py first.")

    seed = json.loads(path.read_text())

    # Phase 1: every raw email lands in its own session as ground truth.
    for item in seed:
        body = item.get("body", "")
        meta = {k: v for k, v in item.items() if k != "body"}
        text = f"OUTBOUND EMAIL\n{json.dumps(meta, ensure_ascii=False)}\n---\n{body}"
        await cognee.remember(
            text,
            dataset_name=config.DATASET,
            session_id=config.session_id_for(item["id"]),
        )

    # Phase 2: distill patterns + only promote ones that pass the rule.
    promoted = _promotable_patterns(seed)
    for pattern in promoted:
        await cognee.remember(
            f"LEARNED PATTERN: {pattern['text']}",
            dataset_name=config.DATASET,
            # No session_id -> goes into permanent graph.
        )

    return {
        "n_raw": len(seed),
        "n_patterns_promoted": len(promoted),
        "patterns": promoted,
    }


def _promotable_patterns(seed: list[dict]) -> list[dict]:
    """Aggregate observations per (hook_type, industry) and keep ones that pass the rule."""
    bucket: dict[tuple[str, str], list[float]] = defaultdict(list)
    for item in seed:
        hook = item.get("hook_type", "unknown")
        industry = item.get("industry", "unknown")
        score = float(item.get("score", 0))
        bucket[(hook, industry)].append(score)

    promoted = []
    for (hook, industry), scores in bucket.items():
        if len(scores) < PROMOTION_MIN_PROSPECTS:
            continue
        avg = sum(scores) / len(scores)
        if avg < PROMOTION_MIN_AVG_SCORE:
            continue
        promoted.append({
            "hook_type": hook,
            "industry": industry,
            "n_prospects": len(scores),
            "avg_score": round(avg, 2),
            "text": (
                f"Hook '{hook}' for {industry} prospects has scored {avg:.2f} on average "
                f"across {len(scores)} prospects. Use this pattern when targeting {industry}."
            ),
        })

    return promoted


def _items(result: Any) -> list[dict]:
    """Defensive: served remember() may return dict, local returns RememberResult."""
    if isinstance(result, dict):
        return result.get("items", []) or []
    items = getattr(result, "items", None)
    if callable(items) or items is None:
        return []
    return items
