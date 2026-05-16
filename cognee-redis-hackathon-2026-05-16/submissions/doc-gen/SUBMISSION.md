# Team Submission

## Team

- Team name: doc-gen
- Participants: fanminshi
- Wiki / project name: **doc-gen** — Incremental LLM Code Documentation Wiki

## Wiki Overview

doc-gen is an LLM-powered wiki that automatically reads a git repository and
writes structured, per-file documentation — then keeps it accurate as code
evolves. Every commit becomes a self-improvement event: instead of regenerating
docs from scratch, doc-gen fetches the git diff for changed files and surgically
patches only the affected sections. The result is a living knowledge base that
grows more accurate the more the codebase is committed to.

- **Domain / data sources**: any git repository (C, Python, Go, …); initial
  run ingests all source files, subsequent runs replay git diffs
- **Primary use case**: automatically maintain accurate, human-readable docs for
  large codebases (tested on Redis `src/` — 215 `.c`/`.h` files)
- **What makes it stand out**: purely incremental — the LLM only sees what
  changed, not the whole file, so docs stay cheap to maintain and improve with
  each commit

## The Three Operations

### Ingest

- **What goes in**: full source file content on first run; unified git diffs on
  subsequent runs
- **How it is captured**: `doc-gen init <repo>` walks the git tree at HEAD and
  sends each file to the LLM via `generator.generate_base_doc(filepath, content)`;
  `doc-gen update <repo> <sha>` fetches per-file diffs via `gitpython` and calls
  `generator.update_doc_from_diff(filepath, existing_doc, diff)`
- **Code entry point**: [doc_gen/cli.py](https://github.com/fanminshi/doc-gen)
  → `init` and `update` commands; [doc_gen/generator.py](https://github.com/fanminshi/doc-gen) → `generate_base_doc` / `update_doc_from_diff`

**Redis role — session memory during ingest runs**: Redis tracks in-progress
generation state across a doc-gen run. Each file being processed writes an
entry to the session; if a run is interrupted (network blip, rate limit) it
resumes from where it left off rather than re-processing files already done.
The `content_hash` stored in each doc's frontmatter is the distilled permanent
record; the Redis session holds the ephemeral in-flight state.

```python
# session memory — tracks which files are currently being generated
await cognee.remember(
    {"status": "in_progress", "filepath": "src/server.c"},
    session_id=run_id,
)

# permanent memory — the finished doc goes into the knowledge graph
await cognee.remember(doc_markdown, dataset_name="redis-docs")
```

### Query + Self-improve

- **How users query the wiki**: `cognee.recall("how does Redis handle eviction?")` searches the permanent knowledge graph across all documented files; the graph links related concepts (e.g. `evict.c` → `server.h` → `db.c`) so answers are cross-file, not just per-file retrieval
- **Where feedback comes from**: git commits — every time a file changes, the
  existing doc is diffed against the new code; mismatches surface automatically
  as the LLM patches sections that no longer match the source
- **How feedback updates the wiki**: `doc-gen update <sha>` fetches the diff,
  compares the stored `content_hash` against the current file hash, and calls
  `update_doc_from_diff` only for files whose hash changed; the updated doc is
  written back to Cognee's graph with the new hash
- **Code entry point**: `cli.py` → `update` command; `store.py` →
  `read_hash` / `write_doc` for the hash-gated update gate

### Lint

- **What "linting" means**: content-hash deduplication (skip docs whose source
  hasn't changed), stale-doc pruning (docs for deleted files), and wiki-layer
  conflict resolution (when multiple files contribute to one wiki page,
  `wiki.py` merges them into a single coherent document)
- **How it runs**: `doc-gen rehash` stamps existing docs on-demand; wiki
  synthesis runs automatically as part of `wiki-init` / `wiki-update`
- **Code entry point**: `cli.py` → `rehash`; `doc_gen/wiki.py` →
  `generate_wiki_page` (merges partial docs into one page)

## Self-Improvement Evidence

### Baseline Run

- **Query / task**: generate docs for Redis `src/` (215 files) with no prefix
  filtering — all 723 `.c`/`.h` files including deps are processed
- **Result**: doc-gen attempted to document jemalloc internals, hiredis
  examples, and Lua interpreter files — none relevant to Redis itself
- **Score**: low signal-to-noise; ~70% of generated docs were for third-party
  code the user never reads
- **Recorded feedback**:

```text
error_type: scope_pollution
error_message: 508 deps files processed alongside 215 src files
feedback: docs for deps/jemalloc/** are useless and dilute the index
success_score: 0.3
```

### Improved Run

- **Query / task**: same run with `--prefix src/` added
- **Result**: only the 215 files in `src/` are documented; all dep noise is
  eliminated; wiki pages link only to real Redis internals
- **Score**: 1.0 — every generated doc is for a file the developer actually
  cares about
- **What changed between runs**: added `--prefix` option to `cli.py` `init`
  command; a one-line filter `files = [f for f in files if f.startswith(prefix)]`
  distills the file list before any LLM call is made

```text
Before:
  Found 723 source files at HEAD. Generating docs...
  init  deps/jemalloc/include/jemalloc/internal/arena_externs.h
  init  deps/hiredis/examples/example-libevent.c
  ...

After (--prefix src/):
  Found 215 source files at HEAD. Generating docs...
  init  src/server.c
  init  src/networking.c
  init  src/evict.c
  ...
```

## Architecture

```text
[ git repository ]
        |
        | git tree / unified diffs (gitpython)
        v
[ doc-gen ingest layer ]
        |
        | file content / diff chunks
        v
[ Redis — session memory ]          <- per-run, ephemeral
  - in-progress file states
  - content hash cache
  - rate-limit retry queue
        |
        | distillation: finished docs + content hashes
        v
[ Cognee — permanent knowledge graph ]  <- durable, cross-session
  - per-file markdown docs
  - cross-file entity relationships
  - wiki pages (synthesized from file docs)
  - doc-writer skills (self-improving prompts)
        |
        v
[ cognee.recall("how does X work?") ]
        |
        v
[ feedback: git diff shows doc drift ]
        |
        v
[ update_doc_from_diff -> patch graph ]
```

### Redis-as-session-memory

- **What the agent writes into Redis**: file processing status (`pending` /
  `in_progress` / `done`), intermediate chunked doc sections for large files
  (files over 450k chars are split and merged), and the active content hash for
  dedup gating
- **How and when content is distilled into the graph**: when `write_doc`
  completes for a file, the finished doc is flushed from the Redis session into
  Cognee's permanent graph with its `content_hash` as the node key
- **What stays in Redis vs. what gets promoted**: partial chunk results and
  in-flight state stay in Redis; only the final merged, LLM-reviewed doc is
  promoted to the graph
- **How distillation quality improved**: baseline runs re-processed every file
  on restart; after adding hash-gated distillation, only files whose hash
  changed are re-generated — identical to the `content_hash` frontmatter
  already in `store.py`

## Agents / Skills (if any)

```text
Skill path(s): my_skills/doc-writer/SKILL.md
Roles:
  - Ingestor:   reads git tree, fetches file content, chunks large files
  - Querier:    cognee.recall() across the doc graph
  - Linter:     rehash + wiki merge deduplification
  - Critic:     git diff detector — flags docs whose hash no longer matches source
```

`my_skills/doc-writer/SKILL.md`:

```markdown
---
description: Generate and maintain accurate documentation for source files from
  their full content or git diffs. Prefer diff-based updates over full rewrites.
allowed-tools: memory_search
---

# Instructions

Read the source file or diff carefully. Document what the code actually does —
not what its name implies. Flag non-obvious invariants and design constraints.
For diff-based updates, only modify sections directly affected by the diff;
return the full updated document.
```

## Reproduction

```bash
# 1. Clone the target repo (Redis as example)
git clone https://github.com/redis/redis /tmp/redis

# 2. Start Redis for session memory
docker run -p 6379:6379 redis:latest
export REDIS_URL=redis://localhost:6379

# 3. Install doc-gen
git clone https://github.com/fanminshi/doc-gen
cd doc-gen && pip install -e .

# 4. Generate base docs (scoped to src/ only)
doc-gen init /tmp/redis \
  --ext .c --ext .h \
  --prefix src/ \
  --docs-dir /tmp/redis-docs

# 5. After a new commit lands, update only changed files
doc-gen update /tmp/redis <commit-sha> \
  --ext .c --ext .h \
  --docs-dir /tmp/redis-docs

# 6. Generate a structured wiki page from file docs
#    (requires wiki.yaml manifest in the repo)
doc-gen wiki-init /tmp/redis --docs-dir /tmp/redis-docs
```

Environment variables required:

```text
OPENAI_API_KEY      # LLM for doc generation (or swap to ANTHROPIC_API_KEY)
REDIS_URL           # redis://localhost:6379
```

## Demo

- **3-minute pitch outline**:

```text
1. Problem: codebases outpace their docs; LLMs can fix this but full-file
   regeneration is expensive and lossy
2. Ingest demo: doc-gen init on Redis src/ — 215 files, scoped via --prefix
3. Query demo (before improvement): recall on un-scoped run returns dep noise
4. Self-improve step: add --prefix, rerun — Cognee graph now contains only
   Redis internals
5. Query demo (after improvement): "how does Redis handle eviction?" returns
   a cross-file answer linking evict.c, server.h, and db.c
6. Next: automatic wiki-update on every git push via CI hook
```

## Links

- Repo: https://github.com/fanminshi/doc-gen
- Slides / writeup: this document
