# Team Submission

## Team

- Team name: CogneeMind
- Participants: Ashwin Shirke (+ team)
- Company Brain / project name: **CogneeMind — Airport Gate-Ops Brain**

## Company Brain Overview

CogneeMind is a Company Brain for an airport operations team. It assigns flights
to gates, and — crucially — it **discovers the assignment *algorithm* and gets
better at discovering it the more disruptions it sees.** Three agents share the
brain: a **Researcher** (discovers the strategy), a **Planner** (executes it into
a live Gantt chart), and an **Observer** (watches the plan and triggers
re-planning on chaos). Every winning strategy, plus the dead-ends that failed,
is distilled into the Cognee knowledge graph. The next disruption is then
**warm-started from memory** instead of cold-searching — so discovery compounds:
fewer candidate evaluations and better plans over time.

- Domain or data sources: gates + flight schedule + an ops rulebook (hard rules:
  capacity, one-gate-per-flight, compatibility; soft goals: walking, stability).
- Primary use case: legal, low-pain gate plans that self-heal under new flights,
  gate closures, and cascading delays.
- What makes it stand out: it's not retrieval — it's an **auto-researcher** whose
  search space narrows as the wiki grows. One numeric **score** grounds every
  decision, so "smarter" is measurable, not vibes.

## The Three Operations

### Ingest
- What goes in: the rulebook (`data/rules.md`) and four agent **skills**
  (`my_skills/{researcher,planner,observer,linter}/SKILL.md`).
- How: `cognee.remember(rules)` → permanent graph; `cognee.remember(SKILLS_DIR,
  content_type="skills")` → skills. Raw discovery trials → session memory.
- Code entry point: `brain.py::CogneeBrain.setup()`.

### Query + Self-improve
- How users query: `POST /chat` (natural language: "close G3", "storm", "add
  flight 09:15") and the scenario buttons; the agent loop reoptimizes.
- Where feedback comes from: the penalty **score** `1000*U + 500*C + 1*W + 5*R`,
  mapped into a 0..1 `success_score`.
- How feedback updates the brain: `SkillRunEntry(success_score=...,
  skill_improvement={apply:False})` **proposes** a rewrite of the Researcher
  skill; `improve_skill(proposal_id, apply=True)` **applies** it. In parallel the
  winning strategy is distilled to the permanent graph as a reusable
  disruption→strategy mapping + dead-end list.
- Code entry point: `agents.py::optimize()` + `brain.py::self_improve()`.

### Lint
- What it means: dedupe identical strategies, keep only the best winner per
  disruption signature, drop orphan library entries.
- How it runs: on-demand (`POST /lint`, "lint wiki" button).
- Code entry point: `memory.py::LocalWiki.lint()` / linter skill.

## Self-Improvement Evidence

Reproduce with `python backend/evidence.py` (writes `data/evidence.json`).

### Baseline Run
- Query / task: a storm delays 4 international arrivals +30 min; re-plan with the
  naive default (`earliest_arrival`, which was fine on the calm base schedule).
- Result: naive `earliest_arrival` strands a flight at a remote stand.
- Score (penalty, lower=better): **1003.0** (U=1).
- Recorded feedback:

```text
error_type: stranded_flight
error_message: 1 flight with no gate under earliest_arrival
feedback: -1.0
success_score: 0.0
```

### Improved Run
- Query / task: same storm, after discovery.
- Result: discovered **`latest_departure`** — every flight gated, zero remote stands.
- Score: **6.0** (U=0)  → **~167× lower penalty.**
- What changed in the brain between runs:

```text
Before: Researcher had no prior; cold-searched the menu.
After:  Wiki holds {signature: delay:storm:heavy -> winner: latest_departure,
        score 6}, with the strategies that stranded a flight recorded as dead-ends.
```

### Compounding proof (the headline — memory makes discovery cheaper)
Same storm, same 2-try re-planning budget:

```text
COLD wiki : score 1003  (2 evals)  tried [earliest_arrival, earliest_departure]  -> strands a flight
WARM wiki : score    6  (2 evals)  tried [latest_departure, latest_departure+walk] -> all gated
full-budget cold reaches score 6 only after 6 evals — the warm brain gets there in 2.
```

→ With memory, the brain finds a **~167× better plan in the same budget**, and the
**same optimum in 3× fewer evaluations**.

## Architecture

```text
[scenario / chat turn]
        |
        v
[ session memory (session_id=run-...) ]   <- raw trials, per-run scratchpad
        |
        | distillation: winner + disruption->strategy + dead-ends
        v
[ permanent graph (no session_id) ]       <- rulebook, best strategies, score log
        |
        v
[ Researcher recalls priors -> Planner builds Gantt -> Observer watches ]
        |
        v
[ score -> SkillRunEntry (propose) -> improve_skill (apply) ]
```

Three agents = three skills, scored by one penalty number. The Researcher's
recall step is what makes discovery compound.

### Cognee — verified working
With `LLM_API_KEY` set, `brain.py` runs the full Cognee loop against a local
cognee 1.2.0.dev1 instance (we kept the graph local; `cognee.push("cogneemind")`
would upload it to Cloud unchanged). Verified end-to-end:

- **Ingest** — rulebook + 4 SKILL.md files → `cognee.remember(... content_type="skills")`
  ingests skills `[linter, observer, planner, researcher]`.
- **Agentic search** — `cognee.search(AGENTIC_COMPLETION, skills=[...])` answers
  *"the Researcher should adopt the `latest_departure` strategy…"* reasoning over
  the skills + graph.
- **Self-improve (applied)** — a stranded-flight failure records
  `SkillRunEntry(success_score=0.0)`; `cognee.remember(..., skill_improvement={apply:False})`
  proposes a researcher-skill rewrite and `improve_skill(apply=True)` **applies it**
  (live run: `{'applied': True, 'skill': 'researcher', 'success_score': 0.0}`).
- **Distill + recall** — winners go to the permanent graph (no session_id);
  `cognee.recall("best gate strategy for a storm")` returns the distilled
  *latest_departure* guidance. Session trials use `session_id=run-...`.

## Agents / Skills

```text
Skill path(s): backend/my_skills/{researcher,planner,observer,linter}/SKILL.md
Roles:
  - Ingestor: setup() ingests rules + skills
  - Querier:  Researcher (recall+propose) + Planner (execute)
  - Linter:   dedupe / prune / conflict-resolve
  - Critic:   Observer (chaos detection -> triggers re-discovery)
```

## Reproduction

```bash
# backend
cd backend
uv venv && uv pip install --python .venv/bin/python fastapi "uvicorn[standard]"
# (at the event also: uv pip install cognee==1.2.0.dev1 ; export LLM_API_KEY=...)
.venv/bin/python -m uvicorn api:app --port 8077

# evidence
python evidence.py

# frontend
cd ../frontend && npm install && npm run dev   # open http://localhost:5173
```

Environment variables (optional — Cognee lights up if present):

```text
LLM_API_KEY        # OpenAI key (provided at kickoff)
COGNEE_CLOUD_URL   # only if pushing to Cognee Cloud
COGNEE_API_KEY
```

## Demo

- Local: open the frontend, click **Base → +Flight → Close G3 → Storm**, then
  **run cold vs warm** in the Compounding card.
- 3-minute pitch outline:

```text
1. Problem: gates + disruptions; hook = "discovery that compounds via memory"
2. Base scenario: Gantt + score 10 (Researcher found latest_departure)
3. Storm: overlaps + a flight to remote stand; Observer flags chaos, brain heals
4. Money shot: cold vs warm on the same storm — 1003 (strands a flight) vs 6 (all gated), same budget
5. Open the wiki timeline: the brain literally got smarter from memory
6. Lint + Cognee distillation + what's next
```

## Links

- Repo: (this folder) `cogneemind/`
- Slides / writeup: `PROPOSAL.md`, `README.md`
