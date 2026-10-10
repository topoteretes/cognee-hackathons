# Team Submission

## Team

- Team name: Kevin Cress
- Participants: Kevin Cress 
- Wiki / project name: What Remains

## Wiki Overview

What Remains is an AI-powered AIDS memorial archive that turns primary source documents like letters, biographies, quilt panel records, oral histories, etc., into a living knowledge graph. It ingests documents using Cognee's `remember()` pipeline, extracts named entities (persons, organizations, places, events) and relationships between them, and stores everything in a persistent graph that improves over time. Self-improvement happens when a search interaction is scored: the task, result, and score are recorded as a QA entry in Redis session memory, then `cognee.improve()` is called to synthesize that interaction into new graph nodes and edges and re-enrich the full relationship structure. Each scored run adds knowledge — the graph grows and the connections between people, organizations, and events become richer. (For the demo the improve/linting is done via a terminal.) A domain-aware pruning step uses an LLM to scan every node and remove anything unrelated to the AIDS crisis, keeping the knowledge graph focused and meaningful.

## The Three Operations

### Ingest

- What goes in: PDF and TXT documents — memorial biographies, oral histories, finding aids, activist records
- How it is captured: `cognee.remember(file_path, dataset_name="what_remains")` via the `/ingest` and `/ingest-path` endpoints.
- Code entry point: `app.py:324` (`POST /ingest`), `app.py:350` (`POST /ingest-path`), `app.py:572` (`POST /remember`)

### Query + Self-improve

- How users query the wiki: Natural language via `GET /search?q=...` — searches Redis session memory first, falls through to the permanent Cognee graph. The `/api/person` endpoint returns structured entity data (bio, connections) for a named person.
- Where feedback comes from: Admin form on `/upload` — a human scores the result 0–1 after reviewing it. The `demo.py` script automates this with a fixed score of 0.92 to demonstrate the loop.
- How feedback updates the wiki: `/improve` records the interaction as a `QAEntry` (question, answer, feedback_score) in session memory, then calls `cognee.improve()` which synthesizes the interaction into new permanent graph nodes and re-enriches triplet embeddings across the dataset. `/lint` is then run to consolidate the new relationships into the full graph structure.
- Code entry point: `app.py:370` (`GET /search`), `app.py:588` (`POST /improve`)

### Lint

- What "linting" means: Two operations run in sequence. First, `POST /lint` rebuilds triplet embeddings and re-enriches relationships across the entire `what_remains` dataset — resolves conflicting edges, reconnects orphaned nodes, reprocesses entity co-references. Then `POST /prune` runs a domain-aware curation pass: every node label is sent to an LLM (gpt-4o-mini) which classifies whether it belongs to the AIDS crisis / LGBTQ memorial domain. Nodes that don't belong — historical figures, unrelated events, off-topic dates — are deleted from the graph engine directly. The result is a graph that stays focused on its domain no matter what incidental references appear in the source documents.
- How it runs: On-demand. Both called automatically at the end of every `demo.py` run (lint → prune → after-snapshot). Can also be triggered individually via the admin UI or curl.
- Code entry point: `app.py` `POST /lint`, `POST /prune`

## Self-Improvement Evidence

### Baseline Run

- Query / task: `"AIDS memorial artist"`
- Result: `"Cleve Jones — initiator/creator of the AIDS Memorial Quilt (NAMES Project)."`
- Score: 0.92 (positive feedback submitted)
- Recorded feedback: task + result summary recorded as QA entry with `feedback_score: +1`

```text
error_type: none
error_message: none
feedback: "Successfully retrieved memorial records matching 'AIDS memorial artist'. Entities, relationships, and life details extracted from ingested files."
success_score: 0.92
```

Graph state before improve + lint:
```text
nodes: 561
edges: 1604
```

### Improved Run

- Query / task: `"AIDS memorial artist"` (same query)
- Result: `"Cleve Jones — initiator/creator of the AIDS Memorial Quilt (NAMES Project)."`
- Score: n/a (post-improvement)
- What changed in the wiki between runs: `cognee.improve()` synthesized the scored QA interaction into 17 new graph nodes and 27 new edges. `cognee.lint()` re-enriched the full relationship structure to integrate the new knowledge.

```text
Before:
  nodes: 561
  edges: 1604

After (improve + lint + prune):
  nodes: 578  (Δ +17 from improve, minus off-topic nodes removed by prune)
  edges: 1631  (Δ +27)
  pruned: off-topic nodes removed (e.g. "Timothy McVeigh", "Vietnam Women's Memorial",
          "1993 as the year the Vietnam Women's Memorial was added") — printed explicitly
          in demo terminal output
```

## Architecture

```text
[PDF / TXT documents]
        |
        v POST /ingest, /ingest-path
[ cognee.remember() ]
        |
        v
[ Cognee pipeline: chunk → embed → extract entities → build triplets ]
        |
        +----> [ LanceDB — vector store (persistent) ]
        |
        +----> [ Cognee graph DB — nodes & edges (persistent) ]

[ GET /search ]
        |
        v
[ Redis — session memory ]   <- hot, scoped to session_id
        |
        | cognee.recall() falls through to →
        v
[ Cognee graph — permanent, cross-document ]
        |
        v
[ result returned to user ]
        |
        v POST /improve (scored by human or demo script)
[ QAEntry written to session memory ]
        |
        v cognee.improve()
[ new nodes synthesized, feedback applied, embeddings rebuilt ]
        |
        v POST /lint
[ cognee.improve() (no feedback) — consolidates full graph structure ]
        |
        v POST /prune
[ LLM scans every node label → deletes anything outside AIDS/LGBTQ domain ]
```

### Redis-as-session-memory

- What gets written into Redis: Search context scoped by `session_id`; QA entries from `/improve` calls (task, result summary, feedback score)
- How and when content is distilled into the graph: `cognee.improve()` bridges session QA entries into the permanent graph — synthesizing new nodes from the interaction text and applying feedback as weights
- What stays in Redis vs. what gets promoted: Raw session working memory stays in Redis (TTL-bounded); QA entries and their synthesized entity relationships get promoted into the permanent Cognee graph
- How distillation quality improved: Each scored improve call added new graph nodes derived from the Q&A text — the +17 nodes / +27 edges delta is directly from session content being promoted into the permanent graph

## Agents / Skills

```text
Skill path(s): my_skills/memorial-extraction/SKILL.md
Roles:
  - Ingestor: cognee.remember() pipeline — chunks docs, extracts entities via memorial-extraction skill, builds graph
  - Querier: cognee.recall() — searches Redis session then falls through to permanent graph
  - Linter: cognee.improve(dataset="what_remains") — re-enriches relationships, no feedback input
  - Critic: human admin via /upload form, or demo.py with fixed score
```

The `memorial-extraction` skill defines entity types (Person, Organization, Place, Event, Document) and relationships (COMMEMORATES, DIED_OF, LOVED, PARTICIPATED_IN, LOCATED_IN). It is re-ingested into the `what_remains_skills` dataset on every `/improve` call so edits to the skill are picked up without polluting the archive graph.

## Reproduction

```bash
# 1. Start Redis
docker run -p 6379:6379 redis:latest

# 2. Start the API server
uvicorn app:app --reload

# 3. Run the before/after demo (in a second terminal)
python demo.py --folder ./Data/DocsToIngestDemo --query "AIDS memorial artist"

# 4. View the graph
open http://localhost:8000/graph-view

# 5. Use the admin UI
open http://localhost:8000/upload
```

Environment variables required:

```text
OPENAI_API_KEY=sk-...      # or LLM_API_KEY
REDIS_URL=redis://localhost:6379
```

## Demo

- Live demo link: n/a
- 3-minute pitch outline:
Problem / idea — AIDS memorial archives exist but are static; people, relationships,
   and stories aren't connected across documents. What Remains makes the archive alive.

## Links

- Repo: https://github.com/kevrcress/HackathonWhatRemains
