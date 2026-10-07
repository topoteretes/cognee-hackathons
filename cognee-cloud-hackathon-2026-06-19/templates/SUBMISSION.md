# Team Submission

## Team

- Team name: Citadel Archive
- Participants: Hrishikesh and Sarthi
- Company Brain / project name: Citadel Archive

## Company Brain Overview

Citadel Archive is an Organization Vault: a company brain for teams and agents that continuously ingests approved project sources, turns them into structured Cognee memory, exposes the memory through a web UI, HTTP API, and hosted MCP server, and then improves itself from source activity, user feedback, and bounded optimization passes. The brain is designed for real company usage rather than toy retrieval: every answer is provenance-carrying, every write is access-controlled, conflicts stay visible until resolved, and self-improvement is additive so the system gets smarter without silently deleting or overwriting prior knowledge.

- Repo: [https://github.com/Hrishikesh332/Citadel-Archive](https://github.com/Hrishikesh332/Citadel-Archive)
- Hosted deployed URL: [https://citadel-archive.onrender.com](https://citadel-archive.onrender.com)

Cognee Company Brain Workflow

- Domain or data sources: GitHub organization activity, README/SKILL/docs repository content, Obsidian vault notes, direct teammate and agent contributions, search/feedback events, and Cognee graph/vector/session memory.
- Primary use case: Give teammates and coding agents a shared, source-linked memory for architecture decisions, current repository momentum, runbooks, product knowledge, and reusable project context.
- What makes it stand out: It combines Cognee memory with production-grade company-brain controls: role-scoped tokens, private seat nodes, curated central memory, provenance envelopes, hosted MCP tools, audit logs, conflict handling, source-learning jobs, and a bounded self-improvement loop.

## The Three Operations

### Ingest

- What goes in: Curated project notes, agent contributions, Obsidian documents, GitHub daily updates, repository READMEs/SKILL/docs, and source-linked decisions.
- How it is captured: All accepted source material flows through the Learning Process, which filters, optionally enriches/chunks, routes to the correct memory tier, attaches provenance metadata, and calls Cognee `remember(...)`. Session-scoped writes use `session_id=...`; durable company knowledge is written without a session or promoted into the central graph.
- Code entry point: `kb/learning.py`, `kb/service.py`, `kb/cognee_client.py`, `kb/github_sync.py`, `kb/repo_content_sync.py`, `kb/server.py`.

### Query + Self-improve

- How users query the Company Brain: Users search from the web UI, direct HTTP (`POST /search`, `GET /api/knowledge`), or hosted MCP (`citadel_search`, `citadel_get_document`, `citadel_get_mesh`). Search results include a `_citadel` provenance envelope with dataset, rank, content hash, source metadata, and document drill-down information.
- Where feedback comes from: Teammate ratings on answers, MCP `citadel_record_feedback`, direct `POST /feedback`, source-learning runs, GitHub/repo-content sync outcomes, and the optimization endpoint's review of recent mesh activity.
- How feedback updates the brain: Feedback is written to Cognee session feedback and can trigger `cognee.improve(...)`. Source-learning and optimization runs then add better summaries/tags back through the same Learning Process, so improvement is source-linked and additive rather than a destructive rewrite.
- Code entry point: `kb/service.py`, `kb/self_improve.py`, `kb/learning_agent.py`, `kb/server.py`, `kb/mcp_server.py`.

### Lint

- What "linting" means in this brain: Reject low-value or duplicate inputs, normalize tags, block suspicious source material before ingest, detect visible Knowledge Conflicts, keep private seat memory from leaking into central memory, and avoid logging raw secrets or sensitive queries.
- How it runs: On write for ingest filtering, persistent ingest-ledger dedupe, security scanning, role/scope enforcement, conflict detection, and provenance wrapping; on demand or scheduled for self-improvement, source sync, and backup/audit inspection.
- Code entry point: `kb/service.py`, `kb/ingest_ledger.py`, `kb/learning.py`, `kb/github_sync.py`, `kb/repo_content_sync.py`, `kb/server.py`.

## Self-Improvement Evidence

### Baseline Run

- Query / task: "What shipped recently in the Masumi organization, and what source supports it?"
- Result: The baseline system could retrieve a plain chunk from Cognee, but an empty vector result for the GitHub dataset produced no useful answer unless the user knew which source state file to inspect.
- Score: 0.42 / 1.0. The answer had partial recall but weak provenance, no fallback when Cognee had no indexed result, and no clear route for improvement.
- Recorded feedback:

```text
error_type: weak_source_grounding
error_message: Answer missed the persisted GitHub digest when Cognee recall returned no data.
feedback: Add a fallback over the GitHub sync state, expose source provenance, and run improve after feedback/source ingest.
success_score: 0.42
```

### Improved Run

- Query / task: "What shipped recently in the Masumi organization, and what source supports it?"
- Result: The improved brain searches the configured session/dataset, falls back to the persisted GitHub digest when needed, returns source-linked hits, and includes `_citadel` metadata so agents can drill down to the backing document.
- What changed in the brain between runs: Feedback and source-sync results caused a new fallback/search path, provenance envelope, ingest ledger, and Cognee improvement call. The Learning Process now reuses the same route for GitHub digests, repo-content files, teammate contributions, and optimization notes.

```text
Before:
Search could return an empty answer for the company activity question even though the GitHub sync state contained a useful digest. Results also lacked a stable provenance contract for agents.

After:
Search returns source-backed results such as github_sync_state / repo_content with dataset, session, content hash, source URL, and document drill-down metadata. Follow-up feedback triggers Cognee improve for the relevant dataset/session.
```

Additional concrete checks from the reference implementation:

- `test_search_falls_back_to_persisted_github_digest` proves the brain can answer from the persisted GitHub digest when Cognee recall is empty.
- `test_search_feedback_improve_flow_uses_cognee_session` proves feedback is recorded against the Cognee QA result and triggers `improve(dataset="notes", session_ids=["personal-session"])`.
- `test_optimize_endpoint_is_admin_only_bounded_and_audited` proves the self-improvement pass is bounded, admin-gated, audited, and deterministic when no LLM key is available.

## Architecture

```text
[teammates, agents, GitHub, Obsidian]
        |
        v
[Citadel API / Web UI / Hosted MCP]
        |
        v
[Learning Process]
  - pre-ingest filtering
  - LLM enrichment/chunking when enabled
  - tag normalization
  - conflict detection
  - provenance metadata
        |
        v
[Cognee instance]
  - session memory: private seat/session scratchpad (session_id=...)
  - permanent graph: central Organization Vault knowledge (no session_id)
  - vector + graph recall
        |
        v
[Search, MCP tools, mesh graph, document drill-down]
        |
        v
[Feedback + source-learning + optimization -> improve]
```

The core split is seat/session memory versus central durable memory. A user's private node writes to `seat:<slug>` with a matching session such as `seat-bob`, while company-ready knowledge is promoted to the central dataset (`masumi-network`). Promotion is explicit: org-bound tags such as `org-ready`, `vault-contribution`, `repo-content`, and `product-knowledge` decide whether content remains private, goes straight to central memory, or dual-writes private node plus central graph.

### Cognee Instance

- What the team writes to session memory (`session_id=...`): Raw agent/user turns, private seat notes, GitHub daily sync session material (`masumi-github-daily`), repo-content sync session material (`masumi-repo-content`), and feedback-linked QA context.
- What goes straight to the permanent graph (no `session_id`): Curated vault contributions, organization-ready notes, repository product knowledge, source-linked decisions, and self-improvement optimization notes.
- How and when content is distilled from session memory into the permanent graph: Distillation is triggered by explicit promotion tags, contribution writes, source-learning runs, and improvement passes. The Learning Process decides target datasets, then Cognee `remember(...)` and `improve(...)` materialize durable graph memory.
- What stays session-only vs. what gets promoted: Raw personal scratchpad, local seat memory, and transient agent context stay scoped to the session/private node. Decisions, source facts, runbooks, docs, and organization-ready contributions are promoted to central memory.
- Proof the brain got smarter between baseline and improved run: After adding fallback recall, provenance metadata, dedupe, and improve-on-feedback, the same company-activity query returns source-linked answers instead of an empty or uncited response.

For the hackathon demo, the same two tiers are intended to run inside the dedicated Cognee instance by calling `cognee.serve(url=os.environ["COGNEE_INSTANCE_URL"], api_key=os.environ["COGNEE_API_KEY"])` before Citadel performs `remember`, `recall`, and `improve`. The project repository is [https://github.com/Hrishikesh332/Citadel-Archive](https://github.com/Hrishikesh332/Citadel-Archive), and the deployed version is available at [https://citadel-archive.onrender.com](https://citadel-archive.onrender.com).

## Agents / Skills (if any)

```text
Skill path(s):
  - SKILL.md
  - hosted /skills/connect
  - hosted /skills/vault
  - hosted /skills/boundary
  - my_skills/qa-answerer/SKILL.md

Roles:
  - Ingestor: LearningProcess + citadel_ingest / citadel_contribute
  - Querier: citadel_search, /api/knowledge, qa-answerer skill
  - Linter: PreIngestFilter, IngestLedger, security scan, KnowledgeConflictStore
  - Critic: feedback endpoint, Cognee session feedback, SelfImprovement optimizer
  - Source-learning agent: GitHubOrgSyncer + RepoContentSyncer + LearningAgent
```

## Reproduction

Commands to reproduce the demo:

```bash
cd /Users/hrishikesh/Documents/cogneex/Citadel-Archive
uv sync --dev

export COGNEE_INSTANCE_URL="https://your-instance.cognee.ai"
export COGNEE_API_KEY="ck_..."
export LLM_API_KEY="<event-provided-llm-key>"
export CITADEL_ADMIN_KEY="local-admin"
export CITADEL_WRITER_KEYS="local-writer"
export CITADEL_READER_KEYS="local-reader"
export CITADEL_DEFAULT_DATASET="personal"
export CITADEL_SEARCH_DEFAULT_DATASET="masumi-network"
export CITADEL_GITHUB_ORG="masumi-network"
export CITADEL_GITHUB_SYNC_DATASET="masumi-network"
export CITADEL_GITHUB_SYNC_SESSION="masumi-github-daily"
export CITADEL_REPO_CONTENT_SYNC_ENABLED=true

uv run uvicorn kb.server:app --reload --port 8000

# In another terminal:
curl -fsS http://localhost:8000/healthz
curl -fsS -X POST http://localhost:8000/admin/session \
  -H "Content-Type: application/json" \
  --data '{"access_key":"local-admin"}'

# Demo ingest through the Learning Process:
curl -fsS -X POST http://localhost:8000/api/contribute \
  -H "Authorization: Bearer local-writer" \
  -H "Content-Type: application/json" \
  --data '{"title":"Decision: use Citadel as company brain","content":"Citadel stores source-linked project memory and exposes it through MCP.","tags":["decision","org-ready"],"source_url":"https://github.com/Hrishikesh332/Citadel-Archive"}'

# Demo query:
curl -fsS -X POST http://localhost:8000/search \
  -H "Authorization: Bearer local-reader" \
  -H "Content-Type: application/json" \
  --data '{"query":"What is Citadel used for?","dataset":"masumi-network","top_k":3}'

# Demo improvement:
curl -fsS -X POST http://localhost:8000/feedback \
  -H "Authorization: Bearer local-writer" \
  -H "Content-Type: application/json" \
  --data '{"qa_id":"qa-1","score":1,"text":"Useful answer with source grounding.","dataset":"masumi-network","session_id":"masumi-github-daily"}'

curl -fsS -X POST http://localhost:8000/api/learning-agent/optimize \
  -H "Authorization: Bearer local-admin" \
  -H "Content-Type: application/json" \
  --data '{"dry_run":true,"max_items":5}'
```

Environment variables required:

```text
COGNEE_INSTANCE_URL
COGNEE_API_KEY
LLM_API_KEY
CITADEL_ADMIN_KEY
CITADEL_WRITER_KEYS
CITADEL_READER_KEYS
CITADEL_DEFAULT_DATASET
CITADEL_SEARCH_DEFAULT_DATASET
CITADEL_GITHUB_ORG
CITADEL_GITHUB_TOKEN              # optional, for private/high-rate GitHub sync
CITADEL_GITHUB_SYNC_DATASET
CITADEL_GITHUB_SYNC_SESSION
CITADEL_REPO_CONTENT_SYNC_ENABLED
OPENROUTER_API_KEY                # optional alternative for enrichment/optimization
```

## Demo

- Demo video: [https://youtu.be/wgMGPM7yVJM](https://youtu.be/wgMGPM7yVJM)
- Live demo / local instructions: Run the local FastAPI service, open `http://localhost:8000/`, log in with the admin key, then show the Search, Ingest, Sources, Activity, Access, and MCP sections. For the hosted demo, use [https://citadel-archive.onrender.com](https://citadel-archive.onrender.com) with a role-scoped token. Source code is at [https://github.com/Hrishikesh332/Citadel-Archive](https://github.com/Hrishikesh332/Citadel-Archive).
- 3-minute pitch outline:

```text
1. Problem / idea
   Companies do not just need document retrieval; they need a shared, governed memory that agents can read and improve safely.

2. Ingest demo
   Add a source-linked contribution and show GitHub/repo-content/Obsidian sources feeding the Learning Process.

3. Query demo (before improvement)
   Ask a company activity question and show why plain recall without provenance/fallback is not enough.

4. Self-improve step
   Record feedback or run the bounded optimizer; show Cognee improve plus additive optimization notes.

5. Query demo (after improvement)
   Ask again and show source-linked results with dataset, content hash, provenance, and document drill-down.

6. What is next
   Move all tiers fully into the managed Cognee instance, add richer skill-run scoring, and expand the hosted MCP/seat-node model for teams.
```

## Links

- Repo: [https://github.com/Hrishikesh332/Citadel-Archive](https://github.com/Hrishikesh332/Citadel-Archive)
- Demo video: [https://youtu.be/wgMGPM7yVJM](https://youtu.be/wgMGPM7yVJM)
- Hosted deployed URL: [https://citadel-archive.onrender.com](https://citadel-archive.onrender.com)
- Agent discovery manifest: [https://citadel-archive.onrender.com/.well-known/citadel.json](https://citadel-archive.onrender.com/.well-known/citadel.json)
- Hosted skills: [https://citadel-archive.onrender.com/skills](https://citadel-archive.onrender.com/skills)

