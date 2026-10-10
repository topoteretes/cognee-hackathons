from dataclasses import dataclass, asdict
from pathlib import Path
from brain.facts import load_facts
from brain.drift import find_candidates
from brain.router import route
from brain.ledger import health
from brain.imposer import impose

def summarize(decisions) -> dict:
    parked = sum(1 for d in decisions if d.action in ("park", "quarantine"))
    judged = sum(1 for d in decisions if d.path == "judge" and d.action not in ("park", "quarantine"))
    free = sum(1 for d in decisions if d.path == "heuristic")
    return {"before": len(decisions), "resolved_free": free,
            "needed_judge": judged, "parked": parked,
            "after": parked, "health": health(parked)}

async def run_lint(client, name: str, as_of: str, judge_fn=None,
                   md=Path("receipts.md"), jl=Path("receipts.jsonl")) -> dict:
    cands = find_candidates(load_facts(name), as_of)
    decisions = [route(c, as_of, judge_fn) for c in cands]
    wrote = False
    for d in decisions:
        await impose(client, d, name, as_of, md, jl)
        if d.action in ("override", "merge", "hold", "retire"):
            wrote = True
    if wrote:
        # index the correctives the imposer wrote so recall reflects the resolution
        await client.cognify(datasets=name)
    return summarize(decisions)
