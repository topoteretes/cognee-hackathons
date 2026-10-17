# Mem Off Submission

## Team

- Team name: Sthanuverse
- Participants (GitHub handles): TODO — fill before opening the PR
- Contact for results (GitHub handle or email): TODO

## Track

- [x] Track 1 — Run a memory system (`memory.yml` + scripts in this folder)
- [ ] Track 2 — Extend the benchmark (`issues/<NN-slug>/ISSUE_PROPOSAL.md` in this folder)

## What you entered

### Track 1 — the memory system

- System name and version/commit: `cognee-diffmem` v1.0.0 — a thin Claude Code hook bundle
  over cognee's own REST API (`cognee==1.6.0`), not the marketplace `cognee-memory@cognee`
  plugin.
- Where it lives (repo link) and how the harness installs it (`install.sh` summary):
  `plugin/` in this folder (`plugin_dirs: ["plugin"]`). `install.sh` creates a venv,
  `pip install`s cognee + uvicorn, writes a one-line `main.py` (`from cognee.api.client
  import app`), and starts it as a background `uvicorn` process on `127.0.0.1:8057`,
  polling `/health` until ready. Idempotent via a pidfile.
- Hooks used (SessionStart / UserPromptSubmit / PostToolUse / Stop / SessionEnd / MCP / skills):
  `UserPromptSubmit` only. The write side (remembering each issue's diff) runs inside
  `wait.sh`, not a hook — `SessionEnd` is documented as best-effort and the sequencer
  already calls `wait.sh` as a separate step after the agent session exits and the
  code is committed, so nothing depends on an unreliable hook firing.
- Storage and declared network endpoints: local cognee-service (SQLite + fastembed
  vector index) under `~/.memoff-cognee`; one Anthropic endpoint declared in `network`
  (cognee's own extraction/graph-build calls, reusing the runner's `ANTHROPIC_API_KEY`).
  Embeddings are fully local (fastembed), no network call, no key.
- The memory system's own model(s): provider, model, embedding model — or `none`:
  `anthropic` / `claude-haiku-5-5` for extraction; `fastembed/BAAI/bge-small-en-v1.5`
  (local) for embeddings.
- Pre-index before issue 1? What does it index and how long does it take?
  No (`preindex: false`). This arm only remembers per-issue diffs as they happen; it
  does not pre-index xitkit's existing source tree.
- How `wipe.sh` empties the store and how `wipe_check.sh` proves it: `wipe.sh` calls
  `POST /api/v1/forget {"dataset": "$MEMOFF_MEMORY_STORE"}`. A 404 (dataset never
  created, e.g. repeat 1) is treated as already-empty, not a failure. `wipe_check.sh`
  calls `GET /api/v1/datasets` and fails if the dataset name is still listed.
- How `wait.sh` knows post-session processing is done: it calls cognee's `/remember`
  with no `session_id` and `run_in_background=false`, which blocks until cognify
  finishes building the graph — the call itself *is* the wait, nothing is polled
  afterwards.
- What `receipt.sh` reports (ids, ranks, reasons) and what `usage.sh` measures:
  `receipt.sh` prints the JSON `wait.sh` wrote (issue, dataset, chars written,
  elapsed time, cognee's own `status`) plus what the `UserPromptSubmit` hook recorded
  for that issue's recall (items recalled, chars injected) — no bodies. `usage.sh`
  reports an **estimate** (`chars_written / 4` as a token proxy, `cost_usd: null`) —
  cognee's REST API has no public per-call usage endpoint we could find; this is a
  known gap, not hidden.
- Anything non-default in the configuration, and why it is still fair:
  `ENABLE_BACKEND_ACCESS_CONTROL=False` on the cognee-service — disables cognee's
  multi-tenant auth, correct here because this is one throwaway service per (arm,
  repeat), never shared. Doesn't affect fairness: every arm gets its own isolated
  store regardless.

### Track 2 — the proposed issue(s)

Not entered.

## Recall story (Track 1, for the Best Recall Story award)

TODO — fill from `results/injected/issue-08/` and `results/receipts/issue-08.json`
once the organisers attach them.

## Memory report

Produced by the `memoff-memory-report` skill. TODO — run
`skills/memoff-memory-report/install.sh --event "Mem Off <date>" --team sthanuverse`
and fill this section at wrap-up.

- `report/memoff-report.md` and `report/memoff-report.json` present: TODO
- Runs recorded (count, of which smoke): TODO
- The one number you would show a judge, and the run folder it comes from: TODO

## Reproduction

```bash
# from the hackathon folder, with the harness installed and the cognee plugin present
memoff run --arms submissions/sthanuverse --repeats 1 --out /tmp/memoff-sthanuverse \
  --xitkit-source /path/to/xitkit --model <pinned model>
```

Environment variables your system needs (names only, never values):

```text
ANTHROPIC_API_KEY
```

## Links

- Repo: TODO — this PR, from a fork of `topoteretes/cognee-hackathons`
- Demo (Loom / YouTube) or local instructions: TODO
- Slides / write-up: TODO
- Anything else: This arm's design reuses patterns (not code) from our own
  production cognee integration — `apps/cognee-service` and `packages/cognee-client`
  in the Sthanuverse-org monorepo, which already runs cognee-backed session memory
  in a deployed Next.js app. `packages/harness/src/analyzeMemory.ts` there is a
  second, independent production use of the same `rememberTurn`/`recallContext`
  pattern, for a read-only repo-analysis flow — unrelated to this benchmark's
  coding-agent flow, cited here only as evidence this isn't a hackathon-only toy.

## Results

Written by the GitHub Action after the organisers' run. Do not edit `results/` by hand.
