# Team Submission

## Team

- Team name: Helix Brain
- Participants: Nidhir Bhavsar (@Nid989)
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

Concrete before→after, driven by `demo.py` over both clients.

### Baseline Run

- Query / task: "Which LLM does RFI Copilot use today?" and "Where can we store BauStein raw helmet-cam video?"
- Result: stale/contradicted answers (old GPT-4o model; US-east raw video suggested by a low-trust Slack message).
- Score (own metric): headline questions graded WRONG against the answer-key before lint.
- Recorded feedback:

```text
error_type: contradiction / staleness / hard-fact-violation
error_message: newer or higher-trust fact not yet winning; low-trust source contradicts a signed contract
feedback: route deterministically (trust+recency, hard-fact HOLD); escalate grey-band to judge; PARK if unsure
success_score: 0 (pre-lint)
```

### Improved Run

- Query / task: same questions after `run_lint`.
- Result: answers flip to RIGHT — "Claude Sonnet 4.5" for RFI Copilot; "EU-Frankfurt, anonymized" for video residency (signed DPA upheld over the Slack shortcut).
- Score: headline questions graded FIXED; `clashes N→0` with path stats (free / judge / parked).
- Every resolution recorded as an append-only receipt — no silent forgetting.

## Best use of Cognee Cloud

Cognee Cloud is the backbone (LLM + hosting). `cognee.serve(url, api_key) → CloudClient`; all `remember/recall/cognify/forget/improve` go through the cloud. Verified live: cloud connect, the LLM judge returning a real verdict, and per-client ingest+recall — all as gated integration tests. (We also surfaced a cloud DELETE 500 and made `forget` best-effort project-wide via `config.safe_forget`.)

## Run

```bash
.venv/bin/python -m pytest -v                  # unit tests (offline, pure logic)
.venv/bin/python -m pytest -v -m integration   # cloud integration tests
.venv/bin/python demo.py                        # end-to-end before→after + receipts
```
