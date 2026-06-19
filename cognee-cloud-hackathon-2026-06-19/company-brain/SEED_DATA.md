# Seed Data — Helix AI Consulting "Company Brain" demo

**Scenario:** Helix AI Consulting (Deloitte-like) builds custom AI projects for clients across industries.
The Company Brain ingests scattered project + firm knowledge and self-cleans. Facts are deliberately messy
to exercise every drift channel and router path.

**Fact schema:** `id | text | source | date | hard | planted_issue`
- `source` ∈ {wiki, slack#…, onboarding-doc, ticket, meeting-notes, email, contract, handbook, none}
- `hard=true` → policy / security / money / compliance (router must escalate to LLM judge before any delete)
- `planted_issue` → which drift case + partner id for pairs

**Source-trust order (proposed):** contract / handbook > meeting-notes / email > wiki / onboarding-doc > slack > none
**Refresh horizons (proposed):** policy/contract = none(durable) · model choice = 9mo · pricing/budget = 12mo · OKR/milestone = 6mo

---

## Client 1 — BauStein GmbH (Construction)

Projects:
- **SiteGuard CV** — computer-vision PPE/hazard detection on site CCTV + helmet cams.
- **ProgressAI Drone Twin** — drone + 360-photo progress vs BIM model, percent-complete by trade.
- **RFI Copilot** — RAG assistant over contracts/specs/submittals, drafts RFI responses, flags spec conflicts.

| id | text | source | date | hard | planted_issue |
|----|------|--------|------|------|---------------|
| bau-01 | SiteGuard CV PPE-detection runs on a YOLOv8 backbone fine-tuned on BauStein helmet-cam footage. | wiki | 2025-09-12 | false | clean |
| bau-02 | All worker-identifiable SiteGuard video must be anonymized (faces blurred) within 24h and never leave EU-Frankfurt, per GDPR + signed DPA. | contract | 2025-02-18 | true | stakes-override-pair (bau-03) |
| bau-03 | quick note — we're piping raw helmet-cam clips straight to the US-east bucket so the demo loads faster, faces still visible for now | slack#proj-baustein | 2026-05-30 | false | stakes-override-pair (bau-02) |
| bau-04 | RFI Copilot is built on GPT-4o for spec summarization and answer drafting. | meeting-notes | 2024-11-05 | false | contradiction-pair (bau-05) |
| bau-05 | RFI Copilot migrated to Claude Sonnet 4.5 as primary drafting model after Q1 2026 accuracy review; GPT-4o kept as fallback. | slack#proj-baustein | 2026-04-22 | false | contradiction-pair (bau-04 → this wins) |
| bau-06 | ProgressAI Drone Twin compares drone captures vs the client BIM model to compute percent-complete by trade. | wiki | 2025-10-01 | false | redundancy-pair (bau-07) |
| bau-07 | ProgressAI matches drone + 360-photo imagery to the BIM model to calculate completion % per trade and area. | onboarding-doc | 2025-10-15 | false | redundancy-pair (bau-06) |
| bau-08 | RFI Copilot uses Pinecone as its vector store; ProgressAI uses PostGIS for spatial BIM queries. | wiki | 2026-01-20 | false | fake-contradiction-pair (bau-09) |
| bau-09 | The platform standardized on Pinecone for all retrieval workloads on the BauStein engagement. | meeting-notes | 2026-02-03 | false | fake-contradiction-pair (bau-08 — PostGIS is GIS, not a vector store; no real conflict) |
| bau-10 | SiteGuard CV first milestone was a single-camera PoC at Munich Tower, targeted end of Q2 2024. | meeting-notes | 2024-04-10 | false | staleness-easy |
| bau-11 | Signed SOW budget for BauStein is EUR 480,000 across three AI workstreams for the current phase. | none | 2025-06-25 | true | no-source + staleness-borderline |

Headline Q: *"Where can we store BauStein's raw helmet-cam video, and which LLM does RFI Copilot run on today?"*
Before: surfaces bau-03 (raw video → US-east, faces visible) + bau-04 (GPT-4o) — wrong + dangerous.
After: HARD contract bau-02 stands (Slack note flagged, not applied); model resolves to bau-05 (Claude Sonnet 4.5); bau-11 flagged borderline-stale.

---

## Client 2 — SafeGuard Insurance

Projects:
- **Project Atlas** — claims triage + straight-through processing (doc extraction + severity scoring).
- **Project Sentinel** — fraud detection (gradient-boosted + anomaly) feeding the SIU.
- **Project Beacon** — generative underwriting copilot (summarize submission packets for P&C underwriters).

| id | text | source | date | hard | planted_issue |
|----|------|--------|------|------|---------------|
| ins-01 | Project Atlas uses a fine-tuned LayoutLM to extract loss details from FNOL docs before routing to the severity scorer. | wiki | 2025-09-12 | false | clean |
| ins-02 | Sentinel fraud model must hit precision 0.85 at the SIU referral threshold before production sign-off. | contract | 2025-04-03 | true | contradiction-pair (ins-03 — older, superseded) |
| ins-03 | Per revised SOW addendum, Sentinel's production target was lowered to precision 0.78 at the SIU threshold. | contract | 2026-02-18 | true | contradiction-pair (ins-02 → this wins) |
| ins-04 | All claimant PII must be anonymized and no policyholder data may leave the EU-hosted Azure tenant, per GDPR + DPA. | contract | 2025-01-22 | true | stakes-override-pair (ins-05) |
| ins-05 | Someone said we can just pipe the claims sample to the OpenAI US endpoint for the Beacon demo, fine for now. | slack#proj-safeguard | 2026-05-30 | false | stakes-override-pair (ins-04) |
| ins-06 | Project Beacon runs on Claude Sonnet 4.5 for underwriting summarization (long-context multi-doc packets). | meeting-notes | 2025-05-08 | false | staleness-borderline (~13mo) |
| ins-07 | The 2024 Atlas pilot was scoped only to personal auto glass claims under $2,500 in Texas. | onboarding-doc | 2024-03-15 | false | staleness-easy |
| ins-08 | The Atlas extraction service auto-routes any FNOL doc it parses to the severity scoring model. | wiki | 2025-09-20 | false | redundancy-pair (ins-01) |
| ins-09 | SafeGuard mandates bias/discrimination testing on Sentinel + Beacon per Colorado ECDIS and NAIC AI governance. | email | 2025-10-09 | true | clean |
| ins-10 | Project Beacon's pipeline is built on Apache Tika for text extraction. | ticket | 2026-01-14 | false | fake-contradiction-pair (ins-11) |
| ins-11 | Project Beacon uses Tesseract OCR to read scanned PDF submissions. | ticket | 2026-01-16 | false | fake-contradiction-pair (ins-10 — OCR + text extraction are complementary) |
| ins-12 | SafeGuard's preferred go-live target for Atlas STP rollout is end of Q3 2026. | none | 2026-03-01 | false | no-source |

Headline Q: *"What's the production sign-off precision for the SafeGuard fraud model, and where can we send claims data for the Beacon demo?"*
Before: stale 0.85 (ins-02) + casual ins-05 (PII → US OpenAI). After: resolves to 0.78 (ins-03); HARD ins-04 overrides the Slack note.

---

## Client 3 — Vitalis Health (Healthcare)

Projects:
- **Scribe Assist** — ambient clinical scribe drafting EHR notes, integrated with Epic.
- **AuthFlow** — prior-auth automation (LLM drafts + submits payer requests, human sign-off).
- **ReAdmit** — 30-day readmission risk model driving care-management outreach.

| id | text | source | date | hard | planted_issue |
|----|------|--------|------|------|---------------|
| hlth-01 | Scribe Assist runs in Azure US-East inside Vitalis's HIPAA-covered tenant, never on public consumer endpoints. | contract | 2025-03-11 | true | clean |
| hlth-02 | All PHI processed for Vitalis must stay within US data-residency boundaries and be encrypted at rest under the signed BAA. | contract | 2025-02-18 | true | stakes-override-pair (hlth-03) |
| hlth-03 | Eli says we can just spin up the scribe demo on the standard OpenAI consumer API, residency doesn't matter for a quick test. | slack#proj-vitalis | 2026-05-29 | false | stakes-override-pair (hlth-02) |
| hlth-04 | Scribe Assist generates draft notes using Anthropic Claude as the primary LLM. | meeting-notes | 2026-04-22 | false | contradiction-pair (hlth-05 → this wins) |
| hlth-05 | The scribe note-generation model is GPT-4o; that's what we picked for Vitalis. | none | 2025-08-14 | false | no-source + contradiction-pair (hlth-04 — older, unsourced, loses) |
| hlth-06 | AuthFlow exchanges prior-auth payloads with payers using HL7 FHIR R4. | wiki | 2026-01-09 | false | fake-contradiction-pair (hlth-07) |
| hlth-07 | AuthFlow ingests inbound clinical docs from the hospital interface engine over HL7 v2 messaging. | wiki | 2026-01-09 | false | fake-contradiction-pair (hlth-06 — FHIR + HL7 v2 coexist) |
| hlth-08 | ReAdmit targets AUROC ≥ 0.78 on the 30-day readmission validation set before clinical rollout. | onboarding-doc | 2025-11-03 | false | staleness-borderline (~12-14mo) |
| hlth-09 | The Scribe Assist 2024 pilot is scoped to outpatient cardiology at the Riverside clinic only. | meeting-notes | 2024-02-27 | false | staleness-easy |
| hlth-10 | Vitalis's signed SOW caps AuthFlow Phase 1 at USD 480,000 across discovery, build, validation. | contract | 2025-06-30 | true | clean |
| hlth-11 | Generated scribe notes land in Epic as unsigned drafts a clinician must review and sign off before they enter the record. | slack#proj-vitalis | 2025-10-02 | false | redundancy-pair (hlth-11b) |
| hlth-11b | Scribe Assist notes are saved into Epic as draft entries requiring clinician sign-off prior to becoming part of the chart. | onboarding-doc | 2025-09-12 | false | redundancy-pair (hlth-11 — dedupe to one) |

Headline Q: *"Which LLM powers Vitalis's Scribe Assist note generation, and where is it allowed to run?"*
Before: stale unsourced hlth-05 (GPT-4o) + casual hlth-03 (consumer OpenAI) → wrong, compliance-violating.
After: resolves to Claude (hlth-04); HARD BAA residency hlth-02 overrides the Slack note.

---

## Firm-level (cross-client)

Scope: people/roles, engineering standards, security & data-handling policy, AI tooling/model defaults, rate card, on-call, hiring, office logistics.

| id | text | source | date | hard | planted_issue |
|----|------|--------|------|------|---------------|
| firm-01 | Helix's New York office is at 30 Hudson Yards, 41st Floor; reception badges issued at the front desk on arrival. | wiki | 2026-03-12 | false | clean |
| firm-02 | Default LLM for new client engagements is Claude Sonnet 4.5 via Amazon Bedrock unless the client requires otherwise. | onboarding-doc | 2025-05-08 | false | contradiction-pair (firm-03) + staleness-borderline (~13mo) |
| firm-03 | Default model for all new builds is now Claude Opus 4.5 on Bedrock; Sonnet is the cost-tier fallback. | wiki | 2026-04-22 | false | contradiction-pair (firm-02 → this wins) |
| firm-04 | Standard rate card lists Senior AI Engineer at $295/hr. | handbook | 2025-11-03 | true | redundancy-pair (firm-05) |
| firm-05 | Senior AI Engineer bills at $295/hour on the standard rate card. | email | 2025-12-01 | true | redundancy-pair (firm-04) |
| firm-06 | Production deploys to client environments require two reviewer approvals on the PR before merge. | handbook | 2025-09-15 | true | stakes-override-pair (firm-07) |
| firm-07 | For the hotfix this week let's just do single-approval merges to move faster, two reviewers is overkill. | slack#eng | 2026-05-30 | false | stakes-override-pair (firm-06) |
| firm-08 | Client PII is processed and stored only in eu-west-1 for EU clients. | slack#eng | 2026-05-18 | true | park-case (firm-09) |
| firm-09 | EU client PII may be processed in eu-central-1 as well as eu-west-1 for the DACH accounts. | none | 2026-05-21 | true | park-case (firm-08) + no-source → quarantine, no tie-breaker |
| firm-10 | We standardize on GitHub Actions for CI across all client repos. | wiki | 2026-02-10 | false | fake-contradiction-pair (firm-11) |
| firm-11 | Our CI runs on GitHub-hosted runners with reusable workflow templates. | onboarding-doc | 2026-02-14 | false | fake-contradiction-pair (firm-10 — same thing) |
| firm-12 | Engineers manage secrets locally with the Doppler CLI synced from the shared 2024 project config. | onboarding-doc | 2024-06-20 | true | staleness-easy |

Headline Q: *"What's our default LLM for a new client build, and how much does a Senior AI Engineer bill per hour?"*
Before: stale firm-02 (Sonnet 4.5) + double-counted rate card. After: firm-03 wins (Claude Opus 4.5); firm-04/05 collapse to one $295/hr; firm-06 two-approval policy NOT relaxed; firm-08/09 EU-PII conflict parked for human.

---

## Drift-channel coverage (every case is represented)

| Channel / case | Examples |
|---|---|
| clean | bau-01, ins-01, ins-09, hlth-01, hlth-10, firm-01 |
| redundancy-pair | bau-06/07, ins-01/08, hlth-11/11b, firm-04/05 |
| contradiction-pair (newer wins) | bau-04/05, ins-02/03, hlth-04/05, firm-02/03 |
| fake-contradiction (judge) | bau-08/09, ins-10/11, hlth-06/07, firm-10/11 |
| staleness-easy | bau-10, ins-07, hlth-09, firm-12 |
| staleness-borderline | bau-11, ins-06, hlth-08, firm-02 |
| stakes-override (hard, must NOT silently drop) | bau-02/03, ins-04/05, hlth-02/03, firm-06/07 |
| no-source | bau-11, ins-12, hlth-05, firm-09 |
| park / quarantine (nobody sure) | firm-08/09 |

**Recurring demo punch:** the EUR/USD 480,000 SOW figure appears for all 3 clients — a deliberate cross-client
near-collision to show scoped resolution (don't merge across clients; `node_set`/dataset per client keeps them separate).

**Total:** ~46 facts. For a tight 3-min demo, seed one client (BauStein or Vitalis — both have a compliance stakes-override
that makes the strongest story) + a few firm-level facts, and reserve the rest.
