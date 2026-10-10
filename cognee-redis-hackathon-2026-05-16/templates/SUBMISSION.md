# Team Submission — Cinegraph

## Team

- Team name: Cinegraph
- Participants: Piotr Tyrakowski, Michał Zajączkowski, Łukasz Kryczka
- Wiki / project name: **Cinegraph** — an editor agent that learns from the videos it tries to imitate

## Wiki Overview

Cinegraph is an LLM Wiki for video editing. A human cuts a short clip by hand;
the agent watches the result, attempts the same edit, scores its attempt
against the human's version, and distills what went wrong into its own
`SKILL.md` rulebook. The next attempt loads the rewritten wiki, not a new
prompt or new weights — same agent, smarter every run.

- Domain or data sources: short-form video edits. Each "source" is a pair of
  raw clips + a human-edited target video. Gemini extracts observations
  (cuts, b-roll, pacing, on-screen text) into the wiki.
- Primary use case: bootstrap a video-editor agent that improves by imitation
  rather than by prompt engineering or fine-tuning.
- What makes it stand out: the feedback signal is the human's final cut
  itself — no labels, no RL infra. The wiki is the policy.

## The Three Operations

### Ingest

- What goes in: the human-edited target video and the raw source clips.
- How it is captured: `llmwiki ingest` sends the target to Gemini, which
  answers a fixed set of observation prompts (cuts, b-roll, pacing,
  on-screen text). Each answer is written to:
  - Redis session memory via `cognee.remember(..., session_id=ingest-<slug>)`
  - the durable wiki at `wiki/observations/<slug>/`
  - the Redis event stream via `publish_event("observation", {...})`
- Code entry point: `llmwiki/ingest.py`

### Query + Self-improve

- How users query the wiki: **we use Claude models for the agent.** Claude
  reads the SKILL.md files from the cognee graph and writes
  `remotion/src/Hero.tsx`, which renders to `attempt.mp4`. Intermediate
  thoughts go to Redis via `session_id=<run_slug>`.
- Where feedback comes from: a dual-video critique step — Gemini watches the
  agent's `attempt.mp4` *and* the human `target/edited.mp4` in one call and
  returns a precision/recall/F1 score over cut placements plus per-skill
  proposals.
- How feedback updates the wiki: each proposal becomes a `SkillRunEntry` in
  Cognee with `apply=False` (proposes a rewrite). The proposal IDs are then
  passed to `improve_skill(proposal_id, apply=True)` which commits the
  rewrite into the graph. The next agent run pulls the rewritten skill via
  `cognee.recall("…current rules in the '{skill}' editing skill…")` — the
  SKILL.md on disk stays as the *seed*, and the Cognee graph is the
  evolving source of truth.
- Code entry points: `llmwiki/critique.py`, `llmwiki/self_improve.py`
  (propose: `self_improve.py:96–111`, apply: `self_improve.py:138–144`,
  recall-back: `self_improve.py:157–165`)

### Lint

- What "linting" means here:
  - dedupe redundant rules across SKILL.md proposals (Cognee graph handles
    similarity collapse for us)
  - flag thin skills (very short body, low utility) and orphan proposals
  - flag regressions: if a skill's F1 dropped run-over-run, surface it in
    the viz
  - prune stale per-run observations on `reset` (per `session_id`)
- How it runs: on demand via `llmwiki lint`, plus passive surface in the
  viz at `localhost:8002` (run table highlights regressions, SKILL.md
  cards show stale flags).
- Code entry points: `llmwiki/lint.py`, `viz/server.py`

## Self-Improvement Evidence

### Baseline Run

- Query / task: imitate `data/demo/target/edited.mp4` — agent emits a list of
  cuts and renders them via Remotion to `runs/<slug>/attempt.mp4`.
- Result: `runs/attempt-v1-2026-05-16T22-49-33Z/attempt.mp4`
- Score (cut-placement F1 vs target):

```text
precision: 1.000
recall:    0.333
f1:        0.500
matched:   4 of 12 target cuts
```

- Recorded feedback (one `SkillRunEntry` per skill, all routed through Cognee):

```text
error_type:      missing_cuts
error_message:   Agent placed 4 cuts; target had 12. Three high-confidence
                 topic-shift / b-roll / on-screen-text moments were missed.
feedback:        -1.0
success_score:   0.5
```

### Improved Run

- Query / task: same — imitate the same target with the rewritten wiki.
- What changed in the wiki between runs: three SKILL.md files were rewritten
  by `cognee.improve_skill(apply=True)` after the critique.

```text
Before  (cut-detection / SKILL.md — baseline rules):
  1. Prefer end-of-sentence cuts.
  2. Stay around 4–8 seconds per shot.
  3. Cut on motion.
  4. Tighten pauses > 0.4s.
  5. Avoid back-to-back wide shots.

After   (cut-detection — committed via improve_skill, apply=True):
  + NEW: cut away from speaker at topic shifts
        (evidence: @1.9s the target leaves the talking head;
         v1 stays on it).
  + NEW: insert b-roll composite when narration shifts subject
        (evidence: @1.9s target shows a multi-layer b-roll grid).
  ~ CHANGED: place a bold center-text headline on the punch line
        ('NOT ALL SAUNAS ARE CREATED EQUAL' @ 6.9s).
```

Proposal accounting from `runs/<slug>/skill_diff.md`:

```text
F1 = 0.5
proposals integrated: 3 / 3
skills changed:       3   (cut-detection, broll-selection, on-screen-text)
commit path:          cognee.improve_skill(apply=True)
```

## Architecture

```text
                       human-edited target  +  raw clips
                                  │
                                  ▼
                       ┌──────────────────────┐
                       │ Gemini observations  │     (vision layer)
                       └─────────┬────────────┘
                                 │
              cognee.remember(..., session_id=<slug>)
                                 ▼
                ┌────────────────────────────────────┐
                │ REDIS  — session memory + indexes   │  hot, ephemeral
                │  · per-run observations             │  per-conversation
                │    (via cognee session_id routing)  │  forgets per run
                │  · event stream (XADD/XREVRANGE)    │
                │    llmwiki:events, maxlen 10_000    │
                │  · RediSearch HNSW vector index     │
                │    llmwiki:clip-vectors (COSINE)    │
                └────────────────┬───────────────────┘
                                 │
                       distillation (improve_skill)
                                 ▼
                ┌────────────────────────────────────┐
                │ COGNEE — permanent graph            │  durable, cross-run
                │  · SKILL.md nodes                   │
                │  · SkillRunEntry history            │
                │  · improvement proposals            │
                │  · applied rewrites (apply=True)    │
                └────────────────┬───────────────────┘
                                 │
                                 ▼
                       recall → next agent run
                                 │
                                 ▼
                       feedback → improve → loop
```

### Redis-as-session-memory

- What goes into Redis (and how):
  - **session keys** — populated *indirectly* by Cognee. Every
    `cognee.remember(text, session_id=<run_slug>)` and
    `memory.remember_session(...)` call lands in Cognee's Redis backend.
    Our application code never `r.set`s a session key directly.
  - **clip-vector hashes** — written directly by `upsert_clip()` in
    `llmwiki/redis_use.py:98–110`; stored as Redis hashes under the
    `clip:*` prefix with a 1536-dim FLOAT32 embedding field.
  - **event stream** — every `publish_event(kind, payload)` call
    (`llmwiki/redis_use.py:23–35`) `XADD`s to `llmwiki:events` with
    `maxlen=10_000 approximate=True`.
- How and when content is distilled into the graph:
  - immediately after critique: a `SkillRunEntry` is `remember`ed with
    `skill_improvement={"apply": False, "score_threshold": 0.9}` — this
    creates a proposal in the Cognee graph.
  - `improve_skill(skill, proposal_id=..., apply=True)` commits the
    rewritten SKILL.md body into the graph (graph only — disk file is
    intentionally left as the seed).
- What stays in Redis vs. what gets promoted:
  - stays: per-run scratchpad (via cognee session keys), clip-vector
    hashes, event-stream entries.
  - promoted: SKILL.md graph nodes, SkillRunEntry history, improvement
    proposals, applied rewrites.
- How distillation quality improved between baseline and improved run:
  - baseline: 0 cumulative proposals in the graph; agent runs on seed
    rules read straight from `my_skills/`.
  - after run v1: 3 proposals committed via `improve_skill(apply=True)`
    across 3 skills (cut-detection, broll-selection, on-screen-text).
    The next run pulls these via `cognee.recall(...)`.
  - the graph grows monotonically with each run while Redis stays
    constant-size (capped stream `maxlen=10_000`).

## Agents / Skills

```text
Skill path: ./my_skills/
  ├── cut-detection/SKILL.md
  ├── broll-selection/SKILL.md
  ├── pacing/SKILL.md
  ├── transitions/SKILL.md
  └── on-screen-text/SKILL.md

Roles:
  - Ingestor:   Gemini 3.1 (vision) — extracts observations from target.mp4
  - Querier:    Claude — reads SKILL.md from the graph, writes Hero.tsx
                (the Remotion edit), which renders attempt.mp4.
  - Critic:     Gemini dual-video — watches attempt + target side-by-side,
                returns scores + per-skill proposals.
  - Linter:     Cognee graph + llmwiki/lint.py — dedupe, thin/orphan
                detection, regression flags.
```

## Reproduction

### Commands

```bash
cd /path/to/LLM-Wiki-Hackaton
set -a && source .env && set +a

# 0. Background services
docker run -d --name llmwiki-redis -p 6380:6379 redis/redis-stack-server:latest
uv run cognee-cli -ui &                                  # localhost:3000
uv run uvicorn viz.server:app --port 8002 &              # localhost:8002

# 1. Wipe Cognee + Redis state
uv run python -m llmwiki reset

# 2. Ingest the target (Gemini → Redis session + wiki/observations/)
uv run python -m llmwiki ingest

# 3. Render the current Hero.tsx as attempt v1
uv run python -m llmwiki attempt --label v1
SLUG_V1=$(ls -t runs/ | head -1)

# 4. Critique v1 — Gemini scores both videos, emits proposals
uv run python -m llmwiki critique $SLUG_V1

# 5. Self-improve — SkillRunEntry + improve_skill(apply=True)
uv run python -m llmwiki self-improve $SLUG_V1

# 6. Render attempt v2 with the new wiki
uv run python -m llmwiki attempt --label v2
SLUG_V2=$(ls -t runs/ | head -1)
uv run python -m llmwiki critique $SLUG_V2

# 7. Inspect
open http://localhost:8002         # before/after viz, event stream
open http://localhost:3000         # cognee graph UI
```

### Environment variables

```text
LLM_API_KEY=<provided at kickoff>
REDIS_URL=redis://localhost:6380
GEMINI_API_KEY=<for the vision + critique steps>
COGNEE_VECTOR_DB_PROVIDER=redis
COGNEE_VECTOR_DB_URL=redis://localhost:6380
```

### Inspect Redis live

```bash
docker exec llmwiki-redis redis-cli DBSIZE
docker exec llmwiki-redis redis-cli XREVRANGE llmwiki:events + - COUNT 30
docker exec llmwiki-redis redis-cli --scan --pattern 'agent_sessions:*' | head
docker exec llmwiki-redis redis-cli FT.INFO llmwiki:clip-vectors | head -20
```

## Demo

- **🎬 Video walkthrough:** https://youtu.be/H3fIXsQ9GVA
- Live demo: 3-minute walkthrough during the finals (5:00 PM slot).
  Slides at `slides/index.html` (Reveal.js).
- 3-minute pitch outline:

```text
1. Idea           — video editing is an RL environment in disguise;
                    the human edit IS the reward signal.
2. Live demo      — reset → ingest → attempt v1 → critique → self-improve
                    → attempt v2. Watch the F1 score climb and the
                    SKILL.md cards on localhost:8002 rewrite themselves.
3. What Cognee does — permanent SKILL.md graph + SkillRunEntry +
                    improve_skill(apply=True). Propose, then commit;
                    next run reads the rewrite back via cognee.recall.
4. What Redis does — session memory (via cognee session_id), RediSearch
                    HNSW vector index over source clips, and the durable
                    event stream the live viz reads from.
5. Close          — wiki, not weights. Same agent, smarter every run.
```

## Links

- **Video walkthrough:** https://youtu.be/H3fIXsQ9GVA
- Repo: https://github.com/PiotrTyrakowski/LLM-Wiki-Hackaton
- Slides / writeup: `slides/index.html` (Reveal.js, included in repo)
- Live event stream proof: `docker exec llmwiki-redis redis-cli XREVRANGE llmwiki:events + - COUNT 30`
- Example run artifacts: `runs/attempt-v1-2026-05-16T22-49-33Z/`
  (`critique.md`, `skill_diff.md`, `attempt.mp4`)
