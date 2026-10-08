# Team Submission

## Team

- Team name: VirtusLab
- Participants: Michał Ogrodnik, Paweł Dolega
- Company Brain / project name: Event Brain — one live status page per company event

## Company Brain Overview

VirtusLab runs many events and trips (SF Tech Week, TechCrunch Disrupt, meetups)
with few people. Information gets lost: invites and partner codes scroll past in
mail and Slack, people miss the thread, action items have no owner. Event Brain
pulls the event's mail (everything sent or CC'd to the event Google Group), the
event Slack channel and the company's travel/event guides, remembers them in
Cognee per user, and keeps one Coda page — the event's "single pane of glass" —
refreshed with key dates, decisions, open action items with owners, tickets and
the travel rules that apply. Users: the people organising and attending the event.

- Data sources connected through Scalekit (≥ 2 apps): Gmail (event Google Group),
  Coda / Superhuman Docs (Company Guide; custom connector), Slack (event channel)
- Primary use case / team workflow: "don't miss anything about the event" —
  a self-refreshing event status page
- Users in the demo and how their access differs: TODO (see Access Story)
- What makes it stand out: the agent may read the whole company guide but can
  only edit one page; email reaches the brain just by CC'ing the event group

## The Three Layers

### Pull — Scalekit

- Connections created (`connection_name` → app): `gmail` → Gmail (own Google
  OAuth app, `gmail.readonly`), `VL_Coda` → Coda REST API (custom Bearer connector
  created by `scripts/create_coda_connector.py`, per-user Coda token), Slack: in progress (Paweł)
- Tools called: `gmail_fetch_mails`, `gmail_get_attachment_by_id` (calendar
  invites); Coda via `actions.request`: `/resolveBrowserLink`, `/docs/{id}/pages`,
  page export, page content update
- How users are identified (`identifier` ↔ Cognee user): Scalekit identifier per
  person ↔ Cognee user email; each user's pulls go to `<name>-brain`
- Write-back actions: replaces the content of one Coda page (Tech Week SF).
  `CodaClient._call` refuses every other write before sending; Gmail is
  read-only twice (OAuth scope + tool allowlist in `GmailClient._tool`)
- Code entry point: `company_brain/coda.py`, `company_brain/gmail.py`

### Remember — Cognee

- Permanent graph: each event email (with calendar invite summary) and each
  selected Company Guide page (Business Travel, travel insurance, Events,
  travel recommendations) via `cognee.remember(..., dataset_name, node_set, user)`
- Session memory: not used
- `node_set` tags: `source:gmail`, `source:coda`, `page:<name>`, `owner:<email>`
- Datasets: one per user (`mogrodnik-brain`, ...), readable by its owner until shared
- Access control: `ENABLE_BACKEND_ACCESS_CONTROL=true`; shares: TODO
- Beyond defaults: the destination page is never ingested (no feedback loop)
- Code entry point: `company_brain/brain.py` (`ingest`, `ask`)

### Act + Evaluate — your agent(s) + Respan

- Agent: `brain.py refresh` recalls the event state from every dataset the user
  may read and writes the status page (key dates, decisions, owners, tickets,
  travel rules, sources) into Coda
- LLM calls routed through the Respan gateway: yes — Cognee (`openai/gpt-5-mini`)
  and the page writer (`gpt-5-mini`)
- Tracing: every gateway call is logged in Respan
- Scenario file: `eval/scenarios.json` (8 scenarios)
- Evaluator: deterministic keyword match (`company_brain/evaluate.py`), results
  appended to `eval/results.jsonl`
- Code entry point: `company_brain/evaluate.py`

### Slack → structured event state (extractor)

- Every event Slack channel is synced into Cognee (Cognee Slack integration, one document per
  thread, re-synced every 10 min, edits/deletes reconciled); one dataset per event, many
  channels per event (`events.json`).
- `python -m company_brain.extract` reads each channel's threads from Cognee and has Claude
  (structured JSON output) maintain the event state per channel in
  `data/events/<event>/<channel_id>.json`: tasks, decisions, questions, deadlines and info, with
  owners (Slack IDs resolved to names via Scalekit `slack_list_users`), due dates, status,
  evidence and links to the source messages.
- The previous state is fed back on every run, so item IDs stay stable and statuses evolve
  (open → done) instead of being regenerated; items are never silently dropped. Live on SF Tech
  Week: 2 channels, 247 messages → 29 items; IDs stable across runs; 51 unit tests.

## Evaluation Evidence

### Baseline Run

- Respan trace / eval run link: Respan dashboard (gateway logs for this project)
- Scenarios run: 8 (`eval/scenarios.json`, run log in `eval/results.jsonl`)
- Mean score: 1.00 as the trip organiser (all must-mention facts found)
- Worst scenario and why it failed: none failed for the organiser; the access run below is where scores drop

### Improved Run

- What changed between runs: TODO
- Mean score: TODO

```text
Before:  mean = ___   (n = 8 scenarios)
After:   mean = ___   (n = 8 scenarios)
```

## Access Story

- User A: TODO
- User B: TODO
- Question asked by both: TODO
- Result for A / B before the share / grant / B after: TODO

## Architecture

```text
[ Gmail: mail to/cc tech-week-sf@ ]  [ Coda: Company Guide ]  [ Slack: event channel ]
              \                              |                        /
               execute_tool / actions.request(identifier=<user>)   (Scalekit)
                                     |
            cognee.remember(node_set=[source:*], dataset_name=<user>-brain, user=<user>)
                                     |
                 cognee.recall(status question, user=<user>)  -> grounded context
                                     |
              page writer (Respan gateway)  -> Coda "Tech Week SF" page (replace)
                                     |
                       evaluate.py over eval/scenarios.json
```

Access is enforced at three points: Scalekit (each user's own tokens), Cognee
(per-user datasets with access control), and our clients (Coda: one writable
page; Gmail: read-only tools).

## Reproduction

```bash
uv sync
cp .env.example .env            # fill in Scalekit, Respan and connection settings
uv run python scripts/create_coda_connector.py   # once; then create a connection for it
uv run python quickstart/coda_quickstart.py      # authorize Coda (prints a link first)
uv run python quickstart/gmail_quickstart.py     # authorize Gmail (prints a link first)
uv run python -m company_brain.brain ingest --user you@company.com
uv run python -m company_brain.brain refresh --user you@company.com
uv run python -m company_brain.evaluate --label baseline
uv run pytest
```

Environment variables: see `.env.example`.

Judges without our SaaS accounts: TODO (sample data)

## Demo

```text
1. Problem: events, scattered mail/Slack, nobody owns the action items
2. Pull: Gmail group mail + Coda guide as user A
3. Brain: Cognee graph (cognee-cli -ui) + a cross-source answer
4. Access: user B asks, gets less; share; asks again
5. Agent: refresh -> Coda Tech Week SF page updates live
6. Eval: before/after scores
7. Next: Slack channel bot, Google Group CC as the default for every event
```

## Links

- Repo: https://github.com/VirtusLab/company-brain
- Respan traces / eval runs: Respan dashboard (gateway logs)
