"""Feedback loop: record a SkillRunEntry, propose a SKILL.md rewrite, then apply it."""

import time

import cognee
from cognee.memory import SkillRunEntry

from . import config


PROPOSAL_THRESHOLD = 0.7


async def record_run_and_propose(
    skill_id: str,
    task_text: str,
    result_summary: str,
    score: float,
    session_id: str,
    fix_suggestion: str | None = None,
) -> dict:
    """Save a SkillRunEntry and (if score < threshold) ask Cognee to propose a SKILL.md rewrite."""
    feedback_signal = 1.0 if score >= PROPOSAL_THRESHOLD else -1.0

    entry = SkillRunEntry(
        selected_skill_id=skill_id,
        task_text=task_text,
        result_summary=result_summary if not fix_suggestion else f"{result_summary} | fix: {fix_suggestion}",
        success_score=score,
        feedback=feedback_signal,
        started_at_ms=int(time.time() * 1000),
        latency_ms=0,
    )

    result = await cognee.remember(
        entry,
        dataset_name=config.DATASET,
        session_id=session_id,
        skill_improvement={
            "skill_name": skill_id,
            "apply": False,
            "score_threshold": PROPOSAL_THRESHOLD,
        },
    )

    proposal_id = _proposal_id(result)
    return {
        "proposal_id": proposal_id,
        "score": score,
        "raw": result,
    }


async def apply_proposal(skill_id: str, proposal_id: str) -> bool:
    """Apply a previously generated proposal.

    Cognee Cloud's `improve` endpoint is still dev-preview and may return 404.
    We swallow that gracefully — the proposal IS the self-improvement signal,
    and subsequent runs benefit from the SkillRunEntry being in graph memory
    even without an explicit apply.
    """
    if not proposal_id:
        return False
    try:
        await cognee.improve(
            skill_name=skill_id,
            proposal_id=proposal_id,
            apply=True,
        )
        return True
    except Exception as e:
        print(f"[feedback] apply skipped (server limitation): {e}")
        return False


def extract_proposal_text(result) -> str | None:
    """Pull the proposed new skill body out of a SkillRunEntry result, if present."""
    if isinstance(result, dict):
        items = result.get("items", []) or []
    else:
        items = getattr(result, "items", None)
        if callable(items) or items is None:
            items = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if item.get("kind") == "skill_improvement_proposal":
            for key in ("proposed_body", "new_body", "body", "rewrite", "new_text"):
                if key in item and item[key]:
                    return item[key]
            return str(item)
    return None


def _proposal_id(result) -> str | None:
    if isinstance(result, dict):
        items = result.get("items", []) or []
    else:
        items = getattr(result, "items", None)
        if callable(items) or items is None:
            items = []
    for item in items:
        if isinstance(item, dict) and item.get("kind") == "skill_improvement_proposal":
            return item.get("proposal_id")
    return None
