# BauStein Engagement — Platform Overview

*Internal Engineering Wiki · Helix AI Consulting*
*Last edited: 14 Jan 2026 by M. Okonkwo (Lead ML Engineer)*
*Engagement code: HX-BST-2024-11 · Practice: Industrial AI / Construction Tech*

---

## Purpose of this page

This page is the canonical onboarding reference for engineers joining the **BauStein GmbH** account. BauStein is a mid-cap German construction firm (HQ Munich, ~2,400 staff) running large vertical-build and infrastructure sites across the DACH region. Helix was engaged in Q4 2024 to deliver an integrated "Connected Site" platform. Three products are now in production or late staging. Read this before touching any repo or requesting prod access — for credentials see the separate `baustein/access` page.

**Account team:** Engagement lead Sofia Brandt; Tech lead Marcus Okonkwo; ML leads Priya Raman (CV) and Tomás Vidal (Geo/BIM); Client sponsor Ing. Hannah Vogel (BauStein Head of Digital).

---

## The three projects

We deliver three loosely-coupled products that share a common identity layer and event bus but are otherwise independently deployable.

### 1. SiteGuard CV — PPE & safety detection

SiteGuard is our worker-safety computer-vision product. It flags missing personal protective equipment (hard hats, hi-vis vests) in near-real-time from site camera feeds and helmet-cam streams.

- **SiteGuard CV PPE-detection runs on a YOLOv8 backbone fine-tuned on BauStein helmet-cam footage.** The fine-tune set is roughly 180k labelled frames captured on BauStein sites; this on-domain data is what lets us hit acceptable recall under dust, glare, and low-light conditions where the stock COCO-class detector struggled.
- Inference is containerised and runs at the edge on site gateways, with alerts pushed back to the SiteGuard dashboard.
- Active learning loop: low-confidence detections are routed to the annotation queue for periodic re-training.

### 2. ProgressAI Drone Twin — automated progress tracking

ProgressAI ingests periodic drone flyovers of a site and reconciles them against the design model to report construction progress without manual surveying.

- **ProgressAI Drone Twin compares drone captures against the client BIM model to compute percent-complete by trade.** Output is a per-trade breakdown (structural, MEP, façade, etc.) rather than a single blended number, which is what BauStein's PMs actually need for earned-value reporting.
- Drone captures are photogrammetrically reconstructed, aligned to the BIM coordinate frame, and diffed against expected geometry per work package.

### 3. RFI Copilot — request-for-information assistant

RFI Copilot is a retrieval-augmented assistant that drafts responses to contractor RFIs by pulling relevant spec sections, drawings, and prior responses.

- It surfaces the most relevant clauses from the spec library and prior-RFI corpus, then drafts a grounded reply for an engineer to review.
- Human-in-the-loop by design — every draft is reviewed before it leaves the system.

---

## Tech stack at a glance

| Area | SiteGuard CV | ProgressAI Drone Twin | RFI Copilot |
|---|---|---|---|
| Core model | YOLOv8 (fine-tuned) | Photogrammetry + BIM diff | LLM + RAG |
| Primary datastore | Object store (frames/labels) | PostGIS | PostgreSQL (app) |
| Vector / spatial layer | — | PostGIS spatial queries | Pinecone |
| Deploy target | Edge gateways | Cloud batch | Cloud service |

A note worth calling out for new joiners, because it trips people up: **RFI Copilot uses Pinecone as its vector store while ProgressAI uses PostGIS for spatial BIM queries.** They are different concerns — Pinecone backs semantic retrieval over documents, whereas PostGIS handles geometric/spatial lookups against the BIM model. Do not assume one product's data layer applies to the other.

---

## Shared infrastructure

All three products authenticate through the shared Helix-managed identity layer and emit events to a common Kafka bus for audit and cross-product dashboards. CI/CD runs through the standard Helix GitLab pipelines; infra is Terraform-managed on the client's EU-region cloud tenant for data-residency reasons.

---

## Status (as of Jan 2026)

- SiteGuard CV — **Production** on three pilot sites; rollout to remaining sites planned Q1.
- ProgressAI Drone Twin — **Late staging**, weekly flyover cadence with two reference sites.
- RFI Copilot — **Production (limited)**, gated to the Munich project office.

*Questions: #baustein-eng on Slack, or ping the tech lead.*
