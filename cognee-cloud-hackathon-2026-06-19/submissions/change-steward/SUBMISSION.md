# Change Steward

## Project

Change Steward is a self-improving Company Brain for safe AI-assisted software changes.

AI makes code generation cheap. The bottleneck moves to review: knowing the latest architecture decisions, repo ownership, design rules, incident lessons, PR review history, and rollout risks. Change Steward ingests that scattered company knowledge into Cognee Cloud, answers proposed change questions, learns from expert feedback, and lints stale guidance so future changes are safer.

The demo centers on one software-change question:

```text
We need to add a billing settings screen for enterprise admins.
Which repos should I touch, what patterns should I use, and what risks should I avoid?
```

## What It Ingests

The Company Brain uses a synthetic but realistic engineering corpus:

- Repo docs: `admin-app`, `dashboard-app`, `platform-api`
- Architecture decisions: ADR-009 and ADR-014
- Ownership map for repo and reviewer routing
- Design system docs from 2025 and 2026
- Enterprise billing UX brief
- Incident postmortem INC-231 and rollback runbook
- PR review notes that capture prior mistakes

## Skills

Change Steward registers skills with Cognee separately from the company knowledge corpus:

- `qa-answerer`: the live answerer skill. It starts weak, receives feedback, and is re-ingested after improvement.
- `change-critic`: a locked/narrative skill that scores proposed plans against the review checklist and prepares SkillRunEntry-ready feedback.
- `staleness-linter`: a locked/narrative skill that detects stale/conflicting company guidance using source precedence rules.

The live demo runs `qa-answerer`; the other two skills are shown in the UI to make the intended multi-skill Company Brain architecture visible without adding live-demo risk.

## Cognee Cloud Usage

Change Steward runs against Cognee Cloud with the hackathon two-tier memory model:

- Session memory via `session_id`: current change request, retrieved sources, draft answer, critic feedback, score, and lint findings for the run.
- Permanent graph without `session_id`: canonical architecture rules, ownership, design-system rules, incident lessons, deprecated patterns, and improved skills.

The distillation rule is simple: raw conversation stays in session memory; reusable engineering lessons are promoted to the durable graph. Examples:

- `AuthProviderV1` is deprecated for new admin screens.
- Enterprise billing settings belong in `admin-app`.
- Billing entitlements live in `platform-api`.
- INC-231 makes token refresh a required regression check.
- design-system-2026 semantic tokens supersede direct color tokens.

In this demo, the promotion step demonstrates the durable write path. The improved answer quality still comes from the improved `qa-answerer` skill; the newly promoted graph item is not assumed to automatically change the intentionally weak baseline on the next run.

## Self-Improvement Loop

The demo uses Cognee's skill feedback path:

1. Ingest the company corpus and baseline skill.
2. Ask the hero query with `SearchType.AGENTIC_COMPLETION`.
3. Score the baseline answer with the live checklist score and store that score on the `SkillRunEntry`.
4. Store a `SkillRunEntry` with critic feedback:
   - prefer ADR-014 over ADR-009
   - use `admin-app`, not `dashboard-app`
   - update `platform-api` entitlements
   - use AuthKit v3
   - use design-system-2026 semantic tokens
   - include INC-231 token refresh risk
   - request Platform Auth and Design Systems review
   - flag stale `admin-app` README guidance
5. Apply the skill improvement proposal metadata in Cognee.
6. Because Cognee Cloud skill body updates are not yet reliably wired, materialize the improved skill locally, re-ingest it to Cloud, and use the returned canonical skill name.
7. Run lint to detect stale/conflicting company knowledge.
8. Promote the resolved lint lesson to the permanent graph with a `remember(...)` call that has no `session_id`.

The live demo runs the `qa-answerer` skill because that path is rehearsed and reliable. The repository also includes two locked/narrative skills in the localhost UI:

- `change-critic` represents the expert-review habit: score the answer, identify missing checks, and shape feedback for `SkillRunEntry`.
- `staleness-linter` represents the memory-coherence habit: find conflicts such as README guidance versus active ADRs and propose the reusable rule to promote.

Those skills are shown as available-but-locked in the UI to make the multi-skill Company Brain architecture clear without adding live-demo risk.

## Verified Demo Result

Command:

```bash
source .venv/bin/activate
python main.py
```

Localhost demo UI:

```bash
python demo_ui.py
```

Open `http://127.0.0.1:8787` to trigger the same flow from a browser. The UI shows the prefilled hero query, live run output, score/readiness metrics, presenter notes, and the available skill set.

Verified on 2026-06-19 against Cognee `1.2.0.dev1` and Cognee Cloud.

Final readiness output:

```text
Ready: True
Dataset: change-steward-company-brain-v2
Baseline skill: cognee-skills-ggxu7mal
Final skill: cognee-skills-3bmln8dt
Final score: 1.0
Used local guardrail: True
```

The first answer scored poorly according to the live checklist scorer. The promoted long-term lesson does not currently make the intentionally weak baseline answer improve by itself; the correction is enforced through the improved `qa-answerer` skill. Because Cognee Cloud skill body updates are not reliably wired yet, some runs return the corrected answer directly from the re-ingested improved skill and some runs use the transparent local guardrail after Cloud serves a stale skill body. In the latest promotion verification run, the final answer scored `1.0` and included every required correction:

- Add the screen in `admin-app`, not `dashboard-app`.
- Use AuthKit v3; `AuthProviderV1` is deprecated per ADR-014.
- Update entitlements and billing APIs in `platform-api`.
- Use design-system-2026 semantic tokens, not `primary-blue-500`.
- Add token refresh regression checks because of INC-231.
- Request Platform Auth owner and Design Systems owner review.
- Flag the `admin-app` README auth section as stale.

## Lint Result

The lint pass detects stale company knowledge and produces an actionable resolution:

```json
{
  "lint_type": "stale_conflict",
  "topic": "Auth pattern for new admin screens",
  "passed": true,
  "conflict": [
    "admin-app README recommends or references AuthProviderV1",
    "ADR-014 says AuthProviderV1 is deprecated and AuthKit v3 is mandatory"
  ],
  "resolution": "Prefer ADR-014 as canonical.",
  "action": "Mark README guidance stale and promote AuthKit v3 rule to permanent graph.",
  "sources": [
    "data/repos/admin-app.md",
    "data/architecture/ADR-014-authkit-v3.md"
  ]
}
```

After lint passes, the demo promotes this reusable lesson into long-term memory:

```text
ADR-014 is canonical for new admin screens. AuthKit v3 is mandatory,
AuthProviderV1 is deprecated, and stale admin-app README guidance that
references AuthProviderV1 should not be followed.
```

That final `remember(...)` call intentionally omits `session_id`, so the resolved rule goes to the durable graph rather than the run scratchpad.

The promoted graph item is evidence of long-term memory persistence, not the mechanism that forces the next baseline answer to improve. The demo keeps those concerns separate: skill improvement changes answer behavior; lint promotion records the reusable rule durably.

Latest promotion verification returned a completed Cognee Cloud write:

```text
Promoted lesson to permanent graph.
Promotion result: status=completed, dataset=change-steward-company-brain-v2
```

## Why It Matters

Change Steward shows the Company Brain pattern as a real workflow, not just retrieval. It starts with stale, conflicting company knowledge, produces an incomplete change plan against the review checklist, receives expert feedback, improves the skill that answers future questions, and then catches the stale source with lint.

The before/after is the product: the brain learns the review habit, not only the answer.

## Three-Minute Demo Script

1. Show the problem: a developer asks where and how to add enterprise billing settings.
2. Show the skill panel: `qa-answerer` is active; `change-critic` and `staleness-linter` are locked narrative skills for the multi-skill architecture.
3. Run the baseline answer and point out the failure mode: stale or incomplete change guidance.
4. Inject expert feedback through the Cognee skill run entry.
5. Apply the proposal metadata, materialize the improved skill locally, and re-ingest it to Cognee Cloud.
6. Run the query again and show the seven corrected recommendations.
7. Run lint and show the stale `admin-app` README vs ADR-014 conflict.
8. Show the promotion step that remembers the resolved ADR-014 rule as long-term memory.

## Files To Review

- `main.py`: end-to-end demo orchestration
- `ingest.py`: Cognee Cloud connection and data/skill ingestion
- `query.py`: hero query, answer extraction, and scoring
- `improve.py`: skill run feedback and improvement application
- `lint.py`: stale conflict detection
- `data/`: synthetic company knowledge
- `my_skills/qa-answerer/`: baseline and improved answerer skill
- `my_skills/change-critic/`: locked critic skill for scoring plans and producing feedback
- `my_skills/staleness-linter/`: locked linter skill for source-conflict findings
- `demo_ui.py` and `ui/`: localhost demo surface with staged output and presenter notes
