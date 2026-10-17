"""Capture the self-improvement / compounding evidence for the submission.

Run:  python evidence.py
Prints a judge-readable before/after block and writes evidence.json.
"""
from __future__ import annotations

import json

import agents as A
import disruptions as D
import simulator as S
from memory import LocalWiki, strategy_key


def baseline_vs_improved():
    """A storm hits: the naive default (what worked on the calm base) strands a
    flight; the strategy the brain discovers heals it back to zero remote stands."""
    gates = S.load_gates()
    storm = D.apply_delays(S.load_flights(), ["CD201", "GH401", "IJ501", "CD202"], 30)
    naive = {"name": "earliest_arrival", "priority_key": "earliest_arrival",
             "soft_weights": {"walking": 1.0, "stability": 1.0}, "applies_to": "storm"}
    storm_naive = S.assign(storm, gates, naive)

    sig = D.signature("delay", weather="storm", severity="heavy")
    wiki = LocalWiki(path=S.DATA_DIR / "wiki_evidence.json"); wiki.reset()
    res = A.researcher_discover(storm, gates, sig, wiki)  # cold discovery
    return {
        "baseline": {"strategy": "earliest_arrival", "score": storm_naive["score"]},
        "improved": {"strategy": res.strategy["name"], "score": res.plan["score"], "evals": res.evals},
    }


def cold_vs_warm(budget=2):
    """Same storm, same tiny re-planning budget — cold wiki vs warm wiki."""
    gates = S.load_gates()
    storm = D.apply_delays(S.load_flights(), ["CD201", "GH401", "IJ501", "CD202"], 30)
    sig = D.signature("delay", weather="storm", severity="heavy")

    wiki = LocalWiki(path=S.DATA_DIR / "wiki_evidence.json"); wiki.reset()
    cold = A.researcher_discover(storm, gates, sig, wiki, budget=budget)
    full = A.researcher_discover(storm, gates, sig, wiki)            # full-budget cold to learn
    wiki.promote(sig, full.strategy, full.dead_ends, full.plan["score"]["total"], "seed")
    warm = A.researcher_discover(storm, gates, sig, wiki, budget=budget)
    return {
        "scenario": sig, "budget": budget,
        "cold": {"score": cold.plan["score"]["total"], "evals": cold.evals,
                 "tried": [t["name"] for t in cold.trace], "dead_ends_known": 0},
        "warm": {"score": warm.plan["score"]["total"], "evals": warm.evals,
                 "tried": [t["name"] for t in warm.trace],
                 "recalled": warm.source == "warm"},
        "full_budget_cold": {"score": full.plan["score"]["total"], "evals": full.evals},
    }


if __name__ == "__main__":
    bi = baseline_vs_improved()
    cw = cold_vs_warm()
    out = {"baseline_vs_improved": bi, "cold_vs_warm": cw}

    print("\n=== SELF-IMPROVEMENT (base schedule) ===")
    print(f"  baseline  earliest_arrival -> {bi['baseline']['score']['total']}  "
          f"(U={bi['baseline']['score']['U']})")
    print(f"  improved  {bi['improved']['strategy']:16s} -> {bi['improved']['score']['total']}  "
          f"(U={bi['improved']['score']['U']}, {bi['improved']['evals']} evals)")

    print("\n=== COMPOUNDING (storm, 2-try budget) ===")
    print(f"  COLD wiki : score {cw['cold']['score']:>7}  ({cw['cold']['evals']} evals)  tried {cw['cold']['tried']}")
    print(f"  WARM wiki : score {cw['warm']['score']:>7}  ({cw['warm']['evals']} evals)  tried {cw['warm']['tried']}")
    print(f"  full cold : score {cw['full_budget_cold']['score']} took {cw['full_budget_cold']['evals']} evals "
          f"-> warm reaches it in {cw['warm']['evals']}")

    (S.DATA_DIR / "evidence.json").write_text(json.dumps(out, indent=2))
    print("\nwrote data/evidence.json")
