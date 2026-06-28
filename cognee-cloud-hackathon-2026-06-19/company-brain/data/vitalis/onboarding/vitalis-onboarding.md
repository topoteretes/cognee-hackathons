# Vitalis Health Engagement — Engineering Onboarding

**Client:** Vitalis Health
**Engagement:** AI Clinical Operations Platform (Phase 2)
**Document owner:** Priya Narayanan, Engineering Lead — Helix AI Consulting
**Last updated:** 2025-09-12
**Audience:** Engineers joining the Vitalis engagement

---

## Welcome

Welcome to the Vitalis Health engagement. This page is your starting point as a new engineer on the team. Vitalis is a regional integrated health system running on Epic, and Helix has been engaged to deliver two AI-driven workstreams that improve clinical throughput and reduce avoidable readmissions. Read this end to end before your first standup, and ping the #vitalis-eng channel with questions.

Before you touch any code, make sure you have completed HIPAA training, signed the client BAA acknowledgement, and been provisioned access to the Vitalis VPC by the platform team (Marcus Feld is the approver). All work happens inside the client's protected environment — no PHI leaves the boundary, ever.

## Engagement at a glance

We are running two primary products in parallel. New engineers are typically rotated onto one of them for their first sprint before being cross-trained.

| Workstream | Purpose | Tech lead |
|---|---|---|
| ReAdmit | Predict 30-day unplanned readmission risk | Daniela Cho |
| Scribe Assist | Ambient clinical documentation assistant | Tomás Riveiro |

---

## ReAdmit

ReAdmit is a risk-stratification model that scores inpatients at discharge for their likelihood of an unplanned readmission within 30 days. The output feeds a care-coordination worklist so that case managers can prioritize follow-up outreach for the highest-risk patients.

The model is trained on de-identified historical encounter data and validated against a held-out cohort curated by the Vitalis data science team. The clinical safety bar is firm and non-negotiable for go-live:

> **The ReAdmit model targets an AUROC of at least 0.78 on the 30-day unplanned-readmission validation set before clinical rollout.**

If a candidate model falls short of that AUROC threshold on the validation set, it does not ship to the clinical floor — full stop. We have a model review board (Helix + Vitalis clinical informatics) that signs off on every release candidate. Calibration, subgroup fairness checks, and drift monitoring are evaluated alongside the headline metric, but the 0.78 AUROC gate is the line we do not cross.

Engineering notes for ReAdmit:
- Feature pipeline is built in PySpark against the Vitalis Clarity extract.
- Inference runs as a scheduled batch job at discharge events, not real-time.
- Model artifacts are versioned in the MLflow registry; never promote a model to `staging` without an attached validation report.

## Scribe Assist

Scribe Assist is an ambient documentation tool. It listens to the clinical encounter (with patient consent), transcribes it, and generates a structured draft note that maps to the relevant Epic note types. The goal is to give clinicians time back by reducing manual charting load.

The critical design constraint — and a point we make repeatedly to both clinicians and auditors — is the human-in-the-loop requirement:

> **Scribe Assist notes are saved into Epic as draft entries requiring clinician sign-off prior to becoming part of the chart.**

In other words, the AI never writes directly to the legal medical record. Everything Scribe Assist produces lands as a draft that the clinician must review, edit, and explicitly sign. Until that sign-off happens, the content is not part of the chart and is not visible in downstream clinical workflows. This is both a safety control and a compliance requirement baked into the integration with Epic.

Engineering notes for Scribe Assist:
- Integration uses Epic's FHIR APIs plus the HL7 interface for note submission.
- Transcription and summarization run in two stages; the summarizer prompt templates live in the `scribe-prompts` repo.
- All audio is processed in-boundary and discarded after note generation per the data retention policy.

---

## Getting set up

1. Request VPC and Epic sandbox access (see #vitalis-access).
2. Clone the monorepo and run the bootstrap script — read the README first.
3. Pair with your workstream lead on your first ticket before opening any PR.
4. Join the Tuesday/Thursday client standup at 9:30am ET.

## Who to ask

- **Priya Narayanan** — Engineering Lead (engagement-wide questions)
- **Daniela Cho** — ReAdmit tech lead
- **Tomás Riveiro** — Scribe Assist tech lead
- **Marcus Feld** — Platform / access provisioning

Welcome aboard.
