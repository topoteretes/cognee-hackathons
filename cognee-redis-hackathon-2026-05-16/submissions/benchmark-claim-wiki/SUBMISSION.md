# Team Submission

## Team

Team name: Benchmark Claim Wiki

Participants: Jin Choi

Wiki / project name: Benchmark Claim Wiki

## Wiki Overview

Benchmark Claim Wiki is a self-correcting knowledge graph for AI benchmark claims. It ingests MLPerf Inference v5.1 result records, keeps raw and candidate claims in Redis session memory, promotes only scoped and provenance-validated claims into Cognee, then uses critic feedback to improve the distiller skill. The live before/after demo shows the wiki learning not to generalize an Offline throughput result into a Server serving-workload claim.

Domain or data sources:

- MLCommons MLPerf Inference v5.1 result records
- Llama2-70B and Mixtral-8x7B benchmark results
- Offline vs Server scenario scope
- AMD Instinct MI300X vs MI325X hardware scope
- Optional Semantic Scholar ingestion path for future benchmark papers

Primary use case:

Audit fast-moving AI benchmark claims: what result is actually supported, under which benchmark, model, hardware, scenario, and metric, and which broad claims should be rejected or retired.

What makes it stand out:

- Redis is treated as untrusted session memory, not as the final wiki.
- Cognee is the permanent trusted graph for scoped, validated claims.
- The live Redis/Cognee path fails loudly if either platform is unavailable.
- Evidence spans and deterministic offsets are validated before claims are written.
- The self-improvement loop is executed: gate feedback rewrites the distiller skill and improves the next run.
- A read-only observability UI shows the Redis quarantine, distillation gate, Cognee trusted graph, before/after scorecards, and source-span provenance from backend state.

## The Three Operations

### Ingest

What goes in:

- MLPerf result cards with source URL, benchmark name, model, hardware, scenario, metric, value, and evidence text
- Candidate claims extracted from those cards
- Raw session observations, rejected claims, and distillation-gate feedback

How it is captured:

- `ingest_real_research.py` extracts candidate claims from source cards.
- `source_spans.validate_claims_against_cards()` validates verbatim evidence spans and offsets.
- `RedisSessionStore.remember(payload, session_id=...)` stores raw and candidate session memory.
- `should_distill(claim, graph_state)` decides whether a candidate can be promoted.
- `CogneeTrustedGraphStore.remember(payload)` writes promoted trusted claims.

Code entry point:

- `ingest_real_research.py`
- `build_benchmark_database.py`
- `backend/storage.py`
- `distillation_policy.py`

### Query + Self-improve

How users query the wiki:

- Deterministic demo: `python3 demo.py`
- Live Redis/Cognee proof: `python3 cognee_redis_spike.py`
- Observability dashboard: `http://127.0.0.1:8000/observability`
- Programmatic query path: `await backend.recall(query, session_id=...)` for Redis session memory or `await backend.recall(query)` for Cognee trusted graph memory.

Where feedback comes from:

- Distillation-gate rejection reasons such as missing benchmark scope
- Critic notes such as scenario overclaiming or ungrounded answers
- Lint issues from missing source, missing scope, duplicate claims, or contradictions
- Test metrics computed from graph state

How feedback updates the wiki:

- `propose_skill_revision(feedback)` turns concrete gate/critic feedback into a stronger distiller skill.
- The proposed skill is written to `my_skills/hypothesis_distiller/SKILL.proposed.md`.
- The same source cards are redistilled with the proposed skill.
- More claims pass the gate, scenario scope is preserved, and a broad Offline-to-Server overclaim is retired.

Code entry point:

- `demo.py`
- `distiller.py`
- `critic.py`

### Lint

What "linting" means in this wiki:

- Reject ungrounded claims with no source
- Reject benchmark hypotheses with missing model, hardware, scenario, or metric scope
- Reject claims whose evidence spans are absent or invalid
- Detect contradictions where a broad claim is undercut by scoped benchmark evidence
- Track claims that should be retired after stronger contrary evidence appears

How it runs:

- On ingest: provenance validation before `claims-out` is written
- On promotion: `should_distill()` runs before Cognee writes
- On query/demo: `lint_claims()` and `score_answer()` run on demand

Code entry point:

- `source_spans.py`
- `distillation_policy.py`
- `critic.py`

## Self-Improvement Evidence

The real-data path proves current AI benchmark claims can be extracted and provenance-validated. The deterministic demo proves the self-improvement loop changes behavior from an unsafe broad claim to a scoped answer.

Real-data ingest proof:

```text
python3 build_benchmark_database.py

database: data/benchmark_claim_audit_db.json
sources:  6
claims:   6
valid:    6
promote:  6
offline:  3
server:   3

python3 ingest_real_research.py \
  --from-cards data/mlperf_v5_1_cards.json \
  --claims-out /tmp/mlperf_claims.json \
  --extractor curated

source_cards: 6 -> data/mlperf_v5_1_cards.json
claims:      6 -> /tmp/mlperf_claims.json
```

Live Redis/Cognee proof:

```text
Session backend: RedisSessionStore
Trusted graph backend: CogneeTrustedGraphStore
session write ok
graph write ok
session recall returned data
graph recall returned data
```

### Baseline Run

Query / task:

Can the top MLPerf Offline Llama2 result be generalized to all serving workloads?

Result:

```text
MI325X delivers top Llama2 throughput and should be used for all Llama2 serving workloads.
```

Score:

```text
retrieval_score:       0.70
hypothesis_hygiene:    0.15
scope_errors:          1
contradictions_caught: 0
retired_claims:        0
```

Recorded feedback:

```text
error_type: missing_scope
error_message: v1 distiller dropped benchmark/model/hardware/scenario scope, so the gate rejected all claims
feedback:
  - each candidate claim was missing scope conditions
  - answer not grounded in any trusted claim
  - overclaimed Offline throughput for serving workloads
success_score: 0.15
```

### Improved Run

Query / task:

Can the top MLPerf Offline Llama2 result be generalized to all serving workloads?

Result:

```text
MI325X Llama2 performance is supported only under MLPerf Inference v5.1,
llama2-70b-99, Offline scenario, 8x AMD Instinct MI325X; Offline results do
not generalize to Server serving workloads because MLPerf reports a separate
lower Server result.
```

Score:

```text
retrieval_score:       1.00
hypothesis_hygiene:    1.00
scope_errors:          0
contradictions_caught: 3
retired_claims:        1
```

What changed in the wiki between runs:

Before:

- v1 skill erased benchmark, model, hardware, scenario, and metric scope
- all distilled claims were rejected
- the trusted graph was empty
- the answer overclaimed from untrusted Redis session memory

After:

- critic/gate feedback produced `SKILL.proposed.md`
- v2-style skill preserved benchmark, model, hardware, scenario, metric, and negative/conditional evidence
- scoped MLPerf claims were promoted into the Cognee trusted graph
- Server scenario evidence prevented the Offline result from being treated as universal
- one broad serving-workload claim was retired

Before / after:

```text
retrieval_score:       0.70 -> 1.00
hypothesis_hygiene:    0.15 -> 1.00
scope_errors:          1    -> 0
contradictions_caught: 0    -> 3
retired_claims:        0    -> 1
```

Retrieval improves because the final answer is grounded in trusted graph claims and directly addresses the MLPerf/Llama2 question.

## Architecture

```text
[MLPerf result cards / agent turns / run traces]
        |
        v
[ Redis - session memory quarantine ]
        |
        | source-span validation + distillation gate
        v
[ Cognee - permanent trusted graph ]
        |
        v
[ recall / answer generation ]
        |
        v
[ critic + lint feedback -> skill improvement ]
        |
        v
[ revised distiller skill -> re-ingest / re-query ]
```

Components:

- `ingest_real_research.py`: use source cards and extract claims
- `build_benchmark_database.py`: generate the final audit database
- `source_spans.py`: validate evidence spans and offsets
- `backend/storage.py`: Redis session store and Cognee trusted graph adapter
- `distillation_policy.py`: promotion gate
- `distiller.py`: skill-driven claim distiller and skill proposer
- `critic.py`: graph-derived scoring and lint
- `demo.py`: deterministic self-improvement run
- `cognee_redis_spike.py`: live Redis/Cognee proof
- `observability/api.py`: read-only state endpoint and dashboard server
- `observability/state.py`: backend state projection for the observability UI

## Redis-as-session-memory

What the agent writes into Redis:

- raw source cards
- candidate benchmark claims
- rejected claims and rejection reasons
- critic feedback
- run-specific observations and traces

How and when content is distilled into the graph:

- Candidate claims first live in Redis under a session id.
- The distillation gate checks attribution, evidence-span validity, scope, duplication, and conflicts.
- Only promoted claims are written to Cognee.

What stays in Redis vs. what gets promoted:

- Stays in Redis: raw cards, untrusted candidate claims, rejected claims, failed spans, run-local feedback.
- Promoted to Cognee: attributed, scoped, validated benchmark claims; scenario distinctions; contradiction/retirement-relevant claims.

How distillation quality improved between baseline and improved run:

- Baseline skill dropped scope, so every claim was rejected.
- Improved skill preserved scope and conditional evidence, so the graph gained usable trusted claims and the answer became scenario-specific instead of universal.

## Agents / Skills

Skill path(s):

- `my_skills/hypothesis_distiller/SKILL.md`
- `my_skills/hypothesis_distiller/SKILL.v2.md`
- `my_skills/hypothesis_distiller/SKILL.proposed.md`

Roles:

- Ingestor: `ingest_real_research.py`, `research_claim_extractor.py`, `source_spans.py`
- Querier: `demo.py`, `backend.recall(...)`
- Linter: `source_spans.py`, `critic.py`, `distillation_policy.py`
- Critic: `critic.py`, `distiller.propose_skill_revision(...)`

## Reproduction

Commands to reproduce the judged demo:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

python3 -m pytest -q

python3 build_benchmark_database.py

python3 ingest_real_research.py \
  --from-cards data/mlperf_v5_1_cards.json \
  --claims-out /tmp/mlperf_claims.json \
  --extractor curated

python3 demo.py
```

Commands to run the observability UI:

```bash
.venv/bin/uvicorn observability.api:app --host 127.0.0.1 --port 8000
# open http://127.0.0.1:8000/observability
```

Commands to reproduce the live Redis/Cognee proof:

```bash
brew services start redis

export REDIS_URL=redis://localhost:6379
export LLM_API_KEY=...
export COGNEE_DATASET=benchmark-claim-wiki-trusted

python3 cognee_redis_spike.py
```

Environment variables required:

```text
LLM_API_KEY
REDIS_URL
COGNEE_DATASET
```

Optional:

```text
OPENAI_API_KEY
OPENAI_MODEL
SEMANTIC_SCHOLAR_API_KEY
COGNEE_URL
COGNEE_API_KEY
```

## Demo

Live demo link:

Local instructions above. A screen recording can show the commands in this order: benchmark database build, source-card ingest, tests, self-improvement demo, observability UI, live Redis/Cognee spike.

3-minute pitch outline:

1. Problem / idea
   - AI benchmark claims spread faster than their scope.
   - The wiki treats raw claims as untrusted until they pass provenance and scope checks.
2. Ingest demo
   - Run MLPerf v5.1 ingest.
   - Show 6 validated benchmark claims with source URLs, exact evidence spans, hardware scope, model scope, metric scope, and Offline/Server scenario scope.
3. Query demo before improvement
   - Run `python3 demo.py`.
   - Show v1 answer overclaims because the distiller erased scope.
4. Self-improve step
   - Show feedback from gate rejections plus critic notes.
   - Show `SKILL.proposed.md` generated from that feedback.
5. Query demo after improvement
   - Show the improved answer preserves scope and avoids the Offline-to-Server generalization.
   - Show hygiene 0.15 -> 1.00, contradictions 0 -> 3, retired claims 0 -> 1.
6. What is next
   - Expand beyond the 6-record seed into a held-out benchmark corpus.
   - Gate future skill revisions on external benchmark accuracy, not internal score alone.

## Links

Repo:

https://github.com/gorajing/benchmark-claim-wiki

Slides / writeup:

TBD

Anything else:

- `docs/COGNEE_REDIS_SPIKE.md`
- `docs/BENCHMARK_RESULT_INGESTION.md`
- `docs/PROVENANCE_CONTRACT.md`
- `docs/OBSERVABILITY.md`
