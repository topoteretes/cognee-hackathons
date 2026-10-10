import json
from pathlib import Path
from brain.router import Decision

def _what(d: Decision) -> str:
    if d.action in ("merge", "override", "hold"):
        w = d.winner.value if d.winner else "?"
        l = d.loser.value if d.loser else "?"
        return f'kept "{w}" ({d.winner.source}) | dropped/flagged "{l}" ({d.loser.source})'
    if d.action == "retire":
        return f'retired "{d.loser.value}" ({d.loser.source}, {d.loser.date})'
    if d.action in ("park", "quarantine", "keep_both"):
        vals = " / ".join(f.value for f in d.candidate.facts)
        return f'topic {d.candidate.topic}: {vals}'
    return d.candidate.topic

def write_receipt(d: Decision, as_of: str, md_path: Path, jsonl_path: Path) -> dict:
    client = d.candidate.facts[0].client
    rec = {"when": as_of, "action": d.action, "path": d.path,
           "what": _what(d), "why": d.reason, "client": client}
    line = f'{rec["when"]} | {rec["action"].upper()} | {rec["client"]} | {rec["what"]} | {rec["why"]} (via {rec["path"]})'
    with md_path.open("a") as f:
        f.write(line + "\n")
    with jsonl_path.open("a") as f:
        f.write(json.dumps(rec) + "\n")
    return rec

def health(open_debt: int) -> float:
    return 1.0 / (1 + open_debt)
