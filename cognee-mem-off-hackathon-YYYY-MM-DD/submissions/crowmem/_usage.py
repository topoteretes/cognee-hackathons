"""Helper for usage.sh. stdlib only. Tracks a persistent "since" timestamp
per store (not per-issue state, which may not survive between issues) so
each call reports only new usage since the last call.
"""

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

BASE_URL = os.environ.get("CROWMEM_BASE_URL", "http://127.0.0.1:8765")
STORE = os.environ.get("MEMOFF_MEMORY_STORE", "manual-test")
HOME = os.environ.get("CROWMEM_HOME", os.path.join(os.path.expanduser("~"), ".crowmem"))
STATE_DIR = os.path.join(HOME, "usage_state")
STATE_FILE = os.path.join(STATE_DIR, f"{STORE}.since")


def _read_since() -> str | None:
    if not os.path.isfile(STATE_FILE):
        return None
    with open(STATE_FILE, encoding="utf-8") as f:
        return f.read().strip() or None


def _write_since(value: str) -> None:
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write(value)


def main() -> None:
    since = _read_since()
    now = datetime.now(timezone.utc).isoformat()

    params = {"project_id": STORE}
    if since:
        params["since"] = since
    url = f"{BASE_URL}/admin/usage?{urllib.parse.urlencode(params)}"

    with urllib.request.urlopen(url, timeout=30) as resp:
        records = json.load(resp)

    print(json.dumps(records))
    _write_since(now)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Exit non-zero and print nothing to stdout: CONTRACT.md treats
        # usage as "unmeasured (null), never zero" when it can't be
        # reported. An empty `[]` here would be misread as "confirmed
        # zero cost," which is a different (and false) claim.
        print(f"[crowmem] usage helper failed: {exc}", file=sys.stderr)
        sys.exit(1)
