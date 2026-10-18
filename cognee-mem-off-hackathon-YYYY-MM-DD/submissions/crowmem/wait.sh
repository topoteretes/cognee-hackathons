#!/bin/sh
# Blocks until post-session processing is done; exits non-zero on timeout.
# Crowmem's POST /events is synchronous -- salience scoring and extraction
# complete before the HTTP response returns, so there is no async backlog
# to drain here. This just reconfirms the service is alive within the
# runner's bound ($MEMOFF_WAIT_SECONDS, default 600).
set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
. "$SCRIPT_DIR/_common.sh"

TIMEOUT="${MEMOFF_WAIT_SECONDS:-600}"
i=0
while [ "$i" -lt "$TIMEOUT" ]; do
  if curl -sf "$CROWMEM_BASE_URL/health" >/dev/null 2>&1; then
    exit 0
  fi
  i=$((i + 1))
  sleep 1
done

echo "[crowmem] wait.sh TIMEOUT after ${TIMEOUT}s -- engine unreachable" >&2
exit 1
