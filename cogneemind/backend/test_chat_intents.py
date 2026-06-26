"""Standalone test for the chat intent parser (rule path).

Runs without a server, without an LLM key, without cognee. Exercises the
typo-tolerant fallback parser against the exact garbage messages that broke
the Ops Console — plus the clean cases.

    .venv/bin/python test_chat_intents.py
"""
from __future__ import annotations

from chat_intent import parse_rules

FLIGHTS = [
    "AB101", "AB102", "AB103", "AB104", "AB105",
    "CD201", "CD202", "CD203",
    "EF301", "EF302", "EF303",
    "GH401", "GH402",
    "IJ501", "IJ502",
]
GATES = ["G1", "G2", "G3", "G4", "G5", "G6", "G7"]


CASES: list[tuple[str, dict]] = [
    # The exact messes from the user transcript:
    ("AB104 IS deallzed ba 1 hr",      {"action": "delay", "flight": "AB104", "minutes": 60}),
    ("G4 FLIGHT AB104 DEALZED BS 40 MINS",
                                       {"action": "delay", "flight": "AB104", "minutes": 40}),
    ("ok then update",                 {"action": "unknown"}),

    # The basic verbs. Close WITHOUT an explicit window must omit start/end
    # so the dispatcher derives them from the live schedule (no hardcoded times).
    ("close G3",                       {"action": "close", "gate": "G3"}),
    ("g4 gate is clsoed",              {"action": "close", "gate": "G4"}),
    ("close g4",                       {"action": "close", "gate": "G4"}),
    # Explicit window: parser MUST carry it through.
    ("close G3 from 09:00 to 11:30",   {"action": "close", "gate": "G3", "start": "09:00", "end": "11:30"}),
    ("reopen G3",                      {"action": "open", "gate": "G3"}),
    ("open g3",                        {"action": "open", "gate": "G3"}),

    # Per-flight delay variants:
    ("delay AB104 by 30 min",          {"action": "delay", "flight": "AB104", "minutes": 30}),
    ("ab104 late half an hour",        {"action": "delay", "flight": "AB104", "minutes": 30}),
    ("push CD202 30m",                 {"action": "delay", "flight": "CD202", "minutes": 30}),

    # Add / move / storm / new day:
    ("add flight 09:15",               {"action": "add", "arrival": "09:15"}),
    ("new flight 10:30 to G2",         {"action": "add", "arrival": "10:30", "gate": "G2"}),
    ("move AB104 to G2",               {"action": "move", "flight": "AB104", "gate": "G2"}),
    ("storm",                          {"action": "storm"}),
    ("cascading delays 45 min",        {"action": "storm", "minutes": 45}),
    ("new day",                        {"action": "new_day"}),
    ("tomorrow please",                {"action": "new_day"}),
    ("reset",                          {"action": "reset"}),
    ("lint wiki",                      {"action": "lint"}),
    ("help",                           {"action": "help"}),

    # Query phrasings (must NOT dump raw recall — that's the dispatcher's job):
    ("what is the best strategy?",     {"action": "query"}),
    ("why did the brain pick that?",   {"action": "query"}),
]


def _matches(actual: dict, expected: dict) -> bool:
    return all(actual.get(k) == v for k, v in expected.items())


def main() -> int:
    fails = 0
    for text, expected in CASES:
        got = parse_rules(text, FLIGHTS, GATES)
        ok = _matches(got, expected)
        status = "ok " if ok else "FAIL"
        print(f"  [{status}] {text!r:50s} -> {got}")
        if not ok:
            print(f"        expected superset: {expected}")
            fails += 1

    # Negative assertion: 'close g4' (no times given) must NOT carry hardcoded
    # start/end forward; the dispatcher derives the window from live schedule.
    no_window = parse_rules("close g4", FLIGHTS, GATES)
    if "start" in no_window or "end" in no_window:
        print(f"  [FAIL] 'close g4' leaked hardcoded times: {no_window}")
        fails += 1
    else:
        print(f"  [ok ] 'close g4' correctly omits start/end (dispatcher derives them)")

    print()
    if fails:
        print(f"{fails} test case(s) failed.")
        return 1
    print(f"All {len(CASES)} cases passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
