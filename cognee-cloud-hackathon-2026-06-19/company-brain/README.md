# Cognee Company Brain — Self-Cleaning Knowledge Memory

## Overview

A self-cleaning **"Company Brain"** on Cognee Cloud that ingests scattered client documents, answers questions, lints itself for drift (staleness, redundancy, contradiction), and **never silently forgets**: every removal or override writes a receipt in an immutable decision log. Derived from constraint-lease-mesh research on agent drift, specialized to knowledge memory. Built for Helix AI Consultancy's multi-client document store.

---

## Setup

### Environment
Create a `.env` file (gitignored) with:
```bash
COGNEE_API_KEY=<64-hex-key>
COGNEE_CLOUD_URL=<tenant-url>
COGNEE_TENANT_ID=<id>
COGNEE_USER_ID=<id>
ENABLE_BACKEND_ACCESS_CONTROL=false
```

Obtain credentials from Cognee Cloud tenant portal.

### Python & Dependencies
- Python 3.14 (installed in `.venv` at project root)
- `cognee==1.2.0.dev1` (already in `.venv/bin/python`)

Verify:
```bash
.venv/bin/python --version
.venv/bin/python -c "import cognee; print(cognee.__version__)"
```

---

## Run: Tests

### Unit Tests (Pure Logic, No Network)
Pure drift-router logic, fact record schema, decision ledger, JSONL linting — all offline.
```bash
.venv/bin/python -m pytest tests/test_facts.py tests/test_drift.py tests/test_router.py tests/test_ledger.py tests/test_lint.py -v
```

Expected: All green. ~50–100 test cases covering deterministic resolution (trust+recency, staleness, redundancy, unsourced quarantine, multivalue keep-both).

### Cloud Integration Tests
Live tests against Cognee Cloud. Requires `.env` with valid credentials.
```bash
.venv/bin/python -m pytest -v -m integration
```

Test suite:
- `test_cloud_smoke`: `remember()` → `recall()` round-trip (validates cloud connection)
- `test_safe_forget`: `config.safe_forget()` doesn't crash on 500
- `test_judge_escalation`: Cloud LLM judge escalates grey-band cases, PARKs on unsure
- `test_per_client_scoping`: Dataset isolation (baustein queries don't see vitalis data)

### Run the Demo
Full end-to-end: ingest client docs, query, detect drift, run lint, escalate to judge, show receipts.
```bash
.venv/bin/python demo.py
```

Expected output:
```
=== BEFORE ===
Q: Is BauStein a software company?
A: [WRONG/STALE] No, it's a construction-tech firm.

[Running lint engine...]
  Drift router: found X clashes (redundancy, staleness, contradiction)
  Escalated Y to judge; judge PARK'd Z (unsure), applied W fixes
  
[Re-ingesting winners + audit receipt...]

=== AFTER ===
Q: Is BauStein a software company?
A: [RIGHT] Yes, BauStein provides SaaS construction-management platform.

=== STATS ===
Clashes: 5 → 0
Decisions: 4 applied, 1 parked (unsure)
Receipts: decisions.md, decisions.jsonl
```

---

## 3-Minute Pitch Script

### Setup (30 sec)
"We're working with two clients: **BauStein**, a construction-tech SaaS firm, and **Vitalis**, a healthcare company. Both have scattered docs — contracts, wikis, Slack, DPA, onboarding notes. We ingest them into Cognee Cloud."

### Before (30 sec)
"We ask the brain: *Is BauStein a software company?* It says **no, construction firm**. Wrong — it's actually a software platform for construction. Why? Old unsourced .txt files are drowning out recent DPA contract that says SaaS. The brain doesn't know what's stale or contradictory."

### The Fix (60 sec)
"Run **lint**. Our drift router detects:
  - **Redundancy:** Same fact ingested twice from wiki and Slack (keep one, mark decision)
  - **Staleness:** Old file is 6 months, recent DPA is 2 weeks (high-trust recent wins)
  - **Contradiction:** BauStein is *software* AND *construction* — actually *construction SaaS* (keep both, resolve via context)
  - **Unsourced:** Random .txt with no source → PARK (escalate to judge)

Judge LLM reviews the unsourced claims. Confident ones apply; unsure ones stay parked. Every decision — trust override, redundancy merge, escalation — writes a **receipt** in `decisions.md` and `decisions.jsonl`. This is the contract: never silent disappearance."

### After (30 sec)
"Re-ask: *Is BauStein a software company?* Now it says **yes, SaaS platform**. Right. Clashes went from 5 to 0. The receipts show exactly why each decision was made, who decided, and when. And because Vitalis data lives in a different dataset, it never leaked into BauStein answers. Self-cleaning, auditable, cross-client safe."

### Closer (30 sec)
"The core insight: drift isn't random. Most cases — trust, recency, redundancy, staleness — resolve deterministically. Only the grey-band cases go to the LLM judge, and the judge parks when unsure instead of guessing. Knowledge memory that never forgets you what it did."

---

## Key Files

- **`data/baustein/`** – 11 client documents (PDFs, .docx, JSON, .txt)
- **`data/vitalis/`** – 11 client documents
- **`src/facts.py`** – Fact record schema (Fact, Candidate, Decision types)
- **`src/drift.py`** – Deterministic drift router (T+R, staleness, redundancy, unsourced)
- **`src/router.py`** – Route candidate to resolution (local rule or cloud judge)
- **`src/ledger.py`** – Decision ledger + receipt writer (JSONL + Markdown)
- **`src/lint.py`** – End-to-end lint orchestration
- **`src/config.py`** – CloudClient init, safe_forget, env loading
- **`demo.py`** – Full pipeline: ingest → query (before) → lint → judge → query (after) → stats
- **`implementation.md`** – This decision log (locked decisions + verified API facts)

---

## Troubleshooting

### Cloud Connection Issues
- **Error:** `COGNEE_API_KEY not found`
  - Fix: Create `.env` with valid creds (see Setup)
- **Error:** `401 Unauthorized`
  - Fix: Check key format (64-hex) and tenant URL
- **Error:** `forget() returns 500`
  - Expected: Use `config.safe_forget()` instead (best-effort)

### Judge Verbosity
- **Problem:** Judge returns multi-paragraph explanations instead of YES/NO
- **Fix:** Guard with `response.startswith("YES")` + PARK fallback (in router)

### Dataset Cleanup (409 Conflict)
- **Problem:** Repeated demo runs 409 on dataset name collision
- **Fix:** Use uuid-suffixed names; pre-generating unique dataset names avoids collisions

### Test Failures
- **`test_cloud_smoke` fails:** Check `.env` validity; run with `-vv` for stack trace
- **`test_safe_forget` fails:** Expected if backend forget endpoint is down; safe_forget should still not crash
- **`test_judge_escalation` fails:** Judge may be verbose; check startswith guard in router

---

## Architecture Diagram

```
Input Docs
  ├─ BauStein: contracts, wiki, notes, Slack, DPA, unsourced .txt
  ├─ Vitalis: wiki, onboarding, DPA, notes, unsourced .txt
  │
  ↓ Ingest (liteparse)
  │
Cognee Cloud Datasets
  ├─ dataset="baustein" → 20+ facts (contract + recent sourced + wiki + slack)
  ├─ dataset="vitalis" → 20+ facts
  │
  ↓ Query (before lint)
  │
Brain Says: [WRONG] "No, BauStein is construction firm"
Brain Says: [STALE] "Vitalis is non-profit" (old unsourced)
  │
  ↓ Lint Engine
  │
Drift Router (deterministic)
  ├─ T+R override: recent DPA > old .txt
  ├─ Staleness: age(fact) > 2×recent?
  ├─ Redundancy: duplicate fact + source?
  ├─ Unsourced: source=null? → PARK
  ├─ Multivalue: both true (keep-both) or error (escalate)
  │
  ├─→ Apply 4 fixes (with receipts)
  │
  ├─→ Escalate 1 unsourced to judge
       Judge: "Yes, claim is valid" → apply (with receipt)
       Or: "Unsure" → PARK (with receipt)
  │
  ↓ Re-ingest winners
  │
Cognee Cloud (updated)
  ├─ dataset="baustein" → 20+ facts, stale removed, recent wins
  ├─ dataset="vitalis" → updated
  │
  ↓ Query (after lint)
  │
Brain Says: [RIGHT] "Yes, BauStein is SaaS construction platform"
Brain Says: [RIGHT] "Vitalis is healthcare company"
  │
  ↓ Receipt Log
  │
decisions.md: "Trust+recency: old .txt → DPA contract (reason: DPA 2wk, .txt 6mo)"
decisions.jsonl: {"action":"override", "reason":"staleness", "winner":"..."}
```

---

## Bonus: Cloud Push

The "Best use of Cognee Cloud" bonus can be unlocked with a one-liner in `demo.py` at the end:
```python
client.push("baustein")  # or cognify/improved(...) for full cloud-native flow
```
This stages the cleaned brain for production without re-ingesting. Optional; demo works without it.

---

## Success Criteria (Hackathon)

- [x] Ingest two clients' docs
- [x] Query before lint (wrong answers)
- [x] Run drift router + judge (deterministic + escalation)
- [x] Query after lint (right answers)
- [x] Show decision receipts (never silent)
- [x] Narrate 3–4 flips (evidence of self-repair)
- [x] Cross-client firewall (datasets isolate)
- [ ] Cloud push bonus (stretch)

---

**Contact:** bhavsar@1alpha.ai  
**Hackathon:** Cognee Cloud, Berlin 2026-06-19, 6pm–9pm  
**Build time:** ~3 hours  
**Status:** Ready to implement (design locked, cloud verified)
