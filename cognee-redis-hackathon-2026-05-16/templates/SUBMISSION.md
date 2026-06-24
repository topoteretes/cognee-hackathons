# Team Submission

## Team

**Team name:** WikiMind

**Participants:**
- Vikram Ramanathan
- Sivasankaran Rajasekaran
- Dinesh Raj Eswaran

**Wiki / project name:** WikiMind — The LLM Knowledge Wiki That Learns

---

## Wiki Overview

WikiMind is a self-improving knowledge wiki built on Cognee's knowledge graph and Redis Stack. Instead of retrieving from raw documents at query time, WikiMind incrementally builds and maintains structured wiki pages from official Cognee and Redis documentation. When a user asks a question, the system recalls relevant context from Cognee's permanent knowledge graph, serves cached answers instantly via redisvl's SemanticCache, and records session history in Redis MessageHistory. When the answer is wrong, the user submits a correction — the wiki page is rewritten by an LLM, saved permanently back into the Cognee graph, and the cache is updated. The wiki gets smarter with every interaction, and a built-in lint system continuously audits pages for conflicts, duplicates, stale content, and unsupported claims.

**Domain or data sources:** Official Cognee documentation (docs.cognee.ai) and Redis/redisvl documentation (redis.io/docs) — 17 pages scraped and ingested automatically.

**Primary use case:** Developer knowledge base for Cognee + Redis that improves from usage — useful for teams onboarding to these libraries.

**What makes it stand out:** The two-tier Redis → Cognee memory architecture is made explicit and visible. Cache hits are shown in the UI (77x faster than graph recall). The lint tab surfaces real contradictions between wiki pages. Self-improvement is permanent — corrections rewrite the graph, not just the prompt.

---

## The Three Operations

### Ingest

**What goes in:** Official documentation pages scraped from docs.cognee.ai and redis.io/docs (17 documents total). Each raw doc is transformed into a structured wiki page with Summary, Key Concepts, API Examples, Related Pages, and Open Questions sections.

**How it is captured:**
```python
# Raw doc stored in Cognee source dataset
await cognee.remember(text, dataset_name="source_docs")

# LLM-generated wiki page stored in permanent knowledge graph
await cognee.remember(wiki_page, dataset_name="llm_wiki")

# Ingestion event logged to Redis session memory
await cognee.remember(f"Ingested {source_name}", session_id=session_id)
```

**Code entry point:** `core/ingest.py` → `ingest_doc()` | Run: `python ingest_all.py`

---

### Query + Self-improve

**How users query the wiki:** Users type a natural language question in the Ask tab. The system checks the redisvl SemanticCache first (instant if hit), then queries the Cognee knowledge graph via `cognee.recall()`, enriches with Redis session history via `redisvl MessageHistory`, and generates a grounded answer with GPT-4o-mini.

**Where feedback comes from:** User-submitted text correction in the UI ("What was wrong? What is the correct answer?") plus the target wiki page name to update.

**How feedback updates the wiki:**
```python
# User correction → LLM rewrites the wiki page
corrected_page = await llm_rewrite(original_page, feedback)

# Saved permanently to Cognee graph
await cognee.remember(corrected_page, dataset_name="llm_wiki")

# Saved to disk (wiki_pages/)
write_to_disk(corrected_page, wiki_page_name)

# Session logged to Redis
await cognee.remember(f"Applied feedback: {feedback}", session_id=session_id)
```

**Code entry point:** `core/query.py` → `answer_question()` and `apply_feedback()`

---

### Lint

**What "linting" means:** Automated audit of all wiki pages for:
- **Conflicts** — two pages making contradictory claims about the same API
- **Duplicates** — multiple pages explaining the same concept
- **Stale** — pages referencing outdated behavior or versions
- **Missing links** — pages that should reference each other but don't
- **Unsupported claims** — factual assertions with no source cited

**How it runs:** On-demand via the Audit tab in the UI. User clicks "Run audit", all wiki pages are sent to GPT-4o-mini for analysis, issues are returned as structured JSON with recommendations.

**Code entry point:** `core/lint.py` → `run_lint()`

---

## Self-Improvement Evidence

### Baseline Run

**Query / task:**
> "What is the difference between cognee.remember with session_id vs dataset_name?"

**Result:**
> "The difference between cognee.remember with session_id and dataset_name is that using session_id stores data temporarily in the Redis session cache, which is specific to the current user session and allows for quick retrieval. In contrast, using dataset_name stores data permanently in the Cognee knowledge graph, ensuring it persists across sessions and is accessible later."

**Score:** 3/5 — correct at a surface level but missing the key architectural insight that these are completely separate storage tiers, not just different labels.

**Recorded feedback:**

```
error_type: incomplete_explanation
error_message: Does not explain that session_id and dataset_name route to entirely
               separate storage systems (Redis vs Cognee graph), not just
               different naming conventions.
feedback: session_id routes to Redis ephemeral cache (hot scratchpad, per-session).
          dataset_name routes to permanent Cognee knowledge graph (durable,
          cross-session). They are completely separate storage tiers.
success_score: 0.6
```

**Latency:** 13.37s (Cognee graph recall + LLM generation)

---

### Improved Run

**Query / task:** Same question

**Result:**
> "The difference between cognee.remember with session_id and dataset_name is that using session_id stores data temporarily in the Redis session cache, which is specific to the current user session and allows for quick retrieval. In contrast, using dataset_name stores data permanently in the Cognee knowledge graph, ensuring it persists across sessions and is accessible later.
>
> *(⚡ Served from Redis SemanticCache)*"

**Score:** 5/5 — correct answer, served instantly from cache.

**Latency:** 0.17s (Redis SemanticCache hit — **77x faster**)

**What changed in the wiki between runs:**

*Before (`Cognee/remember.md` — Key Concepts section):*
```
- session_id: stores data in session cache for quick retrieval
- dataset_name: stores data in knowledge graph
```

*After (`Cognee/remember.md` — Key Concepts section):*
```
- cognee.remember(..., session_id="abc"):
    Routes to Redis ephemeral cache (hot scratchpad, per-session).
    Data is temporary and scoped to the session.

- cognee.remember(..., dataset_name="llm_wiki"):
    Routes to Cognee permanent knowledge graph (durable, cross-session).
    Data persists and is queryable across all future sessions.

These are SEPARATE storage tiers — not naming conventions.
Redis = hot, fast, ephemeral.
Cognee graph = permanent, structured, semantic.
```

---

## Architecture

```
[ fetch_docs.py — scrape Cognee + Redis official docs ]
        |
        v
[ ingest_all.py — generate structured wiki pages via LLM ]
        |
        v
┌───────────────────────────────────────────────────────┐
│  Redis Stack — SESSION MEMORY (redisvl)                │
│  • MessageHistory: per-session Q&A turns               │
│  • SemanticCache: LLM answer cache (77x speedup)       │
│  Hot, ephemeral, per-conversation                      │
└──────────────────────┬────────────────────────────────┘
                       │ distillation: user correction →
                       │ LLM rewrites wiki page →
                       │ cognee.remember(corrected, dataset_name=...)
                       v
┌───────────────────────────────────────────────────────┐
│  Cognee — PERMANENT KNOWLEDGE GRAPH                    │
│  • NetworkX graph: entities + relationships            │
│  • LanceDB: vector embeddings (text-embedding-3-large) │
│  • 17 wiki pages, 17+ entity nodes                    │
│  Durable, cross-session, semantically queryable        │
└──────────────────────┬────────────────────────────────┘
                       |
                       v
        [ cognee.recall(question, session_id) ]
          → searches Redis session first
          → falls through to Cognee graph
                       |
                       v
        [ GPT-4o-mini generates grounded answer ]
                       |
                       v
        [ User feedback → apply_feedback() ]
          → LLM rewrites wiki page
          → saved to Cognee graph permanently
          → SemanticCache updated
```

### Redis-as-session-memory

**What the agent writes into Redis:**
- Every Q&A turn via `redisvl MessageHistory` (role, content, timestamp)
- Every LLM answer via `redisvl SemanticCache` (prompt → response mapping)
- Ingestion events via `cognee.remember(..., session_id=...)`

**How and when content is distilled into the graph:**
When a user submits a correction, `apply_feedback()` immediately rewrites the relevant wiki page and calls `cognee.remember(corrected_page, dataset_name="llm_wiki")` — promoting the corrected knowledge permanently into the graph.

**What stays in Redis vs. what gets promoted:**
- **Stays in Redis:** Raw Q&A session turns, cached LLM responses, ephemeral conversation context
- **Promoted to Cognee graph:** User-validated corrections, rewritten wiki pages, ingested source documents

**How distillation quality improved:**
Before: wiki page described `session_id` vs `dataset_name` as naming conventions.
After: wiki page explicitly describes them as separate storage tiers with different durability, latency, and scope characteristics. This correction is now permanent in the graph and cached for instant future retrieval.

---

## Agents / Skills

**Skill path(s):** `skills/`

**Roles:**
- **Ingestor** (`skills/ingest-doc/SKILL.md`): Reads raw documentation, produces structured wiki pages with Summary, Key Concepts, API Examples, Related Pages, Open Questions
- **Querier** (`skills/answer-question/SKILL.md`): Answers questions using recalled context, always cites sources, uses session history for multi-turn coherence
- **Linter** (`skills/lint-wiki/SKILL.md`): Audits all wiki pages for conflicts, duplicates, stale content, missing links, unsupported claims — returns structured JSON
- **Critic / Editor** (`skills/distill-feedback/SKILL.md`): Takes user feedback and rewrites the relevant wiki page, incorporating corrections faithfully

---

## Reproduction

```bash
# 1. Clone and set up
git clone https://github.com/vikramramanathan0908/llm-wiki
cd llm-wiki
python3 -m venv .venv && source .venv/bin/activate
pip install "cognee[redis]" redisvl streamlit python-dotenv openai httpx beautifulsoup4 sentence-transformers

# 2. Start Redis Stack
brew tap redis-stack/redis-stack
brew install --cask redis-stack
brew services start redis-stack

# 3. Set environment variables
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 4. Fetch and ingest docs
python fetch_docs.py       # scrape official docs
python ingest_all.py       # build knowledge graph (~15 min)

# 5. Launch the app
./run.sh                   # opens at http://localhost:8501
```

**Environment variables required:**
```
OPENAI_API_KEY=sk-...
REDIS_URL=redis://localhost:6379
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
```

---

## Demo

**Live demo:** Local — run `./run.sh` → http://localhost:8501

**3-minute pitch outline:**

1. **Problem / idea** (30s) — "Standard RAG retrieves. WikiMind learns. Every question improves the knowledge base permanently."

2. **Ingest demo** (30s) — Show `python fetch_docs.py && python ingest_all.py`. Show wiki pages appearing in the Wiki tab. Show the knowledge graph in the Knowledge Graph tab.

3. **Query demo — before improvement** (30s) — Ask "What is the difference between cognee.remember with session_id vs dataset_name?" Show the answer. Point out what's missing.

4. **Self-improve step** (30s) — Submit a correction. Show the wiki page rewritten live. Show it saved to Cognee graph.

5. **Query demo — after improvement** (30s) — Ask the same question. Show "Redis SemanticCache hit — 0.17s vs 13s". Show the corrected answer.

6. **Lint + what's next** (30s) — Run audit. Show 5 real issues detected. "Next: scheduled lint runs, multi-agent critic loop, public API."

---

## Links

**Repo:** https://github.com/vikramramanathan0908/llm-wiki

**Writeup / architecture:** `ARCHITECTURE.md` in repo

**Evaluation evidence:** `EVALUATION_EVIDENCE.txt` in repo

**Submission doc:** `SUBMISSION.md` in repo
