#!/bin/sh
# Exits non-zero when $MEMOFF_MEMORY_STORE is not actually empty, so the
# runner can catch a wipe.sh that silently failed.
set -eu
DIR="$(dirname "$0")"
STATE_DIR="$HOME/.memoff-cognee"
STORE="${MEMOFF_MEMORY_STORE:-$(cat "$STATE_DIR/memory_store" 2>/dev/null || true)}"
if [ -z "$STORE" ]; then
  echo "wipe_check.sh: no memory store name available (MEMOFF_MEMORY_STORE unset)" >&2
  exit 1
fi
python3 "$DIR/scripts/wipe_dataset.py" --check "$STORE"
