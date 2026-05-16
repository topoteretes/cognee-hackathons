# Team Submission

## Team

Team name: TBD

Participants:

- TBD

Wiki / project name: Self-Healing Debug Wiki

## Wiki Overview

Self-Healing Debug Wiki is an LLM Knowledge Wiki for developer debugging memory. It stores error reports, attempted fixes, current solutions, deprecated solutions, lint findings, and self-improvement events. The wiki self-improves by detecting when an older debugging fix becomes stale for a newer library version, deprecating the old fix, promoting a corrected fix, and recording the update as an evolution event so future queries return the improved answer.

Domain or data sources:

- Developer error reports
- Stack traces
- Library/version-specific fixes
- Failed and successful fix attempts
- Seeded demo stories for Pydantic, LangChain, and Python collections

Primary use case:

- Give developers and coding agents version-aware debugging fixes that do not silently go stale after library upgrades.

What makes it stand out:

- It treats debugging knowledge as living memory, not static retrieval.
- It records both successful and failed fixes, then uses contradictions as self-improvement signals.
- It has an explicit lint phase for stale, contradictory, low-confidence, or under-versioned wiki entries.
- It exposes the same wiki through a web dashboard and MCP editor tools.
- It uses Redis for fast repeated answers and Cognee for persistent semantic memory over ingested fix text.

## The Three Operations

### Ingest

What goes in:

- Error message
- Optional stack trace
- Programming language
- Library name
- Library/runtime version
- Fix attempted
- Outcome: `worked`, `failed`, or `unknown`
- Source: manual, seed, auto, or editor tool

How it is captured:

- The HTTP API calls `agent.ingest(...)`.
- The MCP tool `save_to_wiki` calls the same ingest path.
- `seed.py` creates the demo knowledge base.
- The ingest path writes structured state into `debugwiki_store.json`.
- The ingest path also calls `cognee_add(text)` and `cognee_cognify()` so the fix story is added to Cognee's `debugwiki` dataset.
- Redis cache entries for the affected library are cleared so stale cached answers do not survive a wiki update.

Code entry point:

- `agent.py` -> `ingest`
- `web.py` -> `POST /api/ingest`
- `server.py` -> `save_to_wiki`
- `seed.py` -> `main`

### Query + Self-improve

How users query the wiki:

- Web dashboard: `POST /api/query`
- MCP editor tool: `search_wiki(error, library, version)`
- Programmatic path: `pipeline.query_and_improve(error, library, version)`

Where feedback comes from:

- Version-aware stale checks in `rules.is_stale`
- Failed reports for the same library and fix
- Deprecated flags and version ranges
- Low confidence scores
- Lint findings generated from wiki state

How feedback updates the wiki:

- If a query finds a stale solution, `agent.self_heal_from_solution` creates a replacement solution.
- The old solution is marked `deprecated`.
- The old solution receives `deprecated_reason`, `valid_until`, and `superseded_by`.
- The wiki page's `current_fix_id` is moved to the new solution.
- The old solution ID is added to `deprecated_fix_ids`.
- An event is written with `before`, `after`, `confidence_delta`, and `reason`.
- Cognee receives an old-to-new update text and is cognified again.
- Redis cache entries for the library are cleared.

Code entry point:

- `pipeline.py` -> `query_and_improve`
- `agent.py` -> `self_heal_from_solution`
- `agent.py` -> `_apply_heal`
- `web.py` -> `POST /api/query`
- `server.py` -> `search_wiki`

### Lint

What linting means in this wiki:

- Detect stale fixes.
- Detect contradictions such as "worked in v1.10, failed in v2.0".
- Detect low-confidence solutions.
- Detect solutions with missing version context.
- Create actionable findings that can be self-healed.

How it runs:

- On demand from the dashboard through `POST /api/lint`.
- On demand from MCP through `check_wiki_health`.
- Cached in Redis as `lint:last_run` for 60 seconds.
- Invalidated when ingest changes the wiki.

Code entry point:

- `agent.py` -> `lint`
- `web.py` -> `POST /api/lint`
- `server.py` -> `check_wiki_health`

## Self-Improvement Evidence

Show that the wiki actually got smarter. Concrete before/after beats prose.

### Baseline Run

Query / task:

```text
PydanticUserError: The `dict` method is deprecated; use `model_dump` instead
library: pydantic
version: 2.0
```

Result:

```text
Before self-heal, the stale historical fix is represented as:
user.dict()
```

Score:

```text
confidence: 0.20 to 0.30 in seeded stale solution examples
status: deprecated or stale
```

Recorded feedback:

```yaml
error_type: stale_versioned_fix
error_message: "PydanticUserError: The `dict` method is deprecated; use `model_dump` instead"
feedback: "user.dict() worked in Pydantic v1.x but failed in v2.0"
success_score: 0.20
```

### Improved Run

Query / task:

```text
PydanticUserError: The `dict` method is deprecated; use `model_dump` instead
library: pydantic
version: 2.0
```

Result:

```text
user.model_dump()
```

Score:

```text
confidence: 0.90 after self-heal
status: active current fix
```

What changed in the wiki between runs:

Before:

```json
{
  "fix": "user.dict()",
  "valid_until": "1.99",
  "deprecated": true,
  "confidence": 0.2
}
```

After:

```json
{
  "fix": "user.model_dump()",
  "valid_from": "2.0",
  "deprecated": false,
  "confidence": 0.9
}
```

The wiki also records an event:

```json
{
  "action": "updated",
  "before": {"fix": "user.dict()"},
  "after": {"fix": "user.model_dump()"},
  "confidence_delta": 0.7
}
```

## Architecture

The intended hackathon pattern is Redis as hot memory and Cognee as durable semantic graph. This repo uses that split, with one important implementation detail: the structured JSON wiki is the canonical source of truth, Redis is a cache, and Cognee is the semantic search layer built from ingested text.

```text
[ingest / agent turns]
        |
        v
[ debugwiki_store.json - structured wiki source of truth ]
        |
        +--> [ Redis - fast cached query/lint responses ]
        |
        +--> [ Cognee - permanent semantic graph over fix text ]
        |
        v
[ recall / query pipeline ]
        |
        v
[ rules + feedback -> self-heal -> improved wiki ]
```

Practical query order:

```text
User query
  -> Redis cache
  -> structured JSON wiki match
  -> Cognee semantic graph search
  -> Claude fallback
  -> save new/improved state
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

## Redis-as-session-memory

What the agent writes into Redis:

- Query result JSON keyed by hash of `error:library:version`.
- Lint result JSON under `lint:last_run`.

How and when content is distilled into the graph:

- Ingest: each error/fix/outcome story is converted into text and sent to Cognee.
- Seed: demo stories are added to Cognee and cognified.
- Self-heal: old-to-new fix updates are added to Cognee and cognified.

What stays in Redis vs. what gets promoted:

- Redis keeps short-lived cached API responses only.
- Structured durable knowledge is written to `debugwiki_store.json`.
- Semantic durable knowledge is promoted to Cognee through `cognee.add` and `cognee.cognify`.

How distillation quality improved between baseline and improved run:

- Baseline memory contains an old successful fix and a newer failure.
- Lint/query feedback recognizes the contradiction.
- Self-heal promotes a version-correct fix and records the before/after event.
- Future queries return the corrected fix from durable wiki memory.

Note:

- This repo does not store raw conversation turns in Redis. Redis is used as a fast cache/context layer, while durable state is in JSON and Cognee.

## Agents / Skills

No external skill packs are required. The repo implements lightweight agent roles as modules:

Skill path(s):

- Not applicable.

Roles:

- Ingestor: `agent.ingest`, `seed.py`, `server.save_to_wiki`
- Querier: `pipeline.query_and_improve`, `server.search_wiki`
- Linter: `agent.lint`, `server.check_wiki_health`
- Critic: `rules.is_stale`, `rules.check_known_fix`

## Reproduction

Commands to reproduce the demo:

```powershell
cd C:\AI\Projects\WikiStack2\debug_wiki
pip install -r requirements.txt
copy .env.example .env
REM Edit .env and set required keys.
python seed.py
python web.py
```

In another terminal:

```powershell
python server.py
```

Useful API checks:

```powershell
Invoke-RestMethod http://localhost:8000/api/health
Invoke-RestMethod http://localhost:8000/api/iq
Invoke-RestMethod http://localhost:8000/api/wiki
```

Query example:

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8000/api/query `
  -ContentType "application/json" `
  -Body '{"error":"PydanticUserError: The dict method is deprecated; use model_dump instead","library":"pydantic","version":"2.0"}'
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

Live demo link:

```text
TBD
```

Local instructions:

1. Run `python seed.py`.
2. Run `python web.py`.
3. Open `http://localhost:8000`.
4. Show `/api/health` with Redis status.
5. Query the Pydantic v2 error.
6. Run lint.
7. Self-heal a high-severity finding.
8. Query again and show the corrected fix.
9. Repeat the same query to show Redis cache hit in the terminal.
10. Show `.cognee_data` / `.cognee_system` as graph memory directories.

3-minute pitch outline:

1. Problem / idea: debugging fixes expire as libraries change; static RAG can repeat stale advice.
2. Ingest demo: save successful and failed fix attempts into the wiki.
3. Query demo before improvement: show the stale fix pattern and version mismatch.
4. Self-improve step: lint or query detects staleness, deprecates old fix, promotes new fix.
5. Query demo after improvement: same query returns corrected answer from durable wiki state.
6. What is next: stronger Cognee health checks, richer feedback metrics, scheduled linting, and OpenAI reasoning model swap if desired.

## Links

Repo:

```text
TBD
```

Slides / writeup:

```text
TBD
```

Anything else:

- Codebase documentation: `CODEBASE_DOCUMENTATION.md`
- Manual tests: `TESTS.md`
- Cursor integration: `connect/cursor.json`
- Claude Code integration: `connect/claude_code.sh`

## Honest Implementation Notes

- Redis is proven as a cache path when dependencies and Redis are configured.
- Cognee is wired into seed, ingest, query, and self-heal, but may be flaky on Windows because of graph/path/file-lock issues.
- `/api/health` checks whether an Anthropic key exists for `cognee: true`; it is not a full graph-health check.
- The structured JSON wiki is the most reliable demo path.
- The dashboard currently has some API contract drift with `web.py`; the backend API and MCP paths are the more reliable source of truth.
