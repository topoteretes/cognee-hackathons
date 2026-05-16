# Team Submission

## Team

- Team name: Personalized Business Wiki
- Participants: Mina / Codex
- Wiki / project name: Personalized Wiki for Juniper & Finch Coffee

## Wiki Overview

Personalized Wiki for Juniper & Finch Coffee builds a user-specific wiki for a fictional neighborhood cafe. The user edits one text box with profile/preferences, then clicks `Generate Wiki`. The backend parses that current text into atomic facts, retrieves relevant review evidence from Redis, writes the current generation turn into Redis session memory, distills the generation bundle into Cognee permanent memory, and uses a stateless LLM to generate a Markdown wiki.

- Domain or data sources: synthetic cafe reviews, official cafe facts, neighborhood/logistics notes, user profile text, generated wiki runs.
- Primary use case: help a customer understand whether a small business fits their exact preferences and constraints.
- What makes it stand out: the same business produces a different wiki when user facts change, and the same user produces a different wiki when fresh relevant reviews are added.

## The Three Operations

### Ingest

- What goes in: 420 synthetic reviews, newly added review text, user profile text, parsed facts, retrieved evidence, conflict notes, generated wiki text.
- How it is captured: reviews are stored under `pbw:review:*` Redis hashes; each generation writes `pbw:session:<session_id>` Redis session memory; generated artifacts are added to Cognee with `cognee.add(...)` and `cognee.cognify(...)`.
- Code entry point: `server.py` -> `ReviewIndex.index`, `ReviewIndex.write_session_memory`, `remember_with_cognee`.

### Query + Self-improve

- How users query the wiki: edit `User Info`, click `Generate Wiki`.
- Where feedback comes from: the current user text and newly added reviews are treated as feedback signals. Adding or deleting a fact changes the generated wiki; adding a review changes the evidence corpus.
- How feedback updates the wiki: the next generation uses the latest user text and current Redis-backed review evidence. The resulting session bundle is promoted from Redis into Cognee as permanent graph memory.
- Code entry point: `server.py` -> `generate_personalized_wiki`.

### Lint

- What linting means: dedupe retrieved evidence, detect conflicting review claims, and prefer the latest relevant review when reviews disagree.
- How it runs: on every wiki generation.
- Code entry point: `server.py` -> `dedupe_reviews`, `detect_conflicts`, `add_conflict_candidates`.

## Self-Improvement Evidence

### Baseline Run

- Query / task: default user profile with no extra manual-brew meetup preference.
- Result: wiki recommends no-car logistics, matcha/oat milk, long-line avoidance, and general visit timing.
- Score: pass if the wiki contains the fixed sections and cites retrieved reviews.
- Recorded feedback:

```text
error_type: missing-new-preference
error_message: Baseline wiki cannot know about a boyfriend/manual-brew date because that fact is absent.
feedback: Add the manual-brew meetup fact to User Info and regenerate.
success_score: 0.65
```

### Improved Run

- Query / task: same cafe, updated user profile: "She wants to meet her boyfriend who prefers special manual brew coffee."
- Result: wiki adds low-pressure one-on-one meetup guidance and drink-focused recommendations around manual brew / pour-over.
- Score: pass if manual-brew or pour-over appears, and unrelated facts stay unchanged.
- What changed in the wiki between runs:

```text
Before:
Best fit focuses on transit, matcha/oat milk, savory breakfast, and avoiding lines.

After:
Best fit includes a manual-brew / pour-over conversation plan for a quiet one-on-one meetup.
```

### Review-Corpus Improvement

- Query / task: add a new `r421` review about a Panama Gesha manual-brew flight, then regenerate the same user profile.
- Result: the new wiki cites `r421` and mentions Gesha/manual-brew evidence.
- Score: pass if `r421` appears in the evidence set and generated wiki.

## Architecture

```text
[User Info textarea]           [/review add-review page]
          |                              |
          v                              v
       Python API ----------------> Redis review hashes
          |                         pbw:review:*
          |                         RediSearch or hash-scan scorer
          |
          +-----------------------> Redis session memory
          |                         pbw:session:<session_id>
          |                         current user turn + facts + evidence
          |
          v
       Cognee permanent graph
          generated wiki + facts + evidence + conflict notes
          |
          v
       Stateless LLM generator
          current user text + current evidence only
          |
          v
       Personalized Markdown Wiki
```

### Redis-as-session-memory

- What the agent writes into Redis: current user text, parsed facts, retrieved review evidence, conflict notes, wiki preview, and timestamp in `pbw:session:<session_id>`.
- How and when content is distilled into the graph: after each generation, the Redis session key and full generated artifacts are passed into Cognee and `cognify` runs in the background.
- What stays in Redis vs. what gets promoted: raw review hashes and current-turn session bundles stay in Redis; generated wiki, facts, evidence, and lint/conflict notes are promoted into Cognee.
- How distillation quality improved between baseline and improved run: new user facts and new reviews produce different session bundles, which then become different Cognee graph memories for future runs.

## Agents / Skills

```text
Skill path(s): none for the MVP; the wiki generator prompt is implemented in server.py.
Roles:
  - Ingestor: ReviewIndex + /api/reviews
  - Querier: /api/wiki/generate
  - Linter: conflict detection + latest-review-wins policy
  - Critic: tests assert add/delete user facts and added reviews change the wiki
```

## Reproduction

```bash
python3 -m pip install --user -r requirements.txt
redis-server --daemonize yes
export REDIS_URL=redis://localhost:6379/0
export LLM_API_KEY="<event-provided-key>"
export LLM_MODEL=gpt-5.5
export LLM_REASONING_EFFORT=low
python3 server.py
```

Environment variables required:

```text
LLM_API_KEY
REDIS_URL
LLM_MODEL=gpt-5.5
LLM_REASONING_EFFORT=low
```

## Demo

- Live demo link: local app at `http://127.0.0.1:8891`; review page at `http://127.0.0.1:8891/review`.
- 3-minute pitch outline:

```text
1. Problem / idea: small businesses have lots of review knowledge, but generic pages do not adapt to the user.
2. Ingest demo: show 420 reviews and add a fresh review on /review.
3. Query demo: generate a wiki from default User Info.
4. Self-improve step: add manual-brew meetup preference and regenerate.
5. Improved query: delete laptop/work-block fact and show that the related recommendation disappears.
6. Review update: add r421 manual-brew review and show the same user info now cites the new review.
```

## Links

- Full code repo: https://github.com/NUM-GITHUB/personalized-business-wiki-demo
- Submission PR: https://github.com/topoteretes/cognee-hackathons/pull/11
- Writeup and screenshots: see `README.md` and `screenshots/`
- Live demo script: see `DEMO_SCRIPT.md`
