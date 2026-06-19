"""The three-agent loop: Researcher, Planner, Observer (+ Linter).

The Researcher does WARM-STARTED discovery: it recalls past winning strategies
and known dead-ends from the wiki and seeds its (small) candidate search from
them, instead of cold-searching the full menu every time. That memory is why
discovery compounds — fewer candidate evals and equal-or-better scores as the
wiki grows.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import simulator as S
from memory import Memory, strategy_key

# A re-planning compute budget: under a disruption you can only try so many
# candidates. Cold search burns evals on naive heuristics; a warm wiki spends
# them on the candidates memory already knows are good. Full menu = 6, so the
# default budget lets a cold brain eventually find the winner (just slowly).
EVAL_BUDGET = 6

# "Naive-first" menu a cold brain explores. The non-obvious 'latest_departure'
# winner sits LAST, so cold search only reaches it after trying everything else
# — exactly the cost that memory removes.
COLD_MENU_KEYS = [
    "earliest_arrival", "earliest_departure", "tightest_turnaround",
    "longest_first", "constrained_first", "latest_departure",
]


def _strat(priority_key: str, walking=1.0, stability=1.0, applies_to="base", name=None) -> dict:
    return {
        "name": name or priority_key,
        "priority_key": priority_key,
        "soft_weights": {"walking": walking, "stability": stability},
        "applies_to": applies_to,
    }


Event = Callable[[str, str, dict], None]  # (agent, message, data)


@dataclass
class DiscoveryResult:
    strategy: dict
    plan: dict
    evals: int
    source: str               # "cold" | "warm"
    trace: list               # [{key, score}] in evaluation order
    dead_ends: list


# --------------------------------------------------------------------------- #
# Researcher
# --------------------------------------------------------------------------- #
def _candidate_order(priors: dict, signature: str) -> list[dict]:
    """Warm: recalled winners first, then a tuned mutation, then the rest of the
    menu (skipping dead-ends). Cold: the naive-first menu."""
    dead = set(priors.get("dead_ends", []))
    seeds = priors.get("strategies", [])
    cands: list[dict] = []
    seen: set[str] = set()

    def push(s: dict):
        k = strategy_key(s)
        if k in seen or k in dead:
            return
        seen.add(k)
        cands.append(s)

    if seeds:  # WARM start — jump straight to what worked before
        for s in seeds:
            push({**s, "applies_to": signature})
        # one mutation of the top seed: emphasise passenger walking
        top = seeds[0]
        push(_strat(top["priority_key"], walking=2.0, stability=1.0,
                    applies_to=signature, name=top["priority_key"] + "+walk"))

    for k in COLD_MENU_KEYS:  # fill the rest of the menu (cold uses only this)
        push(_strat(k, applies_to=signature))
    return cands


def researcher_discover(flights, gates, signature: str, memory: Memory,
                        prev: Optional[dict] = None, budget: int = EVAL_BUDGET,
                        emit: Optional[Event] = None) -> DiscoveryResult:
    priors = memory.recall(signature)
    source = priors.get("source", "cold")
    if emit:
        emit("researcher", f"recall({signature}) → {source}", {
            "source": source, "priors": [s.get("name") for s in priors.get("strategies", [])],
            "dead_ends": priors.get("dead_ends", []),
        })

    candidates = _candidate_order(priors, signature)
    trace, best = [], None
    for cand in candidates[:budget]:
        plan = S.assign(flights, gates, cand, prev=prev)
        total = plan["score"]["total"]
        trace.append({"key": strategy_key(cand), "name": cand["name"], "score": total})
        if emit:
            emit("researcher", f"try {cand['name']} → {total}", {"score": total})
        if best is None or total < best[0]:
            best = (total, cand, plan)

    best_score, best_strat, best_plan = best
    # Anything clearly worse than the winner (or that strands a flight it didn't
    # need to) becomes a recorded dead-end for this signature.
    dead_ends = [t["key"] for t in trace
                 if t["score"] > best_score and (t["score"] >= best_score * 3 or t["score"] >= 1000)]
    if emit:
        emit("researcher", f"winner: {best_strat['name']} (score {best_score}, {len(trace)} evals, {source})",
             {"strategy": best_strat, "score": best_score, "evals": len(trace), "source": source})
    return DiscoveryResult(best_strat, best_plan, len(trace), source, trace, dead_ends)


# --------------------------------------------------------------------------- #
# Planner
# --------------------------------------------------------------------------- #
def planner_build(flights, gates, strategy: dict, prev: Optional[dict] = None,
                  emit: Optional[Event] = None) -> dict:
    plan = S.assign(flights, gates, strategy, prev=prev)
    if emit:
        sc = plan["score"]
        emit("planner", f"built plan with {strategy['name']} → score {sc['total']} "
                        f"(U={sc['U']} C={sc['C']} W={sc['W']} R={sc['R']})", {"score": sc})
    return plan


# --------------------------------------------------------------------------- #
# Observer
# --------------------------------------------------------------------------- #
CHAOS_THRESHOLD = 100  # score above this (or any conflict/unassigned) = chaos


def observer_inspect(plan: dict, emit: Optional[Event] = None) -> dict:
    sc = plan["score"]
    chaos = sc["U"] > 0 or sc["C"] > 0 or sc["total"] > CHAOS_THRESHOLD
    reasons = []
    if sc["U"]:
        reasons.append(f"{sc['U']} flight(s) with no gate")
    if sc["C"]:
        reasons.append(f"{sc['C']} gate conflict(s)")
    if not reasons and sc["total"] > CHAOS_THRESHOLD:
        reasons.append(f"score {sc['total']} over threshold {CHAOS_THRESHOLD}")
    verdict = {"chaos": chaos, "reasons": reasons, "score": sc}
    if emit:
        emit("observer", ("CHAOS: " + "; ".join(reasons)) if chaos else "plan healthy ✓", verdict)
    return verdict


# --------------------------------------------------------------------------- #
# Full optimization step: Observe → (if chaos) Discover → Plan → Distill
# --------------------------------------------------------------------------- #
def optimize(flights, gates, signature: str, memory: Memory,
             prev_plan: Optional[dict] = None, emit: Optional[Event] = None) -> dict:
    prev_assign = (prev_plan or {}).get("assignment") if prev_plan else None
    fail_score = None  # the chaos that triggered re-research -> drives skill self-improvement

    # 1. Observe the current (possibly stale) plan if one exists.
    if prev_plan is not None:
        stale = S.assign(flights, gates, prev_plan["strategy"], prev=prev_assign)
        verdict = observer_inspect(stale, emit)
        if not verdict["chaos"]:
            return {"plan": S.public_plan(stale), "discovery": None, "verdict": verdict}
        fail_score = stale["score"]   # the failed attempt the Researcher must beat

    # 2. Researcher discovers (warm-started from the wiki).
    result = researcher_discover(flights, gates, signature, memory, prev=prev_assign, emit=emit)

    # 3. Planner commits the winning strategy.
    plan = planner_build(flights, gates, result.strategy, prev=prev_assign, emit=emit)

    # 4. Distill the winner + dead-ends into the wiki (permanent graph).
    note = f"{result.source} discovery, {result.evals} evals"
    promo = memory.promote(signature, result.strategy, result.dead_ends,
                           plan["score"]["total"], note)
    if emit:
        emit("brain", f"distilled → wiki v{promo['version']} ({note})",
             {"version": promo["version"], "signature": signature})

    return {
        "plan": S.public_plan(plan),
        "discovery": {
            "strategy": result.strategy, "evals": result.evals, "source": result.source,
            "trace": result.trace, "score": plan["score"]["total"],
        },
        "verdict": observer_inspect(plan, emit=None),
        "wiki_version": promo["version"],
        # the failed prior attempt (if any) — graded by Cognee to rewrite the skill
        "fail_score": fail_score,
    }
