import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASETS = ["baustein", "vitalis"]

TRUST_RANK = {
    "contract": 5, "handbook": 5, "email": 4, "meeting-notes": 4,
    "wiki": 3, "onboarding-doc": 3, "slack": 2, "none": 0,
}
REFRESH_HORIZONS = {  # days; None = durable
    "policy": None, "compliance": None,
    "model": 270, "pricing": 365, "budget": 365,
    "okr": 180, "milestone": 180, "default": 365,
}
THRESHOLDS = {
    "stale_retire": 2.0, "stale_judge_low": 1.0,
    "contradiction_trust_gap": 2, "recency_days": 180,
}

def load_env(path: Path | None = None) -> dict:
    path = path or (ROOT / ".env")
    env = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    for k, v in env.items():
        os.environ.setdefault(k, v)
    return env

def normalize_source(source: str) -> str:
    s = (source or "none").lower()
    if s.startswith("slack"):
        return "slack"
    return s if s in TRUST_RANK else "none"

def trust(source: str) -> int:
    return TRUST_RANK[normalize_source(source)]

async def get_client():
    import cognee
    env = load_env()
    return await cognee.serve(url=env["COGNEE_CLOUD_URL"], api_key=env["COGNEE_API_KEY"])

async def safe_forget(client, **kwargs) -> bool:
    """Best-effort forget. The cloud DELETE endpoint is flaky (returns 500);
    cleanup must never crash callers. Returns True if forget succeeded, else False."""
    try:
        await client.forget(**kwargs)
        return True
    except Exception:
        return False
