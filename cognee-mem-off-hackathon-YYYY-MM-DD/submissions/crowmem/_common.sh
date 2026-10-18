#!/bin/sh
# Shared config/helpers for the Crowmem Mem Off adapter scripts. Not one of
# the contract's named scripts itself -- sourced by all of them.

CROWMEM_PORT="${CROWMEM_PORT:-8765}"
CROWMEM_BASE_URL="http://127.0.0.1:${CROWMEM_PORT}"
CROWMEM_HOME="${CROWMEM_HOME:-$HOME/.crowmem}"
CROWMEM_ENGINE_DIR="$CROWMEM_HOME/engine"
CROWMEM_VENV="$CROWMEM_ENGINE_DIR/.venv"
CROWMEM_PIDFILE="$CROWMEM_HOME/uvicorn.pid"
CROWMEM_REPO_URL="${CROWMEM_REPO_URL:-https://github.com/rwberndt/Crowmem.git}"
CROWMEM_PINNED_COMMIT="6c925b6b084430eb6e246abf5b6262a623e44056"  # keep in sync with memory.yml's version field

# The store the memory system actually uses, shared across one (arm,
# repeat)'s eight issues -- this is our project_id. Defaults to a fixed
# name so each script is also runnable by hand outside the harness.
crowmem_store() {
  printf '%s' "${MEMOFF_MEMORY_STORE:-manual-test}"
}
