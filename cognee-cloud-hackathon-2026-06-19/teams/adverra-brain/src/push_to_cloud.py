"""Push the locally-built brain up to Cognee Cloud (optional, rewarded bonus).

Credentials come from the environment — never hardcode the API key:
    export COGNEE_CLOUD_URL="https://your-instance.cognee.ai"
    export COGNEE_API_KEY="ck_..."

Run:
    python -m src.push_to_cloud
"""

from __future__ import annotations

import asyncio
import os

import cognee

from .brain import DATASET


async def push() -> None:
    url = os.environ.get("COGNEE_CLOUD_URL", "").strip()
    api_key = os.environ.get("COGNEE_API_KEY", "").strip()
    if not (url and api_key):
        raise SystemExit("Set COGNEE_CLOUD_URL and COGNEE_API_KEY to push to Cloud.")

    await cognee.serve(url=url, api_key=api_key)
    print(f"[push] uploading '{DATASET}' to {url} ...")
    result = await cognee.push(DATASET)  # mode='preserve' => no remote LLM calls
    print("[push] done:", result)


if __name__ == "__main__":
    asyncio.run(push())
