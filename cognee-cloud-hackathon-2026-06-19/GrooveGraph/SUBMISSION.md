# Team Submission

## Team

- Team name: GrooveGraph
- Participants: Sergej Kurtasch
- Company Brain / project name: GrooveGraph — A Self-Improving Brain for Ableton Live

## Company Brain Overview

GrooveGraph is a personal learning brain that I built to help me learn Ableton
Live on my local Mac. Instead of trying to cover the entire application, it
organizes the Ableton material I have ingested, remembers what happened in my
own learning sessions, and promotes only useful, validated answers into
long-term memory. When an answer misses an important detail, a critic records
the failure and GrooveGraph can propose a concrete update to its answerer
skill.

- Domain or data sources: selected Ableton Live manual content, material added
  during my learning, assistant conversations, and my validated workflow
  notes.
- Primary use case: helping one learner understand and practise Ableton Live
  workflows without losing useful context between sessions.
- What makes it stand out: it can learn from a specific failed explanation,
  update its answering instructions, rerun the same question, and measure
  whether the explanation became more useful.

## The Three Operations

### Ingest

- What goes in (documents, conversations, runs, ...): selected Ableton manual
  content, learning resources that I add, conversation turns,
  validated personal workflow notes, `SkillRunEntry` records, and GrooveGraph
  skills.
- How it is captured (`cognee.remember(...)`, custom pipeline, ...):
  documents use Cognee add/cognify; session entries, promoted knowledge,
  skills, and improvement runs use `cognee.remember(...)`.
- Code entry point: `scripts/hackathon_demo.py`,
  `src/cognee_kb/ingest.py`, `src/cognee_kb/memory.py`, and
  `src/cognee_kb/skills.py`.

### Query + Self-improve

- How users query the Company Brain: I ask questions through the ASA macOS
  client or the Gradio console while learning Ableton. Recall combines the
  current learning session with previously validated knowledge.
- Where feedback comes from (user rating, agent critic, eval, ...): user
  thumbs ratings, task completion, screenshot validation, golden evaluations,
  and the `groovegraph-critic` skill.
- How feedback updates the brain (`SkillRunEntry`, edge re-weighting,
  graph rewrite, ...): a failed answer becomes a `SkillRunEntry`;
  `cognee.remember(..., skill_improvement={"apply": false})` creates a
  proposal; GrooveGraph applies the selected proposal explicitly and reruns
  the same task. Validated successful knowledge can then be promoted from
  session memory into the permanent graph.
- Code entry point: `src/cognee_kb/improvement.py`,
  `src/cognee_kb/memory.py`, and `scripts/run_improvement_cycle.py`.

### Lint

- What "linting" means in your brain (dedupe, conflict resolution, stale
  pruning, ...): detecting duplicate facts, conflicting instructions, missing
  provenance, stale Ableton-version knowledge, unsupported claims, and
  unvalidated session content.
- How it runs (scheduled, on-write, on-demand): on demand, with a safe dry-run
  followed by explicit remediation and a verification scan.
- Code entry point: `src/cognee_kb/lint.py` and
  `scripts/cognee_lint.py`.

## Self-Improvement Evidence

### Baseline Run

- Query / task: "How do I record automation into an existing Arrangement in
  Ableton Live 12?"
- Result: the answer gave basic automation steps but did not distinguish
  Automation Arm, track Arm, Arrangement Record, and Session Record.
- Score (your own metric, judge-readable): **0.65 / 1.00**.
- Recorded feedback:

```text
error_type: missing_safety_context
error_message: The answer does not distinguish Automation Arm,
               Arrangement Record, and Session Record.
feedback: Explain which controls write automation and which can create
          unintended Session clips.
success_score: 0.65
```

### Improved Run

- Query / task: the same Arrangement automation task.
- Result: the answer enabled Automation Arm and Arrangement Record,
  distinguished track Arm, and warned against Session Record and empty
  Session clip slots.
- Score: **0.95 / 1.00** (**+0.30**).
- What changed in the brain between runs: Cognee generated an improvement
  proposal from the `SkillRunEntry`; GrooveGraph applied it explicitly; the
  answerer skill gained recording-control safety rules; the successful answer
  was promoted to permanent memory.

```text
Before:
Give practical recording steps, without an explicit rule for neighboring
Ableton recording controls.

After:
When explaining recording, distinguish Automation Arm, track Arm,
Arrangement Record, and Session Record to prevent unintended recording.
```

The same demo also reduced three seeded knowledge-quality findings—one
duplicate, one conflict, and one unsupported claim—to zero.

## Architecture

```text
[selected learning material / ASA turns / workflow notes]
                       |
                       v
[Cognee Cloud — session memory]
 session_id=<conversation>
 raw turns, feedback, task state
                       |
                       | promote only when positively rated,
                       | task-solved, validated, or high-scoring
                       v
[Cognee Cloud — permanent graph]
 sourced cross-session knowledge and skills
                       |
                       v
[recall -> answerer -> ASA / FastAPI / Gradio]
                       |
                       v
[critic -> SkillRunEntry -> proposal -> explicit apply]

[linter -> dry-run findings -> explicit remediation -> verification]
```

### Cognee Cloud (optional, rewarded)

- What I write to session memory (`session_id=...`) — raw turns,
  retrieved sources, answers, critic output, ratings, task outcomes, and
  validation results.
- What goes straight to the permanent graph (no `session_id`) — selected
  sourced learning material, GrooveGraph skills, and workflow knowledge that
  I have validated across sessions.
- How and when content is distilled from session memory into the permanent
  graph, inside the Cloud instance (what gets promoted? what triggers it?) —
  promotion requires positive feedback, a solved task, passed validation, or
  a critic score above the configured threshold.
- What stays session-only vs. what gets promoted — raw turns, failed answers,
  temporary observations, and unsupported claims stay session-only; sourced
  and validated learning notes are promoted.
- Proof the brain got smarter between baseline and improved run (how
  distillation quality improved) — the reproducible improvement run increased
  the critic score from **0.65** to **0.95**, changed the answerer skill, and
  promoted the validated answer. The Cloud check separately verified the same
  session and permanent memory interfaces with scoped recall.

Cognee Cloud was verified with an isolated session write/recall and a
permanent graph write/recall. Both scoped recalls returned the expected record.

## Agents / Skills (if any)

```text
Skill path(s):
  - skills/groovegraph-answerer/SKILL.md
  - skills/groovegraph-critic/SKILL.md
  - skills/groovegraph-linter/SKILL.md

Roles:
  - Ingestor: captures documents, turns, runs, and skills.
  - Querier: recalls both memory tiers and answers questions from the
    available learning material.
  - Linter: audits permanent knowledge and applies reviewed remediation.
  - Critic: scores answers and produces structured improvement feedback.
```

## Reproduction

Commands to reproduce the demo:

```bash
git clone https://github.com/SergejKurtasch/AbletonSmartAssistant.git
cd AbletonSmartAssistant
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp env.example .env

.venv/bin/python scripts/hackathon_demo.py
.venv/bin/python scripts/check_cognee_cloud_memory.py
```

Environment variables required:

```text
GEMINI_API_KEY

Cognee Cloud:
COGNEE_REMOTE_ENABLED=true
COGNEE_SERVICE_URL
COGNEE_API_KEY
```

## Demo

- Live demo link (Loom, YouTube, etc.) or local instructions: on macOS, open
  Ableton Live 12, start the FastAPI backend, launch ASA, and run
  `.venv/bin/python scripts/run_kb_ui.py`. The complete reproducible learning
  cycle is also available through
  `.venv/bin/python scripts/hackathon_demo.py`.
- 3-minute pitch outline:

```text
1. Problem: while learning Ableton, useful explanations and discoveries are
   easily lost between sessions.
2. Ingest selected learning material, conversations, workflow notes, and
   skills.
3. Run the baseline query and show the 0.65 score.
4. Show critic feedback, SkillRunEntry, proposal, and explicit apply.
5. Rerun the same query and show the 0.95 score.
6. Show a validated learning result entering long-term memory and lint
   reducing 3 issues to 0.
```

## Links

- Repo: https://github.com/SergejKurtasch/AbletonSmartAssistant
- Slides / writeup: Not applicable
- Anything else: Self-improvement, lint, and Cloud memory evidence are
  included in `docs/hackathon/evidence/`.
