# Running the gtm-brain Slack bot

The bot listens to messages in configured channels, **live-ingests** each new message into the Cognee graph, then **recalls** relevant context from `gtm_brain` and replies when the graph has something useful. Same single-file codebase as the tutorial — no extra runtime beyond cognee + slack-sdk + an OpenAI key.

This guide walks through setting it up against a Slack workspace from scratch.

## 1. Prereqs

- macOS or Linux with Python 3.11+
- An OpenAI API key (cognee uses it for extraction and recall embeddings)
- A Slack workspace you can install apps into
- This repo cloned:

  ```bash
  git clone git@github.com:topoteretes/cognee-companybrain.git
  cd cognee-companybrain
  uv venv && source .venv/bin/activate
  uv pip install -e ".[dev]"
  ```

## 2. Create the Slack app

The bot uses **Socket Mode** (no public webhook needed). At https://api.slack.com/apps → **Create New App** → *From scratch*:

### Bot OAuth scopes — *OAuth & Permissions → Scopes → Bot Token Scopes*

| Scope | Why |
|---|---|
| `channels:history`, `groups:history` | Read message history for live-ingest |
| `channels:read`, `groups:read` | Resolve channel IDs to names |
| `chat:write` | Post replies |
| `users:read`, `users:read.email` | Resolve user IDs to emails for canonical Person nodes |
| `im:history`, `mpim:history` *(optional)* | DM the bot |

### Socket Mode — *Socket Mode → Enable Socket Mode*

Generate an **App-Level Token** with `connections:write` scope. This is the `xapp-…` token.

### Event Subscriptions — *Event Subscriptions → Enable Events*

Subscribe to **Bot Events**:

| Event | Why |
|---|---|
| `message.channels` | Public-channel messages |
| `message.groups` | Private-channel messages |
| `message.im` *(optional)* | DMs |

### Install to Workspace

OAuth & Permissions → **Install to Workspace**. Approve the scopes. Two tokens come out:

- **Bot User OAuth Token** (`xoxb-…`) → goes into `SLACK_BOT_TOKEN`
- **App-Level Token** (`xapp-…`, from earlier) → goes into `SLACK_APP_TOKEN`

### Invite the bot to channels

In each channel you want it to read/answer in: `/invite @<your-bot-name>`.

Get the channel IDs: open a channel → top header → click name → **About** → ID is at the bottom (looks like `C0BXXXXXXX`).

## 3. Configure `.env`

```bash
cp .env.example .env
```

Fill in:

```bash
# Required — Cognee uses this for everything
LLM_API_KEY=sk-...

# Cognee backend
COGNEE_SERVICE_URL=http://localhost:8000
COGNEE_API_KEY=                       # set if your local Cognee requires auth
COGNEE_DATASET=gtm_brain          # the dataset the bot reads/writes

# Slack
SLACK_BOT_TOKEN=xoxb-...              # from "Install to Workspace"
SLACK_APP_TOKEN=xapp-1-...            # from Socket Mode app-level token

# Channels the bot will participate in (comma-separated IDs).
# If left empty, falls back to SLACK_CHANNELS.
SLACK_BOT_CHANNELS=C0BXXXXXXX,C0BYYYYYYY

# Channels the *ingest* pulls historical threads from. Often the same.
SLACK_CHANNELS=C0BXXXXXXX,C0BYYYYYYY
SLACK_BOT_RECALL_TOP_K=3

# Granola off for the bot path
GRANOLA_DISABLED=1

# Ingest window (only used by the batch ingest, not the bot)
INGEST_SINCE_DAYS=30
```

## 4. Start the Cognee backend

The bot needs a running Cognee server to write to and recall from:

```bash
# Detached so it survives terminal close
nohup ~/.cognee-plugin/venv/bin/uvicorn cognee.api.client:app \
  --host 127.0.0.1 --port 8000 \
  > ~/.cognee-plugin/server.log 2>&1 &
disown
```

Wait until `curl http://127.0.0.1:8000/` returns 200.

## 5. Seed the graph (one-time)

The bot can answer questions only against content that's in the graph. Two paths to populate it:

**Option A — Backfill from existing Slack history:**

```bash
uv run gtm-brain-ingest
```

This pulls the last `INGEST_SINCE_DAYS` of each channel in `SLACK_CHANNELS`, classifies and writes everything via `cognify(graph_model=Thread)`. ~30 minutes for ~200 threads.

**Option B — Start empty, let the bot live-ingest as you go:**

Skip the batch ingest. Every message the bot sees in an allowed channel gets ingested before recall fires, so the graph grows organically. First few questions will get "no relevant context" responses until messages accumulate.

## 6. Start the bot

```bash
# Detached so it survives terminal close
nohup uv run gtm-brain-slackbot \
  > ~/.cognee-plugin/slackbot.log 2>&1 &
disown
```

Tail the log to confirm it connected:

```bash
tail -f ~/.cognee-plugin/slackbot.log
```

You should see:

```
cognee: connected to http://localhost:8000
A new session (s_...) has been established
slackbot: listening as U0BXXXXXXX on C0BXXXXXXX, C0BYYYYYYY
```

## 7. Use it in Slack

Post a fact in one channel:

> "Veljko is leading the n8n integration."

Wait ~30–60s for live-ingest to finish (you can watch `~/.cognee-plugin/slackbot.log`).

Ask a question in another channel:

> "Who is leading n8n?"

If the graph has relevant context, the bot replies inline as a thread reply.

## 8. Stop / restart

```bash
# Bot
pkill -f "uv run gtm-brain-slackbot"

# Cognee server
pkill -f "uvicorn cognee.api.client:app"
```

Re-run the same `nohup …` commands to bring them back.

## How it works (one paragraph)

For every non-bot message in an allowed channel, the listener:

1. **Live-ingest** — pulls the full thread via Slack API, formats it as a transcript, runs the two-axis LLM classifier (`product` × `client` × `domain`), and writes it through `cognee.add()` + `cognee.cognify(graph_model=Thread, custom_prompt=…)`. A per-(channel, thread) cooldown prevents thrashing on chatty threads.
2. **Recall** — calls `cognee.recall(text, only_context=True)`; if the returned chunks don't share significant terms with the question, stays silent.
3. **Reply** — formats the top‑k results into a single Slack message and posts it as a reply.

Everything happens in a background asyncio task per event, so the Slack ACK is immediate and the slow cognify work doesn't block the socket.

## Useful environment overrides

| Var | Default | Behavior |
|---|---|---|
| `SLACK_BOT_CHANNELS` | falls back to `SLACK_CHANNELS` | Channels the bot listens to |
| `SLACK_BOT_RECALL_TOP_K` | `3` | How many graph chunks to surface per reply |
| `SLACK_BOT_RECALL_TIMEOUT` | `45` | Seconds before a stuck recall is abandoned |
| `SLACKBOT_INGEST_COOLDOWN` | `30` | Seconds between re-cognifies of the same thread |
| `SLACKBOT_LIVE_INGEST_DISABLED` | unset | Set to `1` to read-only mode (no live ingest) |
| `SLACKBOT_ISSUE_FILTER` | unset | Set to `1` to restrict replies to bug/issue-style questions only |

## Troubleshooting

**Bot logs "listening as …" but never says "received event"** → Slack isn't delivering events. Re-check Event Subscriptions are enabled and `message.channels` / `message.groups` are subscribed. Reinstall the app afterward and refresh `SLACK_BOT_TOKEN`.

**Live-ingest errors with `Remote add failed (500): Broken pipe`** → Cognee server got into a bad state. Restart it (`pkill -f uvicorn cognee.api.client` + re-launch).

**Bot stays silent on every question** → It's probably the relevance filter — the recall results don't share significant terms with the question. Confirm by tailing the log: you'll see `slackbot: no relevant graph context for message …; staying silent`. Either ask a question that overlaps with stored content, or set `SLACK_BOT_RECALL_TOP_K=5` to widen the pool.

**Granola in the loop?** Open the Granola Mac app once to refresh the WorkOS session, flip `GRANOLA_DISABLED=` (empty) in `.env`, and re-run `uv run gtm-brain-ingest` to pull meeting notes alongside Slack threads.
