#!/bin/sh
# Wait until the worker is idle (GET /api/processing-status returns
# {isProcessing, queueDepth, parkedSessions}), bounded. An unreachable worker or a
# response without these keys counts as not idle.
set -eu
port="${CLAUDE_MEM_WORKER_PORT:-37777}"
deadline=$(( $(date +%s) + ${MEMOFF_WAIT_SECONDS:-600} ))
while [ "$(date +%s)" -lt "$deadline" ]; do
  status="$(curl -fsS "http://127.0.0.1:${port}/api/processing-status" 2>/dev/null || echo '{}')"
  if printf '%s' "$status" | python3 -c 'import json,sys; d=json.load(sys.stdin); sys.exit(0 if d["isProcessing"] is False and d["queueDepth"]==0 and d.get("parkedSessions",0)==0 else 1)' 2>/dev/null; then exit 0; fi
  sleep 2
done
echo "wait.sh: claude-mem worker still processing after ${MEMOFF_WAIT_SECONDS:-600}s" >&2
exit 1
