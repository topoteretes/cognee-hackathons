import json
from brain.facts import Fact
from brain.drift import Candidate
from brain.router import Decision
from brain.ledger import write_receipt, health

def _decision():
    a = Fact("bau-04","baustein","t","meeting-notes","2024-11-05",False,"baustein.rfi_model","GPT-4o")
    b = Fact("bau-05","baustein","t","slack#proj-baustein","2026-04-22",False,"baustein.rfi_model","Claude Sonnet 4.5")
    c = Candidate("contradiction",[a,b],"baustein.rfi_model")
    return Decision("override","heuristic",b,a,"newer wins",c)

def test_write_receipt(tmp_path):
    md, jl = tmp_path/"receipts.md", tmp_path/"receipts.jsonl"
    rec = write_receipt(_decision(), "2026-06-19", md, jl)
    assert rec["action"] == "override" and rec["client"] == "baustein"
    assert "Claude Sonnet 4.5" in md.read_text()
    rows = [json.loads(l) for l in jl.read_text().splitlines() if l.strip()]
    assert rows[-1]["why"] == "newer wins"

def test_health():
    assert health(0) == 1.0
    assert health(3) == 0.25
