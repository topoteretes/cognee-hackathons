# Team Submission

## Team

- Team name: StudyAtlas
- Participants: TODO: Pratik Manghwani, Jilie SUn, Zhenghan, Huong
- Wiki / project name: StudyAtlas

## Wiki Overview

StudyAtlas is a personalized LLM wiki for students. It turns course PDFs, notes, and student confusion into a living study wiki, then uses feedback from each query to improve both the student's memory state and the answering skill. Redis is the per-session working memory: it stores mastery scores, recent study events, TTL-based forgetting markers, and live decay notifications. Cognee is the long-term memory: it stores durable course concepts, source summaries, student context, bridge pages, study guides, and the personalized explainer skill.

- Domain or data sources: EA51 Empirical Analyses course materials, including syllabus PDFs, science communication readings, research design material, case study notes, evidence-based argument readings, hypothesis development, and plausibility readings.
- Primary use case: A student asks questions across scattered course materials and gets answers tailored to what they understand, what they recently forgot, and what concepts need review.
- What makes it stand out: The wiki does not only retrieve information. It models knowledge as something with a half-life. Redis mastery bars decay in real time, lint flags fading concepts, and a self-improvement loop rewrites the answering skill after low-scored answers.

## The Three Operations

### Ingest

- What goes in (documents, conversations, runs, ...): Course PDFs, DOCX readings, markdown/text notes, uploaded files, preloaded demo assets, and a student context note describing what the student finds confusing.
- How it is captured (`cognee.remember(...)`, custom pipeline, ...): Files are parsed by the backend ingest pipeline, converted into visible markdown wiki pages, summarized into course/concept/source metadata, remembered by Cognee, and used to seed Redis mastery state for the active session.
- Code entry point: `backend/main.py` routes `POST /ingest`, `POST /ingest-assets`, and `POST /student-context`; `backend/ingest.py` parses files and writes wiki pages; `backend/wiki_writer.py` creates source, course, concept, student, bridge, and study guide pages; `backend/memory.py` writes Cognee memories and Redis mastery/session state.

Ingested demo files:

```text
assets/ea51-syllabus.pdf
assets/EA51 - Science of Science Communication (1).pdf
assets/Research Design.pdf
assets/casestudy.pdf
assets/EA51 Session 15 - (8.2) Case study.docx
assets/evidencebased.pdf
assets/hypothesisdevelopment.pdf
assets/plausibility.pdf
```

Generated wiki artifacts shown in the demo:

```text
wiki/courses/...
wiki/sources/...
wiki/concepts/case_study.md
wiki/concepts/evidence_based_argument.md
wiki/concepts/hypothesis_development.md
wiki/concepts/plausibility.md
wiki/concepts/research_design.md
wiki/student/profile.md
wiki/study_guides/...
wiki/bridges/...
```

### Query + Self-improve

- How users query the wiki: The frontend `Query` tab sends a question to `POST /query`. The backend combines local wiki search over generated markdown pages with Cognee recall, using the current `session_id` to preserve the student's working context.
- Where feedback comes from (user rating, agent critic, eval, ...): The student rates the answer from 0.1 to 1.0. Low scores trigger the improve flow. High scores reinforce mastery for concepts touched by the answer.
- How feedback updates the wiki (`SkillRunEntry`, edge re-weighting, graph rewrite, ...): Ratings update Redis mastery scores and are remembered as feedback. The improve path shows a before/after `SKILL.md` rewrite for `my_skills/personalized-explainer/SKILL.md`, then applies the improved answering instructions. Useful answers can also be saved back into the wiki as study guides or bridge pages.
- Code entry point: `backend/query.py`, `backend/main.py` (`POST /query`, `POST /rate`, `POST /improve`, `POST /save-answer`), `backend/improve.py`, `backend/search.py`, and `my_skills/personalized-explainer/SKILL.md`.

Demo question:

```text
Help me explain why the Zika microcephaly reading is a case study, and connect it to evidence-based argument, hypothesis development, and plausibility.
```

### Lint

- What "linting" means in your wiki (dedupe, conflict resolution, stale pruning, ...): StudyAtlas lint checks for missing concept pages, orphaned concepts, weak bridges between courses/concepts, unlinked sources, and fading concepts whose Redis mastery score has decayed below the review threshold.
- How it runs (scheduled, on-write, on-demand): It runs on demand from the `Lint` frontend tab through `GET /lint`. The decay watcher also surfaces real-time fading warnings through Server-Sent Events.
- Code entry point: `backend/lint.py`, `backend/memory.py`, `backend/main.py` (`GET /lint`, `GET /events/decay`), and `frontend/src/components/LintReport.jsx`.

## Self-Improvement Evidence

Concrete before/after demo evidence for the same Zika case-study question.

### Baseline Run

- Query / task: "Help me explain why the Zika microcephaly reading is a case study, and connect it to evidence-based argument, hypothesis development, and plausibility."
- Result: The baseline answer defined case study, hypothesis development, and plausibility separately. It correctly identified the Zika reading as a case study, but mostly recited definitions and did not connect the concepts into a student-friendly reasoning chain.
- Score (your own metric, judge-readable): 0.3 / 1.0
- Recorded feedback:

```text
error_type: disconnected_explanation
error_message: Answer gives correct definitions but does not show the evidence chain from case study to hypothesis to plausibility.
feedback: Tie the Zika case back to argument structure. Separate claim, evidence, assumption, and limitation. Use the student's strength in argument structure to explain research-methods vocabulary.
success_score: 0.3
```

Baseline excerpt:

```text
A case study is an in-depth examination of a single instance or event. The Zika microcephaly reading qualifies as a case study because it focuses on one specific outbreak.

Hypothesis development is the process of forming testable predictions based on observations. A hypothesis must be specific and falsifiable.

Plausibility refers to how reasonable or believable a claim is given existing knowledge.
```

### Improved Run

- Query / task: Same Zika case-study question.
- Result: The improved answer explicitly chained the student's course concepts: case study -> evidence -> evidence-based argument -> hypothesis -> plausibility. It anchored the abstract research methods vocabulary to the Zika outbreak and included a personalized "For you specifically" note.
- Score: 0.8 / 1.0
- What changed in the wiki between runs: The `personalized-explainer` skill gained instructions to connect concepts as a reasoning chain, anchor to the Zika example, and use the student's known strength in argument structure.

```text
Before:

# Skill: Personalized Explainer

## Role
You are a helpful study assistant. Answer questions about course material clearly and accurately.

## Instructions
- Define terms clearly before using them
- Use examples from the course readings when available
- Keep answers concise and factual
- Cite the relevant wiki pages at the end

After:

# Skill: Personalized Explainer

## Role
You are a personalized study coach who knows this student's confusion patterns and learning style.

## Student Profile
This student understands argument structure well but struggles to connect case studies to broader analytical concepts. They need concrete evidence chains, not just definitions.

## Instructions
- ALWAYS connect concepts in a chain: case study -> evidence -> hypothesis -> plausibility
- Show the logical structure explicitly with arrows or structured steps
- Anchor abstract concepts to the Zika example the student already encountered
- After defining a concept, show immediately how it appears in the Zika case
- End with "For you specifically:" and tailor the explanation to what this student finds hard
- Cite the relevant wiki pages at the end
```

Improved excerpt:

```text
The Zika reading is a case study because it takes one outbreak - a specific place, time, and population - and extracts every inferential insight from it. Depth over breadth: that is the genre.

Case Study (Zika outbreak, Brazil 2015)
  -> generates rich Evidence (microcephaly spike, geographic correlation)
  -> organized into Evidence-Based Argument
  -> central Hypothesis: "Zika causes microcephaly in fetuses"
  -> Plausibility check: biological mechanism, timing, and geography

For you specifically: you already understand argument structure well. Treat each case study as an argument: case = premise, evidence = support, hypothesis = central claim, plausibility = the opening warrant.
```

## Architecture

```text
[student / agent turns]
        |
        v
[ FastAPI backend ]
        |
        +------------------------------+
        |                              |
        v                              v
[ Redis - session memory ]       [ Cognee - permanent graph ]
 hot, per-conversation            durable, cross-session
 mastery scores                   course pages
 TTL forgetting markers           concept pages
 event streams                    source summaries
 pub/sub decay warnings           bridge pages
        |                          saved study guides
        | distillation             personalized skill memory
        v
[ consolidated concepts + known_as_of timestamps ]
        |
        v
[ recall / agent loop ]
        |
        v
[ user rating -> mastery update -> skill improvement ]
```

### Redis-as-session-memory

- What the agent writes into Redis (raw turns, intermediate observations, ...): Per-session mastery scores, query/rating/ingest events, known-as-of timestamps, concept excerpts, decay keys with TTLs, and decay warning messages.
- How and when content is distilled into the graph: When a concept is reinforced by queries, ratings, saved answers, or bridge pages, it is remembered by Cognee as durable knowledge with session metadata and a known-as-of timestamp.
- What stays in Redis vs. what gets promoted: Redis keeps hot session state: recent events, mastery bars, TTL decay markers, and pub/sub warning events. Cognee stores durable knowledge: course concepts, source memories, student profile, saved guides, bridges, and improved skills.
- How distillation quality improved between baseline and improved run: The baseline answer produced disconnected definitions. The low score recorded a failure pattern. The improved skill then promoted a better structure into future responses: connect research design vocabulary through the student's stronger argument-structure frame.

Redis primitives used:

```text
Sorted sets:
  mastery:<session_id>
  ZADD / ZINCRBY store per-concept mastery scores.
  ZRANGEBYSCORE finds fading concepts below the review threshold.

TTL keys:
  decay:<session_id>:<concept_slug>
  Expiration models forgetting; demo time is accelerated with DEMO_TIME_SCALE.

Streams:
  events:<session_id> or stream:decay:<session_id>
  XADD records ingest, query, rating, save, and decay events.

Pub/sub + SSE:
  events:decay:<session_id>
  Backend publishes decay warnings and the frontend renders a live toast.
```

## Agents / Skills (if any)

```text
Skill path(s):
  my_skills/personalized-explainer/SKILL.md

Roles:
  - Ingestor: backend/ingest.py extracts course/source/concept structure and seeds memory.
  - Querier: backend/query.py searches wiki pages and Cognee memory for answers.
  - Linter: backend/lint.py detects missing concepts, weak bridges, orphaned pages, and fading concepts.
  - Critic: user rating on /rate provides the success_score that drives the improve loop.
  - Improver: backend/improve.py rewrites personalized-explainer instructions and returns a visible diff.
```

Current skill:

```markdown
---
description: Explain course concepts using the student's current context and saved wiki memory.
allowed-tools: memory_search
---

# Personalized Explainer

Use the student's course materials and profile to answer clearly.

When answering:
- Start with the student's question.
- Use relevant course concepts and source pages.
- Connect the answer to the student's stated confusion.
- End with a short study checklist.
```

## Reproduction

Commands to reproduce the demo:

```bash
# Terminal 1: start Redis with keyspace notifications for decay events
docker run -p 6379:6379 redis:latest --notify-keyspace-events KEA

# Terminal 2: backend
cd llm-wiki
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export LLM_API_KEY="<event-provided-key>"
export REDIS_URL="redis://localhost:6379"
export DEMO_TIME_SCALE=100
uvicorn backend.main:app --reload

# Terminal 3: frontend
cd llm-wiki/frontend
npm install
npm run dev
```

Windows PowerShell version:

```powershell
docker run -p 6379:6379 redis:latest --notify-keyspace-events KEA

cd C:\Users\mangh\redis-hack\llm-wiki
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:LLM_API_KEY="<event-provided-key>"
$env:REDIS_URL="redis://localhost:6379"
$env:DEMO_TIME_SCALE="100"
uvicorn backend.main:app --reload

cd C:\Users\mangh\redis-hack\llm-wiki\frontend
npm install
npm run dev
```

Demo flow:

```text
1. Open http://localhost:5173.
2. Ingest the EA51 assets from the Ingest tab.
3. Open Mastery and show Redis-backed mastery bars.
4. Ask the Zika case-study question in Query.
5. Rate the baseline answer 0.3.
6. Click Improve Skill and show the SKILL.md diff.
7. Apply the improvement.
8. Re-ask the same question and show the improved answer.
9. Open Mastery/Lint to show fading concepts and decay warnings.
```

Environment variables required:

```text
LLM_API_KEY
REDIS_URL
DEMO_TIME_SCALE
DEFAULT_SESSION_ID
DECAY_THRESHOLD
COGNEE_TIMEOUT_SECONDS
```

## Demo

- Live demo link (Loom, YouTube, etc.) or local instructions: TODO: add final video link or "Run locally with the commands above."
- 3-minute pitch outline:

```text
1. Problem / idea
   "How many times have you understood something perfectly, then forgotten it three weeks later? Your notes do not know. Your textbooks do not know. StudyAtlas does."

2. Ingest demo
   Ingest EA51 materials and student context. Show generated wiki pages and mastery bars.

3. Query demo (before improvement)
   Ask the Zika case-study question. Show that the baseline answer is correct but generic. Rate it 0.3.

4. Self-improve step
   Click Improve. Show the personalized-explainer SKILL.md diff. Apply the rewrite.

5. Query demo (after improvement)
   Re-ask the same question. Show the answer now chains case study -> evidence -> hypothesis -> plausibility and tailors the explanation to the student's argument-structure strength.

6. What is next
   Show Redis decay: a mastery bar drops below 40%, the decay toast fires, and lint flags the fading concept as review-worthy.
```

## Links

- Repo: TODO: add GitHub repository URL
- Slides / writeup: `Redis_Cognee_Hackathon.pptx`
- Anything else:
  - Main README: `README.md`
  - Project plan: `courseatlas_project_plan.md`
  - Backend API: `backend/main.py`
  - Frontend app: `frontend/src/App.jsx`
  - Skill: `my_skills/personalized-explainer/SKILL.md`
