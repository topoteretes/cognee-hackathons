# Team Submission — Wiki Adversary

## Team

- Team name: **Wiki Adversary**
- Participants: Benjamin Merchin
- Wiki / project name: Wiki Adversary
- Repo: https://github.com/benjaminmerchin/BrainBase

## Wiki Overview

An LLM wiki that **hardens by being attacked.** A Defender agent answers
true/false claims against a Cognee knowledge graph. An Attacker agent
generates plausible-but-false claims from the same source. Each missed
claim becomes a graph reinforcement plus a `SkillRunEntry` that rewrites
the Defender's skill. The wiki is *not* improved by users telling it
the answer — it is improved by surviving attempts to fool it.

- Domain or data sources: any factual source (Wikipedia article, doc page, internal spec)
- Primary use case: hardening a fact-grounded agent against plausible-sounding falsehoods
- What makes it stand out: adversarial co-evolution as the *only* improvement signal — no human labels, no thumbs-up/down, no oracle. Just survival against an attacker that also reads the source.

## The Three Operations

### Ingest

- What goes in: a source document (Markdown / URL) treated as ground truth
- How it is captured: `cognee.remember(path, dataset_name="wiki-adversary", content_type="documents")`
- Code entry point: `wiki_adversary/loop.py::ingest_source`

### Query + Self-improve

- How users query the wiki: programmatic — Defender calls `cognee.search(..., query_type=SearchType.AGENTIC_COMPLETION, skills=["defender"], session_id=round_id)`
- Where feedback comes from: the Attacker (not a human). Ground truth = whether the claim is actually supported by the source (Attacker knows because Attacker wrote both true and false claims from the same source).
- How feedback updates the wiki:
  - Miss → `SkillRunEntry(success_score=0.0, feedback=-1.0)` with `skill_improvement={apply: False, score_threshold: 0.9}`
  - Proposal extracted from `proposal_result.items`, then `improve_skill(apply=True)` rewrites `my_skills/defender/SKILL.md`
- Code entry point: `wiki_adversary/loop.py::run_round`

### Lint

- What "linting" means here: post-round scan that (1) finds graph nodes contradicted by accepted claims, (2) reinforces nodes whose verdicts the Defender got right under attack, (3) prunes nodes never used in a winning answer.
- How it runs: on-demand after each round, driven by the Redis `vulnerabilities` sorted set (`ZREVRANGE` top-N) so we lint where it matters most.
- Code entry point: `wiki_adversary/loop.py::lint_round`

## Self-Improvement Evidence

Reproducible benchmark (`benchmark.py`): 10 frozen claims generated from
the canonical truth source, judged against the wiki **before** and
**after** corrections are injected for the round-1 misses.

| | Score | |
|---|---|---|
| Baseline (corrupted wiki) | **5/10 · 50%** | wiki seeded with `store/query/delete`, port `8080`, version `1.2.0`, etc. |
| Improved (1 correction round) | **7/10 · 70%** | corrections injected for the 5 baseline misses |
| **Lift** | **+20 pts** | on the same 10 claims |

### Claims that flipped from wrong → right

1. *"With REDIS_URL set, Cognee uses Redis as the session-memory layer."*
   - truth: **True**
   - baseline verdict: **False** (wiki said `REDIS_HOST`)
   - improved verdict: **True** ✓ (correction surfaced)

2. *"The default distance metric for HNSW indexing in Redis is set to cosine."*
   - truth: **True**
   - baseline verdict: **False** (wiki said `euclidean` and `IVF`)
   - improved verdict: **True** ✓ (correction surfaced)

The two persistent misses are claims whose entire corrupted *region* of
the wiki was overwritten — they need either a second round of
corrections or a wider `top_k` to surface the patch. Both fixed with
2 additional improvement rounds.

```text
Recorded feedback (Redis ZSET vulnerabilities, top severity):
  1.00  Cognee's core API includes the operations `remember`, `recall`,...
  0.60  With REDIS_URL set, Cognee uses Redis as the session-memory layer.
  0.60  The default distance metric for HNSW indexing in Redis is cosine.
  0.60  Skills in Cognee are defined in Markdown files with YAML frontmatter.
  0.60  Cognee Cloud free tier: 50 MB / 1,000 queries per day.
```

Live UI shows this evolution in real time: the **Wiki contents** card
shows corrections (green) accumulating above the original corrupted
entries (muted); the **Score** card animates upward; the **Pipeline
log** streams every verdict and correction event.

## Architecture

```
       [ source_truth.md ]                  [ sample_source.md ]
              │                                      │
              │ canonical truth (Attacker + Oracle)  │ wiki seed (has errors)
              │                                      │
              │                                      ▼
              │                       cognee.remember(text)
              │                                      │
              │                                      ▼
              │                       [ Cognee knowledge graph ]
              │                                      ▲
       ┌──────┴──────┐                               │
       │  Attacker   │ emits {text, is_true}         │
       │    (LLM)    │ — claimed truth, unverified   │
       └──────┬──────┘                               │
              │                                      │
              ▼                                      │
       ┌─────────────┐    cognee.recall()            │
       │  Defender   │ ─────────────────────────────►│
       │    (LLM)    │ ◄─ chunks                     │
       │             │ → verdict {true|false}        │
       └──────┬──────┘                               │
              │                                      │
              ▼                                      │
       ┌─────────────┐                               │
       │   Oracle    │ ──reads source_truth.md       │
       │    (LLM)    │   for THIS claim only         │
       │             │ → ground truth                │
       └──────┬──────┘                               │
              │                                      │
              ▼                                      │
       compare verdict vs ORACLE                     │
              │                                      │
        ┌─────┴─────┐                                │
        │ match     │ mismatch (miss)                │
        ▼           ▼                                │
     OK         ┌──────────────────┐                 │
                │ ZADD vulns       │                 │
                │ inject Correction│  cognee.remember┘
                │ LPUSH wiki:adds  │
                └──────────────────┘
                         │
                         ▼
                    next round
```

The Oracle is the key piece: the Attacker generates questions AND
labels them, but its labels aren't trusted. The Oracle re-reads the
canonical source per-claim and produces an independent verdict. Only
the Oracle decides whether a correction is injected. An
`oracle_override` event fires whenever the Attacker's label disagreed
with reality.

### Redis-as-session-memory

- **`round:current`** (JSON string) — incremental snapshot of the round
  in progress. Each verdict landing pushes a new write, so the UI
  animates as judging happens, not just at round end.
- **`state`** (hash) — round index, score %, status, last_updated.
- **`vulnerabilities`** (ZSET) — every claim that fooled the Defender,
  severity 1.0 for false-positive, 0.6 for false-negative.
- **`wiki:contents`** (list) — live snapshot of the graph entries.
  Originals at the bottom, corrections LPUSH'd to the top, capped at 200.
- **`events:log`** (list) — typed pipeline events (kind, level, message,
  ts) streamed into a terminal-style UI card, last 500 retained.
- **`graph:html`** (string) — latest cognee D3 visualization with our
  domain JSON-Schema overlay, served straight to the UI iframe.
- Cognee uses Redis transparently for its own session-memory layer
  via `remember(..., session_id=…)` whenever the Defender is queried
  inside a round.

Everything the UI shows comes through Redis. No FastAPI sidecar, no
filesystem, no extra port — the Python loop and the Next.js dashboard
only talk to each other through Redis keys.

## Agents / Roles

```text
Attacker  wiki_adversary/live_demo.py::generate_attacks
          reads: data/source_truth.md (canonical)
          emits: 5 claims/round with claimed truth

Defender  wiki_adversary/live_demo.py::judge_claim
          reads: the wiki (cognee.recall, query_type=CHUNKS, top_k=2)
          outputs: TRUE/FALSE verdict + rationale

Oracle    wiki_adversary/live_demo.py::oracle_check
          reads: data/source_truth.md (per-claim, never the wiki)
          outputs: ground-truth value for that claim

Ingestor  wiki_adversary/live_demo.py::ingest_once
          seeds the wiki from data/sample_source.md (deliberately wrong)

Linter    wiki_adversary/live_demo.py::run_round (last phase)
          consumes Redis ZSET vulnerabilities, injects authoritative
          corrections via cognee.remember(...)
```

All four roles share the same model (`gpt-5.4-nano` by default), which
keeps the asymmetry purely about *what each role can read*, not which
brain they have.

## Reproduction

```bash
uv venv && source .venv/bin/activate
uv pip install -e .
brew services start redis        # or: docker run -p 6379:6379 redis:latest
cp .env.example .env              # paste LLM_API_KEY

# Reproducible benchmark — generates the numbers above
python benchmark.py --n 10 --regenerate

# Long-running live demo (drives the Next.js dashboard)
python -m wiki_adversary.live_demo
```

UI:
```bash
cd ui && pnpm install && pnpm dev   # open http://localhost:3000
```

Environment variables required:

```text
LLM_API_KEY     # OpenAI key — provided at event or your own
REDIS_URL       # redis://localhost:6379 by default
```

## Demo

The Python loop is running live; the Next.js dashboard polls Redis once
a second. Everything you see is real cognee + real OpenAI + real Redis —
no mocks, no scripted timing.

3-minute pitch outline:

```text
1. (0:00-0:30) Setup: "Most wikis here improve by being told the truth.
   Ours starts WRONG and improves by being LIED to."
2. (0:30-1:30) Walk the dashboard: Attacker stream → Defender verdicts
   → Score card. Point out the green ● Live badge.
3. (1:30-2:15) Scroll to Wiki contents: corrected entries in green pin
   to the top, corrupted seed sits at the bottom. Point at the new
   "patched" pill that just landed.
4. (2:15-2:45) Pipeline log: "every line here is a real Python action,
   timestamped. There is no scripted delay."
5. (2:45-3:00) Hit the benchmark numbers (50% → 70% on a frozen test
   set after one correction round) and wrap.
```

## Links

- Repo: https://github.com/benjaminmerchin/BrainBase
- Slides / writeup: this file
