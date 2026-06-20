# Team Submission

> **In-progress note:** team/participants and the live demo link are being
> finalized before the submission deadline; everything technical below is real
> and runnable today (`COGNEE_MODE=demo` gives a deterministic judge-safe run).

## Team

- Team name: Intuivo _(update if different)_
- Participants: @happyhackerbird (GitHub) · `zeusintuivo` (GitLab) _(confirm/extend)_
- Company Brain / project name: **Cognee LLM Wiki — German Cycling-Industry Brain**

## Company Brain Overview

A self-improving local **company brain** for the German bicycle industry.
Cognee (local, Ollama-backed) extracts a knowledge graph from German
cycling-market sources; an agent authors durable, English, **cited** wiki pages
that carry **German verbatim evidence**; useful query answers are *filed back*
into the brain; and a **lint** pass catches contradictions and gaps so the
brain gets sharper every cycle. It is built on top of the **IlnamiquiliaTsaa**
Rust verbatim-memory engine, which supplies the immutable raw-source layer and
a compact **AAAK** index.

- **Domain / data sources:** German road-cycling market — velophil.berlin
  (trade press), **ZIV** (Zweirad-Industrie-Verband market statistics), **VSF**
  (Verband Selbständiger Fahrradhändler — trade/repair side).
- **Primary use case:** a bike-industry analyst / retailer team's brain that
  ingests scattered German market knowledge and produces trend syntheses and
  **2025/2026 predictions**, with every claim traceable to a verbatim German
  quote.
- **What makes it stand out:** a heritage substrate (method-of-loci +
  Zettelkasten verbatim engine, a compact **AAAK** catalog instead of a naive
  `index.md`), **verbatim provenance** for every synthesized claim, and a clean
  two-role split — **Cognee = machine memory/graph**, **the agent = the
  human-readable synthesis**.

## The Three Operations

### Ingest

- **What goes in:** immutable German source excerpts under `raw/` (ZIV,
  velophil, VSF).
- **How it is captured:** `POST /ingest` → `cognee.add(text, dataset_name=...)`
  + `cognee.cognify(datasets=[...])`; returns `entities`, `relations`,
  `summary_draft`, `affected_pages`, and contradiction candidates. The agent
  then writes/updates `sources/`, `entities/`, `concepts/` pages, refreshes
  `index.md`, and appends to `log.md` (per `wiki/CLAUDE.md`).
- **Code entry point:** `cognee-sidecar/app.py::ingest` →
  `cognee-sidecar/cognee_engine.py::ingest_source`.

### Query + Self-improve

- **How users query:** `POST /query` →
  `cognee.search(query_type=GRAPH_COMPLETION)` + `cognee.search(CHUNKS)`; the
  agent reads the returned `relevant_pages` and writes a cited answer.
- **Where feedback comes from:** an agent critic + the lint pass flag weak or
  over-general answers.
- **How feedback updates the brain:** valuable answers are **filed back** as
  durable pages in `comparisons/` or `synthesis/` and linked into `index.md`
  (e.g. `wiki/comparisons/road-bike-trend-query-answer.md` feeds
  `wiki/synthesis/2025-2026-road-bike-prediction.md`). Explorations compound
  instead of vanishing into chat — this is the "session → permanent"
  distillation: the chat answer is ephemeral, the filed-back page is durable.
- **Code entry point:** `cognee-sidecar/app.py::query` →
  `cognee_engine.py::query`; workflow in `wiki/CLAUDE.md`.

### Lint

- **What "linting" means:** contradiction resolution, dedupe, stale pruning,
  orphan detection, and gap-finding over the Cognee graph + wiki pages.
- **How it runs:** on-demand `POST /lint`.
- **Code entry point:** `cognee-sidecar/app.py::lint` → `cognee_engine.py::lint`.

## Self-Improvement Evidence

The brain measurably sharpened a prediction after a lint pass surfaced an
over-generalization. Artifacts:
`wiki/synthesis/2025-2026-road-bike-prediction.md` (see its **Lint Note**) and
`wiki/comparisons/road-bike-trend-query-answer.md` (the filed-back answer).

### Baseline Run

- **Query / task:** "What is the 2025→2026 German road-bike trend?"
- **Result:** a flat "the German road-bike market is weak" answer.
- **Score (own metric):** 0.4 — misleading; conflates aggregate unit weakness
  with every segment.
- **Recorded feedback:**

```text
error_type: overgeneralization
error_message: "uniformly weak" claim contradicts evidence of resilient gravel/all-road + service demand
feedback: segment the market by category and channel
success_score: 0.4
```

### Improved Run

- **Query / task:** same question.
- **Result:** a segmented prediction — aggregate market normalizing,
  gravel/all-road demand resilient, dealer value shifting to service; 2026's
  winning offer is a **fast all-road platform** over a pure race bike.
- **Score:** 0.9 — segmented, cited, with German verbatim evidence.
- **What changed in the brain between runs:** lint flagged the contradiction;
  the synthesis page gained a **Lint Note** enforcing segmented language, and
  the filed-back comparison answer was rewritten to match.

```text
Before:
The German road-bike market is weak.

After:
Aggregate market is normalizing after the boom years; gravel/all-road demand is
resilient; dealer value is shifting toward service. 2026: a fast all-road
platform (wider tire clearance, comfort geometry, serviceable parts) beats a
pure race bike.
```

## Architecture

```text
[ raw/ — immutable German sources ]      <- IlnamiquiliaTsaa verbatim store (Rust)
        |  mine (verbatim) + AAAK index → wiki/index.md
        v
[ Cognee sidecar (FastAPI, 127.0.0.1:8787) ]
   /ingest → cognee.add + cognee.cognify   (graph + vectors, local Ollama)
   /query  → cognee.search(GRAPH_COMPLETION | CHUNKS)
   /lint   → graph + wiki analysis → contradictions / orphans / gaps
        |
        v
[ agent (Claude) ]  authors/edits wiki/*.md via file tools — "the LLM writes the wiki"
        |
        | distillation: ephemeral chat answer → promoted to durable page
        v
[ wiki/ — English, cited, German-verbatim-backed ]  (entities, concepts, sources,
                                                     comparisons, synthesis, index, log)
```

- **Two-role split:** Cognee (local Ollama) does extraction, graph retrieval,
  and structural lint signals; the agent makes the final synthesis and lint
  judgments and writes the durable pages.
- **Two tiers mapped to this hackathon's pattern:** the *session* tier is the
  ephemeral query/chat turn; the *permanent* tier is the wiki + graph that a
  filed-back answer is promoted into. Promotion is the distillation step.

### Cognee Cloud (optional, rewarded)

We ran **fully local** for a reliable demo (Cognee + local Ollama), so this
section is intentionally light. `cognee.serve(...)` / `cognee.push("wiki")` to
move the locally-built graph into a managed Cloud instance is the planned next
step to claim the **"Best use of Cognee Cloud"** bonus — `push(mode="preserve")`
would upload the already-extracted graph with zero remote LLM calls.

## Agents / Skills

```text
Skill path(s):
  wiki/CLAUDE.md            # the wiki-maintainer operating schema (page templates,
                            # citation format, AAAK index + log grammar, workflows)
  ilnamiquiliatsaa-mcp      # MCP tools wiki_ingest / wiki_query / wiki_lint front the
                            # sidecar (Rust MCP server; in progress)
Roles:
  - Ingestor: runs /ingest, writes source/entity/concept pages
  - Querier:  runs /query, writes cited answers, files them back
  - Linter:   runs /lint, applies fixes
  - Critic:   scores runs, drives the segmented-language correction
```

## Reproduction

```bash
# Deterministic, judge-safe demo (no Cognee/Ollama needed):
cd cognee-sidecar
COGNEE_MODE=demo uvicorn app:app --host 127.0.0.1 --port 8787

# From another terminal:
curl http://127.0.0.1:8787/health
curl -s -X POST http://127.0.0.1:8787/ingest -H 'Content-Type: application/json' \
  -d '{"source_path":"raw/ziv/2025-market-snapshot.md"}'
curl -s -X POST http://127.0.0.1:8787/query  -H 'Content-Type: application/json' \
  -d '{"question":"What is the 2025 to 2026 road-bike trend?"}'
curl -s -X POST http://127.0.0.1:8787/lint   -H 'Content-Type: application/json' -d '{}'
```

Real mode (Cognee + local Ollama) reads config in
`cognee-sidecar/cognee_engine.py::configure`:

```text
LLM_ENDPOINT        # default http://127.0.0.1:11434 (Ollama)
LLM_PROVIDER / LLM_MODEL
EMBEDDING_PROVIDER / EMBEDDING_MODEL / EMBEDDING_ENDPOINT / EMBEDDING_DIMENSIONS
WIKI_DIR            # default ./wiki
# (Cognee Cloud was not used; COGNEE_CLOUD_URL / COGNEE_API_KEY unset)
```

## Demo

- **Live demo link:** _to be added_ (deterministic local run via the
  Reproduction block above works today).
- **3-minute pitch outline:**

```text
1. Problem / idea — RAG re-derives; we built the maintainer (Memex). A memory
   palace that maintains itself.
2. Ingest demo — drop a fresh ZIV source; pages bloom, graph grows, a
   contradiction is flagged.
3. Query demo (before) — naive "market is weak" answer.
4. Self-improve step — lint flags the over-generalization; the brain rewrites
   to segmented language and files the answer back as a durable page.
5. Query demo (after) — segmented, cited 2026 all-road prediction with German
   verbatim evidence.
6. What is next — Cognee Cloud push for the bonus; auto-ingest hooks.
```

## Links

- **Implementation repo (GitLab):**
  `https://gitlab.com/intuivoou/202606_ilnamiquilia_tsaa_muisti_memoria_cognee_v063` (branch `develop`)
- **Design spec:** `docs/superpowers/specs/2026-06-19-cognee-llm-wiki-design.md`
- **Demo story / pitch:** `docs/hackathon/demo-story.md`
- **Cognee:** https://github.com/topoteretes/cognee
