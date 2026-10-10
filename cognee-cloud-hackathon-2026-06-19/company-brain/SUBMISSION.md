# Team Submission

## Team

- Team name: Helix Brain
- Participants: Nidhir Bhavsar & Saswat Dash
- Company Brain / project name: **Company Brain — self-cleaning memory that never silently forgets**

## Company Brain Overview

A self-cleaning Company Brain on Cognee Cloud for an AI consultancy. It ingests scattered client knowledge for two engagements (BauStein construction-tech, Vitalis healthcare), answers questions, and **lints itself** — detecting redundancy, contradictions, and stale facts, resolving them, and writing a **receipt for every change** so nothing is ever silently dropped. It self-improves two ways: a deterministic drift router that cleans the graph on each lint pass, and Cognee's native skills loop.

- Domain or data sources: consulting docs per client — contracts/DPAs/BAAs (PDF), wiki/notes/onboarding (docx), Slack transcripts (JSON), unsourced notes (txt), plus canonical structured fact-records.
- Primary use case: keep a multi-client knowledge base correct and current without a human babysitting it — and prove every automated edit with an auditable receipt.
- What makes it stand out: **never-silent-forgetting** (append-only receipts in `receipts.md` + `receipts.jsonl`), per-client `dataset_name` firewall, hard-fact/compliance facts protected from low-trust overrides, and an LLM judge that **PARKs when unsure** instead of guessing.

## The Three Operations

### Ingest

- What goes in: structured fact-records (canonical, drift-bearing units) + raw docs, scoped per client.
- How it is captured: `client.remember(text, dataset_name=client, node_set=[client, source], self_improvement=False)` then `client.cognify(datasets=client)`.
- Code entry point: `brain/ingest.py` → `ingest_facts(client, name)` and `ingest_documents(client, name)`.

### Query + Self-improve

- How users query: `client.recall(question, datasets=[client])` (cross-client firewall via dataset scoping); demo grades answers against an answer-key.
- Where feedback comes from: an answer-key eval (`eval/questions.jsonl`) plus the drift detectors that flag incoherence on each lint pass; grey-band conflicts escalate to a cloud LLM judge.
- How feedback updates the brain: the drift router re-states winning facts so recall favors them, and a second native `cognee` skills loop (`remember(content_type="skills") → improve()`) refines a `qa-answerer` skill.
- Code entry point: `demo.py` (before/after eval), `brain/skills_loop.py` (native loop, stretch).

### Lint

- What "linting" means: dedupe identical facts (merge), resolve contradictions (trust+recency override, hard-fact HOLD vs low-trust, multivalue keep-both), retire stale facts past 2× their refresh horizon, quarantine/PARK what's genuinely uncertain.
- How it runs: on-demand per client; deterministic detectors first, LLM judge only for the grey band, PARK as the safe default.
- Code entry point: `brain/lint.py` → `run_lint(client, name, as_of, judge_fn)`; detectors in `brain/drift.py`, decisions in `brain/router.py`, receipts in `brain/ledger.py`.

## Self-Improvement Evidence

Verified live against Cognee Cloud (real `demo.py`/recall output, both clients). The standout case is a **compliance-critical correction**: before lint the brain recommends the GDPR-violating storage option; after lint it gives the compliant one — and writes a receipt explaining why.

### Baseline Run (before lint)

- Query: "Where can we store BauStein raw helmet-cam video?"
- Result (real recall): **"Store the BauStein raw helmet‑cam video in the US‑east storage bucket."** → **WRONG**. A newer but low-trust Slack message (`bau-03`, "pipe raw clips to US-east so the demo loads faster") wins on recency over the signed DPA.
- Score: graded WRONG against the answer-key (`expect EU-Frankfurt`, `must_not US-east`).
- Recorded feedback:

```text
error_type: hard-fact-violation (contradiction)
error_message: low-trust Slack source recommends US-east raw video, contradicting the signed DPA (EU-Frankfurt, anonymized)
feedback: HOLD the hard policy; reassert it in memory and explicitly deprecate the US-east option; never overridden by a lower-trust source
success_score: 0 (pre-lint)
```

(Two other headline questions — RFI Copilot's LLM and Scribe Assist's LLM+HIPAA — the brain already answers correctly before lint; cognee's recall synthesizes the current value from the facts. Those stay correct after lint. We report this honestly rather than claim everything flips.)

### Improved Run (after lint)

- Query: same question after `run_lint`.
- Result (real recall): **"EU‑Frankfurt storage bucket"** → **FIXED**. The signed DPA is upheld; the US-east shortcut is no longer recommended.
- Mechanism (the actual fix): `forget()` is unreliable on the cloud (DELETE returns 500), so the imposer does **not** rely on deletion. On a HOLD/OVERRIDE/RETIRE it writes the *resolved truth* back to memory — an authoritative corrective that reasserts the winner and explicitly deprecates the loser — then re-`cognify`s so recall reflects it. The brain now both *knows* (receipt) and *says* (recall) the right answer.
- Stats (real): `clashes 9→0` · `resolved_free: 9` · `needed_judge: 0` · `parked: 0` · `health: 1.0` · **9 receipts** written.
- Sample receipts (`receipts.md`):

```text
2026-06-19 | HOLD     | baustein | kept "EU-Frankfurt anonymized" (contract) | dropped/flagged "US-east raw" (slack#proj-baustein) | hard policy not overridden by lower-trust source
2026-06-19 | OVERRIDE | baustein | kept "Claude Sonnet 4.5" (slack#proj-baustein) | dropped/flagged "GPT-4o" (meeting-notes) | newer and/or more-trusted value wins
2026-06-19 | RETIRE   | baustein | retired "Munich Tower PoC Q2 2024" (meeting-notes, 2024-04-10) | age 800d exceeds 2x refresh horizon
```

Every resolution is an append-only receipt — **nothing is silently forgotten**.

> Reproducibility note: because the cloud DELETE is broken, lint correctives accumulate across re-runs on the same dataset — so a *second* run may already show the corrected answer before lint. To reproduce the clean before→WRONG state, ingest into a fresh dataset name.

## Best use of Cognee Cloud

Cognee Cloud is the backbone (LLM + hosting). `cognee.serve(url, api_key) → CloudClient`; all `remember/recall/cognify/forget/improve` go through the cloud. Verified live: cloud connect, the LLM judge returning a real verdict, and per-client ingest+recall — all as gated integration tests. (We also surfaced a cloud DELETE 500 and made `forget` best-effort project-wide via `config.safe_forget`.)

## Run

```bash
.venv/bin/python -m pytest -v                  # unit tests (offline, pure logic)
.venv/bin/python -m pytest -v -m integration   # cloud integration tests
.venv/bin/python demo.py                        # end-to-end before→after + receipts
```
