# Personal Assistant Brain Implementation Plan

## Goal

Create a copyable template that turns a user's Slack, email, and Granola history
into a Cognee-backed personal memory assistant. Users should only need to set
environment variables for their keys/tokens and run one ingest command.

## Architecture

```text
Slack dlt source   \
Inbox dlt source    -> normalize to Doc -> Cognee add/cognify -> recall assistant
Granola dlt source /
```

The normalization boundary is the important contract. Every source should
produce one transcript-shaped `Doc` with:

- stable `source`, `doc_id`, `title`, `container`, and `started_at`
- ordered utterances with `speaker`, `timestamp`, and `text`
- tags such as `source:email`, `email:INBOX`, `speaker:person@example.com`,
  `needs_reply:true`, `doc:<id>`

## Phase 1: Template Scaffold

- Add `templates/personal_assistant_brain`.
- Add a CLI script with `ingest` and `ask` commands.
- Default `COGNEE_DATASET` to `personal_assistant_brain`.
- Keep credentials in `os.environ`, with optional `.env` loading for local use.
- Reuse `company_brain.normalize.Doc` and `company_brain.cognee_client`.
- Keep this as a repo example for now, not a separate packaged application.

## Phase 2: dlt Extraction Layer

- Add `dlt` as an optional dependency, likely `personal-assistant = ["dlt>=1.27"]`.
- Add `dlt[duckdb]` as the `personal-assistant` optional dependency.
- Vendor dlt's verified Slack source and adapt its rows to Cognee Docs. Done.
- Generate or vendor dlt's verified Inbox source with `dlt init inbox duckdb`.
- Use a local DuckDB destination for source state while each source runs.
- Delete raw dlt tables after Cognee ingestion succeeds.
- Add adapter functions:
  - `slack_rows_to_docs(channels, messages, users) -> Iterable[Doc]`
  - `email_rows_to_docs(messages, attachments) -> Iterable[Doc]`
  - `granola_rows_to_docs(notes, transcripts) -> Iterable[Doc]`
- Persist source state in `.dlt/` or a template-local `.state/` directory.

## Phase 3: Slack Support

- Fetch users and messages through dlt's verified Slack source. Done.
- Resolve Slack user IDs to email/name before normalization. Done.
- Preserve thread boundaries by grouping on `thread_ts` or `ts`. Done.
- Convert mentions from `<@U...>` to stable `@email` references. Done.
- Tag docs with channel, speakers, and `mentioned_self:true` where applicable. Done.
- Write Slack thread docs to datasets named `slack:<channel_name>`. Done.

## Phase 4: Email Support

- Fetch messages through dlt's Inbox source over IMAP.
- Normalize each email thread as a `Doc`.
- Extract speaker from `From`, recipients from `To`/`Cc`, and timestamp from
  `Date`.
- Parse plain text first, with HTML-to-text fallback.
- Include attachment text only for supported document types.
- Add tags for `from:`, `to:`, `subject:`, `thread:`, and `needs_reply`
  heuristics.

## Phase 5: Granola Support

- Prefer Granola's public API with `GRANOLA_API_KEY`. Done.
- Implement a custom dlt source with resources for notes and transcripts. Done.
- Keep the existing `src/company_brain/sources/granola.py` desktop-session
  source only as a fallback/dev reference.
- Normalize each note/transcript as a meeting `Doc`. Done.
- Tag attendees and meetings where the user was assigned an action item.

## Phase 6: Personal Assistant Layer

- Infer the user's identity from `PERSONAL_ASSISTANT_EMAIL`,
  `PERSONAL_ASSISTANT_SLACK_ID`, `EMAIL_IMAP_USER`, and `SLACK_USER_ID`.
- Ask for user feedback only when identity remains uncertain and the CLI is
  running interactively.
- Add a personal-memory graph schema or prompt tuned for:
  - commitments
  - open loops
  - deadlines
  - people and relationships
  - "waiting on me" vs "waiting on others"
- Add canned recall commands:
  - `open-items`
  - `waiting-on-me`
  - `waiting-on-others`
  - `daily-brief`
- Keep raw source scopes queryable with Cognee node sets.

## Acceptance Criteria

- A user can run one command after exporting env vars.
- Slack, email, and Granola can be enabled independently.
- Re-running ingest is incremental and does not duplicate documents.
- Raw dlt tables are cleaned up after successful Cognee ingestion.
- "Me" can be inferred from env vars, with interactive feedback as fallback.
- Slack threads are queryable by per-channel datasets such as `slack:general`.
- Recall can answer cross-source questions such as:
  - "What do I owe people today?"
  - "Which Slack mentions did I not answer?"
  - "What decisions from meetings affect my current email threads?"
- Missing optional credentials produce a skip message, not a crash.

## Decisions

- The template lives as a repo example for now.
- Raw dlt tables should be deleted after successful Cognee ingestion.
- The assistant should infer identity first and ask for feedback only when
  uncertain.
