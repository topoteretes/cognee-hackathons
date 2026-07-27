# Linux Wiki Submission

## Team

- Team name: Linux Wiki
- Participants: Jagrat
- Wiki / project name: Linux Wiki

## Wiki Overview

Linux Wiki is an LLM-maintained Linux companion wiki for discovering,
debugging, and customizing Linux systems. It organizes practical Linux
knowledge around distro choice, package management, boot, audio, networking,
graphics, desktops, terminals, shells, themes, window managers, and reusable
recipes. It self-improves by keeping recent user turns, command output, and
preference signals in Redis session memory, then distilling durable fixes,
profile summaries, wiki edits, and skill improvements into Cognee's permanent
knowledge graph.

- Domain or data sources: Linux wiki pages, distro notes, subsystem docs,
  customization recipes, troubleshooting conversations, command output, and
  user preference profiles.
- Primary use case: Help a user choose, configure, debug, and maintain a Linux
  system with advice that adapts to their hardware, skill level, preferences,
  and previous sessions.
- What makes it stand out: It is not just a Linux Q&A bot. It maintains a
  structured wiki, routes users to the smallest useful page set, records
  preferences, and runs lint passes to keep the knowledge base coherent.

## The Three Operations

### Ingest

- What goes in: Wiki pages, raw Linux source material, distro facts, subsystem
  notes, command output, user messages, user preference signals, and skill
  instructions.
- How it is captured: Ephemeral conversation context is written with
  `cognee.remember(..., session_id=...)`. Stable wiki knowledge, skill notes,
  and distilled profile summaries are remembered without a session id so they
  become part of the permanent graph.
- Code entry point: `hooks/user_preference_profile.py` for profile extraction;
  wiki and skill folders are ingested as content for Cognee recall.

### Query + Self-improve

- How users query the wiki: Users ask Linux questions through the agent, such
  as distro choice, package installation, boot failures, audio routing,
  Wayland/X11 issues, gaming setup, or desktop customization.
- Where feedback comes from: User corrections, failed command output,
  successful fixes, preference profile signals, and scored agent runs.
- How feedback updates the wiki: Useful facts are distilled from Redis session
  memory into Cognee. Repeated preferences become profile pages. Reusable fixes
  become wiki recipe or subsystem updates. Run feedback can be stored as
  `SkillRunEntry` evidence to improve skills like wiki navigation and linting.
- Code entry point: `skills/wiki-navigator/SKILL.md` for query routing;
  `hooks/user_preference_profile.py` for Redis-backed user profiles.

### Lint

- What "linting" means in your wiki: Check broken links, missing index
  coverage, stale freshness claims, source gaps, contradictions, duplicate
  explanations, orphan pages, malformed frontmatter, missing log entries, and
  privacy leaks.
- How it runs: On demand after a wiki update or after a feedback-heavy session.
  The linter reads local wiki files first and only marks external freshness
  checks as follow-up unless web verification is explicitly requested.
- Code entry point: `skills/wiki-lint/SKILL.md`.

## Self-Improvement Evidence

The improvement target is answer quality for a Linux recommendation or
troubleshooting task. The wiki gets smarter by moving from generic advice to
profile-aware, evidence-backed, wiki-routed advice.

### Baseline Run

- Query / task: "I want a Linux setup for gaming and coding on an NVIDIA
  laptop, but I do not want to spend all weekend debugging it."
- Result: Generic distro advice that mentioned Arch, Fedora, and Ubuntu, but
  did not preserve the user's low-maintenance preference or NVIDIA hardware
  constraint for future turns.
- Score: 0.55
- Recorded feedback:

```text
error_type: missing_personalization
error_message: Answer did not retain hardware and maintenance constraints.
feedback: Store NVIDIA laptop, gaming, coding, and low-maintenance signals in Redis-backed profile memory before recommending.
success_score: 0.55
```

### Improved Run

- Query / task: "What should I install?"
- Result: The agent recalls the active profile, routes through the distro and
  graphics/display wiki pages, and recommends a lower-maintenance NVIDIA-aware
  path before mentioning higher-control alternatives.
- Score: 0.85
- What changed in the wiki between runs: The user's preference profile was
  distilled from session memory, the route map pointed the agent at distro and
  graphics pages, and the answer preserved the user's breakage budget.

```text
Before:
Generic recommendation with no durable memory of hardware or preference signals.

After:
Profile-aware recommendation that recalls gaming, coding, NVIDIA laptop, and low-maintenance priorities.
```

## Architecture

```text
[user turns, docs, command output, skill runs]
        |
        v
[ Redis - session memory ]
  recent turns, command evidence, active profile, raw feedback
        |
        | distill durable facts, successful fixes, preferences, skill feedback
        v
[ Cognee - permanent graph ]
  wiki pages, Linux entities, relationships, profiles, skills, recipes
        |
        v
[ recall + wiki-navigator ]
  route to distro, subsystem, customization, or recipe pages
        |
        v
[ answer + feedback ]
        |
        v
[ wiki-lint + skill/profile improvement ]
```

### Redis-as-session-memory

- What the agent writes into Redis: Raw user turns, recent troubleshooting
  attempts, command output, intermediate observations, selected profile id,
  preference signals, and run feedback.
- How and when content is distilled into the graph: After a useful answer,
  corrected command, or repeated preference, the agent promotes stable facts to
  Cognee as wiki entries, profile summaries, recipes, or skill feedback.
- What stays in Redis vs. what gets promoted: Temporary command attempts and
  conversational scratchpad data stay in Redis. Validated fixes, user
  preferences, source-backed Linux facts, and reusable recipes are promoted.
- How distillation quality improved between baseline and improved run: The
  agent learned to preserve decision-changing constraints instead of treating
  each query as isolated.

## Agents / Skills

```text
Skill path(s):
  - skills/wiki-navigator/SKILL.md
  - skills/wiki-lint/SKILL.md
  - skills/discover-os/SKILL.md
  - skills/profile/SKILL.md
  - skills/update-os/SKILL.md
  - skills/intergate-os/SKILL.md

Roles:
  - Ingestor: captures wiki pages, source material, sessions, and preference signals
  - Querier: routes questions through the smallest useful wiki page set
  - Linter: checks links, freshness, contradictions, duplication, and privacy leaks
  - Critic: scores runs and records feedback for skill or wiki improvements
```

## Reproduction

Commands to reproduce your demo:

```bash
uv venv
source .venv/bin/activate
uv pip install "cognee[redis]"
docker run -p 6379:6379 redis:latest
export REDIS_URL=redis://localhost:6379
export LLM_API_KEY="<event-provided-key>"

# Ingest the project wiki and skills, then run a query session.
# Exact demo commands live in the project implementation repo.
```

Environment variables required:

```text
LLM_API_KEY
REDIS_URL
UPSTASH_REDIS_REST_URL
UPSTASH_REDIS_REST_TOKEN
```

## Demo

- Live demo link or local instructions: Run the Linux Wiki agent locally with
  Redis enabled, create a user preference profile, ask a distro or debugging
  question, record feedback, then ask a follow-up that uses the improved
  profile/wiki state.
- 3-minute pitch outline:

```text
1. Problem: Linux advice is fragmented, stale, and rarely personalized.
2. Ingest: Load wiki pages, skills, and a user session into Redis + Cognee.
3. Query before improvement: Ask for a Linux setup recommendation.
4. Self-improve: Store profile signals and feedback from the run.
5. Query after improvement: Ask a follow-up and show profile-aware recall.
6. Next: Add more source-backed pages, automated linting, and richer evals.
```

## Links

- Repo: TBD
- Slides / writeup: TBD
- Anything else: TBD
