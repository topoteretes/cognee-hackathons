# Demo cue sheet — Cognost (3 minutes)

Two verified live cases, mapped to the 3-minute script. Everything here runs against the live
`brainflow` brain on Cognee Cloud (42 docs, `wiki-maintainer` skill registered). Answers below
are the actual recall output, lightly trimmed.

**Have on screen:** (1) a recall console, (2) `brain-diagnostic.html` (the 0 → 6 counter),
(3) `brain/evidence/before-after.md` as backup.

---

## 0:00–0:25 · Hook
> "Every product team has a PRD, a roadmap, a design, sales promises, and decisions buried in
> Slack. They drift apart, and nobody notices until something breaks. What if a wiki maintained
> itself and told you where your stakeholders disagree?"

## 0:25–0:45 · Idea + the differentiator
> "We built Cognost on Cognee. Unlike RAG, which re-reads raw docs and picks one source, ours
> compiles 42 documents into one knowledge graph that surfaces contradictions, tracks which
> decisions are current, and improves its own answering skill from feedback. Live on BrainFlow."

---

## 0:45–1:25 · CASE 1 — "It sees what's buried" (the money-shot)

**Type this query:**
> Does the current design spec match the PRD scope? List every mismatch with citations.

**What it returns (6 cited mismatches, verified):**
| Mismatch | Design says | PRD says |
| --- | --- | --- |
| AI Daily Pick card | ships it (Screen 2) | "Won't have" |
| Paywall trigger | "Day 3" (Screen 5) | Day 7 |
| Platform | iPhone-only shell | Android persona / simultaneous |
| Exercise timer | 08:00 (Screen 3) | 2–5 min |
| HR dashboard | employees by name (Screen 6) | anonymised only |
| Premium price | €3.99 sheet | "no monetisation" in MVP |

**Say:**
> "42 documents, six months of output, nobody's read them all. One question surfaces six
> misalignments no human had connected — each with a citation to the source."

---

## 1:25–2:20 · CASE 2 — "It tracks what's current, and it learns"

**Type this query:**
> What is the current premium-upgrade prompt timing, was it ever changed, and which documents
> still reference the old value?

**What it returns (verified):**
- **Current: Day 7** — Decision Log 2026-04-09 reverted it, superseding the 2026-02-14 Day-3 decision.
- **Still referencing the stale Day 3:** Roadmap 2026 · Design Spec Screen 5 · **QA Test Plan case 2**.
- Authoritative reversal pulled from the unstructured **product-review transcript (2026-04-09)**.

**Say:**
> "A decision that was killed two months ago is still driving a QA test. The brain caught the
> leak across five documents — and pulled the current answer out of a meeting transcript."

**Then the self-improvement beat — flip the skill on the same question:**
- **Baseline skill** (system_prompt = "be concise, give a direct answer") → *"Day 3."*
  Confident, no citation, **wrong**. Rubric score **1/10**.
- **Maintainer skill** → Day 7, cited, current-vs-superseded. Rubric score **10/10**.

Show `brain-diagnostic.html`: the open-contradictions counter ticks **0 → 6**.

**Say:**
> "It didn't just answer — it scored its own bad answer, then rewrote its own operating rules so
> it never makes that mistake again. Before: 1 out of 10. After: 10 out of 10."

---

## 2:20–2:35 · Kicker — "and it doesn't cry wolf"

**Type:**
> Is BrainFlow itself priced at €3.99/month, or is that a competitor's price?

**Returns:** keeps them separate — BrainFlow's launch price **and** CalmDACH's €3.99 — not merged
into a false contradiction. (3/3 decoys held — precision, not just recall.)

---

## 2:35–3:00 · Close
> "Cognost turns a pile of scattered docs into a single source of truth that keeps itself honest.
> 8 out of 8 stakeholder conflicts surfaced with citations, 3 out of 3 traps correctly ignored.
> The wiki gets richer with every source and every question. Give it your Slack export, and it
> aligns your whole company."

---

## Backup / fallback (if the network drops)
- `brainflow/snapshots/query-results.json` — all 11 verified answers, captured.
- `brain/evidence/before-after.md` — the 1.3 → 10 before/after table.
- `brain/evidence/lint-report.md` — all 11 planted issues caught.

## Exact recall call (for reference)
```bash
curl -X POST "$COGNEE_BASE_URL/api/v1/recall" \
  -H "X-Api-Key: $COGNEE_API_KEY" -H "Content-Type: application/json" \
  -d '{"query":"<question>","dataset_name":"brainflow","system_prompt":"<baseline|maintainer skill>"}'
```
Baseline `system_prompt`: *"You answer questions about the BrainFlow product. Be helpful and concise. Give the user a direct answer."*
Maintainer `system_prompt`: *"You maintain a stakeholder-alignment wiki. Cite every claim with its source and date. When sources disagree, present both sides and name the conflict; never pick a winner silently. Always state which value is current, what it superseded, and when."*
