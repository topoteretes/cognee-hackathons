"""Cognee integration for CogneeMind — the judged "Company Brain" layer.

Design: the structured optimization loop always runs on the LocalWiki mirror
(fast, reliable, demo-safe). This module mirrors every result into Cognee and
runs the self-improvement loop the hackathon scores:

  * Ingest  — rules -> permanent graph; skills -> graph via content_type="skills"
  * Session memory — raw discovery trials written with session_id=...
  * Distill — winning strategy promoted to the permanent graph (no session_id)
  * Self-improve — SkillRunEntry (apply=False) proposes a researcher-skill
                   rewrite; improve_skill(apply=True) applies it.

Everything is wrapped so that a missing cognee install or missing LLM key
degrades gracefully to "local only" without breaking the demo.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

HERE = Path(__file__).parent

# Load a local .env (LLM_API_KEY etc.) so the brain auto-enables when present.
_ENV = HERE / ".env"
if _ENV.exists():
    for _line in _ENV.read_text().splitlines():
        if "=" in _line and not _line.strip().startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())
SKILLS_DIR = str(HERE / "my_skills")
RULES_PATH = HERE / "data" / "rules.md"
DATASET = "cogneemind"

# Penalty baseline for mapping our (lower=better) score into SkillRunEntry's
# 0..1 success_score (higher=better). A stranded flight (~1000) -> ~0.
PENALTY_BASELINE = 1000.0


def cognee_available() -> bool:
    try:
        import cognee  # noqa: F401
        return bool(os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
                    or os.environ.get("COGNEE_CLOUD_URL"))
    except Exception:
        return False


def success_score(penalty: float) -> float:
    return max(0.0, min(1.0, 1.0 - penalty / PENALTY_BASELINE))


class CogneeBrain:
    """Async wrapper around cognee. Constructed once at startup; methods no-op
    (returning a status string) if cognee is unavailable."""

    def __init__(self):
        self.enabled = cognee_available()
        self.skill_names: list[str] = []
        self.ready = False

    async def setup(self) -> str:
        if not self.enabled:
            return "cognee disabled (no package or LLM key) — running local-only"
        import cognee
        from cognee.modules.engine.operations.setup import setup as cognee_setup

        await cognee.prune.prune_data()
        await cognee.prune.prune_system(metadata=True)
        await cognee_setup()

        # Ingest the rulebook into the permanent graph.
        await cognee.remember(RULES_PATH.read_text(), dataset_name=DATASET)

        # Ingest the agent skills.
        remembered = await cognee.remember(SKILLS_DIR, dataset_name=DATASET, content_type="skills")
        items = getattr(remembered, "items", None) or remembered.get("items", [])
        self.skill_names = [it["name"] for it in items if it.get("kind") == "skill"]
        self.ready = True
        return f"cognee ready — ingested rulebook + {len(self.skill_names)} skills"

    async def recall_priors(self, signature: str) -> Optional[str]:
        """Narrative warm-start from the permanent graph — returns a short,
        human-readable sentence (just the answer text, no metadata blob)."""
        if not (self.enabled and self.ready):
            return None
        import cognee
        try:
            res = await cognee.recall(f"best gate strategy for disruption {signature}")
            if not res:
                return None
            answers: list[str] = []
            for r in res[:3]:
                # Cognee Recall items expose `.raw["value"]` (string answer).
                # Fall back to `.text` / str(r) if the shape is different.
                raw = getattr(r, "raw", None)
                if isinstance(raw, dict) and raw.get("value"):
                    answers.append(str(raw["value"]).strip())
                    continue
                txt = getattr(r, "text", None)
                if isinstance(txt, str) and txt.strip():
                    answers.append(txt.strip())
                    continue
                answers.append(str(r).strip())
            answers = [a for a in answers if a]
            return " ".join(answers) if answers else None
        except Exception as e:
            return f"(recall error: {type(e).__name__})"

    async def remember_trial(self, signature: str, strategy_name: str, score: float, session_id: str):
        """Raw trial -> session memory (the per-run scratchpad tier)."""
        if not (self.enabled and self.ready):
            return
        import cognee
        try:
            await cognee.remember(
                f"Tried strategy '{strategy_name}' for {signature}: penalty score {score}.",
                dataset_name=DATASET, session_id=session_id,
            )
        except Exception:
            pass

    async def distill(self, signature: str, strategy: dict, score: float) -> str:
        """Promote the winning strategy to the permanent graph (no session_id)."""
        if not (self.enabled and self.ready):
            return "local-only"
        import cognee
        text = (f"Winning gate-assignment strategy for disruption '{signature}': "
                f"priority rule '{strategy['priority_key']}' with weights "
                f"{strategy.get('soft_weights')} achieved penalty score {score}. "
                f"Prefer this strategy when this disruption recurs.")
        try:
            await cognee.remember(text, dataset_name=DATASET)
            return "distilled to permanent graph"
        except Exception as e:
            return f"(distill error: {e})"

    async def self_improve(self, signature: str, strategy: dict, score_breakdown: dict,
                           session_id: str) -> dict:
        """The judged loop: SkillRunEntry (propose) -> improve_skill (apply)."""
        if not (self.enabled and self.ready and self.skill_names):
            return {"applied": False, "reason": "local-only"}
        import cognee
        from cognee.memory import SkillRunEntry

        penalty = score_breakdown["total"]
        succ = success_score(penalty)
        researcher = next((s for s in self.skill_names if "research" in s.lower()), self.skill_names[0])
        try:
            proposal_result = await cognee.remember(
                SkillRunEntry(
                    selected_skill_id=researcher,
                    task_text=f"Choose a gate strategy for {signature}",
                    result_summary=(f"Strategy {strategy['priority_key']} scored {penalty} "
                                    f"(U={score_breakdown['U']} C={score_breakdown['C']})."),
                    success_score=succ,
                    feedback=-1.0 if succ < 0.7 else 1.0,
                ),
                dataset_name=DATASET, session_id=session_id,
                skill_improvement={"skill_name": researcher, "apply": False, "score_threshold": 0.9},
            )
            items = getattr(proposal_result, "items", None) or (
                proposal_result.get("items", []) if isinstance(proposal_result, dict) else [])
            proposal_id = next((it.get("proposal_id") for it in items
                                if it.get("kind") == "skill_improvement_proposal"), None)
            if proposal_id is None:
                return {"applied": False, "reason": "no proposal (score above threshold)"}

            # improve_skill is internal and needs the Dataset object (not a name).
            from cognee.modules.memify.skill_improvement import improve_skill
            from cognee.modules.pipelines.layers.resolve_authorized_user_datasets import (
                resolve_authorized_user_datasets,
            )
            user, datasets = await resolve_authorized_user_datasets(DATASET, None)
            await improve_skill(researcher, dataset=datasets[0], user=user,
                                proposal_id=proposal_id, apply=True)
            return {"applied": True, "skill": researcher, "proposal_id": str(proposal_id),
                    "success_score": round(succ, 3)}
        except Exception as e:
            return {"applied": False, "reason": f"cognee error: {e}"}


# Singleton used by the API.
brain = CogneeBrain()
