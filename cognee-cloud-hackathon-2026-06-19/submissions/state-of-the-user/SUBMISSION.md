# Team Submission

## Team

- Team name: UXers
- Participants: Anna Agliardi & Dejan Karin
- Company Brain / project name: **State of the User**

## Company Brain Overview

State of the User is a self-maintaining wiki of product insight. It ingests every feedback
signal a UX-research team collects — interviews, surveys, support tickets, NPS comments,
analytics — into Cognee, and maintains itself: a **curator** skill distills raw signals (session
memory) into curated insight pages (the permanent graph), an **answerer** triangulates qual +
quant to answer product questions, and a **linter** keeps the wiki coherent. It self-improves
by rewriting the curator's `SKILL.md` from researcher feedback, measurably raising signal-vs-noise
precision run over run.

- Domain or data sources: UX research / mixed product feedback (qual interviews + surveys + tickets + NPS, quant analytics)
- Primary use case: a living "what do we actually know about our users" brain that gets cleaner the more it's used
- What makes it stand out: the self-improvement is **legible** — you watch the curator skill rewrite itself live (before→after diff) and watch a real precision number climb as junk pages disappear

## The Three Operations

### Ingest

- What goes in: feedback signals (`data/signals.json`) — interview, survey, ticket, nps, analytics
- How it is captured: signals → session memory (`cognee.remember(..., session_id=...)`); curator-promoted insights → permanent graph (`cognee.remember(...)`); skills via `cognee.remember(my_skills/, content_type="skills")`
- Code entry point: `backend/operations.py::ingest_batch` → `backend/brain.py::curate_batch`

### Query + Self-improve

- How users query: ask the wiki in natural language; the answerer runs via `cognee.search(query_type=AGENTIC_COMPLETION, skills=["answerer"])`, citing pages/signals and flagging qual-vs-quant conflicts
- Where feedback comes from: a researcher marks a wiki page **signal** or **noise** (one click in the UI)
- How feedback updates the brain: records a `SkillRunEntry` with a score → `cognee.remember(..., skill_improvement={apply:False})` proposes a curator rewrite → `improve_skill(..., apply=True)` applies it
- Code entry point: `operations.py::query` and `operations.py::feedback` → `brain.py::improve_curator`

### Lint

- What "linting" means: MERGE near-duplicate pages, RETIRE pages whose evidence refers to removed features, FLAG contradictory pairs
- How it runs: on demand (the linter skill via `cognee.search(skills=["linter"])`)
- Code entry point: `operations.py::lint` → `brain.py::lint_wiki`

## Self-Improvement Evidence

Numbers below are from the REPLAY-mode reference run; replace with your live-run capture before
submitting (they are computed by `backend/metrics.py` over the held-out `data/labels.json`, never
hard-coded).

### Baseline Run

- Query / task: classify the held-out labelled signals into signal (PROMOTE/REINFORCE) vs noise
- Result: the naive curator promoted everything, including a lone "worst app ever" rant → 4 junk pages
- Score (signal precision): **0.636** (recall 1.0, F1 0.778, junk pages 4)
- Recorded feedback:

```text
error_type: over_promotion
error_message: Curator promoted a single emotional outburst with no corroboration as an insight.
feedback: -1.0
success_score: 0.30
```

### Improved Run

- Query / task: same held-out labelled signals, after one feedback-driven rewrite
- Result: lone outbursts and off-target/vague feedback are now NOISE; corroborated insights still promote
- Score (signal precision): **1.0** (recall 0.857, F1 0.923, **junk pages 0**)
- What changed in the brain between runs: the curator `SKILL.md` was rewritten to require corroboration before PROMOTE

```text
Before:
# Instructions
For each incoming signal decide exactly one: PROMOTE (create a new insight page), REINFORCE
(attach to an existing page and raise its confidence), or NOISE (leave it in the inbox). Promote
anything that expresses a user problem, request, or sentiment. Prefer action — when in doubt, promote.

After:
# Instructions
For each incoming signal decide exactly one: PROMOTE, REINFORCE, or NOISE. Only PROMOTE when the
signal is corroborated by at least two independent sources OR is backed by a supporting analytics
delta. A single emotional outburst or vague sentiment ('worst app ever', 'great', 'it's fine') is
NOISE unless repeated by other users. Prefer REINFORCE over creating a near-duplicate page. Treat
off-topic or non-user feedback as NOISE.
```

## Architecture

Two tiers inside one cognee instance: session memory (`session_id=...`) is the raw inbox;
the permanent graph (no `session_id`) is the curated wiki. Distillation = the curator decision.

```text
[ingest / feedback signals]
        |
        v
[ session memory ]   <- inbox, per-conversation (session_id=...)
        |
        | curator distillation (PROMOTE / REINFORCE / NOISE)
        v
[ permanent graph ]  <- the wiki: insight pages, index, decision log (no session_id)
        |
        v
[ answerer / linter / recall ]
        |
        v
[ researcher feedback -> SkillRunEntry -> improve_skill ]
```

### Cognee Cloud (optional, rewarded) — DONE

Wired via `backend/operations.py::push_cloud` and `scripts/push_cloud.py` →
`cognee.serve(...)` + `cognee.push("state-of-the-user")`. **Verified live** against our Cloud
instance:

```text
PushResult(status='completed', dataset='state-of-the-user',
           nodes=43, edges=93, pipeline_run_id='99563f55-b214-47da-81d3-67e9fa6191f2')
```

`scripts/push_cloud.py` builds both tiers locally (curated wiki → permanent graph; raw signals →
session memory), cognifies them, then pushes the enriched brain (43 nodes / 93 edges) to the
managed Cognee Cloud instance.

- Session memory (`session_id=...`): raw incoming signals (the inbox)
- Permanent graph (no `session_id`): curated insight pages, the index, the decision log, and the three skills
- Distillation: the curator promotes/reinforces/noise on ingest; feedback rewrites the curator skill
- Session-only vs promoted: noise stays in the inbox; corroborated signals become/reinforce pages
- Proof it got smarter: precision 0.636 → 1.0 and junk pages 4 → 0 between baseline and improved runs

## Agents / Skills

```text
Skill path(s): my_skills/curator/SKILL.md, my_skills/answerer/SKILL.md, my_skills/linter/SKILL.md
Roles:
  - Ingestor / Curator: promote/reinforce/noise distillation (the self-improving skill)
  - Querier / Answerer: answer from the wiki, triangulate qual+quant, cite sources, surface conflicts
  - Linter: merge duplicates, retire stale pages, flag conflicts
  - Critic: the researcher feedback loop (signal/noise marking → SkillRunEntry)
```

## Reproduction

```bash
uv venv && source .venv/bin/activate
uv pip install "cognee==1.2.0.dev1" fastapi "uvicorn[standard]" python-dotenv
cp .env.example .env && echo 'LLM_API_KEY=sk-...' >> .env

python scripts/smoke_test.py                     # prove the loop (real LLM)
uvicorn backend.app:app --port 8000              # live app at http://127.0.0.1:8000
REPLAY=1 uvicorn backend.app:app --port 8000     # offline demo (no LLM)
```

Environment variables required:

```text
COGNEE_CLOUD_URL    # optional, Cognee Cloud instance URL
COGNEE_API_KEY      # optional, Cognee Cloud API key
LLM_API_KEY         # OpenAI key
REPLAY              # 1 for offline replay mode
```

## Links

- Repo: https://github.com/dejankarin/state-of-the-user
