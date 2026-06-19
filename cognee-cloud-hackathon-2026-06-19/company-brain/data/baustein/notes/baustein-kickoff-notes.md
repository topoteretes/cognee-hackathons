# BauStein GmbH — Project Kickoff Meeting Notes

**Engagement:** BauStein AI Acceleration Programme
**Client:** BauStein GmbH (Construction & Infrastructure)
**Helix Engagement Code:** HLX-2024-BST-014
**Date:** 2024-11-05
**Time:** 10:00–11:45 CET
**Location:** Helix AI Consulting, Munich Office (Room "Isar 3") + Microsoft Teams hybrid
**Author:** Lena Hoffmann (Engagement Manager, Helix AI Consulting)
**Distribution:** BauStein steering group, Helix delivery team, Helix PMO

---

## Attendees

| Name | Role | Organisation |
|---|---|---|
| Dr. Markus Reinhardt | Head of Digital Construction | BauStein GmbH |
| Sabine Vogel | IT Operations Lead | BauStein GmbH |
| Tobias Brandt | Site Operations Director | BauStein GmbH |
| Lena Hoffmann | Engagement Manager | Helix AI Consulting |
| Arjun Mehta | Lead AI Architect | Helix AI Consulting |
| Clara Weiss | ML Engineer | Helix AI Consulting |
| Daniel Okonkwo | Computer Vision Specialist | Helix AI Consulting |

Apologies: Hannah Fischer (BauStein Procurement) — to be briefed separately.

---

## 1. Purpose & Background

This session formally kicked off the BauStein AI Acceleration Programme. BauStein
approached Helix in Q3 2024 to modernise two pain points: the slow, manual handling
of contractor RFIs (Requests for Information) across large infrastructure projects,
and the lack of automated safety monitoring on active construction sites.

Two workstreams were confirmed for the first phase of delivery: **RFI Copilot** and
**SiteGuard CV**. Dr. Reinhardt opened the meeting by stressing that both initiatives
must demonstrate measurable value before any site-wide rollout is approved by the
BauStein board.

---

## 2. Agenda

1. Programme objectives and scope confirmation
2. RFI Copilot — technical approach
3. SiteGuard CV — pilot approach and milestones
4. Data access, security, and infrastructure
5. Governance, cadence, and next steps

---

## 3. Workstream Discussion

### 3.1 RFI Copilot

Arjun walked the room through the proposed architecture. The team confirmed that
**RFI Copilot is built on GPT-4o for spec-document summarization and answer drafting.**
The tool ingests technical specifications, tender documents, and prior RFI threads,
then produces concise summaries and drafts candidate answers for engineers to review
and approve before sending back to contractors.

Sabine raised the point that all spec documents currently live in BauStein's on-prem
SharePoint; a secure connector will be required. Clara to confirm whether a private
endpoint deployment is needed for data residency. BauStein noted that human sign-off
on every drafted answer is non-negotiable in the first release.

### 3.2 SiteGuard CV

Daniel presented the computer-vision workstream. The agreed entry point keeps scope
deliberately narrow: **the SiteGuard CV first pilot milestone was a single-camera
proof-of-concept at the Munich Tower site, targeted for completion by end of Q2 2024.**
Tobias acknowledged the milestone date and flagged that it had been ambitious given
the contracting timeline; the team agreed to revisit the realised status of this
milestone in the next review and adjust the multi-camera roadmap accordingly.

The proof-of-concept focuses on detecting missing PPE (helmets, hi-vis vests) in the
camera frame, with alerts surfaced to the site supervisor dashboard. No facial
recognition is in scope — confirmed with the works council as a hard constraint.

---

## 4. Decisions

- Both workstreams (RFI Copilot, SiteGuard CV) confirmed for Phase 1 delivery.
- RFI Copilot standardised on **GPT-4o** as the underlying model.
- SiteGuard CV to begin as a **single-camera proof-of-concept at the Munich Tower site**.
- Human-in-the-loop review mandatory for all RFI Copilot outputs.
- No facial recognition anywhere in SiteGuard CV.

---

## 5. Action Items

| # | Action | Owner | Due |
|---|---|---|---|
| A1 | Provision secure SharePoint connector for spec ingestion | Sabine Vogel | 2024-11-19 |
| A2 | Confirm GPT-4o deployment region & data residency options | Clara Weiss | 2024-11-15 |
| A3 | Document realised status of Munich Tower single-camera PoC milestone | Daniel Okonkwo | Next review |
| A4 | Draft RFI Copilot review-and-approval workflow | Arjun Mehta | 2024-11-22 |
| A5 | Schedule works council briefing on SiteGuard CV constraints | Tobias Brandt | 2024-11-20 |

---

## 6. Governance & Cadence

- Weekly delivery stand-up: Tuesdays 09:30 CET.
- Bi-weekly steering review with Dr. Reinhardt.
- All artefacts stored in the Helix knowledge base under engagement HLX-2024-BST-014.

**Next meeting:** 2024-11-19, 10:00 CET (hybrid).

_Notes circulated by Lena Hoffmann. Please reply with corrections within 48 hours._
