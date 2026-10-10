from brain.facts import load_facts
from brain.drift import find_candidates
from brain.router import route
from brain.lint import summarize

AS_OF = "2026-06-19"

def test_summarize_counts_paths():
    decs = [route(c, AS_OF) for c in find_candidates(load_facts("vitalis"), AS_OF)]
    stats = summarize(decs)
    assert stats["before"] == len(decs)
    assert stats["resolved_free"] + stats["needed_judge"] + stats["parked"] == len(decs)
