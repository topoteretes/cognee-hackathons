# Team Submission

## Team

- Team name: MediMind
- Participants: Bhoomika Ganapuram, Nirvisha Sriram
- Wiki / project name: MediMind — Personal Health Memory Agent

## Wiki Overview

MediMind is a personal health wiki that ingests doctor notes, medication lists, and lab results, then organizes, cross-references, and safety-checks everything automatically. It catches dangerous drug interactions (like prescribing amoxicillin to a penicillin-allergic patient), flags outdated information, fills knowledge gaps, and gets smarter every time the user updates their health data. The self-improvement loop rewrites the AI's own skill instructions based on accumulated corrections — the advisor literally learns to check drug families for allergy cross-reactivity after a user flags a missed interaction.

- Domain or data sources: Medical records, doctor visit notes, medication lists, lab results, patient-reported symptoms
- Primary use case: Patients and caregivers managing complex medication regimens across multiple doctors
- What makes it stand out: Applied to healthcare where wiki errors can be fatal. The linter catches life-threatening contradictions (allergy vs prescription). Query answers get filed back into the wiki as safety notes — knowledge compounds with every interaction.

## The Three Operations

### Ingest

- What goes in: Doctor visit summaries, medication lists, lab results, patient-reported symptoms and updates
- How it is captured: `cognee.remember(text)` for permanent graph storage, `cognee.remember(text, session_id=...)` for Redis session cache. OpenAI GPT-4o-mini extracts structured health entities (medications, conditions, symptoms, allergies, lab values) with connections between them. New data updates existing entries if they match (e.g. dosage change), rather than duplicating.
- Code entry point: `wiki/ingester.py` — `ingest_health_text()`

### Query + Self-improve

- How users query the wiki: Chat interface — ask natural language health questions ("Can I take ibuprofen with my current meds?")
- Where feedback comes from: User corrections ("My doctor changed my dosage"), safety warnings auto-filed back into wiki as new entries (Karpathy pattern — wiki grows from queries)
- How feedback updates the wiki: Corrections feed into `SkillRunEntry` → propose skill rewrite → `improve_skill(apply=True)` rewrites SKILL.md files on disk, then re-ingests into Cognee graph. Falls back to LLM-generated improvement if native API unavailable.
- Code entry point: `wiki/advisor.py` — `ask_medimind()`, `wiki/skills.py` — `propose_improvement()` / `apply_improvement()`

### Lint

- What "linting" means in your wiki: Catch contradictions (penicillin allergy + amoxicillin prescription), flag outdated info (old dosages after doctor changed them), remove redundant entries, fill important gaps (condition without treatment), assess completeness
- How it runs: On-demand via UI ("Run Audit" or "Auto-Fix & Fill Gaps")
- Code entry point: `wiki/linter.py` — `lint_wiki()`, `auto_lint_and_improve()`

## Self-Improvement Evidence

### Baseline Run

- Query / task: "Can I take ibuprofen for my knee pain?"
- Result: Identified ibuprofen + Lisinopril interaction and kidney risk, but did not proactively check drug families for allergy cross-reactivity
- Score: 0.7
- Recorded feedback:

```text
error_type: missed_check
error_message: Did not proactively check if ibuprofen has cross-reactivity with any listed allergies
feedback: Always check drug FAMILIES for allergy cross-reactivity, not just exact drug names
success_score: 0.7
```

### Improved Run

- Query / task: "My neighbor offered me Amoxicillin for my sinus infection. Is it safe?"
- Result: Immediately flagged Amoxicillin as penicillin-family antibiotic, cross-referenced with severe penicillin allergy (throat swelling). Marked as life-threatening risk.
- Score: 0.95
- What changed in the wiki between runs:

```text
Before (health-advisor SKILL.md v1):
"Flag potential drug interactions proactively."

After (health-advisor SKILL.md v2):
"Check drug FAMILIES for allergy cross-reactivity (e.g., penicillin family includes amoxicillin, ampicillin). Flag sedating medications for elderly patients living alone (fall risk)."
```

## Architecture

```text
User pastes doctor notes / asks question
        |
        v
[ Redis — session memory ]         <- per-conversation cache
  - Active medication index           sub-ms lookups
  - Session Q&A history               contextual follow-ups
  - Raw health data cache
        |
        | distillation (cognee.remember without session_id)
        v
[ Cognee — permanent graph ]       <- durable, cross-session
  - Health entities & relationships
  - Skill files (SKILL.md)
  - Cross-session knowledge
        |
        v
[ Query pipeline ]
  1. Redis session context (fast)
  2. Cognee graph context (deep)
  3. Wiki profile (structured)
  4. Evolving skill instructions
        |
        v
[ Answer + safety warnings ]
  - Warnings filed back as wiki entries
  - Corrections feed skill improvement
        |
        v
[ SkillRunEntry → improve_skill ]
  - Propose SKILL.md rewrite
  - Apply → skills v1 → v2 → v3
```

### Redis-as-session-memory

- What the agent writes into Redis: Health entry cache (medications, conditions, allergies indexed by category), session Q&A history, raw ingested text
- How and when content is distilled into the graph: `cognee.remember(text)` (no session_id) stores permanently after each ingestion and query cycle
- What stays in Redis vs. what gets promoted: Redis keeps hot session data (TTL 24h) for fast lookups. Structured health knowledge and skill improvements get promoted to the permanent graph.
- How distillation quality improved: After skill v1→v2 upgrade, the advisor now promotes drug-family cross-reactivity checks and elderly-living-alone risk flags into its reasoning — these were missed in v1.

## Agents / Skills

Skill path(s): my_skills/
Roles:
  - health-advisor: Cross-references full health profile to answer questions, flags interactions
  - safety-checker: Drug interaction scanner, allergy cross-reactivity, contraindication checker
  - wiki-linter: Contradiction detector, gap filler, redundancy pruner, completeness auditor


## Reproduction

```bash
cd teams/medimind
pip install "cognee[redis]" streamlit openai redis python-dotenv nest_asyncio
redis-server --daemonize yes
export LLM_API_KEY="<your-key>"
export REDIS_URL=redis://localhost:6379
streamlit run app.py
```

Environment variables required:

LLM_API_KEY (or OPENAI_API_KEY)
REDIS_URL=redis://localhost:6379

## Demo

- Live demo link: https://escalator-remold-kangaroo.ngrok-free.dev
- 3-minute pitch outline:

1. Problem: 3M deaths/year from unsafe care. Half of preventable harm is medication-related. Health data scattered across systems.
2. Ingest: Paste doctor notes → extracts 20+ structured health entries into wiki
3. Query: "Can I take ibuprofen?" → catches drug interaction + kidney risk. Safety notes filed back into wiki.
4. Lint: Add Amoxicillin → linter catches penicillin allergy contradiction. Auto-fills gaps.
5. Self-improve: Propose → Apply → advisor skill v1→v2, now checks drug families for allergy cross-reactivity
6. Vision: Connect to real EHR/pharmacy data. 53M unpaid caregivers need this. This is the company we want to build.

## Links

- Repo: https://github.com/bganapuram-spec/cognee-hackathons
- Live app: https://escalator-remold-kangaroo.ngrok-free.dev
- Built with: Cognee + Redis + OpenAI GPT-4o-mini + Streamlit
