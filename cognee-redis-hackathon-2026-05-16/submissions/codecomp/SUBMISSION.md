# Team Submission

## Team

- Team name: Codecomp
- Participants: Kevin Castro Sosa (@regularkevvv)
- Wiki / project name: Codecomp

## Wiki Overview

Codecomp is memory for coding agents. It builds a developer-focused LLM Wiki from raw coding-agent session history: Claude, Cursor, Codex, OpenCode, and similar tools. Codecomp normalizes those histories into developer-aware memory records, stores the raw/hot/session layer in Redis, distills durable knowledge into Cognee and markdown wiki pages, and runs an agentic lint loop that cleans and improves the wiki over time.

- Domain or data sources: Local coding-agent session histories, project roots, wiki registry metadata, raw Redis memory records, Cognee graph context, markdown wiki pages, and Cognee skill packs.
- Primary use case: Give future coding agents persistent project memory so they can recover architecture, workflows, preferences, open questions, and recurring fixes before they start changing code.
- What makes it stand out: Codecomp is an LLM Wiki for the development process itself. The thing being remembered is not one app's docs; it is how agents and humans have worked across repos, tools, mistakes, conventions, and follow-up tasks.

## The Three Operations

### Ingest

- What goes in (documents, conversations, runs, ...): Raw developer session history from Claude, Cursor, Codex, OpenCode, and other coding-agent providers.
- How it is captured (`cognee.remember(...)`, custom pipeline, ...): `codecomp ingest` scans provider session stores, normalizes each event into Codecomp memory records, maps records to hierarchical wikis, and stores them in Redis under a Codecomp namespace.
- Code entry point: `codecomp ingest --provider cursor --limit 200`

Redis is the hot/raw/session memory layer. It keeps recent and historical agent events fast, filterable, and replayable before any durable distillation happens.

### Query + Self-improve

- How users query the wiki: Humans use `codecomp ask`; coding agents use `codecomp-tool`, a JSON interface with commands like `tools`, `active-wikis`, `ask`, and `search-wiki`.
- Where feedback comes from (user rating, agent critic, eval, ...): Feedback comes from the agentic lint loop, deterministic lint findings, user-visible wiki gaps, and follow-up queries that reveal missing or stale project guidance.
- How feedback updates the wiki (`SkillRunEntry`, edge re-weighting, graph rewrite, ...): `codecomp distill` promotes selected Redis memories into Cognee permanent graph/vector memory and markdown wiki pages. `codecomp lint` then reads the wiki, Cognee graph context, deterministic lint findings, and raw Redis evidence, asks the LLM for cleanup actions, applies safe wiki updates, and remembers the cleanup back into Cognee.
- Code entry point: `codecomp distill --wiki opensource::codecomp --limit 50`, `codecomp ask "what is codecomp?" --wiki opensource::codecomp`, and `codecomp-tool ask "what should I know before working in this repo?" --cwd "$PWD"`

The always-running loop is:

```text
ingest raw sessions -> distill durable knowledge -> lint and clean the wiki -> repeat
```

### Lint

- What "linting" means in your wiki (dedupe, conflict resolution, stale pruning, ...): Linting checks that wiki pages are coherent, deduplicated, grounded in evidence, current with recent work, and actionable for future coding agents.
- How it runs (scheduled, on-write, on-demand): It can run on demand with `codecomp lint` or continuously through `codecomp daemon`, which repeats ingest, distill, and lint on intervals.
- Code entry point: `codecomp lint --wiki opensource::codecomp --dry-run --max-iterations 1`, then `codecomp lint --wiki opensource::codecomp --max-iterations 1`

The lint pass is agentic. It combines deterministic rules, Cognee context, markdown wiki state, and raw Redis evidence, then applies safe wiki edits and records the cleanup as new memory.

## Self-Improvement Evidence

Codecomp demonstrates improvement by starting with raw agent session memory in Redis, distilling it into durable Cognee/wiki knowledge, then running agentic lint to clean and refine the generated wiki. The before/after is visible in the wiki pages and in the quality of answers returned by `codecomp ask` and `codecomp-tool ask`.

### Baseline Run

- Query / task: Ask the fresh system what it knows before durable distillation and cleanup: `codecomp-tool ask "what should I know before working in this repo?" --cwd "$PWD"`.
- Result: The system can inspect active wiki configuration and raw memory, but the durable wiki is incomplete until distillation has promoted important session lessons.
- Score (judge-readable): Baseline is measured by pending wiki lint findings and missing durable guidance in pages like `what.md`, `overview`, `architecture`, `workflows`, `preferences`, `open questions`, and `recent focus`.
- Recorded feedback:

```text
error_type: incomplete_or_unrefined_wiki_memory
error_message: raw session evidence exists, but the durable project wiki still needs distilled guidance and cleanup
feedback: run distillation and agentic lint so future agents get concise, grounded project memory
success_score: baseline before distill/lint
```

### Improved Run

- Query / task: Repeat the same project-memory query after `codecomp distill` and `codecomp lint`.
- Result: The answer is grounded in distilled Codecomp wiki knowledge, backed by Cognee graph retrieval, markdown wiki pages, and Redis evidence fallback.
- Score: Improvement is shown by fewer or resolved lint findings, richer durable wiki pages, and a better `codecomp ask "what is codecomp?" --wiki opensource::codecomp` answer.
- What changed in the wiki between runs:

```text
Before:
Raw agent sessions are present in Redis, but project guidance is scattered and incomplete.
The wiki may lack concise architecture, workflow, preference, and recent-focus pages.

After:
Codecomp has promoted selected Redis memories into Cognee and markdown wiki pages.
Agentic lint has cleaned the wiki, applied safe updates, and remembered the cleanup back into Cognee.
Future agents can ask `codecomp-tool` for repo-specific guidance before editing code.
```

## Architecture

Codecomp follows the hackathon's two-tier memory model: Redis is the fast raw/session memory layer, and Cognee is the permanent graph/vector memory layer. Markdown wiki pages make the durable memory reviewable by humans and directly useful to agents.

```text
[Claude / Cursor / Codex / OpenCode sessions]
        |
        v
[ Codecomp ingest + normalizers ]
        |
        v
[ Redis - raw, hot, filterable session/event memory ]
        |
        | codecomp distill
        v
[ Cognee - durable graph/vector memory + skills + summaries ]
        |
        | wiki writer
        v
[ Hierarchical markdown LLM Wikis ]
        |
        v
[ codecomp ask / codecomp-tool JSON interface ]
        |
        v
[ agentic lint + daemon -> cleanup -> remembered improvements ]
```

Codecomp maintains hierarchical markdown wikis:

```text
super::
opensource
opensource::codecomp
```

Each wiki has a `what.md` instruction/config document. Distillation can write to multiple pages such as `overview`, `architecture`, `workflows`, `preferences`, `open questions`, and `recent focus`.

### Redis-as-session-memory

- What the agent writes into Redis (raw turns, intermediate observations, ...): Normalized provider session records, raw developer events, provider/project metadata, wiki mappings, and search indexes.
- How and when content is distilled into the graph: `codecomp distill --wiki opensource::codecomp --limit 50` selects relevant Redis memories and promotes durable lessons into Cognee permanent memory and markdown wiki pages.
- What stays in Redis vs. what gets promoted: Raw event/session evidence and fast indexes stay in Redis; durable architecture notes, workflows, preferences, summaries, open questions, and cleaned wiki knowledge are promoted to Cognee and markdown.
- How distillation quality improved between baseline and improved run: The agentic lint loop reviews deterministic lint findings plus Cognee/wiki/Redis context, applies safe cleanup actions, and remembers those improvements back into Cognee so later runs start from better guidance.

## Agents / Skills (if any)

Codecomp includes Cognee skills and remembers them into Cognee when using cwd-safe skill roots.

```text
Skill path(s):
  - codecomp/skills/wiki-mapper/SKILL.md
  - codecomp/skills/wiki-distiller/SKILL.md
  - codecomp/skills/wiki-linter/SKILL.md
  - .cursor/skills/codecomp/SKILL.md

Roles:
  - Ingestor: scans and normalizes coding-agent sessions into Redis
  - Mapper: maps raw memories to hierarchical wikis
  - Distiller: promotes useful raw memory into Cognee and markdown wiki pages
  - Querier: answers from Cognee first, then markdown wiki and Redis fallback evidence
  - Linter: detects stale, duplicated, missing, or incoherent wiki guidance
  - Critic: uses agentic lint findings to propose and apply safe wiki cleanups
```

## Reproduction

Before pushing or submitting, validate the project repo:

```bash
cd codecomp
uv run pytest
uv tool install . --force --refresh-package codecomp
```

Make sure Redis and an LLM key are available:

```bash
redis-server
export OPENAI_API_KEY="<your-key>"
# or:
export LLM_API_KEY="<your-key>"
```

Commands to reproduce the demo:

```bash
git clone git@github.com:regularkevvv/codecomp.git
cd codecomp

# 1. Reset and initialize.
codecomp reset-memory --yes
codecomp init

# 2. Create hierarchical wikis.
codecomp wiki create opensource --interactive
codecomp wiki create opensource::codecomp --root "$PWD" --interactive

# 3. Ingest raw developer session memory into Redis.
codecomp ingest --provider cursor --limit 200

# 4. Distill Redis raw memory into permanent Cognee/wiki memory.
codecomp distill --wiki opensource::codecomp --limit 50

# 5. Run agentic lint/self-improvement.
codecomp lint --wiki opensource::codecomp --dry-run --max-iterations 1
codecomp lint --wiki opensource::codecomp --max-iterations 1

# 6. Query the resulting LLM Wiki.
codecomp ask "what is codecomp?" --wiki opensource::codecomp

# 7. Show the agent-facing JSON interface.
codecomp-tool tools
codecomp-tool active-wikis --cwd "$PWD"
codecomp-tool ask "what should I know before working in this repo?" --cwd "$PWD"
codecomp-tool search-wiki "architecture workflows preferences" --cwd "$PWD"

# 8. Show the always-running auto-improvement daemon.
codecomp daemon start \
  --provider cursor \
  --ingest-interval 30 \
  --distill-interval 120 \
  --lint-interval 300 \
  --ingest-limit 50 \
  --distill-limit 10 \
  --lint-iterations 1
codecomp daemon status
codecomp daemon stop
```

Environment variables required:

```text
OPENAI_API_KEY
# or LLM_API_KEY
REDIS_URL
```

## Demo

- Live demo link (Loom, YouTube, etc.) or local instructions: Run the reproduction commands above from the `codecomp` repo with Redis and an LLM key configured.
- 3-minute pitch outline:

```text
1. "Codecomp is memory for coding agents."
2. Show Redis raw memory via ingest/status/search.
3. Show Cognee/wiki distillation with `codecomp distill`.
4. Show `codecomp ask` answering from learned memory.
5. Show `codecomp lint` improving and cleaning the wiki.
6. Show `codecomp daemon status` as the always-running auto-improvement loop.
7. End with `codecomp-tool` as the JSON interface agents use while building software.
```

## Links

- Repo: https://github.com/regularkevvv/codecomp
- Submission fork: https://github.com/regularkevvv/cognee-hackathons
- Challenge: Cognee x Redis Hackathon, "Building your own Agent LLM Wiki"
