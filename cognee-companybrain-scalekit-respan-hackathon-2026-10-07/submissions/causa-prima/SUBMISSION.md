# Team Submission

## Team

- Team name: Causa Prima
- Company Brain / project name: Company Brain: the company-wide standup and cited Q&A
- Code: https://github.com/pmigueli/company-brain-public (public, synthetic sample data only)

## Company Brain Overview

In a growing team, people spend part of every day re-aligning. A decision gets made in one channel
and doesn't reach the people it affects. Two people file tickets for the same bug. A new version of a
flow goes into one document while the spec still describes the old one. The brain reads each person's
Slack, Linear, Notion and Granola through Scalekit, acting as that person, and remembers what they saw
in their own Cognee brain. From that it writes two things. The first is a **company-wide standup**
built from everyone's activity, not just the reader's: exec summary, Yesterday / Today / Blockers per
person, risks, opportunities, and an access line. The second is **answers to questions with a source
link on every claim**. It always works as the user asking, and it uses only what that user may read.

- Data sources connected through Scalekit (≥ 2 apps): Slack, Linear, Notion, Granola (4 apps). On the live run, Linear, Notion and Granola were pulled for both users; the Slack history pull hit Scalekit/Slack rate limits (429) before finishing, so the live brains were built without Slack messages (channel membership was pulled). The synthetic sample includes Slack.
- Primary use case / team workflow: the morning standup and the "who decided this, which ticket, who owns it" questions that today cost a round of pings
- Users in the demo and how their access differs: two users, User A and User B. Each connects the four apps with their own accounts and reads only their own brain until the other grants theirs. A is in channels B is not in, B in channels A is not in, and each has their own meeting notes. The public sample mirrors this with Alice and Bob at a fictional *Acme Robotics*.
- What makes it stand out:
  - **Synthesis across people.** The risks section reports what only shows up when you look across sources and people: duplicate tickets for one bug, a doc that contradicts a newer flow, a decision that affects someone who was not there.
  - **Every claim is cited** with the link to its Slack message, Linear issue, Notion page or meeting note.
  - **It is honest about access.** The agent knows which brains the user cannot read, and it says when the answer may be in one of them.

## The Three Layers

### Pull — Scalekit

- Connections created (`connection_name` → app): `slack` → Slack, `linear` → Linear, `notion` → Notion, `granola` → Granola (MCP connector). Names are configurable with `SCALEKIT_*_CONNECTION`.
- Tools called:
  - Slack: `slack_auth_test`, `slack_list_users`, `slack_list_user_conversations`, `slack_fetch_conversation_history`, and optionally `slack_get_conversation_replies`
  - Linear: `linear_graphql_query` (issues updated in the window, with comments and relations)
  - Notion: `notion_page_search`, `notion_page_markdown_get`
  - Granola: `granolamcp_list_meetings`, `granolamcp_get_meetings`
- How users are identified (`identifier` ↔ Cognee user): the user's work email is the Scalekit `identifier` and also the Cognee user's email. Every Scalekit call passes it, so Scalekit injects that user's token, and the source app enforces that user's permissions before anything reaches us.
- Any write-back actions the agent takes: none in this build. The standup is written to `out/standup-<date>-<user>.md`, and a person posts it. The next step is posting it to Slack through Scalekit as the acting user, as a draft behind a confirmation step.
- Pull scope: public internal channels only. Channels shared with other organisations are skipped, as is any channel matching `BRAIN_EXCLUDE_CHANNELS`. Thread replies are off by default because they hit Slack rate limits. Calls back off on 429 responses, and Slack channels are pulled one at a time.
- Code entry point: `brain/pull.py` (`python -m brain.pull --user <email>`), `brain/scalekit_client.py`

### Remember — Cognee

- What goes into the permanent graph (`cognee.remember(...)` without `session_id`):
  - Compact provenance records in the form `[source · who · when · link] text`: one per Slack message, Linear issue (with relations and its last comments), Notion page and Granola meeting note.
  - Records are batched into documents of about 8k characters, one group per channel (Slack), team (Linear) or source.
  - Scope: Linear issues from the teams in `BRAIN_LINEAR_TEAMS` only. Notion pages, excluding finance, GTM and HR titles. Activity from the last 3 days. Notion pages edited in the last 14 days. Older items the scenarios need can be pinned with `BRAIN_PINNED_TICKETS` / `BRAIN_PINNED_TEXT` (none by default).
- What stays in session memory (`session_id=...`), if anything: nothing (reasons under Memory Design).
- `node_set` tags used for provenance: `source:slack|linear|notion|granola`, `channel:<name>` (Slack) or `team:<name>` (Linear), and `owner:<email>`
- Datasets and who owns / can read each: one `<name>-brain` per user, owned and readable only by that user (sample: `alice-brain`, `bob-brain`). After the grant, B also reads A's brain.
- Access control: `ENABLE_BACKEND_ACCESS_CONTROL=true` is set in `brain/memory.py` before Cognee is imported. A grant is owner → grantee `read` on one dataset through `authorized_give_permission_on_datasets`. A shared dataset is reached by id. A user who addresses another user's dataset by name gets `DatasetNotFoundError` (`brain/verify.py` checks every pair of users).
- Anything beyond defaults:
  - The agent recalls with `query_type=SearchType.CHUNKS`. That returns the raw records, headers included, so the answer can cite them. Ticket keys in the question get an extra `SearchType.CHUNKS_LEXICAL` keyword lookup, because vector search ranks exact identifiers poorly.
  - Extraction runs on `openai/gpt-4.1-mini` through the gateway, which was 3.4x faster per call than gpt-5-mini.
  - Graph extraction uses the default model. We deferred a custom graph model on purpose (see Memory Design).
- Code entry point: `brain/ingest.py` (`python -m brain.ingest`), `brain/split.py`, `brain/memory.py`

### Act + Evaluate — your agent(s) + Respan

- Agent(s) and the task each performs (`brain/agent.py`):
  - `ask --as <email> "<q>"` gives a cited answer from the user's readable brains.
  - `standup --as <email>` runs 8 recall queries (shipped, in progress, blockers, decisions, duplicates, outdated docs, releases, meeting action items) and makes one synthesis call.
  - `grant --from --to --dataset` lets an owner share their brain; `revoke` undoes it.
- LLM calls routed through the Respan gateway? Yes, all of them:
  - Cognee extraction: `openai/gpt-4.1-mini`
  - embeddings: `openai/text-embedding-3-large` (3072 dimensions)
  - the agent's answer: `gpt-4.1` at temperature 0, via the OpenAI SDK with `base_url=https://api.respan.ai/api`
- How the runs are traced: `respan-ai` SDK, `Respan(instrumentations=[OpenAIInstrumentor()])`. `@workflow` (`ask_brain`, `standup`) wraps `@task(name="recall")` and `@task(name="answer")`, so each run is a workflow → recall → answer span tree.
- Scenario file / Respan testset:
  - Real company run: 11 scenarios over our own data. They stay private and are not in this repo.
  - `sample/scenarios.json`: 8 scenarios over the synthetic sample, the access pair included. Fields: `question`, `as_user`, `must_mention`, `must_not_mention`, `expected_sources`, `story`.
- Evaluator: a Python fact check, independent of the agent (`eval/run.py`). The score is the share of `must_mention` facts present (case insensitive), and 0 if any `must_not_mention` fact appears. The evaluator also records whether the answer cites a link, and the latency. `--mode baseline` scores Cognee's own `recall()` answer, and `--mode agent` scores the agent.
- Code entry point: `brain/agent.py`, `eval/run.py`

## Memory Design

- **Per-user brains, not a shared team dataset. This was a deliberate choice.** We follow the challenge
  README's "one Scalekit identifier, one Cognee user" pattern: everything a user pulls goes into one
  dataset only that user can read. We first built the other layout: a team dataset for material
  everyone sees, plus a private dataset for the rest. We dropped it for three reasons.
  - Cognee permissions are dataset-level only.
  - Each dataset is its own isolated graph, so entities don't link across datasets.
  - Splitting one person's world by who else can see each item breaks it into disconnected pieces.
    The same person, ticket or decision would be two unlinked nodes.
- **The cost, accepted:** material two users both see is extracted into each brain that can see it.
  That covers a channel both are in, a Linear issue both can read, and a meeting both attended. For a
  meeting, each attendee has their own Granola note, so the meeting appears in both brains. That is
  correct: each brain holds what that person saw. It costs more extraction, but every graph is
  complete and connected across Slack, Linear, Notion and Granola.
- **A team view comes from grants.** An owner grants read access to their brain. The agent recalls
  over every dataset the user can read, merges the results when it answers, and cites each record's
  own link. Cross-dataset merging happens in our agent, not in Cognee.
- **Provenance:** the `node_set` tags carry source, channel or team, and owner. Every record header
  repeats source, author, time and link inside the text, so a recalled chunk can be cited without a
  second lookup.
- **Default extraction:** we kept Cognee's default graph model and deferred a custom one with
  person, ticket and decision identities. Getting the access story and the eval right came first, in
  the hours available.
- **No session memory:** the standup is a daily batch job and each question is answered from scratch.
  Session state would mix what the agent said with what people wrote, and every claim has to trace back
  to a source record.

## Evaluation Evidence

The real company run is reported as numbers only: its data and scenarios stay private. The synthetic
sample reproduces the same kinds of questions and can be run by anyone.

### Baseline Run

- Respan trace / eval run link: https://platform.respan.ai (traces: workflow -> recall -> answer). Baseline mode calls `cognee.recall()` directly, so its LLM calls appear in the gateway log, not as agent workflows.
- Scenarios run: 11 (real company data, per-user brains)
- Mean score: **0.64**. 0% of answers cited a source.
- Where it failed: identifier questions (which ticket duplicates which, who filed it) and ownership
  questions. Cognee's default answer carries no source link, and vector recall ranks exact ticket keys
  poorly.

### Improved Run

- Respan trace / eval run link: https://platform.respan.ai (traces: workflow -> recall -> answer). Each scenario is one `ask_brain` workflow.
- What changed in the brain or agent between runs: we stopped using Cognee's default answer. For each dataset the user can read, the agent recalls the raw provenance records (`CHUNKS`, plus a `CHUNKS_LEXICAL` keyword lookup for ticket keys), then makes one cited answer call through Respan.
- Mean score: **1.00**. 100% of answers cited a source.

```text
Real company data   baseline: mean = 0.64   cited 0%     (n = 11)
                    agent:    mean = 1.00   cited 100%   (n = 11)
Synthetic sample    agent:    mean = 1.00                (n = 8)
```

## Access Story

On the real company data:

- User A and User B each connect Slack, Linear, Notion and Granola through Scalekit with their own accounts, and each reads only their own brain.
- Question asked by both: one whose answer exists only in one of User A's private meeting notes, from a call B did not attend.
- Result for A: the correct answer, citing that meeting note.
- Result for B before the share: B's recall covers B's brain only, so A's call never surfaces. The scenario's `must_not_mention` facts did not leak (score 1.0). The agent's system prompt lists the brains B cannot read, so it can say the answer may be incomplete.
- After A grants B `read` on A's brain, B's answer draws on both brains and cites the same meeting note.

The same story on the synthetic sample, runnable by anyone:

- User A: `alice@example.com`. Datasets readable: `alice-brain`. Alice has a private Granola call about a second warehouse site.
- User B: `bob@example.com`. Datasets readable: `bob-brain`. Bob is in `#ops-night-shift`, which Alice is not in; Alice is in `#leadership`, which Bob is not in.
- Question asked by both: "What is the codename of the second warehouse site, and which city is it in?"
- Result for A: the codename and the city, citing her Granola note (scenario `site-alice`).
- Result for B before the share: neither fact nor the meeting id appears (scenario `site-bob`, `must_not_mention`), and the agent says some context may sit in datasets Bob cannot read.
- The grant: `python -m brain.agent grant --from alice@example.com --to bob@example.com --dataset alice-brain`, through `authorized_give_permission_on_datasets`. Bob's readable set becomes `['alice-brain', 'bob-brain']`.
- Result for B after the share: the agent recalls from both brains and gives Alice's answer, with the same meeting-note citation. `revoke` (same flags) undoes the grant for a rehearsal.

## Architecture

```text
[ Scalekit connections, per user: Slack · Linear · Notion · Granola ]
        |
        | execute_tool(tool, input, connection_name, identifier=<user email>)      brain/pull.py
        v
[ data/raw/<email>/<source>.jsonl ]  -> scope + window, one dataset per user       brain/split.py
        |
        | remember(records, dataset_name="<name>-brain", user=<that user>,
        |          node_set=[source:*, channel:*|team:*, owner:*])                 brain/ingest.py
        v
[ Cognee: one isolated graph per user, ENABLE_BACKEND_ACCESS_CONTROL=true ]
        |   access enforced here: recall only over the asking user's readable datasets;
        |   grant = owner shares read on their brain                               brain/memory.py
        | recall(question, dataset_ids=<readable>, user=<asker>, query_type=CHUNKS | CHUNKS_LEXICAL)
        v
[ agent: ask / standup, traced by Respan (workflow -> recall -> answer) ]           brain/agent.py
        |   one cited gpt-4.1 call via the Respan gateway -> answer / standup markdown
        v
[ fact-check scorer over scenarios.json ]  -> baseline vs agent, before/after       eval/run.py
```

Access is enforced twice. Scalekit runs every pull as the user, so a source returns only what that
user's account can see. Cognee then lets the agent recall only from datasets the user owns or was
granted.

## Reproduction

Everything runs on the synthetic sample, with only a Respan key. The full walkthrough is in the
[README](README.md).

```bash
python3.13 -m venv .venv
.venv/bin/pip install "cognee>=1.6.3" scalekit-sdk-python python-dotenv "respan-ai>=4" respan-instrumentation-openai openai
cp .env.example .env    # fill in the Respan key (LLM_API_KEY, EMBEDDING_API_KEY, RESPAN_API_KEY); BRAIN_NOW is already set
.venv/bin/python -m brain.split                      # what will be remembered; no Cognee, no LLM
.venv/bin/python -m brain.ingest
.venv/bin/python -m eval.run --mode baseline --label sample-baseline
.venv/bin/python -m eval.run --mode agent --label sample-agent
.venv/bin/python -m brain.agent ask --as bob@example.com "What is the codename of the second warehouse site, and which city is it in?"   # before the grant
.venv/bin/python -m brain.agent grant --from alice@example.com --to bob@example.com --dataset alice-brain
.venv/bin/python -m brain.agent ask --as bob@example.com "What is the codename of the second warehouse site, and which city is it in?"   # after the grant
.venv/bin/python -m brain.agent standup --as alice@example.com
```

Environment variables required:

```text
RESPAN_API_KEY                # Respan gateway credits: agent answer + tracing
LLM_PROVIDER / LLM_ENDPOINT / LLM_API_KEY / LLM_MODEL      # cognee -> Respan gateway (openai/gpt-4.1-mini)
EMBEDDING_PROVIDER / EMBEDDING_ENDPOINT / EMBEDDING_API_KEY / EMBEDDING_MODEL / EMBEDDING_DIMENSIONS
ENABLE_BACKEND_ACCESS_CONTROL=true
BRAIN_NOW=2026-10-08T00:00:00+00:00                         # the sample only
SCALEKIT_ENVIRONMENT_URL      # live pulls only
SCALEKIT_CLIENT_ID            # live pulls only
SCALEKIT_CLIENT_SECRET        # live pulls only
# optional: BRAIN_RAW_DIR (default sample/raw), BRAIN_USERS (default alice/bob), BRAIN_COMPANY,
#           BRAIN_LOCAL_PASSWORD, BRAIN_LINEAR_TEAMS, BRAIN_PINNED_TICKETS, BRAIN_PINNED_TEXT,
#           BRAIN_EXCLUDE_CHANNELS, ANSWER_MODEL, SCALEKIT_*_CONNECTION, SLACK_FETCH_REPLIES,
#           SYSTEM_ROOT_DIRECTORY / DATA_ROOT_DIRECTORY (absolute paths)
```

`sample/raw/alice@example.com/` and `sample/raw/bob@example.com/` hold synthetic Slack, Linear,
Notion and Granola data for a fictional company, *Acme Robotics*. The files use exactly the record
shapes `brain/pull.py` writes, and `sample/scenarios.json` holds 8 scenarios over them, the access
story included. The defaults point the code at the sample, so no Scalekit account is needed.

## Demo

- Live demo link (Loom, YouTube, etc.) or local instructions: shown live from a laptop. Locally: [README](README.md), run A.
- 3-minute pitch outline:

```text
1. Problem: the same bug filed twice, two live versions of one flow, a decision that reaches the
   people it affects too late. Nobody can be in every conversation.
2. Pull: brain.pull as User A, all four sources through Scalekit, no token in sight
3. Brain: cognee-cli -ui, one user's graph connecting a Slack thread, a Linear ticket and a meeting note,
   then a cross-source answer with citations
4. Access: User B asks a question whose answer is only in A's private call and doesn't get it.
   A grants their brain, B asks again and gets the answer with the same citation
5. Agent: today's company-wide standup, traced in Respan (workflow -> recall -> answer)
6. Eval: baseline 0.64 vs agent 1.00 (n = 11), cited 0% -> 100%, one sentence on the change
7. Next: post the standup to Slack as a draft through Scalekit, plus a custom graph model for people,
   tickets and decisions
```

## Links

- Repo: https://github.com/pmigueli/company-brain-public (public, synthetic sample data only)
- Respan traces / eval runs: https://platform.respan.ai (traces: workflow -> recall -> answer)
- Slides / writeup: this file and the [README](README.md)
