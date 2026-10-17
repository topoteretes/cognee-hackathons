"""Memory backends for the CogneeMind wiki.

Two interchangeable implementations behind the same small interface:
  * LocalWiki  — JSON file on disk, always works (no external deps). Default.
  * CogneeWiki — Cognee permanent graph + session memory (brain.py).

The agent loop only talks to this interface, so we can develop/demo without
Cognee and swap it in when the kickoff packages land.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Protocol

WIKI_PATH = Path(__file__).parent / "data" / "wiki.json"


def strategy_key(s: dict) -> str:
    w = s.get("soft_weights", {})
    return f"{s.get('priority_key')}|w{w.get('walking',1)}|s{w.get('stability',1)}"


class Memory(Protocol):
    def recall(self, signature: str) -> dict: ...
    def promote(self, signature: str, winner: dict, dead_ends: list[str],
                score: float, note: str) -> dict: ...
    def history(self) -> list: ...
    def lint(self) -> dict: ...


class LocalWiki:
    """File-backed fallback wiki. Mirrors what the Cognee permanent graph holds:
    a disruption->strategy index, a reusable strategy library, a dead-end list,
    and a version timeline."""

    def __init__(self, path: Path = WIKI_PATH):
        self.path = path
        self._load()

    def _load(self):
        if self.path.exists():
            self.db = json.loads(self.path.read_text())
        else:
            self.db = {"index": {}, "library": {}, "timeline": [], "version": 0}

    def _save(self):
        self.path.write_text(json.dumps(self.db, indent=2))

    def reset(self):
        """Cold-start the brain (empty wiki) — used for the compounding A/B test."""
        self.db = {"index": {}, "library": {}, "timeline": [], "version": 0}
        self._save()

    # -- warm start ------------------------------------------------------- #
    def recall(self, signature: str) -> dict:
        idx = self.db["index"]
        entry = idx.get(signature)
        if entry is None:
            # fuzzy: fall back to same disruption kind (text before first ':')
            kind = signature.split(":")[0]
            cands = [v for k, v in idx.items() if k.split(":")[0] == kind]
            entry = min(cands, key=lambda e: e.get("best_score", 1e9), default=None)
        if entry is None:
            return {"strategies": [], "dead_ends": [], "source": "cold"}
        winners = [self.db["library"][k] for k in entry["winners"] if k in self.db["library"]]
        return {"strategies": winners, "dead_ends": entry.get("dead_ends", []),
                "source": "warm", "best_score": entry.get("best_score")}

    # -- distillation ----------------------------------------------------- #
    def promote(self, signature: str, winner: dict, dead_ends: list[str],
                score: float, note: str) -> dict:
        wkey = strategy_key(winner)
        self.db["library"][wkey] = winner
        entry = self.db["index"].setdefault(signature, {"winners": [], "dead_ends": [], "best_score": 1e9})
        if wkey not in entry["winners"]:
            entry["winners"].insert(0, wkey)
        entry["dead_ends"] = sorted(set(entry["dead_ends"]) | set(dead_ends))
        entry["best_score"] = min(entry["best_score"], score)
        self.db["version"] += 1
        version = self.db["version"]
        self.db["timeline"].append({
            "version": version, "signature": signature,
            "strategy": winner.get("name", wkey), "priority_key": winner.get("priority_key"),
            "score": score, "note": note, "ts": time.time(),
        })
        self._save()
        return {"version": version}

    def history(self) -> list:
        return self.db["timeline"]

    def index(self) -> dict:
        return self.db["index"]

    # -- lint ------------------------------------------------------------- #
    def lint(self) -> dict:
        """Dedupe library, prune dead-end strategies from winner lists, keep
        only the best winner per signature; report what changed."""
        removed = 0
        for sig, entry in self.db["index"].items():
            before = len(entry["winners"])
            entry["winners"] = [w for w in entry["winners"] if w not in entry["dead_ends"]]
            # collapse to a single best winner (the head) — older ones are superseded
            if len(entry["winners"]) > 1:
                entry["winners"] = entry["winners"][:1]
            removed += before - len(entry["winners"])
        used = {w for e in self.db["index"].values() for w in e["winners"]}
        orphans = [k for k in self.db["library"] if k not in used]
        for k in orphans:
            del self.db["library"][k]
        self._save()
        return {"pruned_winners": removed, "pruned_library": len(orphans)}
