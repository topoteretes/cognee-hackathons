#!/bin/sh
set -eu

PIN="0724291bd864cf807e88ee8981c8226644e8fb42"
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
RUNTIME="$ROOT/.runtime/mem0"

if [ ! -d "$RUNTIME/.git" ]; then
  mkdir -p "$ROOT/.runtime"
  git clone --quiet https://github.com/mem0ai/mem0.git "$RUNTIME"
fi

CURRENT="$(git -C "$RUNTIME" rev-parse HEAD 2>/dev/null || true)"
if [ "$CURRENT" != "$PIN" ]; then
  git -C "$RUNTIME" fetch --quiet origin "$PIN"
  git -C "$RUNTIME" checkout --quiet --detach "$PIN"
fi

test -f "$RUNTIME/integrations/claude-code-plugin/core/memory_core.py"
test -f "$RUNTIME/integrations/claude-code-plugin/adapters/claude/transcript.py"
test -f "$ROOT/plugin/hooks/hooks.json"

printf 'Mem0 plugin source pinned at %s\n' "$PIN"
if [ -z "${MEM0_API_KEY:-}" ]; then
  printf '%s\n' 'MEM0_API_KEY is not set; install is complete, but a live run will require it.' >&2
fi
