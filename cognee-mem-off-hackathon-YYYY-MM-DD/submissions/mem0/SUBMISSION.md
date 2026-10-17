# Mem Off Submission

## Team

- Team name: Mem0 Track 1 Adapter
- Participants (GitHub handles): @Helen123
- Contact for results (GitHub handle or email): @Helen123

## Track

- [x] Track 1 — Run a memory system (`memory.yml` + scripts in this folder)
- [ ] Track 2 — Extend the benchmark

## What you entered

### Track 1 — the memory system

- System name and version/commit: Mem0 Claude Code plugin at `0724291bd864cf807e88ee8981c8226644e8fb42`.
- Installation: `install.sh` clones the official repository and checks out the pinned commit.
- Hooks: SessionStart, UserPromptSubmit, PostToolUse, PostToolUseFailure, Stop, PreCompact, SessionEnd.
- Storage: Mem0 Platform plus an isolated local SQLite evidence store and pending queue.
- Models: managed Mem0 Platform extraction and embedding models; their exact identifiers are not exposed per event.
- Pre-index: no.
- Wipe: remote personal and project memories in the repeat-specific scope are deleted, then local evidence is removed; `wipe_check.sh` lists the same remote scope and checks local row counts.
- Wait: waits for pending handoffs and in-flight semantic extraction to reach a terminal successful state.
- Receipt: memory ids, ranks, scores, character counts, trigger and measured search latency; no bodies.
- Usage: honest unmeasured server row because Mem0 Platform does not expose per-event model tokens or cost.

### Track 2 — the proposed issue(s)

Not entered.

## Recall story (Track 1, for the Best Recall Story award)

In the live chained run, Issue 8 retrieved five memories in 629.378 ms and injected
1,206 characters. The injected context included the earlier `TaskService.find_task_files`
decision from Issue 1 and the Markdown read-only safety boundary from Issue 3. The Issue 8
diff then changed `xitkit/services.py` to implement controlled `.xit` discovery and passed
the visible gate. The receipt records ids, ranks and scores without memory bodies.

## Memory report

- `report/memoff-report.md` and `report/memoff-report.json` present: yes
- Runs recorded (count, of which smoke): 2, of which 0 smoke
- The one number you would show a judge, and the run folder it comes from: 33 retrieval
  items across seven later sessions in the live eight-issue run (`outputs/mem0-full-8`),
  with all 8 semantic flushes succeeding.

## Reproduction

```bash
export MEM0_API_KEY='<provided-by-runner>'
memoff run --arms submissions/mem0 --repeats 1 --out /tmp/memoff-mem0 \
  --xitkit-source /path/to/xitkit --model <pinned-model>
```

Environment variables required:

```text
MEM0_API_KEY
```

## Links

- Repo: https://github.com/mem0ai/mem0
- Demo: live Issue 1 pilot and live eight-issue chained run completed locally; the
  organisers' Action should produce the canonical attached result.
- Slides / write-up: `README.md`
- Anything else: managed-memory token and dollar cost remain explicitly unmeasured

## Results

Written by the GitHub Action after the organisers' run. Do not edit `results/` by hand.
