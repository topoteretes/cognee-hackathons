# Vitalis AuthFlow — Integration Architecture

> **Engineering Wiki** · Space: Vitalis Health / Platform Engineering
> **Owner:** Priya Nandakumar (Integration Lead)
> **Reviewers:** Marcus Allred (Solution Architect), Dr. Helen Choi (Clinical Informatics)
> **Last edited:** 14 Jan 2026 · **Status:** Living document

---

## Overview

AuthFlow is the prior-authorization (PA) automation platform Helix AI Consulting built for Vitalis Health. It sits between the hospital's clinical systems and external payers, automating the submission, tracking, and adjudication of prior-authorization requests that historically required manual fax and portal entry by the utilization-management team.

This page documents the end-to-end data flow and the interoperability standards in use. If you are onboarding to the AuthFlow squad, read this first, then see the runbook in `Vitalis / AuthFlow / Ops`.

## Context

Vitalis processes roughly 4,200 prior-auth requests per week across cardiology, oncology, and advanced imaging. Before AuthFlow, median turnaround was 3.5 business days. The target SLA for the automated path is under 6 hours for "clean" requests. Hitting that target depends entirely on standards-based, machine-readable exchange — which is why the integration boundary is built on established healthcare interoperability standards rather than custom payloads.

## End-to-End Data Flow

The flow has three logical legs: inbound ingestion, internal enrichment, and outbound payer exchange.

### 1. Inbound clinical document ingestion

AuthFlow ingests inbound clinical documents from the hospital interface engine over HL7 v2 messaging. The interface engine (Rhapsody) feeds AuthFlow with the clinical context needed to assemble a PA request — orders, encounters, results, and supporting documentation references. Relevant message types include:

| Message | Purpose |
|---------|---------|
| `ORM^O01` | New / updated orders that may require prior auth |
| `ORU^R01` | Observation results attached as clinical evidence |
| `ADT^A01/A08` | Patient and encounter demographics |
| `MDM^T02` | Document notification for supporting clinical notes |

Messages arrive over MLLP on a dedicated channel. The ingestion service acknowledges with an `ACK` and writes a normalized event to the internal queue.

### 2. Internal enrichment

The enrichment service resolves the patient, matches the order against payer-specific PA rule sets, and runs the medical-necessity model to draft justification text. Outputs are staged as a draft authorization record pending submission.

### 3. Outbound payer exchange

AuthFlow exchanges prior-authorization payloads with payers using the HL7 FHIR R4 standard. Each draft authorization is mapped to FHIR R4 resources and submitted to the payer's endpoint, with status polled until a determination is returned. The primary resources in play:

- **Claim** (use = `preauthorization`) — the PA request itself
- **ClaimResponse** — the payer's determination
- **Coverage** — member eligibility and plan linkage
- **DocumentReference / Binder** — supporting clinical attachments
- **Task** — tracks the request lifecycle and follow-up actions

We align to the Da Vinci PAS implementation guide where payers support it, but the underlying wire standard for all payer exchange is HL7 FHIR R4.

## Why two different standards?

A common onboarding question: why HL7 v2 inbound but FHIR R4 outbound?

The hospital's installed clinical systems and the Rhapsody interface engine speak HL7 v2 natively — it is the lingua franca of intramural clinical messaging and changing it is out of scope. Payers, conversely, have standardized their modern PA APIs on FHIR R4 (driven in part by CMS interoperability mandates). AuthFlow acts as the translation boundary: HL7 v2 in, FHIR R4 out.

## Sequence (simplified)

1. Rhapsody emits `ORM^O01` for an MRI order → AuthFlow ingests over HL7 v2.
2. Enrichment matches the order to the member's plan PA rules.
3. Medical-necessity model drafts justification.
4. AuthFlow assembles FHIR R4 `Claim` + attachments → submits to payer.
5. Payer returns `ClaimResponse`; status surfaced to UM team.

## Open Items

- Confirm FHIR R4 subscription support with the two remaining regional payers (tracked in AUTH-1187).
- Backlog: migrate `MDM^T02` document handling to attachment-by-reference.

---

*Questions: #vitalis-authflow on Slack. Architecture decisions live in the ADR log under `Vitalis / AuthFlow / Decisions`.*
