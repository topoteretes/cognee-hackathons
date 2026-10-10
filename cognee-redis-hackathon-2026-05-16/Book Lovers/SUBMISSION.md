# Team Submission

## Team

- Team name: Book Lovers
- Participants: Brihati
- Wiki / project name: BookWiki

## Wiki Overview

BookWiki is an LLM knowledge wiki for preserved books. It ingests chapter summaries, note packets, concepts, and source metadata from a local book preservation pipeline, turns them into linked wiki pages, and stores the same durable memory in Cognee. Users can query across books, inspect cited source hits, and promote useful answers into reusable playbooks. The wiki self-improves by keeping recent query/session events in Redis, then distilling high-signal results into persistent wiki pages and Cognee memory.

- Domain or data sources: Preserved nonfiction/business books from the local `files/` book pipeline, with the demo focused on `The Mom Test`.
- Primary use case: Ask decision questions across books and turn useful answers into reusable, cited playbooks.
- What makes it stand out: It is not only a RAG search over raw PDFs. It builds a living book wiki with books, concepts, query briefs, promoted playbooks, session memory, and lint checks.

## The Three Operations

### Ingest

- What goes in (documents, conversations, runs, ...): Book manifests, chapter summaries, chunk notes, extracted terms, definitions, key points, examples, actionable lessons, and source metadata.
- How it is captured (`cognee.remember(...)`, custom pipeline, ...): A custom pipeline reads preserved book artifacts, writes markdown wiki pages, logs the ingest event to Redis or JSONL session memory, and can call `cognee.remember(...)` when `--use-cognee` is enabled.
- Code entry point: `tools/cognee_bookwiki.py ingest`

### Query + Self-improve

- How users query the wiki: Users run `tools/cognee_bookwiki.py query "<question>"`. The tool searches local book indexes, optionally calls `cognee.recall(...)`, writes a query brief under `wiki/queries/`, and can immediately save a playbook with `--save-playbook`.
- Where feedback comes from (user rating, agent critic, eval, ...): Feedback can come from the user or from the CLI promotion step. In the current demo, `--save-playbook` auto-promotes a useful query answer; `improve --feedback` records explicit improvement notes.
- How feedback updates the wiki (`SkillRunEntry`, edge re-weighting, graph rewrite, ...): Useful query briefs are promoted into durable playbooks under `wiki/playbooks/`. Session events are written to Redis, and promoted content can also be written to Cognee permanent memory with `--use-cognee`.
- Code entry point: `tools/cognee_bookwiki.py query` and `tools/cognee_bookwiki.py improve`

### Lint

- What "linting" means in your wiki (dedupe, conflict resolution, stale pruning, ...): Lint checks broken wiki links, orphan pages, weakly sourced query/playbook pages, and duplicate titles.
- How it runs (scheduled, on-write, on-demand): On demand through the CLI after ingest/query/improve.
- Code entry point: `tools/cognee_bookwiki.py lint`

## Self-Improvement Evidence

Show that the wiki actually got smarter. Concrete before/after beats prose.

### Baseline Run

- Query / task: `How do I validate my AI audit idea without getting fooled by praise?`
- Result: The query page was created, but local lexical search returned zero source hits because the natural-language wording did not align well with the book's concept vocabulary.
- Score (your own metric, judge-readable): 0/3
- Recorded feedback:

```text
error_type: weak_grounding
error_message: The query produced a brief without enough source hits.
feedback: Route broad founder questions through durable Mom Test concepts and promote grounded playbooks when a better query succeeds.
success_score: 0
```

### Improved Run

- Query / task: `compliments facts commitment`
- Result: The query returned 8 source hits from `The Mom Test` and was promoted into `wiki/playbooks/compliments-facts-commitment.md`.
- Score: 3/3
- What changed in the wiki between runs: The successful grounded answer became a durable playbook, so future agents can reuse the distilled answer instead of repeating the failed query path.

```text
Before:
- Query page existed, but had no useful source hits.
- No durable playbook existed for avoiding false validation in customer discovery.

After:
- Query page had 8 source hits.
- `wiki/playbooks/compliments-facts-commitment.md` was created.
- Session memory recorded the query and promotion events.
```

## Architecture

```text
[book artifacts / agent turns]
        |
        v
[ Redis  - session memory ]   <- hot, per-conversation events
        |
        | distillation: query briefs and useful answers are promoted
        v
[ Cognee - permanent graph ]   <- durable cross-session memory
        |
        v
[ markdown wiki ]              <- books, concepts, queries, playbooks, lint
        |
        v
[ recall / agent loop ]
        |
        v
[ feedback -> improve -> promoted playbooks ]
```

Components:

- `files/`: preserved book artifacts from the existing book workflow.
- `tools/cognee_bookwiki.py`: CLI for ingest, query, improve, lint, and status.
- `wiki/`: generated durable markdown wiki.
- `Redis`: session memory for recent operations and working state.
- `Cognee`: permanent memory layer for remembered wiki packets and recalled context.
- `tests/test_cognee_bookwiki.py`: regression tests for ingest, query, promote, and lint.

### Redis-as-session-memory

- What the agent writes into Redis (raw turns, intermediate observations, ...): Ingest events, query events, improvement events, lint results, counts, generated file paths, and query text.
- How and when content is distilled into the graph: Ingest packets and promoted playbooks can be sent to Cognee via `cognee.remember(...)` when `--use-cognee` is enabled. Query results become markdown query briefs first; useful answers are promoted to playbooks.
- What stays in Redis vs. what gets promoted: Redis keeps recent session events and operational trace data. Durable knowledge, book summaries, concepts, and useful playbooks are promoted to the wiki and optionally Cognee.
- How distillation quality improved between baseline and improved run: The baseline broad query produced weak grounding; the improved run used a stronger concept query, got cited hits, and promoted the result into a reusable playbook.

## Agents / Skills (if any)

```text
Skill path(s):
  - .agents/skills/book-price-to-scale-coach
  - .agents/skills/the-mom-test-coach
  - tools/cognee_bookwiki.py

Roles:
  - Ingestor: reads preserved book artifacts and writes wiki/Cognee memory.
  - Querier: searches local indexes and Cognee recall.
  - Linter: checks wiki coherence.
  - Critic: uses query feedback to decide what should be promoted into playbooks.
```

## Reproduction

Commands to reproduce your demo:

```bash
python3 -m venv .venv
.venv/bin/pip install cognee redis
docker run -d --name bookwiki-redis -p 6379:6379 redis:8.0.2

.venv/bin/python tools/cognee_bookwiki.py status
.venv/bin/python tools/cognee_bookwiki.py ingest --books "The Mom Test" --max-chapters 6 --max-note-packets 80 --max-concepts 80
.venv/bin/python tools/cognee_bookwiki.py query "How do I validate my AI audit idea without getting fooled by praise?" --books "The Mom Test" --limit 8
.venv/bin/python tools/cognee_bookwiki.py lint
.venv/bin/python tools/cognee_bookwiki.py query "compliments facts commitment" --books "The Mom Test" --limit 8 --save-playbook
.venv/bin/python tools/cognee_bookwiki.py lint

# Optional Cognee-backed run, requires API credentials.
.venv/bin/python tools/cognee_bookwiki.py ingest --books "The Mom Test" --max-chapters 1 --no-notes --max-concepts 5 --use-cognee
.venv/bin/python tools/cognee_bookwiki.py query "What does The Mom Test say about compliments and commitments?" --books "The Mom Test" --limit 3 --use-cognee
```

Environment variables:

```bash
# Required for Redis-backed session memory.
# The tool defaults to this value when REDIS_URL is not set.
export REDIS_URL="redis://localhost:6379/0"

# Required only for the optional --use-cognee commands.
export OPENAI_API_KEY="sk-..."

# Cognee-compatible aliases. The CLI automatically falls back to OPENAI_API_KEY
# for these when they are not set, but setting them explicitly is also valid.
export LLM_API_KEY="$OPENAI_API_KEY"
export EMBEDDING_API_KEY="$OPENAI_API_KEY"
```

The CLI also loads the same keys from a local `.env` file at the repository root. Do not commit real API keys.

## Demo

- Live demo link (Loom, YouTube, etc.) or local instructions: Run `bash demos/momtest_self_improve.sh`.
- 3-minute pitch outline:

```text
1. Problem / idea
   Raw book RAG answers are one-off. BookWiki turns books into a living agent wiki.

2. Ingest demo
   Show `ingest` creating book pages, concept pages, and session memory.

3. Query demo (before improvement)
   Run the broad AI audit customer-discovery query and show weak grounding.

4. Self-improve step
   Run `compliments facts commitment` and promote it into a playbook.

5. Query demo (after improvement)
   Show the promoted `compliments-facts-commitment` playbook and reusable source-backed answer.

6. What is next
   Add richer concept routing, better automatic feedback scoring, and deeper Cognee graph modeling.
```

## Links

- Repo: https://github.com/brihati/
- Anything else:
  - Local wiki index: `wiki/index.md`
  - Mom Test demo script: `demos/momtest_self_improve.sh`
  - Mom Test demo notes: `demos/MOMTEST_SELF_IMPROVE_DEMO.md`
