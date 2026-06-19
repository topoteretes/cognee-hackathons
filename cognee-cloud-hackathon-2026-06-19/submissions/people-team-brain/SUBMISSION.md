# Team Submission

## Team

- Team name: **People Team Brain**
- Participants: Chris Wilson
- Company Brain / project name: **Honestel People & Talent Brain**

## Company Brain Overview

The Honestel People & Talent Brain is a shared, self-improving knowledge base for
the People team of *Honestel*, a fictional fairness-first mobile network operator.
Honestel's customer USPs (transparent pricing, no surprise bills) drive an ambitious
product roadmap, and the People team's job is to translate that roadmap into a
concrete hiring-and-development plan. The brain answers talent-planning questions and
**gets smarter from feedback**: a weak, generic answering skill is scored by a critic,
that feedback makes cognee **propose a rewrite of the skill**, the rewrite is
**applied**, and the same question is then answered far better — grounded in the
company's own documents, respecting its hard constraints, and citing its sources.

- **Domain / data sources:** curated synthetic People & Talent docs — a 2026
  strategy/roadmap, a team skills inventory, and a people-ops constraints doc — plus a
  multi-stakeholder "running updates log".
- **Primary use case:** a brand-new Head of People (Day 2, under pressure) asks the
  brain for a talent plan to deliver Honestel's new transparent-billing guarantee.
- **What makes it stand out:** the company's *values create the test* — a stock LLM
  gives confidently-wrong generic advice; the brain must learn to ground every answer
  in Honestel's specific roadmap, team, and constraints. The improvement is objectively
  scorable and the before/after is real (**0.167 → 0.833** in our run, +0.666).

## The Three Operations

### Ingest

- **What goes in:** curated People docs (`strategy_2026.md`, `team_skills.md`,
  `people_ops.md`) and the volatile multi-stakeholder updates log (`updates.md`); plus
  the answering skill (`my_skills/qa-answerer/SKILL.md`).
- **How it is captured:** `cognee.remember(...)` — curated docs into the permanent
  graph (`honestel-people-brain`), the volatile log into a *separate* dataset
  (`honestel-updates`) so it can be linted independently, and the skill via
  `cognee.remember(..., content_type="skills")`.
- **Code entry point:** `ingest()` in `main.py`.

### Query + Self-improve

- **How users query:** `run_agent(question, skill_body)` — retrieves context from the
  cognee memory graph, then answers under the current SKILL.
- **Where feedback comes from:** an LLM **critic** (`judge()` in `main.py`) scores the
  answer 0..1 against Honestel ground truth (cites sources? internal-mobility-first?
  respects budget/bands/markets? accounts for historical time-to-fill? grounded?).
- **How feedback updates the brain:** the run is recorded as a `SkillRunEntry`
  (`apply=False`) with `skill_improvement={...}`, which makes cognee **propose** a
  rewritten `SKILL.md`; `improve_skill(..., apply=True)` then **applies** it. That
  two-step propose→apply cycle is the self-improvement loop.
- **Code entry point:** `propose_and_apply()` + `main()` in `main.py`.

### Lint

- **What "linting" means:** the updates log is appended to by multiple stakeholders
  (`[CFO]`, `[VP Eng]`, `[People]`) and rots — **duplicates** (restating a doc),
  **conflicts** (a board headcount change vs. the docs), and **stale** notes
  (superseded decisions). The linter is an LLM critic that classifies each issue and
  resolves it by **recency + author authority** (a `[CFO]`/board budget decision beats
  a `[People]` working assumption).
- **How it runs:** on-demand. It reconciles only the volatile `honestel-updates`
  dataset (wipe + rebuild with the cleaned log), never touching the curated knowledge
  or the self-improved skill.
- **Code entry point:** `lint_brain()` in `lint.py` (`python lint.py`, or
  `python main.py --lint`).

## Self-Improvement Evidence

### Baseline Run

- **Query / task:** "I'm the new Head of People. What's my talent plan to deliver
  Honestel's new transparent-billing guarantee? Give me concrete hire/reskill moves."
- **Result:** generic, high-level HR advice — no specific employees, no budget/market
  constraints, no citations.
- **Score:** **0.167 / 1.0** (5 of 6 criteria fail — no citations, no grounding,
  ignores budget/markets/time-to-fill).
- **Recorded feedback:**

```text
error_type: weak-skill
error_message: generic advice; no citations; ignored skills inventory, budget, markets, time-to-fill
feedback: -1.0
success_score: 0.167
```

### Improved Run

- **Query / task:** identical to baseline.
- **Result:** a grounded, budget-checked, headcount-capped plan — reskills the two
  named billing-experienced engineers (internal mobility), opens the scarce streaming
  roles early (~5-month time-to-fill), respects the 6-hire / €720k cap, comp bands, and
  DE/ES/PL-only hiring, and cites its sources.
- **Score:** **0.833 / 1.0** (5 of 6 criteria pass; tightening budget-enforcement is
  the remaining gap).
- **What changed in the brain between runs:** cognee rewrote the answering SKILL from a
  2-line generic instruction into a multi-step grounded procedure. The skill diff is the
  canonical evidence:

```text
Before:
You are a People & Talent assistant. Answer the question briefly, in 2-3 sentences,
with general HR best-practice advice. Keep it high-level and do not rely on any
company-specific documents, names, numbers, or policies.

After (cognee-proposed, applied):
A multi-step procedure: identify request type; gather evidence from strategy_2026 /
team_skills / people_ops; cite sources [Doc:Section]; check internal mobility before
external hiring; apply constraints (<=6 hires, <=€720k, comp bands, DE/ES/PL); respect
historical time-to-fill; compose a grounded, actionable plan; self-review for
contradictions and citations.
```

## Architecture

- **Two tiers, one instance.** Curated facts + skills live in the **permanent graph**
  (`cognee.remember(...)` with no `session_id`). The run's working memory — the
  `SkillRunEntry` feedback and agent turns — uses the **session tier**
  (`session_id="sam-day-2"`). Distillation = the propose→apply step that promotes a
  scored run into a durable, improved skill in the graph.
- **Volatile layer isolation.** The multi-stakeholder updates log lives in its own
  dataset so Lint can reconcile it without risking the curated knowledge or skill.

```text
[curated docs] --remember()--> [permanent graph: honestel-people-brain] --+
[updates log]  --remember()--> [volatile graph: honestel-updates] --lint--+--> retrieve
[skill]        --remember(content_type=skills)--> [skill in graph]         |
                                                                           v
   run answer under SKILL --> critic scores --> SkillRunEntry(apply=False) --> cognee
   proposes rewrite --> improve_skill(apply=True) --> improved SKILL --> better answer
```

### Cognee Cloud (optional, rewarded)

Built and demoed **locally**. The code is Cloud-ready: `python main.py --cloud` calls
`cognee.serve(COGNEE_CLOUD_URL, COGNEE_API_KEY)` then `cognee.push("honestel-people-brain")`
to push the locally-built brain to a managed instance for the bonus (set the two env
vars to enable).

## Agents / Skills

```text
Skill path(s): my_skills/qa-answerer/SKILL.md  (improved body -> SKILL.improved.md)
Roles:
  - Ingestor: ingest() in main.py
  - Querier:  run_agent() in main.py (answers under the current SKILL)
  - Linter:   lint_brain() in lint.py (authority+recency-aware audit)
  - Critic:   judge() in main.py (scores answers against Honestel ground truth)
```

## Reproduction

```bash
python -m venv .venv && source .venv/bin/activate
pip install cognee==1.2.0.dev1
cp .env.example .env   # then paste your LLM key into .env

python main.py          # ingest -> baseline (0.167) -> propose+apply rewrite -> improved (0.833)
python main.py --lint   # also runs the Lint before/after
python lint.py          # standalone Lint demo
```

Environment variables required (see `.env.example`; we ran on **Scaleway Generative
APIs**, OpenAI-compatible):

```text
LLM_API_KEY, LLM_MODEL=openai/gpt-oss-120b, LLM_ENDPOINT=https://api.scaleway.ai/v1
LLM_INSTRUCTOR_MODE=json_mode            # gpt-oss tool-calling is unreliable; use JSON mode
COGNEE_SKIP_CONNECTION_TEST=true
EMBEDDING_PROVIDER=openai_compatible, EMBEDDING_MODEL=bge-multilingual-gemma2, EMBEDDING_DIMENSIONS=3584
# Optional (Cloud bonus): COGNEE_CLOUD_URL, COGNEE_API_KEY
```

## Demo

- **3-minute pitch outline:**

```text
1. Problem: scattered People knowledge; a brand-new Head of People (Day 2) must deliver.
2. Ingest: curated docs + multi-stakeholder updates -> cognee graph.
3. Query (before): generic skill -> generic answer -> critic scores 0.167.
4. Self-improve: record feedback -> cognee proposes + applies a SKILL rewrite (show the diff).
5. Query (after): same question -> grounded, cited, constraint-respecting plan -> 0.833.
6. Lint: stakeholders log conflicting/stale notes -> linter resolves by authority+recency.
```

## Links

- Repo: full code is included in this submission folder
  (`cognee-cloud-hackathon-2026-06-19/submissions/people-team-brain/`).
- Slides / writeup: this `SUBMISSION.md`.
