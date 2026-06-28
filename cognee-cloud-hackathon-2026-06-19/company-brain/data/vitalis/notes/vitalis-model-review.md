# Vitalis Health — Scribe Assist Model Review Meeting Notes

**Project:** Scribe Assist (Ambient Clinical Documentation)
**Client:** Vitalis Health
**Engagement:** Helix AI Consulting — Clinical AI Platform Workstream
**Meeting Date:** 2026-04-22
**Location:** Hybrid — Helix Boston Office (Conf Rm 4B) + Zoom
**Notes prepared by:** Priya Nandakumar (Helix, AI Lead)
**Doc status:** Final / circulated to working group

---

## Attendees

| Name | Role | Org |
|------|------|-----|
| Priya Nandakumar | AI Lead / Notetaker | Helix AI Consulting |
| Marcus Trofimov | Principal, Healthcare Practice | Helix AI Consulting |
| Dr. Elena Castellanos | Chief Medical Information Officer | Vitalis Health |
| Sam Okeke | Director, Digital Health Platforms | Vitalis Health |
| Hannah Briggs | ML Engineer | Helix AI Consulting |
| Devon Park | Security & Compliance Reviewer | Helix AI Consulting |

Apologies: J. Whitfield (Vitalis Procurement) — to review pricing async.

---

## 1. Purpose

The objective of today's session was to close out the Phase 2 model evaluation and formally select the **primary large language model** that will power the Scribe Assist ambient note pipeline. Scribe Assist captures the clinician–patient conversation via the in-room ambient microphone array, transcribes it, and then drafts a structured clinical note (HPI, exam, assessment, plan) for the provider to review and sign.

This was a decision meeting, not an exploratory one — the eval had already run, and the goal was to ratify a choice and record the rationale.

## 2. Background

Over the prior six weeks the team ran a head-to-head evaluation across three candidate frontier models on a de-identified corpus of 480 encounters spanning primary care, cardiology, and behavioral health. Scoring covered clinical accuracy, hallucination rate, adherence to the Vitalis note template, latency under load, and behavior on safety-sensitive content (e.g., suicidal ideation, medication interactions).

Dr. Castellanos reiterated the non-negotiable: the drafting model must minimize fabricated findings, since a hallucinated symptom or lab value carries direct patient-safety risk even with human review in the loop.

## 3. Eval Summary (high level)

- Clinical faithfulness and low fabrication rate were the dominant scoring weights (combined 55% of the rubric).
- The top candidate led on faithfulness and on following long, structured note templates without dropping sections.
- Latency for all finalists was acceptable for the asynchronous "draft-then-review" workflow; real-time streaming is out of scope for Phase 2.

## 4. Decision

The working group reached consensus:

> **Scribe Assist generates draft clinical notes using Anthropic Claude as the primary LLM for the ambient note pipeline.**

Anthropic Claude was selected as the primary model on the strength of its faithfulness scores, its handling of long structured clinical templates, and its conservative behavior on safety-sensitive passages. Dr. Castellanos and Sam Okeke both signed off on the choice on behalf of Vitalis.

A secondary/fallback model will be revisited in Phase 3 for redundancy; no fallback is being wired in for the initial production cutover.

## 5. Rationale Notes

- Lowest observed fabrication rate among the finalists on the de-identified corpus.
- Strongest adherence to the multi-section Vitalis note template, including reliably populating the Assessment & Plan sections.
- Appropriate caution on safety-sensitive content rather than over-asserting.
- Devon (Compliance) confirmed the chosen deployment path supports a BAA and zero-retention configuration suitable for PHI handling.

## 6. Action Items

| # | Owner | Action | Due |
|---|-------|--------|-----|
| 1 | Hannah Briggs | Lock the production prompt + template config against the selected model | 2026-04-29 |
| 2 | Devon Park | Confirm BAA and zero-retention settings in writing | 2026-04-25 |
| 3 | Priya Nandakumar | Update the architecture doc to name the primary LLM | 2026-04-24 |
| 4 | Sam Okeke | Schedule clinician pilot cohort (n=12) | 2026-05-06 |

## 7. Open Questions

- Phase 3 fallback model — defer decision until pilot data lands.
- Whether behavioral health encounters need a separate, more conservative prompt profile.

---

*Next checkpoint:* Pilot readiness review, week of 2026-05-11.
