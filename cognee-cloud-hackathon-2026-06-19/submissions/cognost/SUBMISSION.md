# Cognost — a self-improving stakeholder-alignment Company Brain

**Cognee Cloud Hackathon · 2026-06-19**

## Team

- **Team name:** Cognost *(Latin: "I know")*
- **Participants:**
  - Maria Beiner — [linkedin.com/in/maria-beiner](https://www.linkedin.com/in/maria-beiner/)
  - Rozy Kassab — [linkedin.com/in/rozy-kassab](https://www.linkedin.com/in/rozy-kassab)
  - Santosh Mutyala — [linkedin.com/in/smutyala2000](https://www.linkedin.com/in/smutyala2000/)
  - Martin Kaiser — [linkedin.com/in/martin-kaiser-ai](https://www.linkedin.com/in/martin-kaiser-ai)
- **Company Brain / project name:** Cognost

## One-liner
A Company Brain for a product team that doesn't just *store* docs — it **surfaces where the docs
disagree**, tracks which decisions are current, flags what has no owner, and **improves its own
answering behavior from feedback**.

## The idea
Every product org has the same failure mode: the PRD says one thing, the roadmap drifted, Sales
signed a contradicting promise, and the design shipped a feature marked "Won't have." The truth
is *knowable* but scattered across a dozen documents written by seven stakeholders. A normal RAG
bot papers over this — it picks one source and sounds confident. **Cognost is built to do the
opposite: preserve the contradiction, cite both sides, and say which version is current.**

We use the synthetic **BrainFlow** dataset (12 product docs with 11 planted misalignments) as the
team knowledge. The brain's operating contract is `CLAUDE.md` (provenance mandatory, never
silently resolve a contradiction, always state current-vs-superseded).

## Architecture — two-tier memory
| Tier | What lives here | In this project |
| --- | --- | --- |
| **Session memory** (ephemeral) | raw Q&A events, scores, feedback per run | `brain/session/*.jsonl` + Cognee session (`session_id`) |
| **Permanent graph** (durable) | entities, typed relationships, summaries, the synthesized wiki | Cognee graph (`cognee.cognify`) + `wiki/` pages |

**Self-improvement = distillation from session → permanent**, via `cognee.improve(session_ids=…)`
plus an explicit rewrite of the maintainer *skill* learned from scored feedback.

## The three operations
```bash
python brain/ingest.py --reset --raw-only          # 1 INGEST  → permanent graph
python brain/query.py  --tag run                    # 2 QUERY   → cited, conflict-aware answers
python brain/selfimprove.py --from-tag run          #   IMPROVE → distill + propose skill rewrite
python brain/lint.py                                # 3 LINT    → contradictions / orphans report
```
One-shot: `bash brain/run_demo.sh`.

## The self-improvement loop (what the judges asked for)
The hackathon's skill cycle — *remember skill → run → score → record feedback (propose, don't
apply) → apply explicitly* — maps 1:1 onto the native Cognee 1.2 API:

1. **Remember skill** — the maintainer skill (`brain/skills/wiki-maintainer.md`) is loaded as the
   `system_prompt` for `cognee.recall`.
2. **Run** — `recall(query, GRAPH_COMPLETION, session_id=…)` answers from the permanent graph and
   writes the interaction to **session memory**.
3. **Score** — a deterministic rubric (cited a source? surfaced the disagreement? stated
   current-vs-superseded?) scores each answer 0–10.
4. **Record feedback (propose, don't apply)** — failures are written to session memory and chained
   to Cognee via `FeedbackEntry(qa_id, score, text)`. `selfimprove.py` then **diagnoses which
   rubric dimensions failed** and writes a **proposed** new skill — adopting the exact `CLAUDE.md`
   policy that would have fixed each failure — to `brain/proposals/` **without applying it**.
5. **Apply explicitly** — `selfimprove.py --apply <proposal>` swaps it into the active skill
   (archiving the previous one). `cognee.improve(session_ids=…)` distills the scored session into
   the permanent graph.

The brain literally **learns its own operating rules from its mistakes**, sourcing them from the
schema rather than inventing them.

## Self-Improvement Evidence

| Run | Skill | Avg score | Cited | Surfaced conflict | Stated currency |
| --- | --- | --- | --- | --- | --- |
| **Before** | baseline v1 | **1.3 / 10** | 0/7 | 0/7 | 0/7 |
| **After** | wiki-maintainer | **10.0 / 10** | 7/7 | 7/7 | 7/7 |

### Baseline Run

- **Query:** What's the current premium-upgrade timing, and was it ever changed?
- **Result:** "The premium upgrade prompt appears on Day 3 after first use."
- **Score: 1/10** — confident, no citation, conflict hidden, wrong value served as live
- **Recorded feedback:**
  ```
  error_type: stale_value_served_as_live
  error_message: Day 3 was reverted to Day 7 on 2026-04-09; baseline picked the superseded value
  feedback: must cite source, must state current-vs-superseded, must flag stale references
  success_score: 1
  ```

### Improved Run

- **Query:** What's the current premium-upgrade timing, and was it ever changed?
- **Result:** "**Current: Day 7 after first use** (Decision Log, 2026-04-09 — Product review
  reverted it, superseding the 2026-02-14 move to Day 3). Originally Day 7 (PRD §Monetisation,
  2026-01-22) → Day 3 (Decision Log 2026-02-14) → **back to Day 7** (Decision Log 2026-04-09).
  ⚠️ Stale references still cite Day 3: **Roadmap 2026** and **Design Spec Screen 5**."
- **Score: 10/10** — cited, surfaced the supersession chain, flagged stale references
- **What changed:** The brain scored its own failure (1/10), diagnosed that it violated
  `CLAUDE.md §3.1` (no provenance) and `§3.6` (no current-vs-superseded). It proposed a skill
  rewrite adopting those exact policies — proposed first, applied explicitly. `cognee.improve()`
  distilled the session into the permanent graph.

Full evidence (7 questions, all 11 planted issues): `brain/evidence/before-after.md` + `brain/evidence/lint-report.md`

## Lint (the alignment money-shot)
`brain/evidence/lint-report.md` catches all 11 planted issues: 6 live contradictions, 2
superseded-but-still-referenced decisions, metric drift, 4 ownership orphans, and a
spec-vs-design gap — each with provenance and the current value. Decisions are **reported, never
auto-resolved** (`CLAUDE.md` §7).

## Cognee Cloud
`python brain/ingest.py --push` pushes the dataset to a Cloud instance
(`COGNEE_CLOUD_URL` / `COGNEE_CLOUD_API_KEY`) without restructuring the code — qualifies for the
Cloud bonus.

## Stack
Cognee `1.2.0.dev1`, local Ollama (cognee-distilled extraction model + `nomic-embed-text`), no
cloud key required to run. Python 3.12.

## Run it
```bash
cd Cognost && uv venv && source .venv/bin/activate
uv pip install "cognee==1.2.0.dev1" transformers
bash brain/run_demo.sh
```

---

## The 5-point pitch

1. **The problem.** Every product team's truth is scattered across a PRD, a roadmap, ADRs, Slack,
   sales promises and a design file — and they quietly drift apart. A normal RAG bot papers over
   the drift: it picks one source and sounds confident.
2. **The product.** Cognost is a Company Brain that does the opposite — it **surfaces where the
   docs disagree**, cites both sides, and says which value is current vs. superseded.
3. **It self-improves.** It scores its own answers (cited? surfaced the conflict? stated
   currency?) and adopts the operating rule that would have fixed each failure — sourced from its
   `CLAUDE.md` contract, proposed first and applied explicitly. `baseline → maintainer`.
4. **It maintains itself.** A lint pass catches all 11 planted misalignments — 6 live
   contradictions, 2 superseded-but-referenced decisions, metric drift, 4 ownership orphans — the
   bookkeeping no team ever does, reported and never auto-resolved.
5. **Proven, not promised.** Run live on Cognee Cloud over a 42-doc needle-in-haystack corpus:
   **8/8** stakeholder questions surfaced their conflict with citations; **3/3** decoys correctly
   left alone (no false positives); the reverted Day-3 paywall traced across 5 documents
   including an unstructured meeting transcript.

## Skills

The brain's behaviour lives in versioned **skills** (`my_skills/`), governed by the `CLAUDE.md`
maintainer contract and improved through Cognee's native skill API:

| Skill | Role |
| --- | --- |
| `wiki-maintainer.baseline.md` | **Before** — naive: "be concise, give a direct answer". |
| `wiki-maintainer.md` | **After** — learned: provenance mandatory · preserve contradictions · current-vs-superseded. |

The improvement loop maps 1:1 onto Cognee 1.2's first-class primitives — `SkillRunEntry` (a
graph-backed scored run), `improve_skill(apply=False→True)` (propose then adopt a
`SkillImprovementProposal`), and `cognee.improve(session_ids=…)` (distil session → permanent
graph). Mapping and runnable reference: `brain/SKILL_API_ALIGNMENT.md`, `brain/skill_native.py`.

## Before / after evidence

Same questions, no question text changed. The baseline skill answers confidently from one source;
the learned skill cites, surfaces the disagreement, and states which value is current.

- **Local pipeline** → `brain/evidence/before-after.md` + `brain/evidence/lint-report.md`
  (generated by `bash brain/run_demo.sh`).
- **Live on Cognee Cloud** → the 42-doc verified suite: `brainflow/snapshots/query-results.json`
  (8/8 conflicts surfaced · 3/3 decoys held) and the visual diagnostic
  `brainflow/brain-diagnostic.html` (the **0 → 6** open-contradictions counter).

## Cognee Cloud (bonus)

Cloud integration is wired two ways:
- **REST** — `remember` / `recall` against the tenant (the 42-doc `brainflow` brain is live).
- **SDK `serve()`** — `brain/serve_cloud.py` connects the SDK to the cloud instance via
  `cognee.serve(url, api_key)`, then routes `remember` / `recall` to it
  (`python brain/serve_cloud.py --recall "..."`).

## Links

- **Repo:** https://github.com/kaiser-data/cognost
- **Slides:** https://canva.link/rv9lj0ni9wiknn5
- **Live diagnostic (artifact):** https://claude.ai/code/artifact/7f6b3fdf-5562-412a-a3e1-a05c46039b36
- **Architecture:** `brainflow/ARCHITECTURE.md`
- **Dataset notes:** `DATASET.md` · **Maintainer contract:** `CLAUDE.md`
