# Mem0 Track 1 adapter

This submission runs the official Mem0 Claude Code memory plugin at commit
`0724291bd864cf807e88ee8981c8226644e8fb42` and adds only the lifecycle glue
required by the Mem Off entrant contract.

## Isolation

`MEMOFF_MEMORY_STORE` is mapped to both `MEM0_PROJECT_ID` and `MEM0_USER_ID`.
One repeat therefore has one remote Mem0 namespace shared by its eight fresh
Claude Code sessions. A different repeat gets a different namespace. Local
evidence and pending flush state live below
`~/.mem0-memoff/<MEMOFF_MEMORY_STORE>/`.

## Capture and recall

The upstream plugin records user prompts, assistant results, changed paths,
and bounded test/build results. `SessionEnd` hands the session to Mem0's
background extraction worker. On the next issue's first prompt, Mem0 searches
the shared namespace and injects up to five relevant coding memories.

The wrapper copies the exact `additionalContext` string to
`MEMOFF_INJECTED_DIR`. `receipt.sh` reports the corresponding memory ids,
ranks, scores, sizes, and recall latency without memory bodies.

## Required environment

```text
MEM0_API_KEY
```

Optional:

```text
MEM0_API_URL             # defaults to https://api.mem0.ai
MEMOFF_MEM0_DATA_ROOT    # defaults to ~/.mem0-memoff
```

Run `./install.sh` before loading `plugin/` with Claude Code. The installer
fetches and checks out the pinned upstream commit. No repository pre-index is
performed.

## Cost-accounting limitation

The Platform event API reports extraction completion and results but not the
managed model's per-event LLM or embedding tokens/cost. `usage.sh` therefore
returns an unmeasured server row. It deliberately does not claim that managed
memory processing costs zero.
