from brain.facts import load_facts
from brain.drift import find_candidates

AS_OF = "2026-06-19"

def test_detects_redundancy_contradiction_stale():
    cands = find_candidates(load_facts("baustein"), AS_OF)
    kinds = {(c.kind, c.topic) for c in cands}
    assert ("redundancy", "baustein.progressai_desc") in kinds   # bau-06/07 same value
    assert ("contradiction", "baustein.rfi_model") in kinds      # bau-04/05 diff value
    assert ("stale", "baustein.siteguard_pilot") in kinds        # bau-10 age>2x horizon

def test_multivalue_topic_not_contradiction():
    cands = find_candidates(load_facts("baustein"), AS_OF)
    # bau-08/09 share a multivalue topic -> NOT a contradiction candidate
    assert not any(c.kind == "contradiction" and c.topic == "baustein.storage_stack" for c in cands)
