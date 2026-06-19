from brain.facts import Fact, load_facts

def test_age_days():
    f = Fact(id="x", client="baustein", text="t", source="wiki",
             date="2025-06-19", hard=False, topic="t.model", value="GPT-4o", multivalue=False)
    assert f.age_days("2026-06-19") == 365

def test_load_facts_baustein():
    facts = load_facts("baustein")
    assert len(facts) >= 10
    ids = {f.id for f in facts}
    assert "bau-04" in ids and "bau-05" in ids       # the model contradiction pair
    pair = [f for f in facts if f.topic == "baustein.rfi_model"]
    assert {f.value for f in pair} == {"GPT-4o", "Claude Sonnet 4.5"}

def test_category_from_topic():
    f = Fact(id="x", client="v", text="t", source="contract",
             date="2025-01-01", hard=True, topic="vitalis.phi_residency",
             value="US", multivalue=False)
    assert f.category() in ("policy", "compliance")
