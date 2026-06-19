"""Push the locally-built brain up to Cognee Cloud for the bonus."""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cognee  # noqa: E402

from brain import config, cognee_client  # noqa: E402


async def main():
    if not config.cloud_configured():
        print("COGNEE_CLOUD_URL / COGNEE_API_KEY not set. Aborting push.")
        return
    await cognee_client.connect()
    result = await cognee.push(config.DATASET)
    print("push result:", result)


if __name__ == "__main__":
    asyncio.run(main())
