# CAPE LLM Wiki — Cognee × Redis Hackathon Submission
Team: Hector Miramontes
Project: CAPE LLM Wiki — IEEPA Tariff Refund Filing Knowledge Graph
Date: May 16, 2026

## The Idea
Customs brokers filing IEEPA tariff refunds through CBP's CAPE portal are drowning in fragmented guidance — CSMS messages, ACE reports, 80-day rolling windows, PSC lock rules. A single wrong answer costs their client a refund.
We built a self-improving LLM knowledge wiki that answers broker questions with specific, actionable answers — referencing exact ACE reports (ESO 22, REV 615), statutory deadlines (§1514), and CBP policy (CSMS #68397097). The wiki knows what it doesn't know, and logs gaps as a product roadmap.
This runs inside RefundDesk, a real Rails product with real customs broker users.

## Three Required Operations
### 1. Ingest
Raw CBP guidance, CSMS messages, and ACE report documentation are ingested into Cognee's knowledge graph. Cognee extracts typed entities — cape phase 1, protest path, refund disbursement, ace portal, importer of record, error codes — building structured permanent memory that persists across sessions.
### 2. Query + Self-Improve
Each broker question is answered by querying the knowledge graph. Every answer is scored against a domain-specific rubric — does it reference ESO 22, REV 615, §1514, CSMS, PSC, ACH? Scores below 0.6 are logged to Redis as wiki gaps.
Redis as session memory: Every question a broker asks is pushed to their session key in Redis with a 1-hour TTL — ephemeral per-conversation working memory before distillation into the permanent graph.
Self-improvement evidence:

Run 1: Wrong SearchType → AttributeError → score 0.0 → gap logged
Run 2: Fixed SearchType + added eligibility and errors data → score 1.0 on all three
The gap log drove the fix. The wiki improved from its own failure signal.

### 3. Lint
Low-scoring answers are logged to wiki:gaps in Redis — a running audit of questions the wiki couldn't answer well. In production this drives re-ingestion cycles where new CBP guidance closes the gaps.

## Demo Questions — All Scored 1.0
Q: My entry liquidated 95 days ago. What are my options?
A: Outside the 80-day CAPE window but inside the 180-day protest window. File under 19 U.S.C. §1514. No extension available.
Q: I filed CAPE but found a classification error. Can I file a PSC?
A: No. Per CSMS #68397097, once CBP accepts a CAPE Declaration, that entry is locked — no Post-Summary Corrections until liquidation. Fix errors via PSC BEFORE submitting to CAPE.
Q: Refund shows in REV 615 but hasn't hit the bank after 10 days. What do I check?
A: REV 615 means the refund left CBP and is in Treasury's queue. Check REV-613 for ACH rejection. Confirm the IOR has refund-specific ACH enrollment — separate from ACH duty payment enrollment. CBP stopped issuing paper checks February 2026.

## Why This Domain
CAPE Phase 1 launched April 20, 2026 — 26 days ago. Guidance is fragmented across CBP CSMS messages, ACE portal docs, and broker forums. No other team at this hackathon has this domain knowledge encoded in their wiki. This is a real product solving a real problem for real users right now. The gap log is literally our product roadmap.

## Stack

Cognee 0.1.20 — knowledge graph, entity extraction, permanent memory
Redis 8.6.3 — session memory, gap logging, broker session tracking
OpenAI — LLM backbone for graph extraction and query answering
Python 3.11 — pipeline orchestration

## Links

Repo: https://github.com/hex-em/ieepa_refund_tool/tree/main/llm-wiki
Product: https://refunddesk.app