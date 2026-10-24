# Team Submission

## Team

* Team name: yanivas
* Participants: Savinay
* Company Brain / project name: Scalekit Cognee Respanse

## Company Brain Overview

Scalekit Cognee Respanse is a Company Brain for engineering support triage. It watches Slack for bug reports and feature requests, pulls GitHub repo and issue context, remembers both sources with user-scoped provenance, creates or drafts Jira tickets, advances work into an implementation state, prepares local code changes plus a PR payload, and evaluates the workflow end-to-end. The target users are engineering/support teams that need Slack-reported problems turned into traceable, permission-aware engineering work without losing repo context or access boundaries.

* Data sources connected through Scalekit (>= 2 apps): Slack, GitHub, and Jira.
* Primary use case / team workflow: Slack request -> grounded repo context -> Jira ticket -> implementation branch/PR payload -> evaluation.
* Users in the demo and how their access differs: Alice owns the Slack + GitHub engineering dataset; Bob starts with a limited Slack-only dataset and sees GitHub context only after Alice shares her dataset.
* What makes it stand out: The demo shows the full Pull -> Remember -> Act -> Evaluate loop, including access-controlled recall and a repeatable local mode that judges can run without SaaS credentials.

## The Three Layers

### Pull - Scalekit

* Connections created (`connection_name` -> app): `slack` -> Slack, `github` -> GitHub, `jira` -> Jira.
* Tools called (`gmail_fetch_mails`, `slack_fetch_conversation_history`, `googledrive_export_file`, `github_file_contents_get`, ...): `slack_fetch_conversation_history`, `slack_send_message`, `github_file_contents_get`, `github_issues_list`, `jira_issue_create`, `jira_issue_get`, and `github_pull_request_create`.
* How users are identified (`identifier` <-> Cognee user): Scalekit tool calls use the acting user's `identifier`; `HACKATHON_USERS` maps those identifiers to Cognee user emails such as `alice@acme.example` and `bob@acme.example`.
* Any write-back actions the agent takes (post, draft, open issue, push branch/commit, open PR): It posts Slack thread status updates, creates/drafts Jira issues, advances tickets to `In Progress`, creates a local branch/commit in the demo repo, and creates or stores a GitHub PR payload.
* Code entry point: `src/scalekit.js`, `src/connectors.js`, and the API handlers in `server.js`.

### Remember - Cognee

* What goes into the permanent graph (`cognee.remember(...)` without `session_id`): Slack messages, GitHub file/issue context, demo repo docs (`AGENTS.md`, `README.md`, `package.json`), and post-action code-change feedback.
* What stays in session memory (`session_id=...`), if anything: Nothing currently depends on Cognee session memory; the demo uses permanent, user-scoped datasets so access behavior is easy to reproduce.
* `node_set` tags used for provenance (`source:*`, `channel:*`, `owner:*`): `source:slack`, `source:github`, `source:agent`, `channel:all-hackathon`, `repo:demo-issue-router`, `file:README.md`, `file:AGENTS.md`, `file:package.json`, `issue:*`, `author:*`, and `memory:improvement`.
* Datasets and who owns / can read each: `company-brain-alice-acme-example-engineering` is owned by Alice and includes Slack + GitHub context; `company-brain-bob-acme-example-engineering` is owned by Bob and starts with Slack-only context. After Alice grants read access, Bob can recall Alice's GitHub-backed dataset.
* Access control (`ENABLE_BACKEND_ACCESS_CONTROL`, shares granted): Real Cognee mode sets `ENABLE_BACKEND_ACCESS_CONTROL=true` and uses `authorized_give_permission_on_datasets` to grant Bob read access to Alice's dataset. Local mode mirrors this by recording `sharedWith` on remembered items.
* Anything beyond defaults (custom graph model, ontology, `improve()`, custom prompt, `query_type` choice): The bridge wraps `cognee.remember`, `cognee.recall`, dataset sharing, and best-effort `cognee.improve()` after code changes. LLM and embedding calls are configured through the Respan-compatible custom endpoints.
* Code entry point: `src/memory.js` and `scripts/cognee_bridge.py`.

### Act + Evaluate - your agent(s) + Respan

* Agent(s) and the task each performs: Slack classifier extracts actionable bug/story items; Jira drafter writes issue summaries/descriptions; repo agent seeds the demo repo and applies parser fixes; PR drafter builds GitHub PR payloads; access-demo agent compares Alice/Bob recall before and after sharing; evaluator scores the run.
* LLM calls routed through the Respan gateway? (models used): Yes when `RESPAN_API_KEY` is set. `askRespan` sends classification and Jira drafting through `https://api.respan.ai/api/chat/completions`, defaulting to `gpt-4o-mini`. Without a key, deterministic fallbacks keep the demo runnable.
* How the runs are traced (Respan SDK decorator / instrumentor): Calls include `respan_params` with `trace_name`, `thread_identifier`, `custom_identifier`, `span_name`, and metadata for app, workflow run, task id, and step.
* Scenario file / Respan testset (path, number of scenarios): `evals/scenarios.json`, 8 scenarios.
* Evaluator (LLM judge + model, Python check, human review): Deterministic JavaScript evaluator in `scripts/evaluate.js`; it runs the workflow over HTTP, checks required facts/actions/source tags, and writes `evals/results/latest.json`.
* Code entry point: `src/agent.js`, `src/repoAgent.js`, `src/respan.js`, `scripts/evaluate.js`, and `server.js`.

## Evaluation Evidence

Show that the brain does the job - and that it got better. Concrete numbers beat prose.

### Baseline Run

* Respan trace / eval run link: Local eval artifact from the earlier run in `evals/results/latest.json` before the current passing rerun; no public Respan link is stored in the repo.
* Scenarios run: 8.
* Mean score: `3/8 = 0.375`.
* Worst scenario and why it failed: Source provenance was not visible to the evaluator, so cross-source workflow and access scenarios failed even when actions were present.

  ```text
  question: Does the workflow detect the can't login request as a shippable task?
  expected: source:slack plus the can't login Bug classification
  got: observedSources = []; reason = missing source source:slack
  score: failed
  ```

### Improved Run

* Respan trace / eval run link: `evals/results/latest.json`, generated locally against `http://localhost:3102` on 2026-10-08T00:48:18.822Z. The session also verified the Cognee bridge with Respan-backed LLM/embedding configuration before the final passing eval.
* What changed in the brain or agent between runs (one or two sentences): The improved run preserves source provenance in remembered `nodeSet` tags plus the `sourcePulls` state used by workflow and access-demo answers, and adds a Cognee bridge for user-scoped remember/recall/share operations. That makes Slack/GitHub provenance observable while retaining the real Cognee/Scalekit/Respan paths for connected demos.
* Mean score: `8/8 = 1.0`.

  ```text
  Before: mean = 0.375   (n = 8 scenarios)
  After:  mean = 1.000   (n = 8 scenarios)
  ```

## Access Story

Two users, the same question, different results - then a grant.

* User A (identifier, connections, datasets readable): Alice, `alice@acme.example`; connected to Slack + GitHub through Scalekit mock/real connectors; can read `company-brain-alice-acme-example-engineering`.
* User B (identifier, connections, datasets readable): Bob, `bob@acme.example`; starts with Slack-only memory in `company-brain-bob-acme-example-engineering`.
* Question asked by both: "Which Slack request is ready to ship, and what repo context supports it?"
* Result for A: Alice recalls authorized Slack + GitHub context, including `source:slack` and `source:github`.
* Result for B before the share: Bob recalls only his authorized Slack context, with `source:slack` and no GitHub provenance.
* The grant (who shared what with whom, which permission): Alice shares `company-brain-alice-acme-example-engineering` with Bob using read permission.
* Result for B after the share: Bob's answer includes GitHub-backed context and the observed sources include `source:github`.

## Architecture

```text
[ Scalekit connections per user: Slack, GitHub, Jira ]
        |
        | execute_tool(identifier=...) -> Slack messages, GitHub files/issues, Jira tickets
        v
[ Cognee / local memory ]
        | remember(node_set=[source:*], dataset_name=company-brain-<user>-engineering, user=...)
        | access enforced by Cognee backend permissions or local sharedWith records
        v
[ Agent workflow traced through Respan params ]
        | classify Slack -> draft Jira -> move In Progress -> branch/commit -> PR payload
        v
[ Respan + evaluator ]
        | evals/scenarios.json -> scripts/evaluate.js -> evals/results/latest.json
        v
[ Scores, before/after access evidence, trace metadata ]
```

## Reproduction

Commands to reproduce the demo and eval:

```bash
cp .env.example .env
npm start
open http://localhost:3000
```

In another terminal, run the deterministic judging path:

```bash
PORT=3102 MEMORY_PROVIDER=local ENABLE_BACKEND_ACCESS_CONTROL=false CONNECTOR_MODE=mock RESPAN_API_KEY= npm start
EVAL_BASE_URL=http://localhost:3102 MEMORY_PROVIDER=local ENABLE_BACKEND_ACCESS_CONTROL=false CONNECTOR_MODE=mock RESPAN_API_KEY= npm run eval
```

Environment variables required:

```text
RESPAN_API_KEY                # Optional for local demo; enables Respan gateway calls when set.
LLM_PROVIDER / LLM_ENDPOINT / LLM_API_KEY / LLM_MODEL
EMBEDDING_PROVIDER / EMBEDDING_ENDPOINT / EMBEDDING_API_KEY / EMBEDDING_MODEL / EMBEDDING_DIMENSIONS
SCALEKIT_ENVIRONMENT_URL
SCALEKIT_CLIENT_ID
SCALEKIT_CLIENT_SECRET
SCALEKIT_USER_IDENTIFIER
HACKATHON_USERS
SCALEKIT_SLACK_CONNECTION
SCALEKIT_JIRA_CONNECTION
SCALEKIT_GITHUB_CONNECTION
SCALEKIT_SLACK_HISTORY_TOOL
SCALEKIT_SLACK_SEND_TOOL
SCALEKIT_JIRA_CREATE_TOOL
SCALEKIT_JIRA_GET_TOOL
SCALEKIT_GITHUB_PR_TOOL
SCALEKIT_GITHUB_FILE_TOOL
SCALEKIT_GITHUB_ISSUES_TOOL
SLACK_WORKSPACE_NAME
SLACK_CHANNEL_NAME
SLACK_CHANNEL_ID
JIRA_PROJECT_KEY
GITHUB_OWNER
GITHUB_REPO
GITHUB_CONTEXT_PATH
MEMORY_PROVIDER
COGNEE_PYTHON_BIN
COGNEE_DATASET_PREFIX
ENABLE_BACKEND_ACCESS_CONTROL
COGNEE_DEMO_PASSWORD
DATA_ROOT_DIRECTORY / SYSTEM_ROOT_DIRECTORY / CACHE_ROOT_DIRECTORY / COGNEE_LOGS_DIR / COGNEE_REPOS_DIR
DB_PATH / MIGRATION_DB_PATH
CONNECTOR_MODE
```

Judges without your SaaS accounts: run with `CONNECTOR_MODE=mock`, `MEMORY_PROVIDER=local`, and an empty `RESPAN_API_KEY`. The app seeds mock Slack messages, mock GitHub context, local memory, a local demo repo, local Jira-like tickets, and local PR payloads.

## Demo

* Live demo link (Loom, YouTube, etc.) or local instructions: Local demo at `http://localhost:3000` after `npm start`. No hosted video link is stored in the repo yet.
* 3-minute pitch outline:

  ```text
  1. Problem / team workflow: Slack engineering requests lose context and ownership.
  2. Pull demo: Scan Slack and pull GitHub context through Scalekit-configured connectors.
  3. Brain demo: Show remembered Slack + GitHub context with source tags.
  4. Access demo: Alice sees cross-source memory; Bob is limited; Alice grants read access; Bob sees GitHub context.
  5. Agent task demo: Jira ticket is drafted, moved to In Progress, a local branch/commit and PR payload are prepared.
  6. Eval demo: Run npm run eval and show 8/8 in evals/results/latest.json.
  7. What is next: deploy hosted demo, attach public Respan traces, and swap mock data for real authorized accounts.
  ```

## Links

* Repo: https://github.com/yanivas/scalekit-cognee-respanse
* Respan traces / eval runs: Local eval artifact at `evals/results/latest.json`; Respan trace name defaults to `scalekit-cognee-respanse` when `RESPAN_API_KEY` is set.
* Slides / writeup: Not committed yet.
* Anything else: README reproduction guide in `README.md`.
