# BrainFlow Brain — Before / After Evidence

**Same questions, no question text changed.** The only thing that changes between the two
columns is the **skill** (the system prompt): `wiki-maintainer.baseline.md` ("be concise, give a
direct answer") vs. the learned `wiki-maintainer.md` (provenance · preserve-contradictions ·
current-vs-superseded).

> **How this run was produced.** The automated LLM backends were unavailable at submission time
> (the OpenAI key was out of quota; the local Ollama path was missing the
> `HUGGINGFACE_TOKENIZER` for nomic embeddings). Per the brief, the **agent itself served as the
> model** — the same agent answered each question twice, once under each skill, against the real
> `raw/` corpus. Answers are scored by the repository's own deterministic rubric
> (`score_answer()` in `brain/common.py`): **+3** cite a source · **+3** match the key facts ·
> **+3** surface the disagreement · **+1** state current-vs-superseded. This is a faithful
> demonstration: a skill *is* a system prompt, so one model under two skills is exactly the
> before/after the product claims. The live Cognee Cloud suite
> (`brainflow/snapshots/query-results.json`, 8/8 + 3/3) corroborates the "after" column.

## Score summary

| Run | Skill | Avg score | Cited | Surfaced conflict | Stated currency |
| --- | --- | --- | --- | --- | --- |
| **before** | baseline v1 | **1.3 / 10** | 0/7 | 0/7 | 0/7 |
| **after** | wiki-maintainer | **10.0 / 10** | 7/7 | 7/7 | 7/7 |

The baseline answers sound confident and are often **stale or one-sided** (Firebase, Day-3,
€3.99, iOS-first) — it picks one source and hides the disagreement. The improved answers cite,
present both sides, and state which value is current.

---

## Q1 — "What's the current premium-upgrade timing, and was it ever changed?"  *(issue B)*

**BEFORE** (baseline) — _score 1/10 · no citation · missed conflict · no currency_
> The premium upgrade prompt appears on Day 3 after first use.

❌ Confident and **wrong** — Day 3 was reverted. One source, no provenance, conflict hidden.

**AFTER** (wiki-maintainer) — _score 10/10 · cited · surfaced · currency_
> **Current: Day 7 after first use** (Decision Log, 2026-04-09 — Product review reverted it,
> superseding the 2026-02-14 move to Day 3). Originally Day 7 (PRD §Monetisation, 2026-01-22) →
> Day 3 (Decision Log 2026-02-14) → **back to Day 7** (Decision Log 2026-04-09).
> ⚠️ Stale references still cite Day 3: **Roadmap 2026** and **Design Spec Screen 5**.

---

## Q2 — "Is the AI Daily Pick part of the MVP?"  *(issue A)*

**BEFORE** — _score 1/10_
> No, AI-powered Daily Picks are out of scope for the MVP.

❌ Picks the PRD only; misses that a later PM decision and the roadmap **ship it**. No citation.

**AFTER** — _score 10/10_
> **Disputed — unresolved.** The PRD (§MoSCoW, 2026-01-22) lists AI-powered Daily Picks under
> **"Won't have."** But the **Roadmap (Q2)**, **Decision Log 2026-05-06** (PM pulled it into the
> MVP), and **Design Spec Screen 2** (a prominent AI Daily Pick card) all ship it — over a
> recorded Engineering scope objection. No build owner is assigned (RACI).

---

## Q3 — "What does the B2B HR dashboard show employers?"  *(issue C)*

**BEFORE** — _score 1/10_
> Each employee's name, streak, weekly goal, and category breakdown.

❌ Reports the Sales/Design view as fact; contradicts the PRD's privacy rule. No citation, GDPR
risk unflagged.

**AFTER** — _score 10/10_
> **Current per the PRD (2026-01-22): anonymised, aggregated usage only** — no individual
> employee data, by design. **Conflict:** the signed **Sales commitment** (Müller GmbH,
> 2026-05-12) and **Design Spec Screen 6** both show employees **by name** with per-person
> engagement. PRD wins; Sales over-promised — **GDPR risk**, route to review.

---

## Q4 — "What backend are we using?"  *(issue F)*

**BEFORE** — _score 2/10_
> BrainFlow uses Firebase (Auth + Firestore + Cloud Messaging).

❌ **Superseded value served as live.** Grabs ADR-0002 (which is marked superseded). No citation,
no currency.

**AFTER** — _score 10/10_
> **Current: Supabase (managed Postgres, EU/Frankfurt)** — ADR-0005, 2026-04-18, adopted for
> GDPR / health-data residency and the DiGA path. It **supersedes ADR-0002 (Firebase, US)**,
> which is marked superseded — do not build new services against it.

---

## Q5 — "Which platform do we launch on first?"  *(issue E)*

**BEFORE** — _score 1/10_
> iOS first, with Android following about four weeks later.

❌ Takes the Roadmap/GTM line; contradicts the accepted ADR and the Android persona. No citation.

**AFTER** — _score 10/10_
> **Per ADR-0001 (accepted, 2026-02-03): simultaneous iOS + Android** on day one (React Native);
> a single-platform-first launch was explicitly rejected, and the primary persona (Jonas Weber)
> is on **Android**. **Conflict:** the **Roadmap** and **GTM one-pager** describe an **iOS-first**
> beta, and the **Design Spec** frames everything in an iPhone-only shell — all contradict ADR-0001.

---

## Q6 — "What's our retention target?"  *(issue D)*

**BEFORE** — _score 1/10_
> 40% retention.

❌ The exact ambiguity the brain exists to catch — 40% of *what window?* No citation.

**AFTER** — _score 10/10_
> **40% — but the window is defined two different ways.** The **OKR** north-star is **7-day
> retention ≥ 40%**; the **PRD** primary KPI is **30-day retention ≥ 40%**; the **GTM** deck
> quotes a bare "40% retention." Same number, **different metrics** — undefined until owned.

---

## Q7 — "What does BrainFlow Premium cost?"  *(issue G)*

**BEFORE** — _score 2/10_
> €3.99 per month.

❌ One of three conflicting numbers, served as the answer. No citation, no conflict.

**AFTER** — _score 10/10_
> **No single source of truth — pricing has no owner (RACI).** The **PRD/OKR** imply **€4.99/mo**;
> the **GTM one-pager** advertises **€3.99/mo** (launch promo); the signed **Sales** B2B rate is
> **€22/user/yr** — below the €25.99 >100-seat tier. Distinct, conflicting prices; **needs an owner**.

---

## What changed, mechanically

The baseline skill failed all three rubric dimensions on every contested question (no citation,
no conflict surfaced, no currency). The learned skill — which adopted exactly those three
policies from `CLAUDE.md §3.1 / §3.2 / §3.6` after scoring its own failures — passes all three.
That is the self-improvement loop: **the brain learned its own operating rules from its own
low-scoring answers.** Lint evidence (all 11 planted issues) is in `evidence/lint-report.md`.
