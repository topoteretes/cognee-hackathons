#!/bin/sh
# Idempotent: installs and starts the cognee-service this arm's hook and
# scripts talk to over HTTP. Safe to call more than once per container.
set -eu

STATE_DIR="$HOME/.memoff-cognee"
VENV="$STATE_DIR/venv"
PORT="${MEMOFF_COGNEE_PORT:-8057}"
SERVICE_URL="http://127.0.0.1:$PORT"
PIDFILE="$STATE_DIR/uvicorn.pid"
LOGFILE="$STATE_DIR/uvicorn.log"

mkdir -p "$STATE_DIR"

# Record the dataset name now, while the runner's env is guaranteed to carry
# it (install.sh runs once per (arm, repeat), matching MEMOFF_MEMORY_STORE's
# own lifetime per CONTRACT.md) -- wipe.sh/wait.sh fall back to this file if
# the live env var is ever missing when they run later in the same repeat.
if [ -n "${MEMOFF_MEMORY_STORE:-}" ]; then
  printf '%s' "$MEMOFF_MEMORY_STORE" > "$STATE_DIR/memory_store"
fi
printf '%s' "$SERVICE_URL" > "$STATE_DIR/service_url"

if [ ! -d "$VENV" ]; then
  python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install -q --upgrade pip
"$VENV/bin/pip" install -q "cognee==1.6.0" "uvicorn[standard]>=0.29.0"

cat > "$STATE_DIR/main.py" <<'PY'
# Stock cognee REST API, nothing custom -- same one-line pattern as
# apps/cognee-service/main.py in the Sthanuverse-org monorepo.
from cognee.api.client import app
__all__ = ["app"]
PY

# Already running (e.g. install.sh called again in the same container)?
if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  echo "install.sh: cognee-service already running (pid $(cat "$PIDFILE"))"
  exit 0
fi

# Keyless by design: this service is one throwaway instance per (arm,
# repeat), never shared across tenants, so cognee's default multi-tenant
# auth posture is the wrong fit -- same reasoning our production
# cognee-service README gives for its own ENABLE_BACKEND_ACCESS_CONTROL=False.
(
  cd "$STATE_DIR"
  ENABLE_BACKEND_ACCESS_CONTROL=False \
  LLM_PROVIDER=anthropic \
  LLM_MODEL=anthropic/claude-haiku-5-5 \
  LLM_API_KEY="${ANTHROPIC_API_KEY:-}" \
  EMBEDDING_PROVIDER=fastembed \
  EMBEDDING_MODEL=BAAI/bge-small-en-v1.5 \
  nohup "$VENV/bin/uvicorn" main:app --host 127.0.0.1 --port "$PORT" \
    > "$LOGFILE" 2>&1 &
  echo $! > "$PIDFILE"
)

i=0
until curl -sf "$SERVICE_URL/health" > /dev/null 2>&1; do
  i=$((i + 1))
  if [ "$i" -ge 60 ]; then
    echo "install.sh: cognee-service did not become healthy within 60s" >&2
    tail -n 40 "$LOGFILE" >&2 || true
    exit 1
  fi
  sleep 1
done

echo "install.sh: cognee-service healthy at $SERVICE_URL"
