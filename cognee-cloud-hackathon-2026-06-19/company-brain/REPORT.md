# REPORT — Company Brain seed data & edge-case coverage

Generated 2026-06-19 for the Cognee Cloud Hackathon. Companion files:
`SEED_DATA.md` (fact catalog), `TEST_EXAMPLES.md` (query tests), `HANDOFF.md` (next-session brief),
diagram → https://claude.ai/code/artifact/72414e72-5ada-4748-ab82-a21ad70ad17f

---

## 1. What we built

**Scenario:** Helix AI Consulting (Deloitte-like) builds AI projects for clients. The "Company Brain"
ingests scattered project + firm docs and self-cleans, with one rule from the underlying agent-drift
research (Constraint Lease Mesh): **never silently forget — every removal/override writes a receipt.**

**Two clients chosen:** BauStein (construction) and Vitalis (healthcare) — both carry a compliance
stakes-override (GDPR / HIPAA-BAA), which is the strongest "never silently forget" story.

### Synthetic documents generated (via a 12-agent dynamic workflow)

Realistic scattered sources, in the formats a real consultancy actually has:

| Client | Source type | Format | File |
|--------|-------------|--------|------|
| BauStein | Contract / DPA | LaTeX → **PDF** | `data/baustein/contracts/baustein-dpa.{tex,pdf}` |
| BauStein | Platform wiki | Markdown → **Word .docx** | `data/baustein/wiki/baustein-platform.{md,docx}` |
| BauStein | Slack export | **JSON** (18 msgs) + transcript | `data/baustein/slack/proj-baustein.{json,txt}` |
| BauStein | Kickoff meeting notes | Markdown → **Word .docx** | `data/baustein/notes/baustein-kickoff-notes.{md,docx}` |
| BauStein | Onboarding doc | Markdown → **Word .docx** | `data/baustein/onboarding/baustein-onboarding.{md,docx}` |
| BauStein | Unsourced stray note | plain **.txt** (no provenance) | `data/baustein/_unsourced/baustein-budget-note.txt` |
| Vitalis | Contract / BAA + SOW | LaTeX → **PDF** | `data/vitalis/contracts/vitalis-baa-sow.{tex,pdf}` |
| Vitalis | AuthFlow wiki | Markdown → **Word .docx** | `data/vitalis/wiki/vitalis-authflow.{md,docx}` |
| Vitalis | Slack export | **JSON** (19 msgs) + transcript | `data/vitalis/slack/proj-vitalis.{json,txt}` |
| Vitalis | Model-review notes | Markdown → **Word .docx** | `data/vitalis/notes/vitalis-model-review.{md,docx}` |
| Vitalis | Onboarding doc | Markdown → **Word .docx** | `data/vitalis/onboarding/vitalis-onboarding.{md,docx}` |
| Vitalis | Unsourced stray note | plain **.txt** (no provenance) | `data/vitalis/_unsourced/vitalis-stray-note.txt` |

**Render pipeline:** `tectonic` (LaTeX→PDF), `pandoc` (md→docx). Slack JSON follows the export schema
`{user, ts, channel, text}`. Markdown is the ingestion source-of-truth; PDF/docx are the "real-looking"
deliverables (and prove the brain can ingest mixed formats).

### Projects represented
- **BauStein:** SiteGuard CV (PPE detection), ProgressAI Drone Twin (drone vs BIM), RFI Copilot (RAG over specs).
- **Vitalis:** Scribe Assist (ambient clinical scribe), AuthFlow (prior-auth automation), ReAdmit (readmission risk).

---

## 2. System structure (recap)

- **Two stores:** Cognee graph (living memory) + `receipts.md` (append-only audit ledger: `when | action | what | why`).
- **Router** (cheap heuristic → escalate to LLM judge only when unsure). Confidence = distance of the cheap
  signal from its decision line; two thresholds → grey dead-band = ask the judge. Three outcomes:
  **heuristic acts · judge acts · nobody sure → quarantine/park.**
- **Stakes override:** `hard=true` facts (policy/security/money/compliance) always escalate to the judge before any delete.
- **5 drift channels:** Contradiction · Staleness · Redundancy · Provenance · Coverage-gap.
- **Per-client scoping** via Cognee `dataset_name` / `node_set` so cross-client collisions don't merge.

---

## 3. Edge cases the application handles (given our structure)

Each planted edge case → what the app does → path → expected receipt.

### 3.1 Contradiction — newer/more-trusted value wins
- **BauStein model:** `RFI Copilot = GPT-4o` (meeting-notes, 2024-11) vs `= Claude Sonnet 4.5` (slack, 2026-04). → override to Sonnet 4.5; GPT-4o demoted to fallback.
  - Path: heuristic (clear recency + same slot). Receipt: `OVERRIDE | kept Sonnet 4.5 (slack, 2026-04) | dropped GPT-4o (notes, 2024-11) | newer`.
- **Vitalis model:** `Claude` (meeting-notes, 2026-04) vs `GPT-4o` (unsourced, 2025-08). → Claude wins (newer + has a source).
  - Path: heuristic. Loser is also no-source (see 3.4).

### 3.2 Staleness — retire or flag by age vs refresh-horizon
- **Easy retire:** BauStein Munich Tower PoC "by end of Q2 2024", Vitalis 2024 pilot scope. age ≫ 2× horizon → retire. Receipt: `RETIRE | … | age ≫ horizon, no re-confirm`.
- **Borderline:** Vitalis ReAdmit AUROC 0.78 target (~13mo), BauStein budget (~12mo). ratio 1.0–2.0 → judge "still true?" → likely FLAG, not delete. Receipt: `FLAG-REFRESH | … | needs confirmation`.

### 3.3 Redundancy — merge near-duplicates, keep all sources
- BauStein ProgressAI "completion %" stated in wiki + onboarding. Vitalis Epic-draft-signoff in slack + onboarding.
  - Path: heuristic (embedding sim > 0.92). Receipt: `MERGE | kept … | folded duplicate from … | both sources kept`.

### 3.4 Provenance — quarantine / demote unsourced claims
- BauStein budget note (source=none), Vitalis GPT-4o stray note (source=none). → served with low trust / demoted, never as authoritative truth. Receipt: `QUARANTINE | … | no source — demoted`.

### 3.5 Fake-contradiction — LLM judge sees no real conflict
- BauStein: "Pinecone vector store" vs "PostGIS for spatial BIM" — different layers, not a conflict.
- Vitalis: "FHIR R4" (outbound to payers) vs "HL7 v2" (inbound from interface engine) — complementary standards.
  - Path: **judge** (cheap signal can't tell). Receipt: `KEEP-BOTH (judge) | not contradictory — … | linked`.

### 3.6 Stakes override — hard policy NEVER silently dropped (the headline)
- **BauStein:** casual slack "pipe raw helmet-cam to US-east, faces visible" vs HARD DPA "anonymize + EU-Frankfurt only".
- **Vitalis:** casual slack "just use consumer OpenAI API, residency doesn't matter" vs HARD BAA "PHI stays in US tenant, encrypted".
  - Path: **forced judge** (hard fact). Outcome: policy HELD, casual msg FLAGGED not applied. Receipt: `HELD (judge, stakes) | kept policy … | did NOT drop for slack claim | source insufficient`.

### 3.7 Park / quarantine — nobody confident → human
- Firm-level EU-PII region conflict (eu-west-1 vs eu-central-1), both recent, security-relevant, no authoritative source. → `QUARANTINE | NEEDS HUMAN`. (Available if firm facts are loaded; see `SEED_DATA.md` firm-08/09.)

### 3.8 Cross-client collision — scoped, not merged
- BauStein SOW **EUR** 480,000 and Vitalis SOW **USD** 480,000 are deliberately near-identical. The brain must NOT merge them — `dataset_name`/`node_set` per client keeps them separate. Receipt: none (correctly left alone); a naive RAG would conflate them.

### 3.9 Mixed-format ingestion
- The same brain ingests PDF (contracts), Word/docx (wiki/notes/onboarding), Slack JSON, and plain txt. Tests that extraction is robust across formats, not just clean markdown.

---

## 4. Edge cases NOT handled (honest limitations — from CLM §14)

- **Metadata trust:** if a source label is wrong (a casual claim mislabeled as `contract`), trust ranking misfires. We trust the `source` tag as given.
- **Predicate/extraction quality:** facts must be extracted cleanly from the docs; a missed extraction = a fact the brain never sees.
- **Semantic-conflict recall:** the judge may miss a subtle contradiction phrased very differently (we mitigate with the grey-band escalation, not eliminate).
- **No action safety:** this is a knowledge brain — we dropped CLM's action-boundary enforcement, revival, and compensation (no risky tool calls here).
- **Quarantine needs a human:** parked items don't self-resolve; they wait. By design (better than a wrong auto-delete).

---

## 5. Demo plan (3 min)

1. Ingest one client (BauStein **or** Vitalis) from `data/<client>/` across all formats → build graph.
2. Ask the headline question (`TEST_EXAMPLES.md` A1–A3) → **wrong / non-compliant answer**.
3. Run the lint cycle → router resolves; `receipts.md` fills.
4. Re-ask → **right answer**. Show the receipt log live, including the HELD hard-policy line.
5. On screen: `clashes N → 0 · resolved_free / needed_judge / parked` + `health` trending up.

The flip from wrong→right, plus the receipt that says *"did NOT drop the GDPR/HIPAA policy for a Slack message,"* is the pitch.

---

## 6. File inventory

```
data/
  baustein/  contracts/{baustein-dpa.tex,.pdf}  wiki/{baustein-platform.md,.docx}
             slack/{proj-baustein.json,.txt}     notes/{baustein-kickoff-notes.md,.docx}
             onboarding/{baustein-onboarding.md,.docx}  _unsourced/baustein-budget-note.txt
  vitalis/   contracts/{vitalis-baa-sow.tex,.pdf}  wiki/{vitalis-authflow.md,.docx}
             slack/{proj-vitalis.json,.txt}        notes/{vitalis-model-review.md,.docx}
             onboarding/{vitalis-onboarding.md,.docx}  _unsourced/vitalis-stray-note.txt
```
22 files. 2 PDF + 2 .tex · 6 .docx + 6 .md · 2 Slack JSON + 2 transcripts · 2 unsourced .txt.
