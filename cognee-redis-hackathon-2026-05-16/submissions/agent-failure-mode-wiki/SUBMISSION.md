# Team Submission

> **Project repo:** [Jiyungi/agent-failure-mode-wiki](https://github.com/Jiyungi/agent-failure-mode-wiki)
> **Live demo entry point:** [`README.md`](https://github.com/Jiyungi/agent-failure-mode-wiki#agent-failure-mode-wiki) | [`demo/visual/`](https://github.com/Jiyungi/agent-failure-mode-wiki/tree/main/demo/visual) | [`demo/record_demo.sh`](https://github.com/Jiyungi/agent-failure-mode-wiki/blob/main/demo/record_demo.sh)

## Team

- **Team name:** Failure Wiki
- **Participants:** Jiyun Kim
- **Wiki / project name:** Agent Failure Mode Wiki

## Wiki Overview

The Agent Failure Mode Wiki is operational memory for long-horizon and
multi-agent systems. It stores past failure modes (signature, root cause,
context tags, recovery action, confidence) and connects each one to the
agent queries that retrieved it, the solution logs that came from
applying its recovery, and the lint issues flagged against weak memory.
Each run grows the wiki: when the agent hits a failure that already has
a high-confidence recovery, it applies the stored fix instead of
re-deriving it; when the failure is new, it ingests the failure as a
low-confidence record. After each run, a propose-then-apply loop walks
the recoveries that succeeded and promotes them up a confidence ladder
(0.4 → 0.7 → 1.0). Lint flags every record below `1.0`, so the wiki
tells you exactly which memories are still worth doubting.

- **Domain or data sources:** agent run telemetry — the failures the
  agent itself emits while traversing graphs, calling tools, or
  retrieving context. Six failure classes are seeded; new failure modes
  are ingested live.
- **Primary use case:** drop-in operational memory for any long-horizon
  or multi-agent system that wants to stop re-discovering the same
  failures (and burning tokens) on every run.
- **What makes it stand out:** the wiki is a structured graph, not
  prose. We bypass `cognify()` and load Cognee directly with typed
  `DataPoint` upserts, so the structured load completes in seconds and
  the demo shows real graph nodes/edges within the 3-minute slot.

## The Three Operations

### Ingest

- **What goes in:** failure events emitted by the agent during a run
  (signature plus the last three traversal steps), agent queries against
  the wiki, the recovery actions applied, the solution-log outcomes,
  lint findings, and the per-session event stream.
- **How it is captured:**
  - **Redis (session tier):** `SessionMemory.record(...)` appends each
    raw event to `session:{id}:events` (a Redis list) and registers the
    session in `session:index`. The `failure_wiki` itself is a RedisVL
    `IndexSchema` with `flat` cosine vector index plus tag/text fields.
  - **Cognee (durable tier):** at the end of the run,
    `cognee_failure_graph.load_failure_wiki_into_cognee` calls
    `cognee.tasks.storage.add_data_points` with typed nodes
    (`FailureMode`, `RecoveryAction`, `AgentQuery`, `SolutionLog`,
    `LintIssue`, `SessionRun`).
- **Code entry point:** [`demo/seed_failures.py`](https://github.com/Jiyungi/agent-failure-mode-wiki/blob/main/demo/seed_failures.py)
  (`FailureWiki.seed`, `add_new_failure`),
  [`demo/session_memory.py`](https://github.com/Jiyungi/agent-failure-mode-wiki/blob/main/demo/session_memory.py)
  (`SessionMemory.record`),
  [`demo/cognee_failure_graph.py`](https://github.com/Jiyungi/agent-failure-mode-wiki/blob/main/demo/cognee_failure_graph.py)
  (`load_failure_wiki_into_cognee`).

### Query + Self-improve

- **How users query the wiki:** the agent calls
  `FailureWiki.lookup(text, threshold=0.82)` on every detected failure.
  RedisVL `HybridQuery` is tried first; on Redis Cloud tiers that reject
  the experimental hybrid syntax, the code falls back to a Redis scan
  with local re-ranking, so the live demo always works.
- **Where feedback comes from:** the agent itself. After each question
  produces a real answer, every recovery applied during that question is
  recorded as a `RecoveryOutcome` with `success=True`. Failed runs would
  produce `success=False`; the engine ignores those for promotion but
  keeps them visible in `manifest.json`.
- **How feedback updates the wiki:**
  `SelfImprovementEngine.compute_proposals(records)` produces an
  `ImprovementProposal` per failure that should move up the confidence
  ladder (0.4 → 0.7 → 1.0). With `--auto-improve` (default), each
  proposal is applied via `FailureWiki.update_record`, which re-embeds
  the record and reloads it into Redis. With `--no-auto-improve`,
  proposals stay in `manifest.json` for an external reviewer.
- **Code entry point:**
  [`demo/main.py`](https://github.com/Jiyungi/agent-failure-mode-wiki/blob/main/demo/main.py) `AgentFailureModeDemo._handle_failure` /
  `_run_self_improvement`,
  [`demo/self_improve.py`](https://github.com/Jiyungi/agent-failure-mode-wiki/blob/main/demo/self_improve.py)
  `SelfImprovementEngine.compute_proposals` and `apply_proposal`.

### Lint

- **What "linting" means:** flag wiki records that should not be trusted
  yet. The current rules: missing signature, missing recovery action,
  fewer than two context tags, `confidence < 0.75`, duplicate
  signatures, and new memory that did not come with a solution-log
  entry. Each issue carries severity `P1`/`P2`.
- **How it runs:** on demand at the end of every CLI run, after the
  self-improvement loop has applied its proposals, so the lint count
  reflects the post-improvement state.
- **Code entry point:**
  [`demo/wiki_artifacts.py`](https://github.com/Jiyungi/agent-failure-mode-wiki/blob/main/demo/wiki_artifacts.py)
  `lint_failure_records` and `FailureWikiArtifacts.lint`.

## Self-Improvement Evidence

### Baseline Run

- **Query / task:** three research questions over a small AI-agent
  concept graph: LangGraph + memory + tool use, reflection in cognitive
  architectures, RAG with LLM generation.
- **Result:** Question 2 surfaced a previously unseen reflection-shape
  failure. The wiki had no high-confidence match (top hit at 0.54), so
  the agent ingested it as a new `FailureMode` with `confidence=0.4`.
- **Score (judge-readable):**
  - failure records: 7 (6 seeded + FM-007 newly logged)
  - wiki queries: 4
  - solution-log entries: 4
  - `FM-007.confidence`: 0.7 after the propose-then-apply step (one
    successful run promoted it 0.4 → 0.7)
  - lint issues: 1 (`FM-007` flagged as `low_confidence_memory`)
  - Cognee structured graph: `status=ready`, 28 nodes, 36 edges
- **Recorded feedback:**

```
error_type: low_confidence_memory
error_message: Confidence is 0.70; verify the recovery before treating this as stable memory.
feedback: success_score=1.0 (question 2 still completed)
success_score: 1.0
```

### Improved Run

- **Query / task:** rerun the same three questions without
  `--reset-failure-wiki`. The wiki now contains the FM-007 record from
  the baseline run.
- **Result:** Question 2's reflection failure now matches FM-007 in the
  wiki at score `0.93` and the stored recovery (`skip current node and
  continue`) is applied directly. The propose-then-apply step bumps
  FM-007 from `0.7` to `1.0`. Lint flags zero issues.
- **Score:**
  - failure records: 7
  - `FM-007.confidence`: 1.0
  - lint issues: 0
  - Cognee structured graph: `status=ready`, 29 nodes, 40 edges
- **What changed in the wiki between runs:**

```
Before:
  FM-007.confidence = 0.7
  lint_issues = [P2 low_confidence_memory FM-007]
  proposals = [PRO-001 confidence_bump FM-007 0.4 -> 0.7 (applied)]

After:
  FM-007.confidence = 1.0
  lint_issues = []
  proposals = [PRO-001 confidence_bump FM-007 0.7 -> 1.0 (applied)]
```

The same data is in
`demo/.demo_state/wiki/manifest.json` (live, gitignored) and committed
snapshots
[`demo/evidence/manifest_before.json`](https://github.com/Jiyungi/agent-failure-mode-wiki/blob/main/demo/evidence/manifest_before.json)
and
[`demo/evidence/manifest_after.json`](https://github.com/Jiyungi/agent-failure-mode-wiki/blob/main/demo/evidence/manifest_after.json).

## Architecture

```
[ agent / multi-agent system ]
              │  emits raw events: failure detected,
              │  wiki lookup, recovery applied, outcome
              ▼
┌──────────────────────────────┐
│ Redis — session memory       │  hot, ephemeral, per-session
│  - session:{id}:events list  │  (Redis list for raw events)
│  - failure_wiki vector index │  (RedisVL flat cosine index)
└──────────────┬───────────────┘
               │ structured upsert
               │ (cognee.tasks.storage.add_data_points)
               ▼
┌──────────────────────────────┐
│ Cognee — permanent memory    │  durable, cross-session
│  FailureMode → RecoveryAction│
│  AgentQuery → SolutionLog    │
│  LintIssue, SessionRun       │
└──────────────┬───────────────┘
               │ recall
               ▼
[ next agent run / lint pass / replay ]
               │
               ▼
[ feedback (RecoveryOutcome) → SelfImprovementEngine.propose → apply ]
```

### Redis-as-session-memory

- **What the agent writes into Redis:** the `failure_wiki` vector
  records (RedisVL hash with `signature`, `context_tags`, `root_cause`,
  `recovery_action`, `confidence`, `embedding`) and a per-run event log
  in a Redis list at `session:{session_id}:events`. The list captures
  nine event kinds: `agent_started`, `question_started`, `traversal`,
  `failure`, `wiki_lookup`, `recovery`, `question_answered`, `lint`,
  `session_ended`. A 6-hour TTL keeps the session-tier honest.
- **How and when content is distilled into the graph:** at the end of
  each run, after the agent has finished all questions and the
  propose-then-apply step has run.
  `cognee_failure_graph.load_failure_wiki_into_cognee` builds typed
  `DataPoint` nodes from the failure wiki (Redis), the queries and
  solutions (the artifacts mirror), and the live session summary, then
  calls `add_data_points` once. Stable UUID5 ids keep the upsert
  idempotent across runs.
- **What stays in Redis vs. what gets promoted:** the live RedisVL
  `failure_wiki` index stays the agent's hot path on every failure, so
  lookups remain millisecond-scale. The session event log stays in
  Redis for the TTL window for replay/audit. Everything that should
  outlive the session (the failure records themselves, the agent
  queries, the solution logs, the lint findings, the session summary
  itself) is mirrored into Cognee as a graph.
- **How distillation quality improved between baseline and improved
  run:** baseline produced a Cognee `SessionRun` linked to 4 new
  `AgentQuery` nodes; the improved run added another `SessionRun`,
  reused the same `FailureMode` ids (UUID5 from `failure_id`), and
  recorded the second confidence bump as a separate `SolutionLog`. So
  Cognee now has the full chain `SessionRun → AgentQuery →
  FailureMode (confidence=1.0) ← SolutionLog × 2`, queryable with one
  graph traversal.

## Agents / Skills

```
Skill path(s): my_skills/failure-triage/SKILL.md
Roles:
  - Ingestor: AgentFailureModeDemo._handle_failure (records new FailureMode)
  - Querier:  AgentFailureModeDemo._handle_failure (FailureWiki.lookup)
  - Linter:   FailureWikiArtifacts.lint (lint_failure_records)
  - Critic:   SelfImprovementEngine (proposes/applies confidence bumps)
```

`my_skills/failure-triage/SKILL.md` is in the brief's frontmatter format
(`description`, `allowed-tools: memory_search`). It documents the policy
the agent follows when calling the wiki. Cognee 0.5.6 (pinned by the
Redis vector adapter) does not expose `cognee.remember(..., content_type="skills")`
or `improve_skill`, so the skill is a literal artifact today and the
critic is implemented in `demo/self_improve.py` instead.

## Reproduction

```bash
# 1. Install
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip setuptools wheel
python -m pip install -r demo/requirements.txt

# 2. Configure
cp demo/.env.example demo/.env
# fill OPENAI_API_KEY, REDIS_HOST, REDIS_PORT, REDIS_USERNAME, REDIS_PASSWORD

# 3. Baseline run (FM-007 is brand new, ends at confidence 0.7, lint=1)
python -B demo/main.py --backend redis --reset-failure-wiki

# 4. Improved run (FM-007 already in wiki, ends at 1.0, lint=0)
python -B demo/main.py --backend redis

# 5. Visual companion (reads .demo_state/wiki/manifest.json)
python -m http.server 8765
# open http://127.0.0.1:8765/demo/visual/
```

Environment variables required:

```
OPENAI_API_KEY            # for embeddings during the Cognee structured load
REDIS_HOST
REDIS_PORT
REDIS_USERNAME
REDIS_PASSWORD
REDIS_SCHEME              # default "redis"; use "rediss" for TLS
ENABLE_BACKEND_ACCESS_CONTROL=false   # required by cognee 0.5.x
COGNEE_SKIP_CONNECTION_TEST=true      # required by cognee 0.5.x
COGNEE_DATASET            # optional; default "agent_failure_wiki"
EMBEDDING_MODEL           # optional; default "text-embedding-3-small"
EMBEDDING_DIMS            # optional; default 1536
```

## Demo

- **Live demo:** `demo/visual/index.html` (served via
  `python -m http.server 8765`). The page reads
  `demo/.demo_state/wiki/manifest.json` so it always reflects the latest
  CLI run, including Cognee status, the live `session_id`, the proposals
  table with applied/pending state, and the lint summary.
- **Reproducible recording (terminal cast):**
  [`bash demo/record_demo.sh`](https://github.com/Jiyungi/agent-failure-mode-wiki/blob/main/demo/record_demo.sh) plays the four
  banners (problem → baseline → improved → evidence) end-to-end against
  the real Redis + Cognee + OpenAI stack. Pair it with `script -q
  demo-cast.txt bash demo/record_demo.sh` or
  `asciinema rec demo.cast -c "bash demo/record_demo.sh"` to capture.
- **Reproducible recording (visual MP4):**
  [`bash demo/record_visual.sh <screen_index>`](https://github.com/Jiyungi/agent-failure-mode-wiki/blob/main/demo/record_visual.sh)
  uses ffmpeg avfoundation to capture the visual companion. Run
  `bash demo/record_visual.sh` with no args to print the device list
  (look for `Capture screen 0`), then re-run with that index. Stop with
  Ctrl+C when the timeline finishes.
- **3-minute pitch outline:**

```
1. Problem / idea
   - "Long-horizon and multi-agent systems re-discover failures every
     run. We make failure modes durable memory."
   - Two-tier model: Redis = session memory, Cognee = permanent graph.
2. Ingest demo
   - Show 6 seeded FailureMode records loaded into Redis.
   - Show the SessionMemory event stream + failure_wiki vector index.
3. Query demo (before improvement)
   - Run the three questions. Question 2 hits a new reflection-shape
     failure that the wiki has not seen before.
   - Wiki returns no match above threshold; we ingest FM-007 at
     confidence 0.4. Lint flags it.
4. Self-improve step
   - propose-then-apply: confidence bump 0.4 -> 0.7 (applied).
   - Cognee structured load mirrors the run: 24 nodes, 19 edges.
5. Query demo (after improvement)
   - Re-run the same questions without --reset-failure-wiki.
   - FM-007 now matches at score 0.93; stored recovery is applied.
   - Confidence promotes to 1.0; lint count drops to 0.
6. What is next
   - Skill rewrite proposals (recovery_action mutations), not just
     confidence bumps.
   - Move to cognee 1.x once the Redis adapter publishes; switch to the
     remember/recall API and SkillRunEntry once available.
   - Multi-agent: each agent registers as a SessionRun; the wiki
     becomes the cross-agent contract for "things that already broke."
```

## Links

- **Repo:** this repository.
- **Slides / writeup:** [`README.md`](https://github.com/Jiyungi/agent-failure-mode-wiki/blob/main/README.md) (problem, idea,
  architecture, evidence, reproduction).
- **Skill:** [`my_skills/failure-triage/SKILL.md`](https://github.com/Jiyungi/agent-failure-mode-wiki/blob/main/my_skills/failure-triage/SKILL.md).
- **Live manifest:** [`demo/.demo_state/wiki/manifest.json`](https://github.com/Jiyungi/agent-failure-mode-wiki/blob/main/demo/.demo_state/wiki/manifest.json) (gitignored, regenerated on each run).
- **Snapshots (committed):**
  [`demo/evidence/manifest_before.json`](https://github.com/Jiyungi/agent-failure-mode-wiki/blob/main/demo/evidence/manifest_before.json),
  [`demo/evidence/manifest_after.json`](https://github.com/Jiyungi/agent-failure-mode-wiki/blob/main/demo/evidence/manifest_after.json).
