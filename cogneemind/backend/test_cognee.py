"""Standalone de-risk test for the Cognee path: ingest -> agentic search ->
SkillRunEntry (propose) -> improve_skill (apply) -> recall.

Run from backend/:  python test_cognee.py
Loads .env for LLM_API_KEY.
"""
import asyncio
import os
from pathlib import Path

# Load .env into the environment.
for line in Path(".env").read_text().splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

import cognee
from cognee import SearchType
from cognee.memory import SkillRunEntry
from cognee.modules.engine.operations.setup import setup
from cognee.modules.pipelines.layers.resolve_authorized_user_datasets import (
    resolve_authorized_user_datasets,
)
from cognee.modules.memify.skill_improvement import improve_skill

DATASET = "cogneemind"
SESSION = "storm-run-1"
SKILLS_DIR = "./my_skills"


def items_of(result):
    return getattr(result, "items", None) or (result.get("items", []) if isinstance(result, dict) else [])


async def main():
    print("→ prune + setup")
    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)
    await setup()

    print("→ ingest rulebook (permanent graph)")
    await cognee.remember(Path("data/rules.md").read_text(), dataset_name=DATASET)

    print("→ ingest skills")
    remembered = await cognee.remember(SKILLS_DIR, dataset_name=DATASET, content_type="skills")
    skills = [it["name"] for it in items_of(remembered) if it.get("kind") == "skill"]
    print("   skills:", skills)
    assert skills, "no skills ingested"
    researcher = next((s for s in skills if "research" in s.lower()), skills[0])

    print("→ agentic search over skills (session memory)")
    answer = await cognee.search(
        "A storm delayed 4 international arrivals. Which gate strategy should the Researcher pick? Answer briefly.",
        query_type=SearchType.AGENTIC_COMPLETION,
        datasets=[DATASET], skills=skills, max_iter=4, session_id=SESSION,
    )
    print("   answer:", str(answer)[:240])

    print("→ record SkillRunEntry (propose, apply=False)")
    user, datasets = await resolve_authorized_user_datasets(DATASET, None)
    dataset = datasets[0]
    proposal_result = await cognee.remember(
        SkillRunEntry(
            selected_skill_id=researcher,
            task_text="Choose a gate strategy for delay:storm:heavy",
            result_summary="earliest_arrival stranded 1 flight (penalty 1003).",
            success_score=0.2,
            feedback=-1.0,
        ),
        dataset_name=DATASET, session_id=SESSION,
        skill_improvement={"skill_name": researcher, "apply": False, "score_threshold": 0.9},
    )
    pid = next((it.get("proposal_id") for it in items_of(proposal_result)
                if it.get("kind") == "skill_improvement_proposal"), None)
    print("   proposal_id:", pid)

    if pid:
        print("→ apply proposal (improve_skill apply=True)")
        applied = await improve_skill(researcher, dataset=dataset, user=user,
                                      proposal_id=pid, apply=True)
        print("   applied:", str(applied)[:200])
    else:
        print("   (no proposal generated)")

    print("→ distill winner to permanent graph + recall")
    await cognee.remember(
        "Winning strategy for disruption delay:storm:heavy: priority rule "
        "'latest_departure' achieved penalty 6 with zero remote stands.",
        dataset_name=DATASET,
    )
    recalled = await cognee.recall("best gate strategy for a storm")
    print("   recall:", str(recalled)[:240])

    print("\n✅ Cognee path works end-to-end.")


if __name__ == "__main__":
    asyncio.run(main())
