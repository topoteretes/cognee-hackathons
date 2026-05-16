# Team Submission

## Team

* Team name:  Moksha Labs Sales GTM Agent 
* Participants: Nikhil Shah, CSO Chief Strategy Officer
* Wiki / project name: Moksha sales-memory wiki  GTM Copilot 

## Wiki Overview

Moksha GTM Copilot is a self-improving sales-memory wiki for Moksha Labs go-to-market teams. It turns proposals, discovery notes, objection handling, battlecards, lead context, and workflow events into a practical copilot for meeting prep, account research, proposal generation, and objection coaching. Cognee is the durable knowledge graph for cross-session sales memory; Redis is the fast session and workflow memory for live lead activity, queues, cached recalls, and next actions. The wiki improves as new lead notes, objections, and proposal requests are captured in Redis, distilled into Cognee memory, and then used to return sharper recommendations with visible source grounding.

* Domain or data sources: Moksha Labs sales knowledge, synthetic account history, proposal summaries, conversation notes, battlecards, objection responses, email templates, lead events, and Cognee triples.
* Primary use case: Help a sales rep prepare for a first client meeting, answer discovery questions, handle objections, and generate the next best action from trusted company memory.
* What makes it stand out: This is not a generic RAG chat box. It is an operational GTM workflow where Redis tracks what is happening now, Cognee remembers what the company has learned over time, and the UI exposes both through source chips, lead timelines, queues, and proposal/objection workflows.

## The Three Operations

### Ingest

* What goes in: Sales knowledge markdown, proposal summaries, call/conversation notes, lead records, objection events, proposal requests, battlecards, email templates, and graph triples.
* How it is captured: The demo UI seeds a local Moksha Labs knowledge base through the Cognee adapter. The FastAPI reference service supports direct `cognee.remember(...)` ingestion for real Cognee Cloud credentials.
* Code entry point:
  * `apps/api/src/data/seed.ts` loads `data/moksha_labs_sales_knowledge_base_v1.md` and seeds Redis workflow events.
  * `apps/api/src/services/cogneeService.ts` implements `ingestKnowledgebase(...)`, mock retrieval, and real Cognee API search mode.
  * `app/main.py` implements `/knowledge/ingest`, `/leads`, and `/leads/{lead_id}/notes` with direct `cognee.remember(...)` calls.

### Query + Self-improve

* How users query the wiki: Reps use Meeting Prep, Ask Knowledgebase, Lead Detail, Proposal Generator, and Objection Coach screens. API routes include `/api/ask`, `/api/meeting-prep`, `/api/proposal`, `/api/objection`, and `/api/cognee/debug-search`.
* Where feedback comes from: Sales actions become feedback signals: objections logged, proposal requests, meeting completions, lead notes, source-hit quality, and whether the rep accepts a next action.
* How feedback updates the wiki: Redis first captures hot session/workflow state as event keys, queues, next actions, and activity logs. Important notes and lead updates can then be promoted into Cognee with `cognee.remember(...)` so future searches retrieve them as permanent sales memory. The mock adapter demonstrates the same promotion pattern with seeded events and markdown chunks; real Cognee mode is isolated behind the same service boundary.
* Code entry point:
  * `apps/api/src/routes/ask.ts`
  * `apps/api/src/routes/meetingPrep.ts`
  * `apps/api/src/routes/proposal.ts`
  * `apps/api/src/routes/objection.ts`
  * `apps/api/src/routes/events.ts`
  * `app/main.py` for real Cognee recall, Redis caching, and note promotion.

### Lint

* What "linting" means in this wiki: Keep the sales wiki trustworthy by removing duplicate workflow queue entries, limiting stale activity logs, resolving completed actions, surfacing source provenance, and detecting thin or irrelevant retrieval through debug search scores.
* How it runs: Queue dedupe happens on write; Redis activity logs are trimmed continuously; events can be resolved on demand; retrieval quality can be checked through `/api/cognee/debug-search` before demo or after ingestion.
* Code entry point:
  * `apps/api/src/services/redisService.ts` prevents duplicate queue IDs, stores `next_action:{lead_id}`, and resolves events.
  * `app/main.py` trims `gtm:activity` to the latest 50 events and caches query results with TTL.
  * `apps/api/src/routes/cogneeDebug.ts` exposes source scores so weak retrieval can be caught before it reaches the rep.

## Self-Improvement Evidence

Concrete before/after target: "A new rep is meeting a healthcare CIO in the USA who wants AI document intake. What should they ask, what objections should they expect, and what next action should they take?"

### Baseline Run

* Query / task: `I am meeting a healthcare CIO in the USA who wants AI for document intake. What should I ask?`
* Result: Without the Moksha sales memory loaded, the assistant can only provide generic discovery advice: ask about process, data, stakeholders, timeline, and budget.
* Score: 2/8 on the demo source-hit rubric. It names useful generic questions but misses the known account, prior conversation, POC proposal, objection playbook, and next action.
* Recorded feedback:

```yaml
error_type: missing_sales_memory
error_message: Generic answer did not retrieve account-specific healthcare intake knowledge.
feedback: Promote healthcare intake proposal, NorthBridge CIO conversation, objection handling, and battlecard into permanent sales memory.
success_score: 0.25
```

### Improved Run

* Query / task: Same query after ingestion and Redis event seeding.
* Result: The wiki retrieves the exact lead, account, prior conversation, proposal, triple, battlecard, email opener, and objection response needed for the meeting.
* Score: 8/8 on the source-hit rubric.
* What changed in the wiki between runs:

```text
Before:
No durable Moksha sales memory for this task; no Redis workflow context showing the lead is hot.

After:
Cognee memory includes 19 markdown knowledge chunks plus structured account, lead, proposal, objection, battlecard, and triple sources.
Redis memory includes 3 seeded workflow events, including a high-priority NorthBridge healthcare intake lead event.
```

Observed improved retrieval:

```json
[
  { "id": "L001", "type": "lead", "title": "Dr. Elaine Porter - AI document intake", "score": 12 },
  { "id": "A001", "type": "account", "title": "NorthBridge Health Systems", "score": 11 },
  { "id": "C001", "type": "conversation", "title": "NorthBridge Health Systems CIO intake discovery", "score": 11 },
  { "id": "P001", "type": "proposal", "title": "AI Document Intake POC for NorthBridge Health Systems", "score": 11 },
  { "id": "T002", "type": "triple", "title": "AI Document Intake -> fits -> Healthcare CIO", "score": 10 },
  { "id": "B001", "type": "battlecard", "title": "AI Document Intake", "score": 8 },
  { "id": "E001", "type": "email", "title": "AI readiness opener", "score": 7 },
  { "id": "O001", "type": "objection", "title": "AI accuracy may not be good enough.", "score": 6 }
]
```

The improved answer recommends a 6-week AI Document Intake POC, asks for anonymized sample documents, includes HIPAA/audit/citation questions, and prepares the rep for accuracy, compliance, and poor scan quality objections.

## Architecture

```text
[rep actions, lead notes, proposal requests, objections]
        |
        v
[Redis - session + workflow memory]
  - event:{event_id}
  - workflow_queue:high_priority
  - workflow_queue:medium_priority
  - next_action:{lead_id}
  - gtm:*_events
  - cached recall answers with TTL
        |
        | distill important events, notes, and accepted recommendations
        v
[Cognee - permanent sales graph]
  - proposals
  - conversations
  - accounts and leads
  - battlecards and objections
  - sales knowledge chunks
  - triples connecting offers, buyers, and use cases
        |
        v
[recall + agent loop]
  - meeting prep
  - ask knowledgebase
  - proposal generator
  - objection coach
        |
        v
[feedback -> improve]
  - log new events in Redis
  - promote important notes to Cognee
  - lint queues, source quality, and stale activity
```

### Redis-as-session-memory

* What the agent writes into Redis: Raw workflow events, event priority queues, next actions, lead timelines, cached recall results, proposal events, objection events, meeting events, and activity logs.
* How and when content is distilled into the graph: High-signal rep actions, call notes, lead updates, accepted objection responses, and proposal decisions are promoted into Cognee via `cognee.remember(...)` in the reference service or through the Cognee adapter boundary in the demo app.
* What stays in Redis vs. what gets promoted: Fast-changing state stays in Redis: queue position, event resolution, hot lead actions, and cached answers. Durable knowledge is promoted: account learnings, proposal outcomes, buyer objections, reusable discovery questions, and successful next actions.
* How distillation quality improved between baseline and improved run: The improved run retrieved all required sales artifacts for the healthcare CIO scenario, raising the source-hit score from 2/8 to 8/8 and changing the answer from generic discovery to account-specific, proposal-backed meeting guidance.

## Agents / Skills

This project uses application-level roles rather than external skill packs:

```text
Roles:
  - Ingestor: seed.ts, cogneeService.ingestKnowledgebase, app/main.py /knowledge/ingest
  - Querier: /api/ask, /api/meeting-prep, /api/proposal, /api/objection
  - Linter: redisService queue dedupe, event resolution, activity trim, debug search scoring
  - Critic: source-hit rubric and rep feedback events such as objection.logged and proposal.requested
```

## Reproduction

Commands to reproduce the demo:

```powershell
Copy-Item .env.local.example .env.local

# Reliable local demo mode
# In .env.local:
# USE_MOCK_COGNEE=true
# USE_MOCK_REDIS=true
# NEXT_PUBLIC_API_URL=http://127.0.0.1:4000
# PORT=4000

npm install
npm run seed
npm run dev
```

Open:

```text
Web app: http://127.0.0.1:3000
API health: http://127.0.0.1:4000/api/health
Debug search: http://127.0.0.1:4000/api/cognee/debug-search?query=healthcare%20CIO%20AI%20document%20intake
```

Optional real Cognee/Redis path:

```powershell
# Express adapter real mode
USE_MOCK_COGNEE=false
USE_MOCK_REDIS=false
COGNEE_BASE_URL=<your Cognee API base URL>
COGNEE_API_KEY=<your Cognee API key>
COGNEE_PROJECT_ID=<optional project id>
REDIS_URL=redis://localhost:6379

# FastAPI direct Cognee reference service
uvicorn app.main:app --reload --port 8000
```

Environment variables required:

```text
OPENAI_API_KEY
OPENAI_BASE_URL
OPENAI_MODEL
REDIS_URL
COGNEE_API_KEY
COGNEE_PROJECT_ID
COGNEE_BASE_URL
USE_MOCK_COGNEE
USE_MOCK_REDIS
NEXT_PUBLIC_API_URL
PORT
```

## Demo

* Live demo link: will be provided seperately 
* Local demo instructions: Run `npm run dev`, open `http://127.0.0.1:3000`, then follow the pitch below.
* 3-minute pitch outline:

1. Problem / idea: Moksha Labs sales reps lose time searching old proposals, battlecards, and call notes. The copilot gives them company memory at the moment they need it.
2. Ingest demo: Run seed, show `19` knowledge chunks ingested from the Moksha sales markdown and `3` Redis workflow events seeded.
3. Query demo before improvement: Explain the baseline generic healthcare CIO discovery answer and its 2/8 source-hit score.
4. Self-improve step: Show Redis high-priority lead event and Cognee retrieved sources for NorthBridge Health Systems.
5. Query demo after improvement: Generate Meeting Prep for NorthBridge. Highlight the account brief, healthcare intake questions, similar proposal, objections, and source chips.
6. What is next: Promote accepted rep actions automatically into Cognee, add CRM ingestion, and use Redis Streams for live workflow updates.

## Links

* Repo: Add GitHub repository URL after push.
* Slides / writeup: This `SUBMISSION.md` plus `docs/demo-script.md`.
* Anything else:
  * Demo script: `docs/demo-script.md`
  * Seed data: `data/moksha_labs_sales_knowledge_base_v1.md`
  * Main web app: `apps/web`
  * Main API: `apps/api`
  * Direct Cognee reference service: `app/main.py`
