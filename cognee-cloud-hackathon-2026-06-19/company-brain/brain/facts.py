import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from brain.config import ROOT

CATEGORY_KEYWORDS = {
    "policy": ("residency", "approval", "deploy", "secrets", "policy"),
    "compliance": ("phi", "gdpr", "hipaa", "dpa", "baa", "pii"),
    "model": ("model", "llm"),
    "pricing": ("rate", "price"),
    "budget": ("budget", "sow"),
    "okr": ("okr", "milestone", "pilot"),
}

@dataclass
class Fact:
    id: str
    client: str
    text: str
    source: str
    date: str          # ISO yyyy-mm-dd
    hard: bool
    topic: str
    value: str
    multivalue: bool = False

    def age_days(self, as_of: str) -> int:
        y, m, d = map(int, self.date.split("-"))
        ay, am, ad = map(int, as_of.split("-"))
        return (date(ay, am, ad) - date(y, m, d)).days

    def category(self) -> str:
        t = self.topic.lower()
        for cat, kws in CATEGORY_KEYWORDS.items():
            if any(k in t for k in kws):
                return cat
        return "default"

def load_facts(client: str) -> list[Fact]:
    path = ROOT / "data_facts" / f"{client}.jsonl"
    facts = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        facts.append(Fact(**json.loads(line)))
    return facts
