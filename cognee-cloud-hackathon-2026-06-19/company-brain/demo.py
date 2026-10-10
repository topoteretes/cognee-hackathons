import asyncio, json, unicodedata
from pathlib import Path
from brain import config
from brain.judge import make_judge
from brain.ingest import ingest_facts
from brain.lint import run_lint

AS_OF = "2026-06-19"
MD, JL = Path("receipts.md"), Path("receipts.jsonl")

def load_questions():
    return [json.loads(l) for l in Path("eval/questions.jsonl").read_text().splitlines() if l.strip()]

def _norm(s):
    # the cloud LLM emits non-breaking hyphens/spaces (U+2011, U+00A0); fold them
    # so substring grading is about meaning, not invisible unicode quirks.
    s = s.replace("‑", "-").replace("‐", "-").replace(" ", " ")
    return unicodedata.normalize("NFKC", s).casefold()

async def ask(client, q):
    res = await client.recall(q["question"], datasets=[q["client"]])
    return (res[0]["text"] if res else "")

def grade(ans, q):
    a = _norm(ans)
    ok = all(_norm(s) in a for s in q["expect_contains"])
    bad = any(_norm(s) in a for s in q.get("must_not_contain", []))
    return ok and not bad

async def main():
    MD.write_text(""); JL.write_text("")   # fresh demo run
    client = await config.get_client()
    judge_fn = await make_judge(client)
    try:
        qs = load_questions()
        for name in config.DATASETS:
            await config.safe_forget(client, dataset=name, everything=True)
            await ingest_facts(client, name)

        print("\n=== BEFORE cleanup ===")
        before = {}
        for q in qs:
            a = await ask(client, q); before[q["question"]] = grade(a, q)
            print(f'[{ "OK" if before[q["question"]] else "WRONG" }] {q["question"]} -> {a[:90]}')

        print("\n=== LINT ===")
        total = {"before":0,"resolved_free":0,"needed_judge":0,"parked":0}
        for name in config.DATASETS:
            s = await run_lint(client, name, AS_OF, judge_fn, MD, JL)
            for k in total: total[k]+=s[k]
            print(f'{name}: {s}')

        print("\n=== AFTER cleanup ===")
        for q in qs:
            a = await ask(client, q); now = grade(a, q)
            flip = "FIXED" if (now and not before[q["question"]]) else ("OK" if now else "STILL WRONG")
            print(f'[{flip}] {q["question"]} -> {a[:90]}')

        # two-tier touch: a session-scoped follow-up
        await client.recall("Summarize what we just discussed.", datasets=["vitalis"], session_id="demo-1")
        print(f'\nclashes {total["before"]}->{total["parked"]} | '
              f'free {total["resolved_free"]} | judge {total["needed_judge"]} | parked {total["parked"]}')
        print(f'receipts -> {MD} ({len(JL.read_text().splitlines())} lines)')
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
