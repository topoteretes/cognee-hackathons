# Adverra Brain 🧠

A **Company Brain** for the (imaginary) company **Adverra** and its consumer
rewarded-earnings product **Cashly**. It implements Karpathy's
[LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
on top of [Cognee](https://docs.cognee.ai/), and exposes it as a **Slack support
agent** that answers from the wiki, escalates to a human when it doesn't know,
and **gets smarter from that human's feedback**.

## Team

| Name | Role |
|------|------|
| **Mert Gökçe** | Data Engineer |
| **Ahmet Sevim** | Agent Orchestrator |

## Karpathy's three layers, mapped

| Karpathy layer | Here |
|---|---|
| Raw sources (immutable) | [`raw/`](raw/) — help-center articles, product pages, FAQ, meeting notes |
| The wiki (LLM-owned, compiled) | Cognee knowledge graph (built by `src/ingest.py`) |
| The schema / workflow | [`my_skills/`](my_skills/) + the three operations below |

## The three operations

1. **Ingest** — `python -m src.ingest` reads `raw/` into the Cognee graph.
2. **Query + Self-improve** — the Slack agent answers questions; 👎 + a human
   correction updates the wiki and improves the answerer skill.
3. **Lint** — `python -m src.lint` finds duplicates, conflicts, and stale facts.

## Memory tiers

Same Cognee instance, two tiers (per the hackathon brief):
- **Session memory** — every Slack call passes `session_id = thread_ts`
  (fast, per-conversation working memory).
- **Permanent graph** — corrections/facts are remembered without a `session_id`
  (durable, cross-session).

## Setup

```bash
uv venv --python python3.13      # a Python with a modern macOS wheel target
source .venv/bin/activate
uv pip install -r requirements.txt
cp .env.example .env             # fill in LLM + Slack keys
```

## The self-improvement loop (the demo)

1. Ask in Slack: `@CompanyBrain Can I cash out to PayPal in Kosovo?`
2. The brain has no answer → it **@tags the responsible expert**.
3. The expert reacts **👎** on the bot message and posts the correct answer in
   the thread.
4. The bot calls `feedback.record_correction`:
   - `cognee.remember(correction)` → the fact is now in the wiki.
   - a `SkillRunEntry` (score 0.2) → proposes & applies a `qa-answerer` rewrite.
5. Ask the same question again → the brain now answers it confidently.

## Run

```bash
python -m src.ingest                       # build the wiki
python -m src.query "How long do PayPal withdrawals take?"
python -m src.slack_app                    # start the Slack bot (Socket Mode)
python -m src.lint                         # health check
python -m src.push_to_cloud                # optional: push to Cognee Cloud (bonus)
```

## Slack app setup (Socket Mode)

1. Create an app at api.slack.com/apps → enable **Socket Mode**.
2. Bot token scopes: `app_mentions:read`, `chat:write`, `reactions:read`,
   `channels:history`, `groups:history`.
3. Subscribe to events: `app_mention`, `reaction_added`.
4. App-level token with `connections:write`.
5. Put `SLACK_BOT_TOKEN` (`xoxb-`), `SLACK_APP_TOKEN` (`xapp-`), and
   `RESPONSIBLE_PERSON` (the expert's Slack user id) in `.env`.
