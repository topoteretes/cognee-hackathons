from brain.facts import load_facts
from brain.drift import find_candidates
from brain.router import route

AS_OF = "2026-06-19"

def _by(client):
    facts = load_facts(client)
    cands = {(c.kind, c.topic): c for c in find_candidates(facts, AS_OF)}
    return facts, cands

def test_redundancy_merges_heuristically():
    _, c = _by("baustein")
    d = route(c[("redundancy", "baustein.progressai_desc")], AS_OF)
    assert d.action == "merge" and d.path == "heuristic"

def test_contradiction_newer_trusted_wins():
    _, c = _by("baustein")
    d = route(c[("contradiction", "baustein.rfi_model")], AS_OF)
    assert d.action == "override" and d.winner.value == "Claude Sonnet 4.5"

def test_stakes_hard_fact_held_against_slack():
    _, c = _by("vitalis")
    d = route(c[("contradiction", "vitalis.phi_residency")], AS_OF)
    assert d.action == "hold" and d.winner.hard is True
    assert d.loser.source.startswith("slack")

def test_stale_retires():
    _, c = _by("baustein")
    d = route(c[("stale", "baustein.siteguard_pilot")], AS_OF)
    assert d.action == "retire"

def test_greyband_parks_without_judge():
    # construct a contradiction with tied trust + recent dates, no judge -> park
    from brain.facts import Fact
    from brain.drift import Candidate
    a = Fact("a","x","t","wiki","2026-06-01",False,"x.t","A")
    b = Fact("b","x","t","wiki","2026-06-10",False,"x.t","B")
    d = route(Candidate("contradiction","x.t",), AS_OF) if False else route(Candidate("contradiction",[a,b],"x.t"), AS_OF)
    assert d.action == "park" and d.path == "judge"
