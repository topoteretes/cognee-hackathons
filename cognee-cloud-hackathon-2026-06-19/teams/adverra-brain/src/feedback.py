"""Self-improvement loop — turn human feedback into a smarter brain.

This is the heart of the project. When the Slack agent escalates a question and
the responsible human responds, we:

  1. If they gave a CORRECTION (the right answer), remember it into the permanent
     graph so the wiki now knows the fact (Karpathy: "valuable answers get filed
     back as new wiki pages").
  2. Record a SkillRunEntry scoring the agent's run. A low score (thumbs down)
     proposes a rewrite of the qa-answerer skill; we then explicitly apply it.

So both tiers improve: the knowledge graph gains the missing fact, and the skill
that answers questions gets better at the task.

Run (manual test):
    python -m src.feedback
"""

from __future__ import annotations

import asyncio

import cognee

from .brain import DATASET, connect_cloud_if_configured, result_items

try:
    from cognee.memory import SkillRunEntry
except Exception:  # pragma: no cover - import path may vary across builds
    SkillRunEntry = None


async def record_correction(
    *,
    question: str,
    correct_answer: str,
    skill_name: str,
    thumbs_up: bool,
    session_id: str | None = None,
    expert: str | None = None,
) -> dict:
    """Apply human feedback to the brain.

    thumbs_up=False with a correction is the key path: the wiki learns the fact
    AND the answerer skill gets a rewrite proposal applied.
    """
    await connect_cloud_if_configured()

    out: dict = {"remembered": False, "proposal_id": None, "applied": False}

    # 1. File the corrected fact back into the permanent graph (the wiki grows).
    if correct_answer.strip():
        note = (
            f"Verified support answer.\n"
            f"Question: {question}\n"
            f"Correct answer: {correct_answer}\n"
            + (f"Verified by: {expert}\n" if expert else "")
        )
        try:
            await cognee.remember(note, dataset_name=DATASET)
            out["remembered"] = True
            print("[feedback] corrected fact remembered into the wiki.")
        except Exception as exc:
            out["error"] = str(exc)
            print(f"[feedback] FAILED to remember correction ({exc}).")
            return out

    # 2. Score the run and propose/apply a skill improvement.
    if SkillRunEntry is None:
        print("[feedback] SkillRunEntry unavailable in this build — skipping skill update.")
        return out

    score = 1.0 if thumbs_up else 0.2
    entry = SkillRunEntry(
        selected_skill_id=skill_name,
        task_text=question,
        result_summary=(
            "Answer confirmed correct by expert."
            if thumbs_up
            else "Answer was wrong/insufficient; expert supplied a correction."
        ),
        success_score=score,
        feedback=1.0 if thumbs_up else -1.0,
    )

    # Best-effort: a failure here must NOT break the correction already filed
    # into the wiki above (which is what makes the brain answer next time).
    try:
        proposal_result = await cognee.remember(
            entry,
            dataset_name=DATASET,
            session_id=session_id,
            skill_improvement={
                "skill_name": skill_name,
                "apply": False,            # propose first
                "score_threshold": 0.9,    # propose whenever the run scored < 0.9
            },
        )
    except Exception as exc:
        print(f"[feedback] skill-run logging failed ({exc}); wiki update stands.")
        return out

    proposal_id = next(
        (
            item.get("proposal_id")
            for item in result_items(proposal_result)
            if item.get("kind") == "skill_improvement_proposal"
        ),
        None,
    )
    out["proposal_id"] = proposal_id

    if proposal_id is None:
        print("[feedback] no skill proposal generated (run scored above threshold).")
        return out

    print(f"[feedback] proposal generated: {proposal_id} — applying...")
    try:
        from cognee.modules.memify.skill_improvement import improve_skill
        from cognee.modules.pipelines.layers.resolve_authorized_user_datasets import (
            resolve_authorized_user_datasets,
        )

        user, datasets = await resolve_authorized_user_datasets(DATASET, None)
        await improve_skill(
            skill_name,
            dataset=datasets[0],
            user=user,
            proposal_id=proposal_id,
            apply=True,
        )
        out["applied"] = True
        print("[feedback] skill improvement applied.")
    except Exception as exc:
        print(f"[feedback] could not auto-apply proposal ({exc}); proposal_id kept.")

    return out


async def _demo():
    res = await record_correction(
        question="Can I cash out to PayPal in Kosovo?",
        correct_answer="No. Cashly PayPal cashouts cover 190+ countries, but Kosovo is not currently supported.",
        skill_name="qa-answerer",
        thumbs_up=False,
        session_id="demo-session",
        expert="Dana (Support Lead)",
    )
    print("result:", res)


if __name__ == "__main__":
    asyncio.run(_demo())
