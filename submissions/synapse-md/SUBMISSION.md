# Synapse MD — Submission

## Team

- Wiki / project name: Synapse MD

## Wiki Overview

Synapse MD is a self-evolving medical knowledge wiki that
breaks down department data silos in hospitals. Doctors input
patient charts as usual. Three AI agents (Connector, Skeptic,
Linter) debate each case using knowledge stored in Redis and
Cognee, detect hidden cross-department patterns, and
automatically rewrite diagnostic skill rules that improve
with every case accumulated.

- Domain: Clinical medicine / hospital EHR systems
- Primary use case: Detecting diabetic retinopathy risk
  from cross-department chart patterns
- What makes it stand out: Passive intelligence — doctors
  never change their workflow. The wiki gets smarter silently.

## The Three Operations

### Ingest

- What goes in: Clinical notes (unstructured text)
- How captured: cognee.remember(notes, dataset_name="medical-wiki")
  for permanent graph + cognee.remember(notes, session_id="demo-session")
  for Redis session memory
- Code entry point: POST /analyze in main.py

### Query + Self-improve

- How users query: POST /query-wiki → cognee.recall(question)
- Feedback source: Linter agent scores each run
  (missing referral = 0.3, no issues = 0.9)
- How feedback updates wiki: OpenAI reads current SKILL.md +
  Linter feedback → rewrites SKILL.md with more specific rules
- Code entry point: POST /debate in main.py (skill improvement loop)

### Lint

- What linting means: Checks clinical notes against ADA 2024
  guidelines. Flags missing referrals, conflicting treatments.
- How it runs: On-demand, triggered on every /debate call
- Code entry point: Linter agent in POST /debate

## Self-Improvement Evidence

### Baseline Run

- Query: 58yo male, Type 2 Diabetes, vision blur, HbA1c 10.1%
- Result: Basic monitoring recommendation
- Score: 0.3 (ophthalmology referral missing)
- Recorded feedback: SkillRunEntry(success_score=0.3, feedback=-1.0)

SKILL.md Before (git: c056664):
```
description: Detect diabetic retinopathy risk in patient charts and recommend
ophthalmology referrals, prioritizing urgent evaluations for acute vision changes.
allowed-tools: memory_search

Current rules:
- Patients with Type 2 Diabetes require regular monitoring, with HbA1c levels
  considered for risk assessment.
- Sudden vision changes, such as blurriness and floaters, must trigger an
  immediate referral to ophthalmology for evaluation of potential diabetic
  retinopathy and other acute conditions.
- Document and flag any missed referrals or treatments based on the urgency of
  vision symptoms and diabetes management protocols.
```

### Improved Run

- Query: Same patient notes (subsequent runs)
- Result: Specific referral criteria, HbA1c thresholds, differential diagnosis
  requirements, and annual exam mandates added
- Score: 0.3 → improvement triggered on every linter alert
- What changed: SKILL.md rewritten with 9 specific rules across 6 agent runs

SKILL.md After (current — auto-evolved):
```
description: Detect diabetic retinopathy risk in patient charts and recommend
timely ophthalmology referrals, prioritizing urgent evaluations for acute vision
changes and considering alternative causes for vision symptoms, while ensuring
comprehensive diabetes management is addressed, including evaluation of other
potential systemic conditions.
allowed-tools: memory_search

Current rules:
- Patients with Type 2 Diabetes require regular monitoring, with HbA1c levels
  considered for risk assessment. An HbA1c above 9% necessitates urgent
  evaluation and potential adjustment of diabetes management plans. With HbA1c
  levels above 11%, immediate action is critical.
- Sudden vision changes, such as blurriness and floaters, must trigger an
  **immediate referral to ophthalmology** for evaluation of potential diabetic
  retinopathy and other acute conditions, including retinal detachment and
  vitreous hemorrhage. This referral should **not be delayed**.
- Conduct a differential diagnosis to rule out alternative causes of vision blur,
  with particular emphasis on retinal vein occlusion, vitreous hemorrhage, and
  retinal detachment, especially when sudden symptoms present.
- Incorporate the need for a **comprehensive eye examination** for patients with
  blurred vision, especially those with HbA1c levels above 9%.
- Recommend follow-up eye exams annually for all patients with diabetes.
- Double-check for the absence of prior ophthalmology referrals, as this poses a
  significant safety concern that must be addressed immediately.

Safety alert raised: True
Score: 0.3
```

## Architecture

[Doctor inputs chart]
|
v
[ Redis — session memory ] <- hot, per-conversation
cognee.remember(notes, session_id="demo-session")
|
| distillation (Cognee background sync)
v
[ Cognee — permanent graph ] <- durable, cross-session
cognee.remember(notes, dataset_name="medical-wiki")
|
v
[ 3 Agents debate (OpenAI) ]
Connector → Skeptic → Linter
|
v
[ Linter scores run → SkillRunEntry ]
|
v
[ OpenAI rewrites SKILL.md ]
|
v
[ Improved wiki for next patient ]

## Redis-as-session-memory

- What agent writes to Redis: clinical notes per session
- When distilled to graph: background sync after remember()
- What stays in Redis: current session raw notes
- What gets promoted: structured medical entities + relationships

## Agents / Skills

Skill path: my_skills/diabetic-retinopathy/SKILL.md
Roles:

- Connector: Links cross-department patterns
- Skeptic: Validates statistically, scores confidence
- Linter: Checks ADA 2024 guidelines, scores run

## Reproduction

cd wikihack
source .venv/bin/activate
uvicorn main:app --reload --port 8000
cd frontend && npm run dev

## Environment Variables

OPENAI_API_KEY=
REDIS_URL=redis://localhost:6379

## Demo

3-minute pitch outline:

1. Problem: Hospital data exists but nobody connects it
2. Ingest demo: Input diabetic patient chart
3. Query demo: Ask wiki about ophthalmology criteria (before)
4. Self-improve: Run agents → SKILL.md rewrites
5. Query demo: Same question → better answer (after)
6. Next: Scale to full hospital EHR system
