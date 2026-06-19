# Team Submission

## Team

- Team name: **Adverra Brain**
- Participants:
  - **Mert Gökçe** — Data Engineer
  - **Ahmet Sevim** — Agent Orchestrator
- Company Brain / project name: **Adverra Brain**

## Company Brain Overview

Adverra Brain is a self-improving support brain for the (imaginary)
user-acquisition company **Adverra** and its consumer rewarded-earnings product
**Cashly**. We ingest the company's scattered knowledge (help-center articles,
product pages, FAQ, meeting notes) into a Cognee knowledge graph — Karpathy's
"LLM wiki" — and expose it as a **Slack support agent**. The agent answers
questions with cited sources, **escalates to a human expert when it doesn't
know**, and **learns from the expert's correction** so the same question is
answered automatically for everyone afterwards.

- Domain or data sources: Cashly help center (withdrawals/PayPal), Cashly &
  Adverra product pages, payments FAQ, internal support meeting notes.
- Primary use case: an internal/customer support agent in Slack that never
  hallucinates — it answers from documented knowledge or routes to a human.
- What makes it stand out: a closed human-in-the-loop self-improvement loop run
  *inside Slack* — one expert's 👎 + correction updates the durable graph **and**
  rewrites the answerer skill (propose → apply), and the learning is immediately
  visible to other users in new conversations.

## The Three Operations

### Ingest

- What goes in: 5 help-center articles, 2 product pages, a payments FAQ, and a
  support meeting-notes file, plus 3 skills (ingestor / qa-answerer / linter).
- How it is captured: `cognee.remember(text, dataset_name=...)` for raw sources
  (permanent graph) and `cognee.remember(SKILLS_DIR, content_type="skills")` for
  skills.
- Code entry point: [`src/ingest.py`](./src/ingest.py)

### Query + Self-improve

- How users query: `@mention` the Slack bot in a channel. The bot runs
  `cognee.search(query_type=AGENTIC_COMPLETION, datasets=[...], skills=
  ["qa-answerer"], session_id=thread_ts)`.
- Where feedback comes from: the responsible human expert, tagged on every
  answer, reacts 👍 / 👎 and replies in-thread with the correct answer.
- How feedback updates the brain: on 👎 + a threaded correction we
  `cognee.remember(correction)` into the permanent graph **and** log a
  `SkillRunEntry` (low score) which proposes a `qa-answerer` rewrite that we then
  apply via `improve_skill(..., apply=True)`. 👍 logs a positive `SkillRunEntry`.
- Code entry point: [`src/query.py`](./src/query.py),
  [`src/feedback.py`](./src/feedback.py), [`src/slack_app.py`](./src/slack_app.py)

### Lint

- What "linting" means: find duplicate facts, conflicting numbers/policies,
  stale entries tied to deprecated systems (e.g. the legacy "Tango" PayPal
  processor noted in the meeting notes), and coverage gaps.
- How it runs: on-demand, via the linter skill.
- Code entry point: [`src/lint.py`](./src/lint.py),
  [`my_skills/linter/SKILL.md`](./my_skills/linter/SKILL.md)

## Self-Improvement Evidence

### Baseline Run

- Query / task: "What is Cashly's referral bonus program?"
- Result: `ESCALATE: Company Brain contains no information about Cashly's
  referral bonus program.` → bot tags the responsible expert.
- Score (our metric): 0.2 (no grounded answer available).
- Recorded feedback:

```text
error_type: missing_knowledge
error_message: Brain has no documented referral program facts.
feedback: -1.0
success_score: 0.2
```

### Improved Run

- Query / task: "What is Cashly's referral bonus program?" (asked by a different
  user, in a new thread / new session).
- Result: "Cashly's referral program: both the referrer and the new user receive
  a $5 bonus after the new user completes their first withdrawal; referrals are
  limited to 20 per month."
- Score: ~0.95 (grounded, specific, matches the expert's correction).
- What changed in the brain between runs: the expert's correction was distilled
  into the permanent graph (no `session_id`), and a `qa-answerer` skill
  improvement proposal was generated and applied.

```text
Before:
  Q: What is Cashly's referral bonus program?
  A: ESCALATE: Company Brain contains no information about Cashly's referral
     bonus program.  (-> tags @expert)

After (new user, new session):
  Q: What is Cashly's referral bonus program?
  A: Both the referrer and the new user receive a $5 bonus after the new user
     completes their first withdrawal; limit 20 referrals per month.
```

## Architecture

```text
[ Slack @mention / expert turns ]
        |
        v
[ session memory ]  <- per-thread working memory (session_id = Slack thread ts)
        |
        | distillation: expert-verified corrections are remembered WITHOUT a
        | session_id, promoting them from a conversation into durable knowledge
        v
[ permanent graph ]  <- durable, cross-session, cross-user knowledge (the wiki)
        |
        v
[ recall: AGENTIC_COMPLETION + qa-answerer skill ]
        |
        v
[ feedback: 👎 + correction -> remember + SkillRunEntry -> improve_skill ]
```

Components:
- **Ingest** — `src/ingest.py` builds the graph from `raw/`.
- **Agent** — `src/slack_app.py` (Slack Bolt, Socket Mode) + `src/query.py`.
- **Self-improvement** — `src/feedback.py`.
- **Lint** — `src/lint.py`.
- **Skills** — `my_skills/{ingestor,qa-answerer,linter}/SKILL.md`.

### Cognee Cloud (optional, rewarded)

We built local-first. `src/push_to_cloud.py` pushes the locally-built brain to a
managed Cognee Cloud instance with `cognee.serve(...)` + `cognee.push(...)`
(set `COGNEE_CLOUD_URL` / `COGNEE_API_KEY`). The same two-tier split applies in
the Cloud instance:

- Session memory (`session_id = Slack thread ts`): the per-conversation
  scratchpad — the user's question and the agent's working memory for that thread.
- Permanent graph (no `session_id`): expert-verified corrections and all
  ingested company knowledge — durable and shared across users/sessions.
- Distillation trigger: an expert 👎 + threaded correction promotes a fact from
  the conversation into the permanent graph; a `SkillRunEntry` improves the skill.
- Stays session-only: the raw per-thread Q&A turns; promoted: the verified fact.

## Agents / Skills

```text
Skill path(s): my_skills/{ingestor,qa-answerer,linter}/SKILL.md
Roles:
  - Ingestor:  extract entities/facts/relationships from raw sources
  - Querier:   qa-answerer — answer from the brain with citations, or ESCALATE
  - Linter:    dedupe / conflict-resolve / flag stale (e.g. legacy Tango)
  - Critic:    the human expert in Slack (👍 / 👎 + correction)
```

## Reproduction

```bash
uv venv --python python3.13 && source .venv/bin/activate
uv pip install -r requirements.txt
cp .env.example .env            # add LLM_API_KEY + Slack tokens + RESPONSIBLE_PERSON

python -m src.ingest            # build the wiki from raw/
python -m src.query "What is the PayPal withdrawal fee and limits?"
python -m src.slack_app         # start the Slack agent (Socket Mode)
python -m src.lint              # coherence check
python -m src.push_to_cloud     # optional: push to Cognee Cloud (bonus)
```

Environment variables required:

```text
LLM_API_KEY                 # OpenAI (gpt-4o-mini) or any cognee-supported provider
COGNEE_SKIP_CONNECTION_TEST # =true (bypass a flaky 30s preflight check)
SLACK_BOT_TOKEN             # xoxb-... (OAuth & Permissions)
SLACK_APP_TOKEN             # xapp-... (Socket Mode app-level token)
RESPONSIBLE_PERSON          # Slack user id of the human expert to tag (U...)
COGNEE_CLOUD_URL            # optional, for the Cloud bonus
COGNEE_API_KEY             # optional, for the Cloud bonus (ck_...)
```

## Demo

- Local instructions: run `python -m src.slack_app`, then `@mention` the bot in
  Slack. Screenshots of the live before/after are included with the submission.
- 3-minute pitch outline:

```text
1. Problem / idea — support agents hallucinate; we want a brain that answers from
   documented knowledge, defers to a human otherwise, and learns from the human.
2. Ingest demo — raw/ help center + product + FAQ -> Cognee graph.
3. Query (before) — PayPal fee question -> correct, cited answer; referral
   question -> ESCALATE + tag the expert.
4. Self-improve — expert 👎 + posts the correct referral terms -> brain remembers
   it + a qa-answerer skill rewrite is proposed and applied.
5. Query (after) — a different user asks the same question in a new thread ->
   the learned answer is returned.
6. What's next — scheduled lint, multi-channel routing, cognee.push to Cloud.
```

## Links

- Repo: this folder — `cognee-cloud-hackathon-2026-06-19/teams/adverra-brain/`
- Slides / writeup: this `SUBMISSION.md` + the project `README.md`
- Anything else: built with cognee `1.2.0.dev1`, Slack Bolt (Socket Mode),
  OpenAI `gpt-4o-mini`.
