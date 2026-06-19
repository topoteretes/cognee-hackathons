# Team Submission

## Team

- Team name: Agent Rebel
- Participants: Matthias Rebel, Claude, Codex, ChatGPT
- Wiki / project name: isi-brain-console

## Wiki Overview

**Isi — Institutional Synaptic Intelligence** is a collaborative LLM Wiki that turns team conversations, project notes, code/debug observations, support reports, runbooks, and postmortems into a living team brain. Redis is used as short-term session memory for active team work, while Cognee stores long-term institutional knowledge in its permanent memory graph. Isi self-improves by capturing feedback after answers, logging it through Cognee’s `FEEDBACK` search type, promoting corrected knowledge into Cognee, and updating local `SKILL.md` files that guide future answers. The result is a wiki where useful knowledge “fires” more often, becomes more important, and stale or conflicting knowledge is detected through linting.

- Domain or data sources: Collaborative engineering knowledge: project chat, debugging notes, support tickets, runbooks, postmortems, code observations, and demo data about a Drupal / HTMX / Elasticsearch race condition.
- Primary use case: Help teams answer “what do we know about this problem?” while turning repeated project discussions into durable, improved institutional memory.
- What makes it stand out: Isi adds a synaptic activity layer on top of Cognee. Every question, note, answer, and feedback event can make related memories “fire.” Fired memories gain activation, repeated team use strengthens them, bad feedback weakens or corrects them, and linting consolidates the graph by marking stale or conflicting knowledge. The Brain Console shows these firings live next to the dialog and Cognee graph.


## The Three Operations

### Ingest

- What goes in:
  - Runbooks
  - Slack-style team conversations
  - Support tickets
  - Postmortems
  - Team notes (via `/api/collab`)
  - Questions and feedback (session memory)
  - Arbitrary documents (via `/api/ingest`)

- How it is captured:
  - Stable documents and long-term knowledge are captured with `cognee.remember(...)` without a `session_id`, making them part of Cognee’s permanent memory.
  - Active questions, team notes, and feedback are captured with `cognee.remember(..., session_id=...)`, routing them into Redis-backed session memory.
  - Skills are stored as local `SKILL.md` files and ingested into Cognee at setup with `content_type="skills"`. Feedback rewrites the skill on disk via Cognee's `improve_skill`.

- Code entry point:
  - `backend/isi/demo_seed.py`
  - `backend/isi/cognee_client.py`
  - `backend/isi/collab_ingest.py`
  - `POST /api/seed`
  - `POST /api/ingest`
  - `POST /api/collab`

### Query + Self-improve

- How users query the wiki:
  - Users ask questions in the Isi Brain Console collaborative dialog.
  - The backend stores the question into Redis session memory via `cognee.remember(..., session_id=...)`.
  - Isi queries Cognee using `SearchType.AGENTIC_COMPLETION` with `skills=["incident-answer"]` and `session_id`, so Cognee selects and applies the skill.
  - `recall(question, session_id=...)` is used to drive graph highlighting and activation. A per-question cache provides a crash-safe fallback answer if the live API is unavailable.

- Where feedback comes from:
  - User rating in the UI, for example score `0.35`.
  - Text feedback, for example: “Missed the race between HTMX refresh and delayed Elasticsearch delete confirmation.”
  - Optional agent critic / deterministic demo evaluator for repeatable before/after evidence.

- How feedback updates the wiki:
  - Feedback is stored in Redis session memory.
  - Feedback is logged through Cognee using the real `SearchType.FEEDBACK` path.
  - Isi records a `SkillRunEntry` (Cognee's real `cognee.memory.SkillRunEntry`; a local dataclass fallback is used only if the import is unavailable).
  - `cognee.remember(SkillRunEntry, skill_improvement={"apply": False, "score_threshold": 0.9})` proposes a skill rewrite; `improve_skill(..., apply=True)` applies it.
  - A correction memory is promoted into Cognee permanent memory.
  - Activation metadata is updated in the Isi overlay: memories that helped increase activation; contradicted/stale memories decay or are marked for linting.

- Code entry point:
  - `backend/isi/api.py`
  - `backend/isi/feedback.py`
  - `backend/isi/brain_overlay.py`
  - `POST /api/ask`
  - `POST /api/feedback`

### Lint

- What linting means in this wiki:
  - Detecting contradictions between old and new knowledge.
  - Detecting duplicate or near-duplicate memories.
  - Finding stale advice that should be decayed.
  - Recommending canonical / promote / decay candidates (returned as lists; not auto-applied this pass).
  - Producing a human-readable lint report.
  - Highlighting conflicts in the Cognee graph overlay.

- How it runs:
  - On-demand through the UI (`POST /api/lint`).
  - In the demo, lint is triggered manually after the feedback/improvement step.

- Code entry point:
  - `backend/isi/linting.py`
  - `backend/isi/brain_overlay.py`
  - `POST /api/lint`

## Self-Improvement Evidence

Show that the wiki actually got smarter. Concrete before/after beats prose.

> **Note:** The scores and answer prose below are the designed/expected values for the demo
> flow. Replace them with the actual output captured from the live run (real Cognee + LLM key)
> during the demo — run the `curl` commands in the Reproduction section and paste the real
> baseline answer, improved answer, and the SKILL.md diff here.

### Baseline Run

- Query / task:
  - “Why does deleting a transparency notice sometimes leave stale UI state?”

- Result:
  - The baseline answer identifies that the UI may show stale state and may mention refreshing the list, but it does not clearly identify the root cause as a race between HTMX refresh and delayed Elasticsearch delete confirmation.
  - It also does not clearly mark the old immediate-refresh runbook as stale or conflicting.

- Score:
  - `0.35 / 1.0`

- Recorded feedback:

```text
error_type: missing_root_cause
error_message: The answer did not identify the HTMX / Elasticsearch timing race and leaned too much on stale immediate-refresh advice.
feedback: Missed the race between HTMX refresh and delayed Elasticsearch delete confirmation. Prefer backend-confirmed refresh or optimistic UI with rollback.
success_score: 0.35
```

### Improved Run

- Query / task:
  - “Why does deleting a transparency notice sometimes leave stale UI state?”

- Result:
  - The improved answer identifies the root cause: HTMX refreshed the UI before Elasticsearch confirmed the delete.
  - It recommends waiting for backend confirmation before refreshing the list, or using optimistic UI with rollback.
  - It marks the older “refresh immediately after delete” runbook as stale/conflicting.
  - It references the newer postmortem and team debugging thread as stronger memories.

- Score:
  - `0.90 / 1.0`

- What changed in the wiki between runs:

```text
Before:
- incident-answer/SKILL.md did not explicitly require checking frontend/backend timing races.
- The old runbook and newer postmortem both existed, but the answer did not strongly prefer the newer confirmed root cause.
- No correction memory existed yet.
- Activation for the old runbook was too high relative to the newer postmortem.

After:
- Feedback was stored in Redis session memory.
- Feedback was logged through Cognee FEEDBACK.
- A SkillRunEntry was recorded and improve_skill(apply=True) rewrote the skill.
- incident-answer/SKILL.md was updated with a learned rule for stale UI after deletion.
- A correction memory was promoted into Cognee permanent memory.
- The newer postmortem / correction memory gained activation.
- The old immediate-refresh runbook was marked as stale/conflicting by lint.
```

## Architecture

The hackathon’s core pattern is **Redis as session memory, distilled into Cognee’s permanent knowledge graph**. Isi uses that split directly:

```text
[team chat / project notes / documents / agent turns]
        |
        v
[ Redis — session memory ]   <- hot, per-conversation
        |
        | promotion (active): feedback writes a correction memory to the permanent graph
        | distillation (planned): repeated/confirmed/conflict-resolving notes -> graph
        v
[ Cognee — permanent graph ]  <- durable, cross-session
        |
        | AGENTIC_COMPLETION(skills=[...]) / recall / cgraph
        v
[ Isi answer loop ]
        |
        | user feedback + Cognee FEEDBACK
        v
[ skill revision + correction promotion + lint ]
```

Components:

- `FastAPI backend`: exposes ask, feedback, lint, ingest, cgraph, and SSE endpoints.
- `Cognee`: permanent long-term memory engine and graph-backed retrieval/completion.
- `Redis`: hot session memory through Cognee `session_id`.
- `Isi skill loop`: records SkillRunEntry and applies Cognee's improve_skill to update the skill.
- `Isi Brain Console`: React UI with dialog, live memory trace, and Cognee cgraph visualization.
- `Brain overlay`: visual state for fired memories, activation, conflicts, stale nodes, and skill changes.

### Redis-as-session-memory

- What the agent writes into Redis (via `cognee.remember(..., session_id=...)`):
  - User questions (`[question] user: ...`)
  - Team notes / decisions / debug observations (`[type] user: ...` via `/api/collab`)
  - Feedback text (`[feedback] user score=...: ...`)

- How and when content is promoted into the graph:
  - Active this pass: on feedback, a correction memory is written to the permanent graph
    (`cognee.remember(...)` without `session_id`).
  - Planned (`/api/distill` is a deferred stub): promote a session note when it is repeated,
    confirmed by multiple users, resolves a conflict, or should be durable across sessions —
    governed by the `memory-distiller` skill.

- What stays in Redis vs. what gets promoted:
  - Stays in Redis:
    - temporary debugging noise
    - transient hypotheses
    - raw chat turns
    - incomplete observations
    - low-confidence notes
  - Gets promoted to Cognee (active: correction memory on feedback; rest planned via distiller):
    - confirmed root causes
    - corrected runbook knowledge
    - stable decisions
    - repeated team questions

- How memory quality improved between baseline and improved run:
  - Baseline: the system treated old runbook advice and newer postmortem information too equally.
  - Improved: after feedback, the system promoted a correction memory to the permanent graph,
    the skill was rewritten via `improve_skill(apply=True)`, and lint marked the old
    immediate-refresh advice as stale/conflicting.

## Agents / Skills

```text
Skill path(s):
- backend/skills/incident-answer/SKILL.md
- backend/skills/wiki-linter/SKILL.md
- backend/skills/memory-distiller/SKILL.md

Roles:
  - Ingestor:
      Captures documents, team notes, support tickets, postmortems, and code/debug observations.
      Stable sources go to Cognee permanent memory; active collaboration goes to Redis session memory.

  - Querier:
      Uses Cognee AGENTIC_COMPLETION with skills=["incident-answer"] and Redis session context to generate answers.

  - Linter:
      Searches for stale, duplicate, and conflicting memories.
      Produces lint reports and conflict highlights in the graph overlay.

  - Critic:
      Captures user feedback, logs it through Cognee FEEDBACK, records a SkillRunEntry, and triggers improve_skill to rewrite the skill.

  - Distiller (skill present; execution deferred this pass):
      Decides which session memories should be promoted into Cognee permanent memory.
```

## Reproduction

Commands to reproduce the demo:

```bash
# clone repo
git clone https://github.com/rebeling/isi-brain-console.git
cd isi-brain-console

# start Redis
docker compose up -d redis

# backend
cd backend
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
cp .env.example .env
# add LLM_API_KEY to .env
uvicorn app:app --reload --port 8000

# frontend, in a second terminal
cd frontend
npm install
npm run dev

# open UI
# http://localhost:5173

# optional scripted demo
cd ..
bash demo.sh
```

Environment variables required:

```text
LLM_API_KEY
REDIS_URL=redis://localhost:6379
# dataset "isi-wiki" and session "demo-1" are set in backend/isi/config.py
```

## Demo

- Live demo link:
  - `<add Loom / YouTube link here>`

- Local demo instructions:
  - Start Redis, backend, and frontend.
  - Open `http://localhost:5173`.
  - Run through the before/feedback/after/lint flow in the Isi Brain Console.

- 3-minute pitch outline:

```text
1. Problem / idea

  Teams lose knowledge across chats, tickets, debugging sessions, runbooks, postmortems, and people’s heads. Classic RAG can retrieve documents, but it does not know which knowledge is alive in the team right now.

  Isi treats every team interaction like a neuron firing.

  When someone asks a question, adds a note, confirms a fix, or gives feedback, related memories in Cognee “fire.” Those fired memories gain activation. If multiple people trigger the same memory, or if feedback confirms it was useful, its synaptic strength increases. If a memory is contradicted, stale, or leads to a bad answer, it weakens and gets flagged by linting.

  Redis is the short-term working memory where today’s firings happen. Cognee is the long-term memory graph where important patterns are consolidated. Isi is the synaptic layer that tracks what fired, what strengthened, what decayed, and what should become canonical team knowledge.

2. Ingest demo
   Show old runbook, Slack-style debug thread, support ticket, and newer postmortem being remembered by Cognee.
   Show Redis session memory for active collaborative chat.

3. Query demo before improvement
   Ask: “Why does deleting a transparency notice sometimes leave stale UI state?”
   Show the answer, fired memories, and Cognee graph activity.
   Baseline answer is incomplete.

4. Self-improve step
   Submit feedback: “Missed the HTMX / Elasticsearch race.”
   Show Redis feedback event, Cognee FEEDBACK logging, SkillRunEntry + improve_skill(apply=True) rewriting the skill, and correction memory promotion.

5. Query demo after improvement
   Ask the same question again.
   Show improved answer, stronger correction memory, and old runbook marked as stale/conflicting.

6. What is next
   Add real Slack/Confluence/GitHub connectors, scheduled linting, stronger cgraph integration, and OKF export for human review.
```

## Links

- Repo: https://github.com/rebeling/isi-brain-console.git
- Slides / writeup: `<add link>`
- Anything else:
  - Local UI: `http://localhost:5173`
  - Backend API: `http://localhost:8000`
  - Design + plan: `docs/superpowers/specs/` and `docs/superpowers/plans/`
