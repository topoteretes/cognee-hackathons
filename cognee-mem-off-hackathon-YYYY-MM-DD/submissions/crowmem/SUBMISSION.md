# Mem Off Submission

## Team

- Team name: Crowmem
- Participants (GitHub handles): @rwberndt
- Contact for results (GitHub handle or email): @rwberndt

## Track

- [x] Track 1 — Run a memory system (`memory.yml` + scripts in this folder)
- [ ] Track 2 — Extend the benchmark (`issues/<NN-slug>/ISSUE_PROPOSAL.md` in this folder)

## What you entered

### Track 1 — the memory system

- System name and version/commit: Crowmem; engine pinned to `6c925b6b084430eb6e246abf5b6262a623e44056`. The bundled adapter uses the hook scripts in this submission.
- Where it lives (repo link) and how the harness installs it (`install.sh` summary): [Crowmem](https://github.com/rwberndt/Crowmem). `install.sh` installs PostgreSQL and pgvector, downloads Python 3.12 with uv, checks out the pinned engine commit, installs its Python dependencies, migrates the database, and starts a local FastAPI service on port 8765.
- Hooks used (SessionStart / UserPromptSubmit / PostToolUse / Stop / SessionEnd / MCP / skills): UserPromptSubmit, PostToolUse, Stop, and SessionEnd. The first recalls memory; selected code edits and explicit tool failures create memory. Stop also records one agent self-report per issue, covering sessions where all successful edits use Bash. Stop and SessionEnd record self-reported outcomes. No SessionStart, MCP, or entrant skill hook is registered.
- Storage and declared network endpoints: Local PostgreSQL with pgvector at `127.0.0.1:5432`; local service at `127.0.0.1:8765`. Installation downloads from GitHub, PyPI, and files.pythonhosted.org; the first embedding downloads model weights from Hugging Face; extraction calls `api.anthropic.com`. Fastembed inference runs locally.
- The memory system's own model(s): provider, model, embedding model — or `none`: Anthropic `claude-haiku-4-5` for extraction; local fastembed `BAAI/bge-small-en-v1.5` for embeddings.
- Pre-index before issue 1? What does it index and how long does it take? No pre-indexing (`preindex: false`). The store begins empty and only receives observations through hooks.
- How `wipe.sh` empties the store and how `wipe_check.sh` proves it: `wipe.sh` calls `DELETE /admin/projects/$MEMOFF_MEMORY_STORE`; `wipe_check.sh` calls the project's `/counts` endpoint and fails if a count is positive.
- How `wait.sh` knows post-session processing is done: Event extraction completes synchronously before the hook's HTTP response. `wait.sh` checks the local `/health` endpoint within `MEMOFF_WAIT_SECONDS`.
- What `receipt.sh` reports (ids, ranks, reasons) and what `usage.sh` measures: `receipt.sh` returns a JSON injection receipt with ids, ranks, and reasons, without memory bodies. `usage.sh` reports the engine's incremental server-side model token and cost records since the previous call.
- Anything non-default in the configuration, and why it is still fair: Crowmem filters routine tool reads and successful shell output to limit observer spend, then stores the agent's own final issue summary as a fallback. It uses its own Haiku extraction calls, which are declared and reported by `usage.sh`. Stop-hook reinforcement uses the agent's own `STATUS` line as a proxy because hooks cannot see the private grader; it is not ground truth.

### Track 2 — the proposed issue(s)

No Track 2 proposal.

## Recall story (Track 1, for the Best Recall Story award)

In a local two-issue probe, Issue 2 received two memories at ranks 1 and 2 (392 injected characters) from the Issue 1 completion summary. Issue 2 met its public visible target. This single run does not show whether the recall caused the pass. The organizers' issue-8 injected dump and receipt are still needed for the award story.

## Memory report

Produced according to the `memoff-memory-report` skill in this event repository. The files record only observed local evidence and mark official results as pending.

- `report/memoff-report.md` and `report/memoff-report.json` present: yes
- Runs recorded (count, of which smoke): 3 completed harness runs, including 1 smoke run; a corrected eight-issue run is in progress.
- The one number you would show a judge, and the run folder it comes from: 392 characters from two recalled items injected into Issue 2 in `/runs/crowmem-memory-probe`; the observed pass does not establish a causal memory effect.

## Reproduction

```bash
# From this event folder, with the harness and cognee plugin installed:
memoff run --arms submissions/crowmem --repeats 1 --out /tmp/memoff-crowmem \
  --xitkit-source /path/to/xitkit --model claude-sonnet-5-5
```

Environment variables your system needs (names only, never values):

```text
ANTHROPIC_API_KEY
```

## Links

- Repo: https://github.com/rwberndt/Crowmem
- Demo (Loom / YouTube) or local instructions: The reproduction command above and the submitted `install.sh` provide local instructions.
- Slides / write-up: None.
- Anything else: The public harness currently sets entrant `usage_complete` to false before `usage.sh` runs, so its total cost remains unmeasured even when both agent and server costs are recorded. The local report keeps them separate. The organizers' Action will attach official `results/`.

## Results

Written by the GitHub Action after the organizers' run. No `results/` is included in this PR.
