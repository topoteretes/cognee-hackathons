# Self-Healing Debug Wiki

**Team:** _(fill in — see SUBMISSION.md)_  
**Hackathon:** [Cognee × Redis — AI-Memory Hackathon (2026-05-16)](https://github.com/topoteretes/cognee-hackathons/tree/main/cognee-redis-hackathon-2026-05-16)

## Project repository

Full source code, dashboard, and MCP server:

**https://github.com/YOUR_USERNAME/self-healing-debug-wiki**

_(Replace with your GitHub repo URL after you push `debug_wiki`.)_

## One-line pitch

An LLM Knowledge Wiki for developer debugging memory that **ingests** error/fix pairs, **lints** for stale and contradictory advice, and **self-improves** when library versions make old fixes wrong — using **Redis** for fast cached answers and **Cognee** for durable semantic memory.

## Quick start

```bash
git clone https://github.com/YOUR_USERNAME/self-healing-debug-wiki.git
cd self-healing-debug-wiki
pip install -r requirements.txt
cp .env.example .env
# Set ANTHROPIC_API_KEY, OPENAI_API_KEY (Cognee embeddings), REDIS_URL (optional)
python seed.py
python web.py
# http://localhost:8000
```

MCP (Cursor / Claude Code): see `connect/README.md` and `server.py`.

## Hackathon operations

| Operation | API | MCP tool |
|-----------|-----|----------|
| Ingest | `POST /api/ingest` | `save_to_wiki` |
| Query + self-improve | `POST /api/query` | `search_wiki` |
| Lint | `POST /api/lint` | `check_wiki_health` |

## Memory architecture

- **Redis** — cached query/lint JSON (hot, ephemeral responses).
- **Cognee** — ingested fix text, graph search on cache miss.
- **`debugwiki_store.json`** — structured source of truth (errors, solutions, wiki pages, findings, events).

## Submission writeup

See [SUBMISSION.md](./SUBMISSION.md) for the full hackathon template (three operations, before/after evidence, reproduction, demo outline).

## Docs in the project repo

- `CODEBASE_DOCUMENTATION.md` — architecture and API
- `TESTS.md` — manual test checklist
- `test_mcp_tools.py` — local MCP tool smoke test
