"""CogneeMind simulator: gate-assignment optimization + scoring.

The actual assignment is deterministic Python (greedy by a priority rule), so
scoring is fast and reproducible. The *brain* (agents + Cognee wiki) only
chooses and tunes the STRATEGY spec that this module executes.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent / "data"
BUFFER_MIN = 15  # turnaround buffer after departure before the gate frees up


# --------------------------------------------------------------------------- #
# Time helpers (internal representation is minutes since midnight)
# --------------------------------------------------------------------------- #
def hhmm_to_min(s: str) -> int:
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def min_to_hhmm(t: int) -> str:
    t = int(round(t))
    return f"{t // 60:02d}:{t % 60:02d}"


# --------------------------------------------------------------------------- #
# Data models
# --------------------------------------------------------------------------- #
@dataclass
class Gate:
    id: str
    position: int          # 1 = closest to terminal, higher = farther
    type: str              # "domestic" | "international" | "both"
    terminal: str
    label: str = ""
    closed_windows: list[tuple[int, int]] = field(default_factory=list)

    def accepts(self, flight: "Flight") -> bool:
        if self.type != "both" and self.type != flight.type:
            return False
        return True

    def is_open(self, start: int, end: int) -> bool:
        for cs, ce in self.closed_windows:
            if start < ce and cs < end:  # overlaps a closed window
                return False
        return True


@dataclass
class Flight:
    id: str
    airline: str
    arrival: int           # minutes
    departure: int         # minutes
    type: str              # "domestic" | "international"
    preferred: list[str] = field(default_factory=list)
    delay: int = 0         # minutes shifted by disruptions (already folded into arr/dep)

    @property
    def turnaround(self) -> int:
        return self.departure - self.arrival

    def occupies(self) -> tuple[int, int]:
        """Window the gate is busy, including buffer."""
        return (self.arrival, self.departure + BUFFER_MIN)


# --------------------------------------------------------------------------- #
# Strategy spec — this is what the Researcher agent discovers / mutates and
# what the Cognee wiki stores as a reusable building block.
# --------------------------------------------------------------------------- #
PRIORITY_KEYS = {
    "earliest_arrival":     lambda f: (f.arrival, f.departure),
    "earliest_departure":   lambda f: (f.departure, f.arrival),
    "tightest_turnaround":  lambda f: (f.turnaround, f.arrival),
    "longest_first":        lambda f: (-f.turnaround, f.arrival),
    "latest_departure":     lambda f: (-f.departure, f.arrival),
    # international flights fit fewer gates -> place the most constrained first
    "constrained_first":    lambda f: (0 if f.type == "international" else 1, f.arrival),
}


def default_strategy() -> dict:
    return {
        "name": "baseline",
        "priority_key": "earliest_arrival",
        "soft_weights": {"walking": 1.0, "stability": 1.0},
        "applies_to": "base",
    }


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def load_gates(path: Optional[Path] = None) -> list[Gate]:
    raw = json.loads((path or DATA_DIR / "gates.json").read_text())
    return [Gate(g["id"], g["position"], g["type"], g["terminal"], g.get("label", "")) for g in raw]


def load_flights(path: Optional[Path] = None) -> list[Flight]:
    raw = json.loads((path or DATA_DIR / "flights.json").read_text())
    return [
        Flight(f["id"], f["airline"], hhmm_to_min(f["arrival"]), hhmm_to_min(f["departure"]),
               f["type"], list(f.get("preferred", [])))
        for f in raw
    ]


# --------------------------------------------------------------------------- #
# Assignment (greedy by strategy) + scoring
# --------------------------------------------------------------------------- #
def _walking_penalty(gate: Gate, flight: Flight, gates_by_id: dict[str, Gate]) -> float:
    if not flight.preferred:
        return 0.0
    if gate.id in flight.preferred:
        return 0.0
    prefs = [gates_by_id[g].position for g in flight.preferred if g in gates_by_id]
    if not prefs:
        return 0.0
    return float(min(abs(gate.position - p) for p in prefs))


def assign(flights: list[Flight], gates: list[Gate], strategy: dict,
           prev: Optional[dict[str, str]] = None) -> dict:
    """Return a plan dict. Greedy: order flights by the strategy priority key,
    then place each on the best feasible gate (compatible, open, no overlap)."""
    prev = prev or {}
    gates_by_id = {g.id: g for g in gates}
    key_fn = PRIORITY_KEYS.get(strategy.get("priority_key", "earliest_arrival"),
                               PRIORITY_KEYS["earliest_arrival"])
    weights = strategy.get("soft_weights", {"walking": 1.0, "stability": 1.0})

    order = sorted(flights, key=key_fn)
    busy: dict[str, list[tuple[int, int]]] = {g.id: [] for g in gates}
    assignment: dict[str, str] = {}
    unassigned: list[str] = []

    for fl in order:
        start, end = fl.occupies()
        feasible = []
        for g in gates:
            if not g.accepts(fl) or not g.is_open(start, end):
                continue
            if any(start < be and bs < end for bs, be in busy[g.id]):
                continue
            feasible.append(g)
        if not feasible:
            unassigned.append(fl.id)
            continue
        # pick gate minimizing walking; prefer the previous gate only as a final
        # tie-breaker so stability never costs us a worse packing (more no-gate).
        def cost(g: Gate):
            walk = _walking_penalty(g, fl, gates_by_id) * weights.get("walking", 1.0)
            keep = 0 if prev.get(fl.id) == g.id else 1   # last tie-breaker
            return (walk, g.position, keep)
        best = min(feasible, key=cost)
        assignment[fl.id] = best.id
        busy[best.id].append((start, end))

    return build_plan(flights, gates, assignment, unassigned, strategy, prev)


def conflicts(assignment: dict[str, str], flights_by_id: dict[str, Flight]) -> list[tuple[str, str]]:
    """Pairs of flights that overlap on the same gate (should be empty after assign)."""
    by_gate: dict[str, list[str]] = {}
    for fid, gid in assignment.items():
        by_gate.setdefault(gid, []).append(fid)
    out = []
    for gid, fids in by_gate.items():
        fids.sort(key=lambda f: flights_by_id[f].arrival)
        for i in range(len(fids)):
            for j in range(i + 1, len(fids)):
                a, b = flights_by_id[fids[i]], flights_by_id[fids[j]]
                as_, ae = a.occupies()
                bs, be = b.occupies()
                if as_ < be and bs < ae:
                    out.append((fids[i], fids[j]))
    return out


def score(plan: dict, prev: Optional[dict[str, str]] = None) -> dict:
    """Penalty score. Lower is better. Returns breakdown + total."""
    prev = prev or {}
    flights_by_id = {f.id: f for f in plan["_flights"]}
    gates_by_id = {g.id: g for g in plan["_gates"]}
    assignment = plan["assignment"]

    U = len(plan["unassigned"])
    C = len(conflicts(assignment, flights_by_id))
    W = sum(_walking_penalty(gates_by_id[gid], flights_by_id[fid], gates_by_id)
            for fid, gid in assignment.items())
    R = sum(1 for fid, gid in assignment.items() if fid in prev and prev[fid] != gid)

    total = 1000 * U + 500 * C + 1 * W + 5 * R
    return {"total": round(total, 1), "U": U, "C": C, "W": round(W, 1), "R": R}


# --------------------------------------------------------------------------- #
# Plan packaging (JSON-friendly for the API/Gantt)
# --------------------------------------------------------------------------- #
def build_plan(flights, gates, assignment, unassigned, strategy, prev=None) -> dict:
    flights_by_id = {f.id: f for f in flights}
    conf_pairs = conflicts(assignment, flights_by_id)
    conflicted = {f for pair in conf_pairs for f in pair}
    bars = []
    for fl in flights:
        gid = assignment.get(fl.id)
        bars.append({
            "flight": fl.id,
            "airline": fl.airline,
            "gate": gid,
            "arrival": min_to_hhmm(fl.arrival),
            "departure": min_to_hhmm(fl.departure),
            "arrival_min": fl.arrival,
            "departure_min": fl.departure,
            "type": fl.type,
            "preferred": fl.preferred,
            "status": "unassigned" if gid is None else ("conflict" if fl.id in conflicted else "ok"),
            "delayed": fl.delay > 0,
        })
    plan = {
        "assignment": assignment,
        "unassigned": unassigned,
        "bars": bars,
        "strategy": strategy,
        "gates": [{"id": g.id, "position": g.position, "type": g.type, "label": g.label,
                   "closed": [[min_to_hhmm(s), min_to_hhmm(e)] for s, e in g.closed_windows]}
                  for g in gates],
        "_flights": flights,
        "_gates": gates,
    }
    plan["score"] = score(plan, prev)
    return plan


def public_plan(plan: dict) -> dict:
    """Strip internal objects for JSON serialization."""
    return {k: v for k, v in plan.items() if not k.startswith("_")}
