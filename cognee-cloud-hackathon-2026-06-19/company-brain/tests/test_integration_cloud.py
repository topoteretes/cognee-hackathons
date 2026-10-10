import os
import pytest
from brain import config

pytestmark = pytest.mark.integration

def _has_key():
    config.load_env()
    return bool(os.environ.get("COGNEE_API_KEY") and os.environ.get("COGNEE_CLOUD_URL"))

@pytest.mark.skipif(not _has_key(), reason="no cloud creds")
@pytest.mark.asyncio
async def test_cloud_connects():
    client = await config.get_client()
    try:
        assert client.__class__.__name__ == "CloudClient"
    finally:
        await client.close()

@pytest.mark.skipif(not _has_key(), reason="no cloud creds")
@pytest.mark.asyncio
async def test_judge_returns_bool_or_none():
    from brain.judge import make_judge
    client = await config.get_client()
    try:
        jf = await make_judge(client)
        verdict = await jf("Is the sky blue?")
        assert verdict in (True, False, None)
    finally:
        await client.close()

@pytest.mark.skipif(not _has_key(), reason="no cloud creds")
@pytest.mark.asyncio
async def test_ingest_facts_then_recall():
    from brain.ingest import ingest_facts
    client = await config.get_client()
    try:
        n = await ingest_facts(client, "baustein")
        assert n >= 10
        res = await client.recall("Which LLM does RFI Copilot use?", datasets=["baustein"])
        assert res and "text" in res[0]
    finally:
        await config.safe_forget(client, dataset="baustein", everything=True)
        await client.close()
