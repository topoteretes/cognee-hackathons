# Team Submission

## Team

- Team name: Ali
- Participants: Ali
- Wiki / project name: Self-Healing Debug Wiki

## Wiki Overview

Self-Healing Debug Wiki is an LLM Knowledge Wiki for developer debugging memory. It stores error reports, attempted fixes, current solutions, deprecated solutions, lint findings, and self-improvement events. The wiki self-improves by detecting when an older debugging fix becomes stale for a newer library version, deprecating the old fix, promoting a corrected fix, and recording that update as an evolution event so future queries return the improved answer instead of repeating stale advice.

- Domain or data sources: Developer error reports, stack traces, library versions, attempted fixes, worked/failed outcomes, and seeded examples for Pydantic, LangChain, and Python collections.
- Primary use case: Give developers and coding agents version-aware debugging fixes that do not silently go stale after library upgrades.
- What makes it stand out: It treats debugging knowledge as living memory. Failed fixes become feedback, lint finds stale or contradictory wiki entries, and self-heal promotes corrected fixes into durable wiki state.

## The Three Operations

### Ingest

- What goes in (documents, conversations, runs, ...): Error messages, optional stack traces, programming language, library name, library/runtime version, fix attempted, outcome (`worked`, `failed`, or `unknown`), and source (`manual`, `seed`, `auto`, or editor tool).
- How it is captured (`cognee.remember(...)`, custom pipeline, ...): A custom pipeline writes structured entities to `debugwiki_store.json`, then sends a text summary to Cognee with `cognee.add(...)` and `cognee.cognify()` through `cognee_client.py`. Redis cache entries for the affected library are cleared after ingest.
- Code entry point: `agent.py -> ingest`, `web.py -> POST /api/ingest`, `server.py -> save_to_wiki`, `seed.py -> main`.

### Query + Self-improve

- How users query the wiki: Users query through the web API `POST /api/query`, the dashboard, or the MCP tool `search_wiki(error, library, version)`.
- Where feedback comes from (user rating, agent critic, eval, ...): Feedback comes from version-aware stale checks, failed reports for the same library/fix, deprecated flags, valid version ranges, confidence scores, and lint findings. The critic logic lives in `rules.py`.
- How feedback updates the wiki (`SkillRunEntry`, edge re-weighting,
  graph rewrite, ...): When a query finds stale knowledge, `agent.self_heal_from_solution` creates a replacement solution, marks the old solution deprecated, updates the wiki page's `current_fix_id`, records an event with before/after snapshots and confidence delta, adds the update text to Cognee, cognifies the graph again, and clears Redis cache for that library.
- Code entry point: `pipeline.py -> query_and_improve`, `agent.py -> self_heal_from_solution`, `agent.py -> _apply_heal`, `web.py -> POST /api/query`, `server.py -> search_wiki`.

### Lint

- What "linting" means in your wiki (dedupe, conflict resolution, stale
  pruning, ...): Linting means auditing wiki knowledge for stale fixes, contradictions like "worked in v1.10 but failed in v2.0", low-confidence solutions, deprecated solutions, and missing version context.
- How it runs (scheduled, on-write, on-demand): It runs on demand through `POST /api/lint` or the MCP tool `check_wiki_health`. Results are cached in Redis under `lint:last_run` for 60 seconds and invalidated when ingest changes the wiki.
- Code entry point: `agent.py -> lint`, `web.py -> POST /api/lint`, `server.py -> check_wiki_health`.

## Self-Improvement Evidence

Show that the wiki actually got smarter. Concrete before/after beats prose.

### Baseline Run

- Query / task: Ask for a fix for `PydanticUserError: The dict method is deprecated; use model_dump instead` with `library: pydantic` and `version: 2.0`.
- Result: The stale historical fix is represented as `user.dict()`, which worked for Pydantic v1 but fails in Pydantic v2.
- Score (your own metric, judge-readable): Seeded stale solution confidence is `0.20` to `0.30`; status is deprecated/stale.
- Recorded feedback:

```text
error_type: stale_versioned_fix
error_message: PydanticUserError: The dict method is deprecated; use model_dump instead
feedback: user.dict() worked in Pydantic v1.x but failed in v2.0
success_score: 0.20
```

### Improved Run

- Query / task: Ask the same Pydantic v2 query after lint/self-heal.
- Result: The wiki returns `user.model_dump()`.
- Score: Improved solution confidence is `0.90`; status is active/current.
- What changed in the wiki between runs: The old solution was deprecated, a new solution was created, the wiki page was repointed to the new solution, and an event recorded the before/after fix and confidence delta.

```text
Before:
fix: user.dict()
valid_until: 1.99
deprecated: true
confidence: 0.20

After:
fix: user.model_dump()
valid_from: 2.0
deprecated: false
confidence: 0.90
```

## Architecture

Short diagram or bullet list of components. The hackathon's core pattern is
**Redis as session memory, distilled into Cognee's permanent knowledge graph**
-- show how your wiki uses that split.

```text
[ingest / agent turns]
        |
        v
[ debugwiki_store.json - structured wiki source of truth ]
        |
        +--> [ Redis - hot cache for query/lint responses ]
        |
        | distillation: error/fix/outcome text promoted on seed, ingest, self-heal
        v
[ Cognee - permanent semantic graph over fix text ]
        |
        v
[ recall / agent loop: Redis -> JSON wiki -> Cognee -> Claude ]
        |
        v
[ feedback -> lint/stale rules -> self-heal -> improved wiki ]
```

Components:

- `web.py`: FastAPI dashboard and HTTP API.
- `server.py`: FastMCP server for editor integration.
- `pipeline.py`: query pipeline.
- `agent.py`: ingest, lint, and self-heal mutations.
- `rules.py`: stale-fix and known-upgrade logic.
- `store.py`: JSON persistence.
- `cache.py`: Redis cache layer.
- `cognee_client.py`: Cognee graph memory wrapper.
- `evolution.py`: IQ score and timeline.

### Redis-as-session-memory

- What the agent writes into Redis (raw turns, intermediate observations, ...): Query result JSON keyed by hash of `error:library:version`, plus lint result JSON under `lint:last_run`.
- How and when content is distilled into the graph: Seed, ingest, and self-heal convert structured fix stories into text and send them to Cognee with `cognee.add(...)` and `cognee.cognify()`.
- What stays in Redis vs. what gets promoted: Redis keeps short-lived cached API responses. Durable structured state is promoted to `debugwiki_store.json`; durable semantic memory is promoted to Cognee's `debugwiki` dataset.
- How distillation quality improved between baseline and improved run: Baseline memory contains an old successful fix and a newer failure. Lint/query feedback detects the contradiction, self-heal promotes the version-correct fix, and future queries return the corrected durable wiki answer.

## Agents / Skills (if any)

If you used skill packs or multi-agent roles:

```text
Skill path(s): none required; implemented as repo modules
Roles:
  - Ingestor: agent.ingest, seed.py, server.save_to_wiki
  - Querier: pipeline.query_and_improve, server.search_wiki
  - Linter: agent.lint, server.check_wiki_health
  - Critic: rules.is_stale, rules.check_known_fix
```

## Reproduction

Commands to reproduce your demo:

```bash
cd debug_wiki
pip install -r requirements.txt
cp .env.example .env
python -c "print('Edit .env and set required keys before continuing')"
python seed.py
python web.py
```

In another terminal:

```bash
cd debug_wiki
python server.py
```

Useful checks:

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/iq
curl http://localhost:8000/api/wiki
```

Example query:

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"error":"PydanticUserError: The dict method is deprecated; use model_dump instead","library":"pydantic","version":"2.0"}'
```

Environment variables required:

```text
ANTHROPIC_API_KEY
OPENAI_API_KEY
REDIS_URL
COGNEE_DATA_DIR
COGNEE_SYSTEM_DIR
WIKI_STORE_PATH
DASHBOARD_PORT
```

`EMBEDDING_API_KEY` can be set instead of relying on `OPENAI_API_KEY` for Cognee embeddings.

## Demo

- Live demo link (Loom, YouTube, etc.) or local instructions: TBD. Local demo: run `python seed.py`, run `python web.py`, open `http://localhost:8000`, show `/api/health`, run a Pydantic query, run lint/self-heal, query again, then repeat the query to show Redis cache hit.
- 3-minute pitch outline:

```text
1. Problem / idea
   Debugging fixes expire as libraries change; static RAG can repeat stale advice.
2. Ingest demo
   Save successful and failed fix attempts into the wiki.
3. Query demo (before improvement)
   Show a stale/version-mismatched fix pattern.
4. Self-improve step
   Lint or query detects staleness, deprecates old fix, promotes new fix.
5. Query demo (after improvement)
   Same query returns corrected answer from durable wiki state.
6. What is next
   Stronger Cognee health checks, richer feedback metrics, scheduled linting, and OpenAI reasoning model support.
```

## Links

- Repo: TBD
- Slides / writeup: TBD
- Anything else:
  - Codebase documentation: `CODEBASE_DOCUMENTATION.md`
  - Manual tests: `TESTS.md`
  - Cursor integration: `connect/cursor.json`
  - Claude Code integration: `connect/claude_code.sh`
