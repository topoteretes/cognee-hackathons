# Team Submission

## Team

- Team name: Change Steward
- Participants: Wassim Boubaker
- Company Brain / project name: Change Steward

## Company Brain Overview

Change Steward is a self-improving Company Brain for safe AI-assisted software changes. It ingests repo docs, ADRs, ownership maps, design-system guidance, incident postmortems, rollback runbooks, and PR review feedback into Cognee Cloud. It answers proposed change questions, learns from expert feedback, and lints stale company knowledge so future AI-assisted changes are safer.

- Domain or data sources: engineering knowledge for software change review
- Primary use case: guide developers and agents on which repos to touch, what current patterns to use, and what risks to avoid
- What makes it stand out: the same demo query is answered incorrectly first, then correctly after the Cognee skill feedback loop improves the answerer skill

## The Three Operations

### Ingest

- What goes in: repo docs, architecture decisions, ownership map, design system docs, UX brief, incident postmortem, rollback runbook, PR reviews, and the answerer skill itself
- How it is captured: `cognee.remember(...)` for data files and `cognee.remember(..., content_type="skills")` for the skill
- Code entry point: `ingest.py`

### Query + Self-improve

- How users query the Company Brain: the demo calls `cognee.search(...)` with `SearchType.AGENTIC_COMPLETION`, the Company Brain dataset, an ingested skill, and a session id
- Where feedback comes from: an agent critic / evaluator gives structured feedback for the failed baseline answer
- How feedback updates the brain: the run is stored as a `SkillRunEntry` with `success_score=0.35`, negative feedback, and `skill_improvement` metadata; Cognee creates/applies the improvement, then the improved skill is re-ingested
- Code entry point: `query.py`, `improve.py`, `main.py`

### Lint

- What "linting" means in this brain: detect stale or conflicting company knowledge and produce a canonical resolution
- How it runs: on demand after the self-improvement loop during the demo
- Code entry point: `lint.py`

## Self-Improvement Evidence

### Baseline Run

- Query / task:

```text
We need to add a billing settings screen for enterprise admins.
Which repos should I touch, what patterns should I use, and what risks should I avoid?
```

- Result: the baseline answer was incomplete and failed the required checklist; the demo baseline score is intentionally set to `0.35`
- Score: `0.35`
- Recorded feedback:

```text
error_type: stale_change_plan
error_message: The plan used stale architecture, stale design tokens, and missed incident risk.
feedback:
  Prefer ADR-014 over ADR-009.
  Billing settings belong in admin-app.
  Do not put enterprise billing settings in dashboard-app.
  Entitlements live in platform-api.
  Use AuthKit v3.
  Use design-system-2026 semantic tokens.
  Mention INC-231 token refresh risk and rollback runbook.
  Request review from Platform Auth and Design Systems owners.
  Flag the admin-app README auth section as stale.
success_score: 0.35
```

### Improved Run

- Query / task: the same enterprise billing settings hero query
- Result: after two feedback/improvement passes, the final answer contained all required corrections
- Score: `1.0`
- What changed in the brain between runs:

```text
Before:
The baseline skill answered from retrieved context but did not reliably resolve stale or conflicting sources.

After:
The improved skill checks current ADRs before README guidance, checks ownership before naming repos, verifies design-system version, checks incidents/postmortems for known risks, flags stale sources, and cites controlling sources.
```

Required corrections present in the final answer:

- Add the screen in `admin-app`, not `dashboard-app`.
- Use AuthKit v3; `AuthProviderV1` is deprecated per ADR-014.
- Update entitlements and billing APIs in `platform-api`.
- Use design-system-2026 semantic tokens, not `primary-blue-500`.
- Add token refresh regression checks because of INC-231.
- Request Platform Auth owner and Design Systems owner review.
- Flag the `admin-app` README auth section as stale.

Verified demo output:

```text
Ready: True
Dataset: change-steward-company-brain-v2
Baseline skill: cognee-skills-mp58225s
Final skill: cognee-skills-10x1tb94
Final score: 1.0
Used local guardrail: False
```

## Architecture

```text
[data/ docs + my_skills/qa-answerer]
        |
        v
[ ingest.py -> Cognee Cloud ]
        |
        v
[ Cognee Cloud session memory ]  <- current query, retrieved sources, critic feedback, score
        |
        | distill reusable lessons through SkillRunEntry + skill improvement
        v
[ Cognee Cloud permanent graph ] <- ADR rules, repo ownership, design rules, incidents, improved skills
        |
        v
[ query.py / main.py ]
        |
        v
[ lint.py -> stale conflict resolution ]
```

### Cognee Cloud

Yes. Change Steward connects to Cognee Cloud with `cognee.serve(...)`.

- What the team writes to session memory (`session_id=...`): current change request, draft answer, retrieved sources, critic feedback, score, and lint findings
- What goes straight to the permanent graph (no `session_id`): canonical architecture rules, repo ownership, design-system rules, incident lessons, deprecated patterns, and improved skills
- How and when content is distilled from session memory into the permanent graph: after a failed answer, reusable lessons are recorded through the skill run feedback path and applied to the answerer skill
- What stays session-only vs. what gets promoted: raw conversation stays session-only; durable rules such as "AuthProviderV1 is deprecated for new admin screens" and "INC-231 requires token refresh regression checks" are promoted
- Proof the brain got smarter between baseline and improved run: the same query moved from a failed baseline score of `0.35` to a final score of `1.0` without using the local guardrail fallback

## Agents / Skills

```text
Skill path(s):
  - my_skills/qa-answerer/SKILL.md
  - my_skills/qa-answerer/SKILL.baseline.md
  - my_skills/qa-answerer/SKILL.improved.md

Roles:
  - Ingestor: ingest.py
  - Querier: query.py
  - Linter: lint.py
  - Critic: improve.py / main.py
```

## Reproduction

Commands to reproduce the demo:

```bash
uv venv
source .venv/bin/activate
uv pip install cognee==1.2.0.dev1 python-dotenv
python main.py
```

Environment variables required:

```text
COGNEE_CLOUD_URL
COGNEE_API_KEY
LLM_API_KEY
CHANGE_STEWARD_DATASET          # optional
CHANGE_STEWARD_SESSION          # optional
CHANGE_STEWARD_SKIP_DATA_INGEST # optional
```

## Demo

- Live demo link: local demo via `python main.py`
- 3-minute pitch outline:

```text
1. Problem: AI can write code quickly, but review depends on scattered company memory.
2. Ingest: load repo docs, ADRs, design docs, incidents, PR reviews, and the answerer skill.
3. Query before improvement: ask where to add enterprise billing settings and show stale/incomplete guidance.
4. Self-improve: record critic feedback with SkillRunEntry and apply the skill improvement.
5. Query after improvement: same query now returns the seven required safe-change recommendations.
6. Lint: detect admin-app README guidance as stale versus ADR-014 and promote the canonical resolution.
```

## Links

- Repo: https://github.com/boubakerwa/Cognee-change-steward
- Slides / writeup: this submission file
- Anything else: verified on 2026-06-19 with Cognee `1.2.0.dev1`
