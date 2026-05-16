# Askvio Wiki Memory PoC

This repository contains a hackathon proof-of-concept for comparing Askvio's current **classic vector retrieval** knowledge-base pattern with an **LLM-wiki-style memory** that promotes uploaded ecommerce HTML into pages, sections, fact cards, and feedback-derived corrections.

The app is intentionally small enough to demo in a hackathon, but it includes the required architecture pieces from the Cognee × Redis challenge:

- **Ingest:** upload one or more `.html` files from ecommerce product, policy, FAQ, or landing pages.
- **Vector baseline:** split the cleaned HTML text into chunks and retrieve using deterministic local term-vector similarity.
- **Wiki memory:** distill the same HTML into canonical wiki pages, headed sections, facts, and entity links.
- **Query + compare:** ask one question and receive side-by-side vector and wiki answers with KPIs.
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
          +--> [Vector KB: chunks + term vectors]
          |
          +--> [Wiki KB: pages + sections + facts + entities]
          |
          +--> [Redis: raw upload/build/query/feedback session events]
          |
          +--> [Cognee optional: distilled pages as permanent memory]

[Ask widget]
          |
          +--> /api/query returns vector answer, wiki answer, evidence, KPIs
          |
          +--> /api/feedback stores Redis event and promotes correction to wiki
```

Redis is used as the hot session scratchpad for uploads, build events, query comparisons, and feedback. The wiki layer represents the durable distilled memory inside the PoC; when `ENABLE_COGNEE=1`, those distilled pages are also sent to Cognee through `cognee.remember(...)`.

## Repository layout

```text
app/
  main.py              # FastAPI routes and orchestration
  html_processing.py   # HTML cleaning, section extraction, sentence splitting
  retrieval.py         # Vector baseline and wiki KB implementations
  memory.py            # Redis session memory and optional Cognee adapter
  static/              # Upload/query/evaluation web UI
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

### 3. Start Redis

The quickest path is Docker Compose:

```bash
docker compose up -d redis
```

If you already have Redis running elsewhere, set:

```bash
export REDIS_URL=redis://localhost:6379/0
```

The app still runs without Redis, but Redis-specific session history will be disabled and `/api/status` will report `available: false`.

### 4. Optional: enable Cognee mirroring

By default the demo uses the in-process wiki as the durable PoC memory so it can run without external credentials. To also mirror distilled wiki pages into Cognee, configure Cognee according to your environment and start the app with:

```bash
export ENABLE_COGNEE=1
```

If Cognee is not configured correctly, the ingest response will include the Cognee error while the local vector/wiki comparison still works.

### 5. Run the web app

```bash
uvicorn app.main:app --reload
```

Open <http://localhost:8000>.

### 6. Demo flow

1. Save a few ecommerce pages as `.html` files. Good examples are product details, shipping policy, return policy, warranty, FAQ, or sizing pages.
2. In the web UI, upload those HTML files and click **Build vector + wiki KB**.
3. Ask a question such as `What is the return policy?` or `How long does express shipping take?`.
4. Compare the two answer cards and KPIs:
   - evidence count,
   - top-score delta,
   - fastest retriever,
   - source snippets.
5. Add a correction in **Self-improve the wiki**, for example `Returns are accepted for 45 days for loyalty members.`
6. Ask the same or related question again; the wiki answer can now use the promoted feedback fact.

## API reference

### `GET /api/status`

Returns current KB size, last build metrics, Redis URL, and Redis availability.

### `POST /api/ingest`

Multipart form field: `files` containing one or more HTML files.

Builds both KBs, lints the wiki, logs session events in Redis, and optionally mirrors distilled pages to Cognee.

### `POST /api/query`

```json
{
  "question": "What is the return policy?",
  "session_id": "demo"
}
```

Returns vector and wiki answers, evidence, latency, and comparison KPIs.

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

- **Baseline:** vector retrieval is a strong and familiar Askvio-style KB: raw HTML text becomes chunks and query-time retrieval selects similar chunks.
- **Wiki differentiator:** the same source material is distilled into stable knowledge objects that can be linted and edited.
- **Self-improvement evidence:** feedback is not just logged; it becomes a new wiki fact that changes future answers.
- **Redis role:** Redis captures the fast session trail of uploads, queries, and user feedback.
- **Cognee role:** Cognee can receive the distilled wiki pages as permanent graph memory when enabled.
