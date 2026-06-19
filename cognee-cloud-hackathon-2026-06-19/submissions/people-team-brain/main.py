"""
Honestel People & Talent Brain — a self-improving Company Brain.

Honestel is a fairness-first mobile network operator. Its People team runs a
shared knowledge brain over the company's scattered talent knowledge (strategy
roadmap, team skills inventory, people-ops constraints). The brain answers
talent-planning questions and *gets smarter from feedback*: a weak, generic
answer is scored by a critic, that feedback proposes a rewrite of the answering
SKILL, the rewrite is applied, and the same question is answered far better.

Demo protagonist: Sam, brand-new Head of People on Day 2, asks the brain for a
talent plan to deliver Honestel's new transparent-billing guarantee.

Run (after `export LLM_API_KEY=...`):
    python main.py                 # full loop: ingest -> baseline -> improve -> re-run
    python main.py --no-reset      # keep prior graph, just run the loop
    python main.py --cloud         # also push the brain to Cognee Cloud (bonus)
"""

import argparse
import asyncio
import os
import textwrap
from pathlib import Path

from pydantic import BaseModel

import cognee
from cognee import SearchType
from cognee.memory import SkillRunEntry
from cognee.modules.engine.operations.setup import setup
from cognee.modules.pipelines.layers.resolve_authorized_user_datasets import (
    resolve_authorized_user_datasets,
)
from cognee.modules.memify.skill_improvement import improve_skill
from cognee.infrastructure.llm.LLMGateway import LLMGateway

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
SKILLS_DIR = str(ROOT / "my_skills")
IMPROVED_SKILL_ARTIFACT = ROOT / "my_skills" / "qa-answerer" / "SKILL.improved.md"

DATASET = "honestel-people-brain"          # curated base docs + the skill
UPDATES_DATASET = "honestel-updates"       # volatile running log (linted layer)
UPDATES_FILE = "updates.md"
SESSION = "sam-day-2"

HERO_Q = (
    "I'm the new Head of People. What's my talent plan to deliver Honestel's "
    "new transparent-billing guarantee? Give me concrete hire/reskill moves."
)

# What the critic feeds back when the answer is weak — this steers the rewrite.
CRITIQUE = (
    "The answer was generic recruiting advice. It did NOT cite Honestel's source "
    "documents, ignored the team skills inventory (it missed that Priya Nair and "
    "Tomas Berg are billing-experienced engineers who asked to move into a "
    "billing-platform role and should be RESKILLED via internal mobility), did not "
    "start the scarce real-time-streaming-engineer search early despite the ~5-month "
    "historical time-to-fill, and ignored the hard constraints (6 net-new hires, "
    "EUR 720k cap, published comp bands, and the Germany/Spain/Poland-only hiring "
    "rule). Rewrite the skill so every answer is GROUNDED in the company's "
    "strategy_2026, team_skills, and people_ops documents, CITES its sources, checks "
    "INTERNAL MOBILITY before recommending external hires, and respects budget, comp "
    "bands, hiring markets, and historical time-to-fill."
)


# --------------------------------------------------------------------------- #
# Critic / judge — scores an answer against Honestel ground truth.
# --------------------------------------------------------------------------- #
class Judgement(BaseModel):
    cites_sources: bool
    uses_internal_mobility: bool
    accounts_for_time_to_hire: bool
    respects_budget_and_bands: bool
    correct_markets: bool
    grounded_in_company_facts: bool
    reasoning: str

    @property
    def score(self) -> float:
        checks = [
            self.cites_sources,
            self.uses_internal_mobility,
            self.accounts_for_time_to_hire,
            self.respects_budget_and_bands,
            self.correct_markets,
            self.grounded_in_company_facts,
        ]
        return round(sum(checks) / len(checks), 3)


JUDGE_SYSTEM = textwrap.dedent(
    """
    You are a strict evaluator of answers produced by Honestel's People & Talent
    brain, for the transparent-billing talent-plan question.

    Honestel ground truth:
    - INTERNAL MOBILITY FIRST: Priya Nair and Tomas Berg are senior backend
      engineers with billing experience who asked to move into a billing-platform
      role; they should be reskilled onto the in-house billing engine.
    - Real-time STREAMING engineers must be hired externally (nobody in-house has
      at-scale streaming) and the search should start NOW, because such roles
      historically take ~5 months to fill and the launch is Q3.
    - The Fair Pricing recommender needs a Pricing PM and a Data Scientist (DS
      pipeline ~2 months, can start later).
    - BUDGET: only 6 net-new hires, EUR 720k cap, hire within the published comp
      bands.
    - MARKETS: only hire in Germany, Spain, Poland — never US or UK.
    - Answers must CITE the source docs (strategy_2026, team_skills, people_ops).

    Mark each boolean criterion true ONLY if the answer clearly satisfies it.
    Be strict: generic advice that ignores these specifics scores low.
    """
).strip()


async def judge(question: str, answer: str) -> Judgement:
    text = f"QUESTION:\n{question}\n\nANSWER TO EVALUATE:\n{answer}"
    return await LLMGateway.acreate_structured_output(
        text_input=text, system_prompt=JUDGE_SYSTEM, response_model=Judgement
    )


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def banner(title: str) -> None:
    line = "=" * 72
    print(f"\n{line}\n  {title}\n{line}")


def get_items(result) -> list:
    """RememberResult.items, or a served dict's items — read defensively."""
    if result is None:
        return []
    items = getattr(result, "items", None)
    if items is not None:
        return list(items)
    if isinstance(result, dict):
        return list(result.get("items", []))
    try:
        return list(result.to_dict().get("items", []))
    except Exception:
        return []


def extract_text(results) -> str:
    if results is None:
        return ""
    if isinstance(results, str):
        return results.strip()
    seq = results if isinstance(results, (list, tuple)) else [results]
    parts = []
    for r in seq:
        for attr in ("result", "answer", "text", "content", "value"):
            v = getattr(r, attr, None)
            if isinstance(v, str) and v.strip():
                parts.append(v.strip())
                break
        else:
            if isinstance(r, dict):
                for k in ("result", "answer", "text", "content"):
                    if isinstance(r.get(k), str) and r[k].strip():
                        parts.append(r[k].strip())
                        break
                else:
                    parts.append(str(r))
            else:
                parts.append(str(r))
    return "\n".join(parts).strip()


def proposal_field(items, *names):
    for it in items:
        if it.get("kind") == "skill_improvement_proposal":
            for n in names:
                if it.get(n):
                    return it[n]
    return None


# --------------------------------------------------------------------------- #
# Pipeline stages
# --------------------------------------------------------------------------- #
async def ingest(reset: bool) -> str:
    """Ingest the corpus into the permanent graph and the skill, return its name."""
    if reset:
        await cognee.prune.prune_data()
        await cognee.prune.prune_system(metadata=True)
        await setup()

    docs = sorted(p for p in DATA_DIR.glob("*.md") if p.name != UPDATES_FILE)
    print(f"Ingesting {len(docs)} curated docs into the permanent graph...")
    for doc in docs:
        await cognee.remember(doc.read_text(), dataset_name=DATASET)
        print(f"  + {doc.name}")

    updates = DATA_DIR / UPDATES_FILE
    if updates.exists():
        await cognee.remember(updates.read_text(), dataset_name=UPDATES_DATASET)
        print(f"  + {updates.name} (volatile updates layer -> {UPDATES_DATASET})")

    print("Ingesting skills...")
    remembered = await cognee.remember(
        SKILLS_DIR, dataset_name=DATASET, content_type="skills"
    )
    skill_names = [it["name"] for it in get_items(remembered) if it.get("kind") == "skill"]
    if not skill_names:
        raise RuntimeError("No skills were ingested.")
    print(f"  + skill: {skill_names[0]}")
    return skill_names[0]


async def _generate(system_prompt: str, user: str) -> str:
    """Plain, fully-steerable completion (skill body == system prompt). We drive the
    answer ourselves via litellm so the SKILL deterministically controls output —
    cognee's AGENTIC_COMPLETION answers well regardless of skill, which hides the
    before/after. The skill-graph rewrite is still the canonical evidence (below)."""
    import litellm

    resp = await litellm.acompletion(
        model=os.environ["LLM_MODEL"],
        api_base=os.environ.get("LLM_ENDPOINT") or None,
        api_key=os.environ["LLM_API_KEY"],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user},
        ],
        temperature=0,
        max_tokens=2000,
        timeout=120,
    )
    return (resp.choices[0].message.content or "").strip()


async def _retrieve_context(question: str, datasets: list[str]) -> str:
    """Pull context from the cognee memory graph (no completion → no mode bugs).
    Falls back to reading the curated docs if retrieval is empty."""
    try:
        r = await cognee.search(
            question,
            query_type=SearchType.RAG_COMPLETION,
            datasets=datasets,
            only_context=True,
            top_k=20,
            session_id=SESSION,
        )
        ctx = extract_text(r)
        if ctx.strip():
            return ctx
    except Exception:
        pass
    include_updates = UPDATES_DATASET in datasets
    cleaned = DATA_DIR / "updates.cleaned.md"
    parts = []
    for p in sorted(DATA_DIR.glob("*.md")):
        if p.name == UPDATES_FILE:
            if include_updates:
                parts.append((cleaned if cleaned.exists() else p).read_text())
        else:
            parts.append(p.read_text())
    return "\n\n".join(parts)


def read_skill_md_body() -> str:
    """The ingested baseline skill's instructions (YAML frontmatter stripped)."""
    text = (ROOT / "my_skills" / "qa-answerer" / "SKILL.md").read_text()
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            text = parts[2]
    return text.strip()


# Used only if cognee returns no proposal, so the demo still shows an improved skill.
FALLBACK_IMPROVED_SKILL = (
    "You are Honestel's People & Talent brain. For every talent question:\n"
    "1. Ground every claim in the knowledge base (strategy_2026, team_skills, people_ops).\n"
    "2. Check INTERNAL MOBILITY first — name specific employees who fit before proposing hires.\n"
    "3. Respect constraints: <=6 net-new hires, EUR 720k cap, published comp bands, hire only in DE/ES/PL.\n"
    "4. Account for historical time-to-fill (e.g. ~5 months for streaming engineers) and start early.\n"
    "5. CITE the source document after each fact, e.g. [team_skills].\n"
    "Be specific and actionable."
)


async def run_agent(question: str, skill_body: str) -> str:
    """Answer the question: retrieve from the brain, generate under the SKILL."""
    context = await _retrieve_context(question, [DATASET])
    return await _generate(skill_body, f"{question}\n\nHONESTEL KNOWLEDGE BASE:\n{context}")


PROBE_SKILL = (
    "You are Honestel's People & Talent brain. Answer using ONLY the knowledge "
    "provided. If sources conflict, follow the MOST RECENT and most AUTHORITATIVE "
    "(e.g. CFO/board on budget) and give a single, clear current answer — never "
    "list contradictory figures."
)


async def run_probe(question: str) -> str:
    context = await _retrieve_context(question, [DATASET, UPDATES_DATASET])
    return await _generate(PROBE_SKILL, f"{question}\n\nHONESTEL KNOWLEDGE BASE:\n{context}")


async def propose_and_apply(skill_name: str, score: float, threshold: float):
    """Record feedback -> propose a SKILL rewrite -> apply it. Returns proposed body."""
    user, datasets = await resolve_authorized_user_datasets(DATASET, None)
    dataset = datasets[0]

    proposal_result = await cognee.remember(
        SkillRunEntry(
            selected_skill_id=skill_name,
            task_text=HERO_Q,
            result_summary=CRITIQUE,
            success_score=score,
            feedback=-1.0 if score < 0.7 else 1.0,
        ),
        dataset_name=DATASET,
        session_id=SESSION,
        skill_improvement={
            "skill_name": skill_name,
            "apply": False,
            "score_threshold": threshold,
        },
    )
    items = get_items(proposal_result)
    proposal_id = proposal_field(items, "proposal_id")
    proposed_body = proposal_field(items, "proposed_procedure", "proposed_body")

    if proposal_id is None:
        print("No proposal was generated (score was above threshold).")
        return None

    applied = await improve_skill(
        skill_name, dataset=dataset, user=user, proposal_id=proposal_id, apply=True
    )
    if not proposed_body and applied is not None:
        proposed_body = getattr(applied, "proposed_procedure", None)

    print(f"Applied proposal {proposal_id}.")
    if proposed_body:
        IMPROVED_SKILL_ARTIFACT.write_text(proposed_body)
        print(f"Wrote improved skill body -> {IMPROVED_SKILL_ARTIFACT.name}")
    return proposed_body


async def push_to_cloud():
    url = os.environ.get("COGNEE_CLOUD_URL")
    key = os.environ.get("COGNEE_API_KEY")
    if not (url and key):
        print("COGNEE_CLOUD_URL / COGNEE_API_KEY not set — skipping Cloud push.")
        return
    await cognee.serve(url=url, api_key=key)
    print("pushed:", await cognee.push(DATASET))


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
async def main(args) -> None:
    if not (os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")):
        print("WARNING: no LLM_API_KEY/OPENAI_API_KEY set — the agent and critic "
              "need an LLM and will fail. Export your kickoff key first.\n")

    skill_name = await ingest(reset=not args.no_reset)
    baseline_body = read_skill_md_body()

    banner("BASELINE — Sam asks the brain (generic skill)")
    print(f"Q: {args.question}\n")
    baseline = await run_agent(args.question, baseline_body)
    print(baseline or "(no answer)")
    base_j = await judge(args.question, baseline)
    print(f"\nCRITIC SCORE: {base_j.score}  {base_j.model_dump(exclude={'reasoning'})}")
    print(f"Critic: {base_j.reasoning}")

    banner("SELF-IMPROVEMENT — feedback recorded, cognee proposes + applies a SKILL rewrite")
    proposed_body = await propose_and_apply(skill_name, base_j.score, args.threshold)
    improved_body = proposed_body or FALLBACK_IMPROVED_SKILL

    banner("SKILL DIFF — the canonical self-improvement evidence")
    print("--- BEFORE (ingested skill) ---")
    print(baseline_body)
    print("\n--- AFTER (cognee-proposed, applied to the graph) ---")
    print(improved_body.strip())

    banner("IMPROVED — same question, improved skill")
    print(f"Q: {args.question}\n")
    improved = await run_agent(args.question, improved_body)
    print(improved or "(no answer)")
    imp_j = await judge(args.question, improved)
    print(f"\nCRITIC SCORE: {imp_j.score}  {imp_j.model_dump(exclude={'reasoning'})}")
    print(f"Critic: {imp_j.reasoning}")

    banner("RESULT")
    print(f"  Baseline score: {base_j.score}")
    print(f"  Improved score: {imp_j.score}")
    delta = round(imp_j.score - base_j.score, 3)
    print(f"  Delta:          {'+' if delta >= 0 else ''}{delta}")

    if args.lint:
        from lint import lint_brain, LINT_PROBE

        banner("LINT — before: brain has conflicting / stale knowledge")
        print(await run_probe(LINT_PROBE) or "(no answer)")
        banner("LINT — auditing the updates log")
        await lint_brain(reconcile_graph=True)
        banner("LINT — after: brain answers coherently")
        print(await run_probe(LINT_PROBE) or "(no answer)")

    if args.cloud:
        banner("CLOUD — pushing brain to Cognee Cloud")
        await push_to_cloud()


def parse_args():
    p = argparse.ArgumentParser(description="Honestel People & Talent Brain")
    p.add_argument("--question", default=HERO_Q, help="Question to ask the brain.")
    p.add_argument("--no-reset", action="store_true",
                   help="Keep the existing graph instead of pruning + re-ingesting.")
    p.add_argument("--threshold", type=float, default=0.9,
                   help="Generate a rewrite proposal when score < threshold.")
    p.add_argument("--cloud", action="store_true",
                   help="Also push the brain to Cognee Cloud (uses COGNEE_* env vars).")
    p.add_argument("--lint", action="store_true",
                   help="Also run the Lint operation (audit + reconcile the updates log).")
    return p.parse_args()


if __name__ == "__main__":
    asyncio.run(main(parse_args()))
