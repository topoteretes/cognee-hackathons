# Team Submission

## Team

- Team name: Redline
- Participants: Victor Wong
- Wiki / project name: Redline

## Wiki Overview

Redline is a living security wiki that acts as a safety layer between coding agents and the code they produce. It solves a real problem: coding agents (Claude, Codex, Copilot) routinely introduce SQL injection, hardcoded secrets, missing auth checks, and other vulnerabilities because they have no persistent memory of security rules. Redline gives them one.

The wiki currently holds **12 safety rules**, **13 observed violations**, **13 regression tests**, and **4 agent-discovered findings** -- and it grew from 10 seeded rules to 12 entirely through the self-improvement loop described below. Two rules (`learned_open_redirect_001` and `learned_csv_formula_injection_001`) were created automatically when agents discovered risks the wiki didn't yet cover.

- **Domain / data sources:** OWASP-sourced Markdown security notes in `raw_sources/`, generated structured wiki entries in `wiki/` (JSON + Markdown), agent-submitted findings, accepted preflight violations, regression tests, and user feedback.
- **Primary use case:** prevent coding agents from introducing known security flaws before code is finalized -- and learn from novel flaws so they are never missed again.
- **What makes it stand out:** Redline is not a static rule list. It is a closed-loop system: agents query the wiki before writing code, the wiki checks their output, agents report novel risks back, and the wiki automatically generates new durable rules from those reports. It operates as both a fully local deterministic system and a connected memory system using Redis (hot session memory, vector search, fingerprints) and Cognee (durable cross-session knowledge graph).

## The Three Operations

### 1. Ingest

**What goes in:** Trusted Markdown security notes, user-ingested rules via the UI, accepted preflight violations with safe rewrites, regression test seeds, and novel agent-discovered security findings.

**How it is captured -- step by step:**

1. **UI/API ingest** (`POST /ingest`): User submits a title, source, and rule text. `backend/app/rule_store.py → extract_rule_from_ingest()` normalizes the text into a structured `SafetyRule` with id, title, category, severity, rule_text, unsafe_patterns, and safe_patterns. The rule is written as both JSON and Markdown to `wiki/safety_rules/`.

2. **Redis hot memory**: The rule is stored via `RedisMemoryAdapter.remember_rule()` which (a) writes the rule document to `rule:{id}`, and (b) builds a vector-embedded memory document at `memory:rule:{id}` using a 128-dimension hash embedding for RediSearch vector similarity.

3. **Cognee durable memory**: `MemoryAdapter.remember_durable("safety_rule", ...)` calls `cognee.add()` with the rule payload and then `cognee.cognify()` to integrate it into the persistent knowledge graph.

4. **Agent-discovered findings** (`POST /agent/finding` or `scripts/redline_finding.py`): When an agent encounters a security issue not covered by the wiki, it calls the finding endpoint. The system first **deduplicates** by searching both Redis vector memory and local `wiki/agent_findings/*.json` using token-overlap scoring with a 0.74 similarity threshold. If no prior match exists, it (a) writes the finding to `wiki/agent_findings/`, (b) checks if the finding category matches a `LearnedRuleTemplate` in `backend/app/learned_rules.py`, and if so (c) **automatically generates a new safety rule** and writes it to `wiki/safety_rules/`. This is how `learned_open_redirect_001` and `learned_csv_formula_injection_001` were created.

5. **Accepted rewrites** (`POST /accept-rewrite`): When a user accepts a safe rewrite from a preflight catch, Redline writes both an observed violation to `wiki/observed_violations/` and a regression test to `wiki/regression_tests/`, plus creates a Redis fingerprint so the same pattern triggers an instant fast-path block on future encounters.

**Code entry points:** `backend/app/main.py` routes `/ingest`, `/accept-rewrite`, `/agent/finding`; rule persistence in `backend/app/rule_store.py`; wiki file writes in `backend/app/wiki_writer.py`; learned rule templates in `backend/app/learned_rules.py`.

### 2. Query + Self-Improve

**How agents query the wiki -- the complete retrieval flow:**

1. Before writing any code, the agent runs `scripts/redline_context.py "<task description>"`. This script calls `POST /agent/context` (or falls back to local wiki retrieval if the backend is unavailable).

2. **Rule scoring**: Every rule in `wiki/safety_rules/*.json` is scored against the task description using two signals: (a) **risk-type hint matching** -- if the task mentions SQL keywords, the SQL injection rule gets +8 points; (b) **term overlap** -- each 4+ character token in the task is checked against the rule's title, category, rule_text, unsafe_patterns, and safe_patterns. Rules are ranked by score, then severity, then title.

3. **Top-K retrieval**: The top 5 rules are returned. If fewer than 3 rules scored above zero, high-severity baseline rules (critical/high) are included as safety padding.

4. **Redis vector recall**: In parallel, `RedisMemoryAdapter.search_similar()` runs a KNN vector search on the `idx:safety_memories` RediSearch index to find similar prior violations, findings, and regression tests from memory.

5. **The agent receives** each rule's id, title, severity, category, source, rule_text, unsafe_patterns, safe_patterns, and a `why_relevant` explanation. It uses this context while coding.

**After writing code, the agent runs preflight:**

1. `scripts/redline_preflight.py --diff` reads the current `git diff`, strips test/doc files, and sends only production-code additions to `POST /preflight`.

2. **Redis Reflex Memory (fast path)**: Before running any detectors, the system checks if the content matches a stored fingerprint. Fingerprints are keyed by risk type + language + pattern (e.g., `sql_injection:python:string_interpolated_sql`). If a fingerprint matches, the preflight immediately returns `REDLINE TRIGGERED` without detector execution -- this is how Redline gets faster over time.

3. **Deterministic detectors** (`backend/app/detectors.py`): Five dedicated detectors run in sequence:
   - `detect_sql_injection`: 4 regex patterns catching f-string interpolation, concatenation, `.format()`, and template literal injection in SQL
   - `detect_prompt_injection`: 9 phrase patterns for instruction-override attempts in untrusted content
   - `detect_secrets`: 6 regex patterns for private keys, API keys (sk-*, ghp_*), hardcoded credentials, connection strings, and bearer tokens
   - `detect_unsafe_execution`: 5 patterns for eval(), exec(), shell=True, child_process.exec, and destructive commands
   - `detect_missing_authorization`: heuristic checking if routes touch user-owned resources without auth middleware

4. **Semantic memory enrichment**: Even if detectors pass, Redis vector search can upgrade a PASS to WARNING if a high-risk similar memory (score >= 0.75) is found -- preventing near-miss escapes.

5. **Verdicts**: `REDLINE TRIGGERED` (must fix), `WARNING` (explain or fix), `NEEDS HUMAN REVIEW`, or `PASS`. Each verdict includes matched rules, evidence with line numbers and snippets, an explanation, and a safe rewrite suggestion.

**How feedback drives self-improvement:**

- **Low-score feedback** (score < 0.5 via `POST /feedback`): Creates an `ImprovementProposal` that can be applied through `/feedback/{id}/apply-improvement`, updating Cognee's knowledge graph via `cognee.add()` + `cognee.cognify()`.
- **Novel agent findings**: When an agent discovers a risk category the wiki doesn't cover (open redirect, SSRF, mass assignment, CSV formula injection), `redline_finding.py` logs the finding AND generates a learned rule if the category matches a `LearnedRuleTemplate`. The templates contain OWASP-sourced rules with unsafe patterns, safe patterns, source URLs, and severity levels.
- **Accepted rewrites**: Each accepted rewrite creates an observed violation + regression test, strengthening the wiki's coverage for that exact attack pattern.

**Code entry points:** `backend/app/main.py` routes `/agent/context`, `/preflight`, `/feedback`, `/feedback/{id}/apply-improvement`, `/agent/finding`; context retrieval in `_agent_rule_contexts()`; detector pipeline in `backend/app/detectors.py`; learned rules in `backend/app/learned_rules.py`; rewrite suggestions in `backend/app/rewrite.py`.

### 3. Lint

**What linting means for Redline's wiki:** The wiki is a living knowledge base that grows through multiple channels (ingest, agent findings, learned rules, accepted rewrites). Without hygiene, it accumulates duplicates, contradictions, and stale state. The lint operation keeps the wiki trustworthy.

**Three concrete lint checks:**

1. **Duplicate detection**: Iterates every `wiki/safety_rules/*.json`, normalizes each rule's `title + rule_text` to lowercase, and hashes the result. If two rules produce the same hash, a `duplicates` finding is emitted referencing both file paths. This prevents the wiki from growing noisy with redundant rules.

2. **Severity conflict detection**: Groups rules by risk type (extracted from rule ID or category). If two rules for the same risk type (e.g., `sql_injection`) declare different severities, a `conflicts` finding is emitted. This catches inconsistencies that would confuse agents about how serious a risk is.

3. **Stale memory detection**: Queries Redis Streams (`stream:redline_events`) for recent events. If no events exist, a `stale` finding warns that live memory has gone cold and a preflight should be run to refresh it. This ensures the hot memory layer stays active.

**How it runs:** On demand via `POST /lint` from the UI or API, with `dry_run` support so you can preview issues without applying changes. The response includes a summary count of duplicates, conflicts, and stale findings, plus the overall status (`PASS` or `WARNING`).

**Code entry point:** `backend/app/main.py` route `/lint` and helper `_lint_wiki()` (lines 897-964).

## Self-Improvement Evidence

### Baseline Run (Before)

- **Task:** "Add a post-login redirect helper that reads `next` from the query string and redirects there."
- **What happened:** Redline had 10 seeded rules covering SQL injection, prompt injection, secrets management, unsafe execution, authorization, XSS, input validation, least privilege, hallucination risk, dependency risk, and unsafe output handling. None of them covered open redirects. The agent context retrieval returned baseline rules, but none were specifically relevant to the redirect task.
- **Agent action:** The coding agent recognized the gap, called `scripts/redline_finding.py` with title "Open redirect risk in post-login redirect helper", description about the missing same-origin validation, and evidence about the `next` query parameter. The system searched existing findings (0 matches above threshold), logged `finding_99e9ffc827d0` to `wiki/agent_findings/`, and automatically generated `learned_open_redirect_001` from the OWASP Unvalidated Redirects template.
- **Coverage score:** 0.35 -- the wiki flagged the issue as `NEEDS HUMAN REVIEW` but lacked a durable rule to proactively prevent it.
- **Recorded feedback:**

```text
error_type: missing_rule
error_message: User-controlled redirect target was not represented by a seeded rule.
feedback: Add durable guidance for open redirects and same-origin/allowlist validation.
success_score: 0.35
```

### Improved Run (After)

- **Task:** Same -- "Add a post-login redirect helper that reads `next` from the query string and redirects there."
- **What happened:** The wiki now contains `learned_open_redirect_001` (sourced from OWASP Unvalidated Redirects and Forwards Cheat Sheet). When the agent runs `redline_context.py` with this task, the scoring system matches "redirect" against the rule's title, unsafe patterns ("redirects directly to a next, returnUrl, redirect, or url parameter"), and safe patterns ("Allow only relative same-origin paths"). The rule scores high and is returned in the top results.
- **Coverage score:** 0.85 -- the agent now receives explicit guidance about unsafe redirect patterns and safe alternatives before writing any code.
- **Concrete wiki diff:**

```text
FILES ADDED (by the self-improvement loop, not by a human):
+ wiki/agent_findings/finding_99e9ffc827d0.json   (novel finding record)
+ wiki/agent_findings/finding_99e9ffc827d0.md      (human-readable finding)
+ wiki/safety_rules/learned_open_redirect_001.json (auto-generated learned rule)
+ wiki/safety_rules/learned_open_redirect_001.md   (human-readable rule)

RULE CONTENT (generated from LearnedRuleTemplate, not hand-written):
  id: learned_open_redirect_001
  title: "Open Redirect: Validate Redirect Targets"
  source: OWASP Unvalidated Redirects and Forwards Cheat Sheet
  severity: medium
  unsafe_patterns:
    - "Login/logout/invite route redirects directly to a next/returnUrl/redirect parameter"
    - "Redirect target accepts absolute external URLs without validation"
    - "Redirect validation checks string prefixes instead of parsing origin"
  safe_patterns:
    - "Prefer fixed server-side redirect destinations for sensitive flows"
    - "Allow only relative same-origin paths"
    - "Validate external redirect targets against an explicit allowlist"
    - "Fall back to a safe default route when validation fails"
```

### Second Self-Improvement Example: CSV Formula Injection

The same loop repeated independently for CSV formula injection:

1. Agent encountered a CSV export route writing untrusted customer notes directly to cells.
2. Called `redline_finding.py` → logged `finding_ce17aa87902b` → auto-generated `learned_csv_formula_injection_001` from the OWASP CSV Injection template.
3. Wiki grew from 11 to 12 safety rules. Future agents querying about CSV exports now receive proactive guidance about formula-cell neutralization.

### Third Self-Improvement Example: SSRF

1. Agent encountered a URL preview endpoint calling `httpx.get(url)` with raw user input.
2. Logged `finding_68cdc4cb615d` with full affected code and a safe rewrite (scheme validation + host allowlist + disabled redirects).
3. Finding was matched to existing rule `raw_input_validation_001` and includes a concrete before/after code example in the wiki.

## Architecture

```text
┌─────────────────────────────────────────────────────────┐
│  CODING AGENT (Claude, Codex, Copilot, etc.)            │
│                                                         │
│  1. redline_context.py "task"  → GET safety rules       │
│  2. agent writes code                                   │
│  3. redline_preflight.py --diff → CHECK proposed code   │
│  4. redline_finding.py → REPORT novel risks             │
└──────────┬──────────────────┬──────────────────┬────────┘
           │                  │                  │
           v                  v                  v
┌──────────────────────────────────────────────────────────┐
│  FastAPI Backend (backend/app/main.py)                   │
│                                                          │
│  /agent/context  - ranked rule retrieval + vector recall  │
│  /preflight      - fingerprint → detectors → enrichment  │
│  /agent/finding  - dedupe → log → auto-generate rule     │
│  /ingest         - parse → store → mirror to memory      │
│  /accept-rewrite - violation + regression + fingerprint  │
│  /feedback       - score → propose improvement           │
│  /lint           - dedupe + conflicts + stale checks     │
│  /wiki/recent    - recently added entries for UI         │
└──────────┬──────────────────┬──────────────────┬────────┘
           │                  │                  │
           v                  v                  v
┌─────────────────┐  ┌──────────────────┐  ┌──────────────┐
│  Local Wiki     │  │  Redis Stack     │  │  Cognee      │
│  (file-backed)  │  │  (hot memory)    │  │  (durable)   │
│                 │  │                  │  │              │
│  12 safety rules│  │  RedisJSON docs  │  │  cognee.add  │
│  13 violations  │  │  RediSearch idx  │  │  cognee.     │
│  13 reg. tests  │  │  Vector KNN      │  │    cognify   │
│  4 findings     │  │  Streams events  │  │  cognee.     │
│                 │  │  Fingerprints    │  │    search    │
│  JSON + MD      │  │  Session TTL     │  │  Graph store │
└─────────────────┘  └──────────────────┘  └──────────────┘
```

### Redis-as-Session-Memory (Sponsor Memory)

- **What the agent writes into Redis:** Rule documents, vector-embedded safety memories (rules, violations, findings, regressions), preflight results, session event histories, fingerprints keyed by `risk_type:language:pattern`, and trace events streamed to `stream:redline_events`.
- **RediSearch vector index:** `idx:safety_memories` indexes all `memory:*` JSON documents with HNSW vector similarity (128-dim, cosine distance) plus TAG fields for kind, risk_type, severity, and TEXT fields for title/content. This enables KNN recall queries like "find the 5 most similar prior safety memories for this code snippet."
- **Redis Reflex Memory (fingerprints):** When a preflight catches unsafe code, the system generates a fingerprint (e.g., `sql_injection:python:string_interpolated_sql`) and stores it. On subsequent preflights, fingerprint lookup runs **before** detectors, providing an instant fast-path block. Fingerprints track `count`, `first_seen`, `last_seen`, and linked violation/preflight IDs.
- **What stays in Redis vs. what gets promoted:** Redis keeps ephemeral session context (24h TTL), per-preflight results (5min TTL), vector embeddings for similarity search, and fingerprints for fast-path detection. Cognee/wiki receive durable rules, findings, violations, regression tests, and feedback that persist across sessions.
- **Distillation improvement:** In the baseline run, the open-redirect issue existed only as a Redis trace event. After the self-improvement loop, it was promoted to a durable wiki rule with OWASP source attribution, structured unsafe/safe patterns, and a severity rating -- recalled in every future agent session.

## Agents / Skills

Redline integrates with coding agents through three CLI scripts that are wired into agent instructions (via `CLAUDE.md` / `AGENTS.md`):

```text
scripts/redline_context.py "<task>"
  → Calls POST /agent/context (or local fallback)
  → Returns ranked safety rules + similar memories
  → Agent uses these as security context while coding

scripts/redline_preflight.py --diff
  → Reads git diff, filters to production code
  → Calls POST /preflight (or local fallback)
  → Returns PASS / WARNING / REDLINE TRIGGERED + evidence + safe rewrite
  → Agent must fix TRIGGERED results before finalizing

scripts/redline_finding.py --title "..." --description "..."
  → Calls POST /agent/finding (or local fallback)
  → Dedupes against existing findings (similarity >= 0.74)
  → Logs novel findings + auto-generates learned rules
  → Wiki grows autonomously from agent discoveries
```

The backend exposes four functional roles:
- **Ingestor** (`/ingest`): converts trusted source notes into structured wiki safety rules.
- **Querier** (`/agent/context`, `/memory/recall`): retrieves relevant rules and similar memories before coding.
- **Critic** (`/preflight`, `/agent/finding`, `/feedback`): detects issues, logs novel risks, and collects feedback.
- **Linter** (`/lint`): checks wiki health -- duplicates, severity conflicts, and stale memory.

## Reproduction

```bash
# Terminal 1: sponsor memory (Redis Stack with JSON, Search, Streams)
docker run --rm --name redline-redis-stack \
  -p 6379:6379 -p 8001:8001 \
  redis/redis-stack:latest

# Terminal 2: backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host localhost --reload

# Terminal 3: frontend
cd frontend
npm install && npm run dev
```

**Try the full agent loop:**

```bash
# 1. QUERY: retrieve safety context for a SQL task
python3 scripts/redline_context.py "implement a SQL-backed user lookup"

# 2. PREFLIGHT: check unsafe code
python3 scripts/redline_preflight.py \
  --content 'query = f"SELECT * FROM users WHERE email = {email}"'
# → REDLINE TRIGGERED, severity: critical, safe_rewrite: "Use parameterized query"

# 3. SELF-IMPROVE: report a novel finding the wiki doesn't cover
python3 scripts/redline_finding.py \
  --title "Open redirect risk in post-login redirect helper" \
  --description "The route redirects to a user-controlled next URL without same-origin validation." \
  --evidence "/api/login/complete reads next from query string and redirects directly." \
  --category open_redirect
# → LOGGED_NEW_FINDING, auto-generated learned_open_redirect_001

# 4. QUERY AGAIN: verify the wiki learned
python3 scripts/redline_context.py "add a post-login redirect helper"
# → Now returns learned_open_redirect_001 in the top results

# 5. LINT: check wiki health
curl -X POST http://localhost:8000/lint -H 'Content-Type: application/json' -d '{}'
```

**Environment variables:**a

```text
REDIS_URL=redis://localhost:6379/0          # Redis Stack connection
COGNEE_ENABLED=true                         # Enable Cognee durable memory
COGNEE_DATASET=redline-hackathon            # Cognee dataset name
COGNEE_SESSION_PREFIX=redline               # Session scoping prefix
REDLINE_REQUIRE_SPONSOR_MEMORY=true         # Require Redis+Cognee for full demo
LLM_PROVIDER=openai                         # Cognee LLM provider
LLM_MODEL=gpt-4o-mini                       # Cognee LLM model
LLM_API_KEY=<your key>                      # Required for Cognee graph operations
```

## Demo

- **Live app:** Run backend + frontend, then open `http://localhost:5173`. Redis Insight at `http://localhost:8001`.
- **3-minute pitch:**

```

## Links

- **Repo:** https://github.com/VictorWong123/llm-wiki
- **Docs:** project PDFs in `docs/`
- **Local app:** `http://localhost:5173`
- **Recently Added (learning evidence):** `http://localhost:5173/recently-added`
