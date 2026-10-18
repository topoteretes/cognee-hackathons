#!/bin/sh
# Empties the memory store for $MEMOFF_MEMORY_STORE. The runner calls
# wipe_check.sh after this to verify it actually worked.
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/_common.sh"

STORE="$(crowmem_store)"
curl -sf -X DELETE "$CROWMEM_BASE_URL/admin/projects/$STORE" >/dev/null
echo "[crowmem] wiped store: $STORE"
