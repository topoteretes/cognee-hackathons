# Team Submission

## Team

- Team name: gasperpre
- Participants: gasperpre
- Wiki / project name: Discord Memory Wiki

## Wiki Overview

Discord Memory Wiki turns a Discord server into a self-improving LLM Wiki. The
bot watches normal Discord support/community conversations, stores recent channel
activity in Redis session memory, distills confirmed reusable knowledge into
Cognee's durable graph, and answers future questions from that durable memory.
The wiki improves when users correct answers, confirm resolutions, or react to
bot answers: those signals are recorded as Cognee memory and as `SkillRunEntry`
feedback for the answer skill. A lint operation keeps the wiki coherent by
finding duplicate, stale, conflicting, uncited, or speculative entries.

- Domain or data sources: Discord messages, replies, reactions, corrections,
  resolution messages, and bot answer feedback.
- Primary use case: Community/support knowledge that improves from real Discord
  conversations instead of requiring a manually maintained FAQ.
- What makes it stand out: It is ambient. Users keep chatting normally; the bot
  separates noisy session context from durable wiki memory, answers only when it
  has confidence, learns from thumbs-down/corrections, and exposes a wiki lint
  pass as an explicit maintenance operation.

## The Three Operations

### Ingest

- What goes in (documents, conversations, runs, ...): Discord channel messages,
  backfilled channel history, classified questions/answers/corrections/resolutions,
  reactions to bot answers, and human answer evaluations.
- How it is captured (`cognee.remember(...)`, custom pipeline, ...): The bot
  snapshots each meaningful Discord message, writes it to Redis via
  `SessionMemory`, and stages it into Cognee session memory with
  `cognee.remember(..., session_id=...)`. Backfill captures recent channel
  history, then runs a distillation prompt through the `discord-distill` skill
  and stores the resulting durable wiki entry with `cognee.remember(...)`
  without a `session_id`.
- Code entry point: `src/discord_memory_wiki/bot.py` (`on_message`,
  `backfill_command`, `_stage_channel_history`) and
  `src/discord_memory_wiki/wiki_memory.py` (`stage_session_message`,
  `distill_thread`).
- Demo evidence: `!wiki backfill 20` promoted this summary from Discord session
  memory into Cognee durable memory:

```text
Backfilled 3 existing messages and promoted a wiki summary.

# Summary

Onboarding error E42 occurs after new users accept invites. A team-member
confirmed an operational fix: clear the onboarding cache first, then rotate the
invite token.

# Durable facts

- E42 observed after new users accept invites.
- Confirmed fix: clear the onboarding cache, then rotate the invite token. Cache
  clear should be done first.
```

### Query + Self-improve

- How users query the wiki: Users ask directly with
  `!wiki ask <question>`, or ask naturally in Discord. If auto-answering is
  enabled, the bot answers observed questions only when the answer does not look
  low-confidence.
- Where feedback comes from (user rating, agent critic, eval, ...): Discord
  reactions on bot answers (`👍`, `✅`, `💯`, `👎`, `❌`, `🚫`), correction and
  resolution messages, and manual human evaluation with
  `!wiki improve <score> propose|apply <feedback>` as a reply to a bot answer.
- How feedback updates the wiki (`SkillRunEntry`, edge re-weighting,
  graph rewrite, ...): Feedback is written into Redis/Cognee memory as a
  durable "Discord answer feedback" record. The same signal is also recorded as
  a Cognee `SkillRunEntry` for the `discord-answer` skill with
  `skill_improvement`. Negative reactions apply improvement immediately; the
  manual command can either propose or apply the answer-skill rewrite.
- Code entry point: `src/discord_memory_wiki/bot.py` (`ask_command`,
  `on_raw_reaction_add`, `improve_command`) and
  `src/discord_memory_wiki/wiki_memory.py` (`answer`, `answer_if_confident`,
  `record_feedback`, `record_answer_evaluation`).

### Lint

- What "linting" means in your wiki (dedupe, conflict resolution, stale
  pruning, ...): A maintenance pass over durable wiki memory that finds duplicate
  guidance, conflicting fixes, stale/superseded claims, uncited durable facts,
  and unresolved guesses that should not be permanent wiki knowledge.
- How it runs (scheduled, on-write, on-demand): The demo runs it on demand with
  `!wiki lint [limit]`. Operationally, the same command is the daily cleanup job
  for each active Discord channel/session.
- Code entry point: `src/discord_memory_wiki/bot.py` (`lint_command`),
  `src/discord_memory_wiki/wiki_memory.py` (`lint`), and
  `skills/discord-lint/SKILL.md`.

## Self-Improvement Evidence

Show that the wiki actually got smarter. Concrete before/after beats prose.

### Baseline Run

- Query / task: `!wiki ask How do I fix onboarding error E42?`
- Result: The bot answered with the correct fix and Discord source links, but it
  kept trying to continue the conversation by asking for infrastructure details:
  "Short fix: clear the onboarding cache, then rotate the invite token (cache
  clear first)... If you need exact commands/where to run the cache clear or how
  to rotate the token, tell me your infra..."
- Score (your own metric, judge-readable): `0.6`. The factual memory retrieval
  worked, but the answer style was not ideal for the wiki use case: it was too
  chatty and ended with a follow-up request.
- Recorded feedback: A thumbs-down reaction was added to the bot answer. Then two
  correction messages were sent in Discord: "should not try to continue
  conversation. Short answers only." and "do not ask clarifying questions".

```text
error_type: reaction_and_human_style_feedback
error_message: Answer should be short and should not ask follow-up questions.
feedback: -1.0
success_score: 0.6
```

### Improved Run

- Query / task: `!wiki ask How do I fix onboarding error E42?`
- Result: The bot kept the same confirmed fix and evidence, but stopped asking a
  follow-up question:
  "Fix: clear the onboarding cache, then rotate the invite token (cache clear
  first).

  Evidence: report —
  https://discord.com/channels/1505317394351001643/1505349344788873357/1505349366226092193;
  confirmation —
  https://discord.com/channels/1505317394351001643/1505349344788873357/1505349458706038794

  Confidence: medium — confirmed in-channel but no formal runbook saved."
- Score: `0.9`. The answer is concise, cites the source messages, preserves the
  confirmed order of operations, and no longer asks the user to continue the
  conversation.
- What changed in the wiki between runs: The negative reaction and explicit style
  corrections were written into Redis/Cognee memory as feedback. Cognee recorded
  a `SkillRunEntry` for `discord-answer` with `skill_improvement.apply=True`,
  improving future answers to be shorter and avoid unnecessary clarifying
  questions.

```text
Before:
Short fix: clear the onboarding cache, then rotate the invite token (cache clear
first). Confirmed in-session: [source]. Original report: [source]
Confidence: medium-high. If you need exact commands/where to run the cache clear
or how to rotate the token, tell me your infra...

After:
Fix: clear the onboarding cache, then rotate the invite token (cache clear first).
Evidence: report — [source]; confirmation — [source]
Confidence: medium — confirmed in-channel but no formal runbook saved.
```

## Architecture

Short diagram or bullet list of components. The hackathon's core pattern is
**Redis as session memory, distilled into Cognee's permanent knowledge graph**
— show how your wiki uses that split.

```text
[Discord messages / bot answers / reactions]
        |
        v
[ Redis  — session memory ]   <- hot, per-conversation
        |
        | distillation via discord-distill
        | promote only confirmed, reusable knowledge
        v
[ Cognee — permanent graph ]  <- durable, cross-session
        |
        v
[ recall / discord-answer skill ]
        |
        v
[ feedback -> SkillRunEntry -> improve ]
        |
        v
[ lint via discord-lint ]
```

### Redis-as-session-memory

- What the agent writes into Redis (raw turns, intermediate observations, ...):
  Per-channel Discord message snapshots, recent turns, classification results,
  temporary observations, and feedback signals under a channel-scoped
  `session_id`.
- How and when content is distilled into the graph: Backfill and durable batches
  run an agentic Cognee search with the `discord-distill` skill using the Redis
  session context, then remember the resulting markdown wiki entry into Cognee
  without a `session_id`.
- What stays in Redis vs. what gets promoted: Raw/noisy recent conversation stays
  in Redis. Confirmed fixes, decisions, recurring issues, corrections,
  citations, lint reports, and reusable feedback summaries are promoted to
  Cognee.
- How distillation quality improved between baseline and improved run: The
  answer feedback and correction become durable memory, and the improved
  `discord-answer` skill is biased toward source-backed corrected guidance
  instead of incomplete session guesses.

## Agents / Skills (if any)

If you used skill packs or multi-agent roles:

```text
Skill path(s):
  - skills/discord-distill/SKILL.md
  - skills/discord-answer/SKILL.md
  - skills/discord-lint/SKILL.md
Roles:
  - Ingestor: discord-distill promotes only confirmed reusable Discord knowledge.
  - Querier: discord-answer answers Discord-native questions from durable memory
    plus current session context.
  - Linter: discord-lint finds duplicate, stale, conflicting, uncited, or
    speculative wiki entries.
  - Critic: Discord users provide reaction feedback, corrections, resolutions,
    and manual scores through !wiki improve.
```

## Reproduction

Commands to reproduce your demo:

```bash
uv sync
cp .env.example .env
docker compose up -d redis

# Discord bot setup:
# 1. Go to https://discord.com/developers/applications and create an application.
# 2. Open Bot, create/reset the bot token, and paste it into .env as DISCORD_TOKEN.
# 3. In Bot > Privileged Gateway Intents, enable Message Content Intent.
# 4. In OAuth2 > URL Generator, select scopes: bot.
# 5. Select bot permissions: Read Messages/View Channels, Send Messages,
#    Read Message History, Add Reactions.
# 6. Open the generated URL and invite the bot to your test server.
#
# Fill .env with DISCORD_TOKEN, LLM_API_KEY, and REDIS_URL.
uv run discord-memory-wiki

# In Discord:
!wiki backfill 20
!wiki ask How do I fix onboarding error E42?

# Reply to the bot's incomplete answer:
!wiki improve 0.2 apply Missing the required cache clear step.

# Run the maintenance pass:
!wiki lint 20

# Ask again to show the improved answer:
!wiki ask How do I fix onboarding error E42?

# Tests:
uv run python -m unittest discover -s tests
```

Environment variables required:

```text
DISCORD_TOKEN
LLM_API_KEY
REDIS_URL
```

Everything else has MVP defaults in code: dataset `discord-memory-wiki`, command
prefix `!wiki`, local Cognee storage directories, auto-answering enabled, and
the default classifier model. The default Redis URL is
`redis://localhost:6379`.

## Demo

- Live demo link (Loom, YouTube, etc.) or local instructions: TODO. Local demo
  is Redis + the Discord bot running with the commands above.
- 3-minute pitch outline:

```text
1. Problem / idea: Discord support knowledge is trapped in noisy chat, and FAQs
   rot immediately.
2. Ingest demo: Run !wiki backfill 20 to stage recent Discord messages in Redis
   and distill confirmed facts into Cognee.
3. Query demo (before improvement): Ask about onboarding error E42 and show the
   answer is missing a step or low-confidence.
4. Self-improve step: React 👎 or reply with !wiki improve 0.2 apply Missing the
   required cache clear step.
5. Lint demo: Run !wiki lint 20 to show stale/conflicting/uncited memory cleanup.
6. Query demo (after improvement): Ask the same question and show the corrected,
   source-backed answer.
7. What is next: Schedule lint daily per active channel, add richer eval scoring,
   and expose a small dashboard for pending skill-improvement proposals.
```

## Links

- Repo: [TODO](https://github.com/gasperpre/discord-memory-wiki)
- Slides / writeup: TODO
- Anything else: Architecture notes in `docs/ARCHITECTURE.md`; skills in
  `skills/discord-distill`, `skills/discord-answer`, and `skills/discord-lint`.