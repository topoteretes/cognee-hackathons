"""Thin wrapper: connect to Cognee Cloud if configured, otherwise run locally."""

import cognee
from cognee.modules.engine.operations.setup import setup

from . import config


_connected = False


async def connect():
    global _connected
    if _connected:
        return
    if config.cloud_configured():
        await cognee.serve(url=config.COGNEE_CLOUD_URL, api_key=config.COGNEE_API_KEY)
        print(f"[cognee] connected to Cloud: {config.COGNEE_CLOUD_URL}")
    else:
        print("[cognee] no Cloud creds — running locally")
    _connected = True


async def reset():
    """Wipe everything and re-initialise. Use sparingly — kills all prior memory."""
    await cognee.prune.prune_data()
    await cognee.prune.prune_system(metadata=True)
    await setup()
