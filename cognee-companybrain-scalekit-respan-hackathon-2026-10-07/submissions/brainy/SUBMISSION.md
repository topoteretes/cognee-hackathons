# Brainy: Team Submission

## Team

- Team name: Brainy
- Participants: Duc Vo.
- Company Brain / project name: Brainy

## Company Brain Overview

Brainy helps engineering teammates reconstruct decisions from source records: why a technology was chosen, who owns the work, and what remains open. It retrieves only from datasets the asking person can read, answers with citations, and lets an owner explicitly share memory. The browser demo uses fictional Northwind Labs records with real Cognee retrieval and model calls. This prototype has personal datasets, not a company/team hierarchy.

- Sources implemented through Scalekit: Slack, GitHub, Gmail, Notion. A live two-app/two-user pull is **not verified**; the demo ingests sample JSON.
- Workflow: decision lookup and an optional Slack post, previewed before sending.
- Demo users: Alice has engineering/project records; Bob initially has general-channel records only.
- Distinction: the same question produces a useful answer or a refusal depending on access; a dataset grant changes what can be retrieved.

## The Three Layers

### Pull: Scalekit

- Configured defaults expected by code: `slack` → Slack, `github` → GitHub, `gmail` → Gmail, `notion` → Notion. These are expected connection names, not a claim that all four are active.
- Tool names in code: `slack_fetch_conversation_history`, `slack_get_conversation_replies`, `slack_get_user_info`, `github_issues_list`, `github_pull_requests_list`, `gmail_fetch_mails`, `gmail_get_message_by_id`, `notion_page_search`, `notion_page_content_get`. Complete live execution is not verified.
- The acting identifier is passed to Scalekit. Cognee maps demo aliases `alice` / `bob` to fictional `alice@acme.com` / `bob@acme.com`; these are not real inboxes or OAuth accounts.
- Write-back: `slack_send_message`, through the acting user's connection. Demo uses `post --dry-run`; a live post is not claimed.
- Latest blockers: Gmail OAuth client configuration; Notion authorization returned connection-not-found.
- Entry points: [brain/pull.py](https://github.com/minhducvo04/brainy/blob/codex/judge-demo-guide/brain/pull.py), [brain/act.py](https://github.com/minhducvo04/brainy/blob/codex/judge-demo-guide/brain/act.py), [brain/cli.py](https://github.com/minhducvo04/brainy/blob/codex/judge-demo-guide/brain/cli.py).

### Remember: Cognee

- Permanent memory: normalized source text passed to `cognee.remember`; no `session_id` is used. No separate session memory is implemented.
- Provenance: `node_set` tags such as `source:slack`, `channel:eng`, `owner:alice@acme.com`, and source-specific author/repository tags.
- Datasets: Alice owns `alice-brain`; Bob owns `bob-brain`. Read access is granted explicitly.
- `ENABLE_BACKEND_ACCESS_CONTROL=true`; recall resolves authorized datasets and supplies only their IDs.
- Uses `SearchType.CHUNKS` to retrieve raw passages. No custom ontology or `improve()` claim.
- Entry points: [brain/records.py](https://github.com/minhducvo04/brainy/blob/codex/judge-demo-guide/brain/records.py), [brain/memory.py](https://github.com/minhducvo04/brainy/blob/codex/judge-demo-guide/brain/memory.py).

### Act + Evaluate: agent + Respan

- Agent: one cited-answer workflow, with refusal when no evidence is retrieved and a prompt against unsupported answers.
- Answer calls use the Respan gateway with default model `openai/gpt-5-mini` (environment configurable).
- Tracing: Respan SDK `workflow(name="answer")` decorator. A live smoke test returned an answer and HTTP 200 trace export; dashboard visibility still needs confirmation.
- Scenario sets: `scenarios/scenarios.json` (12); `scenarios/scenarios_v2.json` (10).
- Evaluator: independent Python checks, 70% required fact mentions and 30% expected source tags; forbidden mentions score zero; refusal scenarios check refusal text. No LLM judge. This is not a full semantic citation audit.
- Entry points: [brain/agent.py](https://github.com/minhducvo04/brainy/blob/codex/judge-demo-guide/brain/agent.py), [eval/score.py](https://github.com/minhducvo04/brainy/blob/codex/judge-demo-guide/eval/score.py).

## Evaluation Evidence

### Baseline Run

- Respan trace / eval run link: **not yet attached**; organizer access must be verified.
- Initial set: 12 scenarios, mean **1.000** (ceiling).
- Harder held-out set: 10 scenarios, baseline **0.900**, as recorded by the planner in the project status.
- Worst reported behavior: a mixed public/private question was refused completely instead of answering its public part. Exact per-scenario question, output, and score are not reproduced here; raw per-scenario evidence is not attached. These aggregate measurements are reported from the team's recorded run, not a new evaluation.

### Improved Run

- Attempt: add provenance labels to chunks and strengthen the citation prompt.
- Harder-set mean fell to **0.877**; the change was reverted. We do not claim improvement.
- Trace / run link: **not yet attached**.

```text
Before: mean = 0.900 (n = 10)
After:  mean = 0.877 (n = 10)
Shipped: reverted baseline
```

## Access Story

- A: `alice`, owns/reads `alice-brain`; recorded engineering and general Slack plus GitHub evidence.
- B: `bob`, owns/reads `bob-brain`; recorded Slack #general only before sharing. Live source connections remain unverified.
- Both ask: “Why did we switch to Postgres and who owns the migration?”
- A: cites JSONB, row-level locking, replication lag, and Carol's ownership.
- B before grant: “I can't see that.”
- Grant: Alice grants Bob `read` on the entire `alice-brain` dataset.
- B after grant: the planner recorded a cited answer from both readable brains. Actual browser sharing has not been independently exercised; browser Alice/refusal/onboarding runs were verified.

## Architecture

```text
Source apps → Scalekit per-user pull ─┐
Recorded sample JSON ────────────────┴→ normalize + provenance
                                      → Cognee owner datasets
User question → readable dataset IDs → scoped recall
                                      → Respan gateway → cited answer
                                      → independent Python evaluator
Owner grant → additional readable dataset on subsequent recall
```

Full diagrams and screenshots: [README](https://github.com/minhducvo04/brainy/blob/codex/judge-demo-guide/README.md#judges-guide-see-the-demo-here). UI identity switching is a demo control, not production authentication. Source permissions are not continuously synchronized with stored memory.

## Reproduction

See the [README](https://github.com/minhducvo04/brainy/blob/codex/judge-demo-guide/README.md) for environment setup and the Apple Silicon dependency fix. From the repository root:

```bash
git clone --branch codex/judge-demo-guide https://github.com/minhducvo04/brainy.git
cd brainy
uv venv --python 3.12
uv pip install -r requirements.txt
cp .env.example .env
# Fill credentials locally; never commit .env.
.venv/bin/python -m brain.cli ingest --user alice --github sample_data/github.json --slack sample_data/slack.json --channels eng,general
.venv/bin/python -m brain.cli ingest --user bob --slack sample_data/slack.json --channels general
.venv/bin/python -m brain.demo_ui --port 8765
# Open http://127.0.0.1:8765/ on this computer.
# In a second terminal, evaluate the public initial set:
.venv/bin/python -m brain.cli eval --scenarios scenarios/scenarios.json --out runs/judge.json
.venv/bin/python -m eval.score --answers runs/judge.json
```

Required configuration: `RESPAN_API_KEY`; `LLM_PROVIDER`, `LLM_ENDPOINT`, `LLM_API_KEY`, `LLM_MODEL`; embedding provider/endpoint/key/model/dimensions as documented in `.env.example`. Live pulls additionally need `SCALEKIT_ENVIRONMENT_URL`, `SCALEKIT_CLIENT_ID`, `SCALEKIT_CLIENT_SECRET` and configured connections.

Judges can use `sample_data/` without our SaaS accounts, but need their own model/embedding credentials. For a repeat demo, use `scripts/reset_demo.sh` and wait for `Reset OK`; ingesting again does not remove prior sharing grants.

## Demo

- Local UI: run the commands above. No public hosted demo or video link is claimed.
- Three-minute pitch: explain fragmented decisions; identify the sample-input versus live-pull path; show Alice's cited answer; show Bob's refusal and onboarding answer; grant and ask again; show tracing and the measured regression; close with permission synchronization and mixed-question handling as next steps.
- Detailed presenter steps and screenshots are in README.

## Links

- Repo: https://github.com/minhducvo04/brainy
- Respan traces / eval runs: not yet attached.
- Writeup and diagrams: [README](https://github.com/minhducvo04/brainy/blob/codex/judge-demo-guide/README.md).
- Runnable demo branch: https://github.com/minhducvo04/brainy/tree/codex/judge-demo-guide

