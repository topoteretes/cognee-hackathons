# Askvio Wiki Memory PoC

This repository contains a hackathon proof-of-concept for comparing Askvio's current **classic vector retrieval** knowledge-base pattern with an **LLM-wiki-style memory** that promotes uploaded ecommerce HTML into pages, sections, fact cards, and feedback-derived corrections.

The app is intentionally small enough to demo in a hackathon, but it includes the required architecture pieces from the Cognee × Redis challenge:

- **Ingest:** upload one or more `.html` files from ecommerce product, policy, FAQ, or landing pages.
- **OpenAI vector baseline:** split cleaned HTML into chunks, embed them with OpenAI (`text-embedding-3-small` by default), and search an in-memory vector database.
- **OpenAI-grounded wiki answers:** distill the same HTML into canonical wiki pages, headed sections, facts, and entity links, then ask OpenAI to answer from the wiki evidence.
- **Query + compare:** ask one question and receive side-by-side vector and wiki answers with KPIs.
- **Inspect wiki:** open the generated pages, facts, and entity index from the browser.
- **Self-improve:** rate/correct an answer; the correction is written to Redis session memory and promoted into the wiki as a new fact.
- **Lint:** deduplicate wiki facts after ingest and feedback.
- **Cognee hook:** optionally mirror distilled wiki pages into Cognee permanent memory with `ENABLE_COGNEE=1`.

## Architecture

```text
[uploaded ecommerce HTML]
          |
          v
[FastAPI ingest endpoint]
          |
          +--> [OpenAI embeddings -> Vector DB: chunks + vectors]
          |
          +--> [Wiki KB: pages + sections + facts + entities]
          |
          +--> [Redis: raw upload/build/query/feedback session events]
          |
          +--> [Cognee optional: distilled pages as permanent memory]

[Ask widget]
          |
          +--> /api/query retrieves vector + wiki evidence
          |
          +--> OpenAI Responses API writes both final answers from evidence
          |
          +--> /api/wiki exposes generated wiki internals
          |
          +--> /api/feedback stores Redis event and promotes correction to wiki
```

Redis is used as the hot session scratchpad for uploads, build events, query comparisons, and feedback. The wiki layer represents the durable distilled memory inside the PoC; when `ENABLE_COGNEE=1`, those distilled pages are also sent to Cognee.

## Repository layout

```text
app/
  main.py              # FastAPI routes and orchestration
  html_processing.py   # HTML cleaning, section extraction, sentence splitting
  retrieval.py         # OpenAI vector DB baseline and wiki KB implementation
  openai_service.py    # OpenAI embeddings and answer generation adapter
  memory.py            # Redis session memory and optional Cognee adapter
  static/              # Upload/query/evaluation/wiki-inspection web UI
cognee-redis-hackathon-2026-05-16/
  README.md            # Original hackathon brief
  templates/           # Submission template
requirements.txt       # Python dependencies
Dockerfile             # Optional container image
```

## Step-by-step local execution

### 1. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Put your OpenAI key here

The app reads OpenAI credentials from environment variables. At minimum set:

```bash
export OPENAI_API_KEY="sk-..."
```

Optional model overrides:

```bash
export OPENAI_CHAT_MODEL="gpt-4.1-mini"
export OPENAI_EMBEDDING_MODEL="text-embedding-3-small"
```

If `OPENAI_API_KEY` is not set, the app still runs in deterministic fallback mode, but:

- vector search falls back to local term vectors instead of OpenAI embeddings,
- final answers are extractive snippets instead of OpenAI-generated answers,
- `/api/status` reports `openai.enabled: false`.

### 4. Start Redis

The quickest path is Docker Compose:

```bash
docker compose up -d redis
```

If you already have Redis running elsewhere, set:

```bash
export REDIS_URL=redis://localhost:6379/0
```

The app still runs without Redis, but Redis-specific session history will be disabled and `/api/status` will report `available: false`.

### 5. Optional: enable Cognee mirroring

Cognee is optional for this demo because the app always keeps an in-process wiki for the live comparison. To mirror distilled wiki pages into Cognee too, set:

```bash
export ENABLE_COGNEE=1
export LLM_API_KEY="$OPENAI_API_KEY"
```

Important Cognee notes:

1. This repo now installs `cognee==1.1.0`. The earlier `module 'cognee' has no attribute 'remember'` error came from using an older Cognee package where the current `remember()` API did not exist.
2. If Cognee exposes `remember()`, the adapter uses it directly.
3. If Cognee does not expose `remember()`, the adapter falls back to the legacy `add()` + `cognify()` flow.
4. Cognee graph extraction/cognify needs an LLM key. In local Cognee setups this is commonly supplied as `LLM_API_KEY`; for this PoC you can point it to the same value as `OPENAI_API_KEY`.
5. If Cognee is not configured correctly, the ingest response will include the Cognee error while the local OpenAI vector/wiki comparison still works.

### 6. Run the web app

```bash
uvicorn app.main:app --reload
```

Open <http://localhost:8000>.

### 7. Demo flow

1. Save a few ecommerce pages as `.html` files. Good examples are product details, shipping policy, return policy, warranty, FAQ, or sizing pages.
2. In the web UI, upload those HTML files and click **Build vector + wiki KB**.
3. Click **Inspect generated wiki** to see generated pages, fact cards, and entity links.
4. Ask a question such as `What is the return policy?` or `How long does express shipping take?`.
5. Compare the two answer cards and KPIs:
   - evidence count,
   - top-score delta,
   - fastest retriever,
   - vector backend (`openai_embeddings` or fallback `local_term_vectors`),
   - OpenAI model used for each answer,
   - source snippets.
6. Add a correction in **Self-improve the wiki**, for example `Returns are accepted for 45 days for loyalty members.`
7. Ask the same or related question again; the wiki answer can now use the promoted feedback fact.

## API reference

### `GET /api/status`

Returns current KB size, last build metrics, Redis URL and availability, and OpenAI configuration status.

### `POST /api/ingest`

Multipart form field: `files` containing one or more HTML files.

Builds both KBs, creates OpenAI embeddings for the vector DB when configured, lints the wiki, logs session events in Redis, and optionally mirrors distilled pages to Cognee.

### `POST /api/query`

```json
{
  "question": "What is the return policy?",
  "session_id": "demo"
}
```

Returns vector and wiki answers, evidence, latency, OpenAI usage status, and comparison KPIs.

### `GET /api/wiki`

Returns the generated wiki internals:

- `pages`: canonical page summaries and sections,
- `facts`: fact cards used for retrieval,
- `entities`: simple entity-to-page links.

### `POST /api/feedback`

```json
{
  "question": "What is the return policy?",
  "correction": "Returns are accepted within 45 days for loyalty members.",
  "rating": 5,
  "session_id": "demo"
}
```

Writes feedback to Redis session memory, promotes it into the wiki, runs linting, and returns recent session events.

## Testing

```bash
pytest
```

## Notes for the hackathon pitch

- **Baseline:** vector retrieval is a strong and familiar Askvio-style KB: raw HTML text becomes chunks, OpenAI embeddings, and query-time vector similarity.
- **Wiki differentiator:** the same source material is distilled into stable knowledge objects that can be inspected, linted, edited, and improved.
- **Self-improvement evidence:** feedback is not just logged; it becomes a new wiki fact that changes future answers.
- **Redis role:** Redis captures the fast session trail of uploads, queries, and user feedback.
- **Cognee role:** Cognee can receive the distilled wiki pages as permanent graph memory when enabled.
