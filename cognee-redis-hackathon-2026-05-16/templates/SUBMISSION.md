# Team Submission

## Team

- Team name: Sherlock
- Participants: Keenan, Brian, Arsh, Abdoulaye
- Wiki / project name: Sherlock - Competitive Intelligence LLM Wiki for Sales

## Wiki Overview

Sherlock is a local-first competitive intelligence LLM wiki for Oyster HR sales. It ingests internal sales signals (calls, reviews, product updates, analyst notes) into a durable wiki and battle-card layer, then improves outputs through analyst feedback. Redis is used as fast session/cache memory for runtime speed and queueing, while Cognee-backed indexing and local markdown stores provide cross-session durable knowledge. Each analyst approval updates canonical knowledge and invalidates stale cache, so the next query is both faster and more accurate.

- Domain or data sources: B2B sales competitive intelligence; local markdown sources in data/sources, incoming notes in data/incoming, and approved wiki content in data/wiki.
- Primary use case: Account executives request a deal-specific competitor brief with citations before evaluation-stage calls.
- What makes it stand out: Human-in-the-loop governance + Redis cache performance + deterministic fallback reliability for live demos.

## The Three Operations

### Ingest

- What goes in (documents, conversations, runs, ...): Sales notes, transcript-style notes, product update notes, and analyst-provided markdown sources.
- How it is captured (cognee.remember(...), custom pipeline, ...): Custom local ingest pipeline via source intake and wiki builder paths; optional Cognee indexing is enabled when environment flags/keys are configured.
- Code entry point: sherlock/source_intake.py, sherlock/ingest.py, scripts/ingest_demo_data.py

### Query + Self-improve

- How users query the wiki: Streamlit Battle Card tab with competitor + deal context; app generates cited brief and shows cache status.
- Where feedback comes from (user rating, agent critic, eval, ...): Competitive analyst approve/edit/reject actions in Analyst Review.
- How feedback updates the wiki (SkillRunEntry, edge re-weighting, graph rewrite, ...): Approved pending changes are written into data/wiki/deel.md and cache keys are invalidated so refreshed context is used on subsequent queries.
- Code entry point: sherlock/card_agent.py, sherlock/retrieval.py, sherlock/pending_changes.py, sherlock/pending_generator.py

### Lint

- What "linting" means in your wiki (dedupe, conflict resolution, stale pruning, ...): Deduplicate/triage pending changes, resolve conflicts through analyst review, and prevent stale guidance by forcing explicit approval.
- How it runs (scheduled, on-write, on-demand): On-demand in Analyst Review and on-write when approve/reject actions persist changes.
- Code entry point: sherlock/pending_changes.py, sherlock/pending_generator.py

## Self-Improvement Evidence

Show that the wiki actually got smarter. Concrete before/after beats prose.

### Baseline Run

- Query / task: "Give me the brief on Deel for a Series A US SaaS prospect, 80 employees, expanding into Germany and UK, evaluation stage."
- Result: Structured brief with citations was generated but one key new competitor signal was missing.
- Score (your own metric, judge-readable): 0.875 (7 of 8 expected competitor signals reflected)
- Recorded feedback:

```text
error_type: missing_competitive_signal
error_message: Brief did not reflect newly introduced Deel AI compliance positioning.
feedback: Add AI compliance positioning and a corresponding trap question; refresh Recent Activity and Trending Intelligence.
success_score: 0.875
```

### Improved Run

- Query / task: Same query context as baseline.
- Result: Brief now includes the missing signal, updated trap question, and refreshed recent activity.
- Score: 1.0 (8 of 8 expected competitor signals reflected)
- What changed in the wiki between runs:

```text
Before:
- data/wiki/deel.md lacked the newest AI compliance signal.
- Battle card output had no corresponding trap question.

After:
- Approved pending change appended new AI compliance evidence in wiki content.
- Regenerated brief included new positioning and trap question.
- Cache invalidation ensured refreshed response on the next query.
```

## Architecture

Sherlock follows the required split: Redis as session memory/cache and Cognee/local wiki as durable memory.

```text
[ingest / source intake]
        |
        v
[ Redis - session/cache memory ]   <- hot, per-conversation
        |
        | distillation + approval workflow
        v
[ Cognee/local wiki - permanent memory ]  <- durable, cross-session
        |
        v
[ retrieval + battle-card generation ]
        |
        v
[ analyst feedback -> improve -> cache invalidate ]
```

### Redis-as-session-memory

- What the agent writes into Redis (raw turns, intermediate observations, ...): Brief payloads keyed by competitor/context/wiki hash, plus runtime cache metadata.
- How and when content is distilled into the graph: Ingested source material and approved analyst updates are persisted into wiki content and optional Cognee indexing paths.
- What stays in Redis vs. what gets promoted: Redis stores hot response/cache/session artifacts; durable competitor knowledge and approved updates are promoted into markdown wiki and indexable graph content.
- How distillation quality improved between baseline and improved run: Signal coverage improved from 0.875 to 1.0 after analyst-approved update and cache invalidation.

## Agents / Skills (if any)

```text
Skill path(s): my_skills/code-review/SKILL.md (supporting skill folder in hackathon workspace)
Roles:
  - Ingestor: sherlock/source_intake.py + sherlock/ingest.py
  - Querier: sherlock/card_agent.py + sherlock/retrieval.py
  - Linter: sherlock/pending_changes.py + sherlock/pending_generator.py
  - Critic: Human analyst in Streamlit Analyst Review tab
```

## Reproduction

Commands to reproduce your demo:

```bash
cd /Users/keenan/Documents/cognee-redis-hackathon
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
cp .env.example .env
docker compose up -d redis
python scripts/reset_demo.py
python scripts/ingest_demo_data.py
streamlit run app/streamlit_app.py --server.port 8502
```

Environment variables required:

```text
REDIS_URL=redis://localhost:6379
# Optional for LLM mode (deterministic fallback works without these):
SHERLOCK_USE_LLM=true
OPENAI_API_KEY=<your_key>
LLM_API_KEY=<your_key>
```

## Demo

- Live demo link (Loom, YouTube, etc.) or local instructions: Local demo at <http://localhost:8502> after running commands above. Optional recording can be created from this flow.
- Demo video file: /Users/keenan/Documents/cognee-redis-hackathon/cognee_demo_video.mov
- 3-minute pitch outline: <https://gamma.app/docs/Battle-cards-go-stale-Deals-dont-wait-tt63by8panm4mpq>

```text
1. Problem / idea
   - Competitive intel becomes stale; reps need reliable pre-call guidance.
2. Ingest demo
   - Add/paste source material, then build wiki.
3. Query demo (before improvement)
   - Generate cited brief, show cache miss and baseline output.
4. Self-improve step
   - Approve analyst proposal in Analyst Review.
5. Query demo (after improvement)
   - Regenerate and show improved content + cache behavior.
6. What is next
   - Multi-competitor expansion, richer source connectors, stronger evals.
```

## Links

- Repo: <https://github.com/kklike32/cognee-redis-hackathon>
- Slides / writeup: [https://gamma.app/docs/Battle-cards-go-stale-Deals-dont-wait-tt63by8panm4mpq](https://gamma.app/docs/Battle-cards-go-stale-Deals-dont-wait-tt63by8panm4mpq)
- Demo video: /Users/keenan/Documents/cognee-redis-hackathon/cognee_demo_video.mov
