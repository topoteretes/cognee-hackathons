# cognee-companybrain

Unify fragmented company context — Slack threads and Granola meeting notes — into a single Cognee knowledge graph. From there, run agents on top: support assistants that recognize repeat customer questions, expert finders that route a question to the right person, contradiction detectors that surface where opinions diverge.

## 🚀 Start here

New to this? Two hands-on tutorials:

1. **Learn Cognee** — `tutorial/intro_to_cognee.ipynb`. Builds a tiny company
   brain from sample Slack + Granola data and walks through the core loop:
   `remember` → `recall` → node sets → typed schema → feedback. Runs in-process
   (no server). Quick start:
   ```bash
   bash tutorial/setup.sh            # creates .venv, installs deps
   # add LLM_API_KEY to .env
   source .venv/bin/activate && jupyter lab tutorial/intro_to_cognee.ipynb
   ```
   No code? Just open `tutorial/graph*.html` in a browser — see `tutorial/GRAPHS.md`.

2. **Build the live Slack bot** — see `BOT.md`.

The rest of this README describes the production ingestion pipeline.

---

## Why

Knowledge in modern companies lives in too many places. Slack threads decay. Meeting notes sit unread. Decisions get re-litigated because nobody can find the prior conversation. **One graph**, fed continuously from the places people actually talk, fixes the retrieval problem.

## What it does (v0)

1. **Ingests** Slack threads and Granola notes from configured sources
2. **Normalizes** them into a single transcript-shaped document with speaker, timestamp, and channel/meeting tags
3. **Writes** each document to Cognee via `remember()` with `node_set` tags carrying source/channel/project/speaker facets
4. **Surfaces** the graph through Cognee's built-in UI; add agents on top via `recall()`

## Design

```
sources/slack.py     → fetch_threads(channel, since)     → ThreadData
sources/granola.py   → fetch_notes(since)                → NoteData
normalize.py         → to_doc(raw)                       → Doc
cognee_client.py     → write(doc)                        → remember(...)
scripts/run_ingest.py                                    → loop over sources
```

Every doc, regardless of source, looks like a transcript:

```
# <title>
[alice@acme.com, 2026-05-28T10:14] We have an auth bug on login.
[bob@acme.com,   2026-05-28T10:16] Same issue we hit last month?
[alice@acme.com, 2026-05-28T10:18] Yes — I'll patch it today.
```

Tags carry the structure: `source:slack`, `slack:#support`, `doc:T123`, `speaker:alice@acme.com`, optionally `project:onboarding`.

Cognee's default extraction reads the transcript with full context and produces `Person`, `Topic`, `Decision`, `Question` nodes with proper attribution. Custom `DataPoint` types can be layered on later when extraction quality plateaus.

## Quickstart

```bash
# 1. Install
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# 2. Configure
cp .env.example .env
# Fill in SLACK_BOT_TOKEN, GRANOLA_API_TOKEN, COGNEE_API_KEY

# 3. Run ingestion
python scripts/run_ingest.py
```


## Roadmap

- **v0** — Slack + Granola ingest into a single Cognee dataset, default extraction
- **v0.1** — `Person`/`Project` DataPoints synced from a source-of-truth (HR, Slack profile API)
- **v0.2** — Demo agents: support agent, expert finder
- **v0.3** — Recency-aware queries and contradiction detection
- **v1.0** — Continuous ingest (webhook-driven), per-tenant access control

## License

Apache 2.0 — see [LICENSE](LICENSE). (Same license as [cognee](https://github.com/topoteretes/cognee).)
