import uuid
from brain.config import safe_forget

async def make_judge(client):
    async def judge_fn(question: str):
        try:
            ds = "judge_tmp_" + uuid.uuid4().hex
            await client.remember(
                "You are a strict reviewer. Answer only YES or NO.",
                dataset_name=ds, self_improvement=False,
            )
            res = await client.recall(question + " Answer YES or NO.", datasets=[ds])
            text = (res[0]["text"] if res else "").strip().upper()
            verdict = True if text.startswith("YES") else False if text.startswith("NO") else None
            await safe_forget(client, dataset=ds, everything=True)
            return verdict
        except Exception:
            return None
    return judge_fn
