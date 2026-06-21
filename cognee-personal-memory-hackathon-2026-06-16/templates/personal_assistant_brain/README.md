# Personal Assistant Brain Template

This template is the planned reusable version of
`tutorial/personal_memory_life_assistant.ipynb`: a personal memory graph fed by
Slack, email, and Granola, then queried through Cognee.

The target user experience is:

```bash
export LLM_API_KEY=...
export COGNEE_DATASET=personal_assistant_brain
export PERSONAL_ASSISTANT_EMAIL=you@example.com

export SLACK_BOT_TOKEN=xoxb-...
export SLACK_CHANNELS=C01234567,C08901234

export EMAIL_IMAP_HOST=imap.gmail.com
export EMAIL_IMAP_USER=you@example.com
export EMAIL_IMAP_PASSWORD=...

export GRANOLA_API_KEY=...

uv pip install -e ".[personal-assistant]"
python templates/personal_assistant_brain/personal_assistant_brain.py ingest
python templates/personal_assistant_brain/personal_assistant_brain.py ask \
  --dataset slack:general \
  "What do I still need to respond to today?"
python templates/personal_assistant_brain/personal_assistant_brain.py visualize \
  --output personal_assistant_brain_graph.html
```

## Why dlt

dlt is a good fit for this template because it gives us incremental extraction,
source state, retries, and source-local customization without making Cognee own
every SaaS API detail.

Recommended implementation split:

- Slack: use dlt's verified Slack source for channels, users, and messages.
- Email: use dlt's verified Inbox source for IMAP messages and attachments.
- Granola: implement a small custom dlt source around Granola's API.
- Cognee: keep Cognee as the memory/graph layer after records are normalized to
  transcript-shaped documents.

## Environment Variables

Core:

- `LLM_API_KEY`: LLM key used by Cognee.
- `COGNEE_DATASET`: defaults to `personal_assistant_brain`.
- `COGNEE_SERVICE_URL`: optional remote Cognee service URL.
- `COGNEE_API_KEY`: optional Cognee service key.
- `COGNEE_DATASETS`: optional comma-separated datasets for `ask`; useful for
  querying multiple Slack channel datasets.
- `INGEST_SINCE_DAYS`: defaults to `30`.
- `PERSONAL_ASSISTANT_EMAIL`: optional explicit identity for "me".
- `PERSONAL_ASSISTANT_SLACK_ID`: optional explicit Slack identity for "me".
- `PERSONAL_ASSISTANT_NAME`: optional display name.

Slack:

- `SLACK_BOT_TOKEN` or `SLACK_USER_TOKEN`.
- `SLACK_CHANNELS`: comma-separated channel IDs or names.
- `SLACK_INCLUDE_PRIVATE_CHANNELS=1`: include private channels and group DMs
  when the token has the needed scopes.
- `SLACK_INCLUDE_BOTS=1`: include bot messages.
- `SLACK_USER_ID`: optional identity fallback for "me".
- `SLACK_DISABLED=1`: skip Slack.

Slack threads are written to Cognee datasets named `slack:<channel_name>`, for
example `slack:general` or `slack:product`. This keeps each channel's chat
history together while preserving source/channel tags on every document.

Email:

- `EMAIL_IMAP_HOST`.
- `EMAIL_IMAP_USER`.
- `EMAIL_IMAP_PASSWORD`: app password for Gmail/Outlook/IMAP.
- `EMAIL_IMAP_FOLDER`: defaults to `INBOX`.
- `EMAIL_DISABLED=1`: skip email.

Granola:

- `GRANOLA_API_KEY`.
- `GRANOLA_API_BASE_URL`: optional override; defaults to Granola's public API.
- `GRANOLA_DISABLED=1`: skip Granola.
- `GRANOLA_DOC_IDS`: optional comma-separated allowlist.

## Files

- `IMPLEMENTATION_PLAN.md`: phased implementation plan and dlt integration
  notes.
- `granola_dlt.py`: custom dlt source for Granola notes and transcripts.
- `slack_verified/`: dlt verified Slack source vendored for this example.
- `slack_dlt.py`: adapter from verified Slack rows to Cognee thread docs.
- `personal_assistant_brain.py`: a runnable scaffold that shows the intended
  command shape and reuses the existing Cognee write path.

## Visualize The Graph

Render all readable Cognee datasets to an interactive HTML file:

```bash
python templates/personal_assistant_brain/personal_assistant_brain.py visualize
```

To scope the visualization to a single dataset, pass `--dataset`. This is useful
for Slack datasets such as `slack:general`:

```bash
python templates/personal_assistant_brain/personal_assistant_brain.py visualize \
  --dataset slack:general \
  --output slack_general_graph.html
```

## Current Status

Slack uses dlt's verified Slack source vendored into this example, then adapts
the rows into Cognee thread docs. Granola ingestion is implemented through a
custom dlt source because the verified-source catalog does not include Granola.
Email still intentionally marks its dlt-backed extractor as TODO while
preserving the CLI shape. The runner now infers the user's identity from env
vars and asks for feedback only when running interactively and still uncertain.
The next step is to vendor or generate the dlt Inbox source under this template
and adapt it into the shared `Doc` shape.
