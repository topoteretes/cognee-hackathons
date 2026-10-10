# BauStein GmbH Engagement — Engineer Onboarding

**Helix AI Consulting — Internal Wiki**
**Last updated:** 2025-10-15
**Owner:** Markus Lehmann (Engagement Lead, Munich office)
**Audience:** Engineers joining the BauStein delivery team

Welcome to the BauStein engagement! This page is the first thing you should read before your kickoff session. It covers what we're building, where the code lives, and who to ask when you get stuck. Please skim it end-to-end, then bookmark it — we keep it current and reference it in standups.

## About the Client

BauStein GmbH is a mid-to-large German construction firm headquartered in Stuttgart, with active sites across Baden-Württemberg and Bavaria. They run large commercial and infrastructure builds and have been an early adopter of digital site management. Our engagement (project code **HX-BAU-2025**) runs through Q2 2026 with an option to extend into a managed-service phase.

The client sponsor is **Dr. Anja Vogt** (Head of Digital Construction). Day-to-day client contact is **Tobias Reiner**, their BIM coordinator. Be courteous, prompt, and precise in all client communications — BauStein is engineering-led and appreciates technical rigor.

## What We're Building

The flagship deliverable is **ProgressAI**, a computer-vision progress-tracking platform.

> **ProgressAI matches drone and 360-photo imagery to the BIM model to calculate completion percentage per trade and area.**

In plain terms: site teams capture drone flyovers and 360-degree walkthrough photos on a regular cadence. ProgressAI registers that imagery against the building information model (BIM), then estimates how far along each trade (e.g., structural, electrical, HVAC, drywall) and each spatial area (floor, zone, room) actually is. The output feeds dashboards that let project managers compare planned vs. actual progress and flag slippage early.

This replaces a manual, error-prone process where site engineers eyeballed progress and typed numbers into spreadsheets.

### Why it matters to the client

- Reduces manual progress surveys from days to hours
- Gives finance an objective basis for milestone billing
- Creates an auditable record of site state over time

## Architecture at a Glance

| Layer | Stack | Notes |
|-------|-------|-------|
| Ingestion | Python, Celery | Pulls drone/360 imagery from site uploads |
| CV / registration | PyTorch, OpenCV | Aligns imagery to the BIM geometry |
| BIM services | IFC.js, Forge API | Parses and serves the model |
| API | FastAPI | Serves completion metrics |
| Frontend | React + TypeScript | PM dashboards |
| Data | PostgreSQL + S3 | Metrics in PG, imagery in S3 |

## Repositories

All repos live under the `helix-baustein` GitHub org. Request access via the IT portal (ticket type: "Repo Access — HX-BAU-2025").

- `progressai-core` — CV pipeline and BIM matching logic
- `progressai-api` — FastAPI service layer
- `progressai-web` — React dashboard
- `baustein-infra` — Terraform + deployment configs
- `baustein-docs` — engagement documentation (you're reading the exported version)

Clone `progressai-core` first and run `make dev-setup`. The README there walks through the local sample dataset (anonymized imagery from the Stuttgart pilot site).

## Who to Ask

- **CV / model questions** — Priya Nair (ML lead)
- **BIM / IFC questions** — Stefan Brandt
- **API / backend** — Lucas Moreau
- **Frontend** — Hannah Klein
- **Infra / deployment** — Markus Lehmann (also engagement lead)
- **Anything client-facing** — route through Markus before contacting BauStein directly

## First Week Checklist

1. Get GitHub org and VPN access (raise IT tickets day one)
2. Read this page plus the architecture deck in `baustein-docs/decks/`
3. Clone `progressai-core` and run the sample pipeline end-to-end
4. Sit in on a client standup (Tue/Thu, 09:30 CET) as an observer
5. Pick a "good first issue" from the `progressai-core` board with your tech lead

## House Rules

- All client imagery is confidential. Never copy it outside approved S3 buckets.
- Branch naming: `feature/HX-BAU-<ticket>-short-desc`
- PRs require one approval from the relevant area owner above
- Standups are short; blockers go in the `#baustein-eng` Slack channel

Questions about onboarding? Ping Markus Lehmann or drop a note in `#baustein-eng`. Welcome aboard.
