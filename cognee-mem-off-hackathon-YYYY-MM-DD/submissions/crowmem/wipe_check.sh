#!/bin/sh
# Exits non-zero when the store is not empty. Called by the runner after
# wipe.sh, per the contract.
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/_common.sh"

STORE="$(crowmem_store)"
COUNTS_JSON="$(curl -sf "$CROWMEM_BASE_URL/admin/projects/$STORE/counts")"

if printf '%s' "$COUNTS_JSON" | grep -Eq '"[a-z_]+": *[1-9]'; then
  echo "[crowmem] wipe_check FAILED, store not empty: $COUNTS_JSON" >&2
  exit 1
fi

echo "[crowmem] wipe_check OK: $COUNTS_JSON"
