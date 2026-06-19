from dataclasses import dataclass
from collections import defaultdict
from brain.facts import Fact
from brain.config import REFRESH_HORIZONS, THRESHOLDS

@dataclass
class Candidate:
    kind: str            # "redundancy" | "contradiction" | "stale"
    facts: list[Fact]
    topic: str

def _horizon(fact: Fact):
    return REFRESH_HORIZONS.get(fact.category(), REFRESH_HORIZONS["default"])

def find_candidates(facts: list[Fact], as_of: str) -> list[Candidate]:
    out: list[Candidate] = []

    # group by topic
    by_topic: dict[str, list[Fact]] = defaultdict(list)
    for f in facts:
        by_topic[f.topic].append(f)

    for topic, group in by_topic.items():
        if len(group) > 1:
            values = {f.value for f in group}
            if len(values) == 1:
                out.append(Candidate("redundancy", group, topic))
            elif not any(f.multivalue for f in group):
                out.append(Candidate("contradiction", group, topic))
            # multivalue + differing values -> intentionally skipped (fake-contradiction)

    # staleness (per fact, durable horizons excluded)
    for f in facts:
        h = _horizon(f)
        if h is None:
            continue
        if f.age_days(as_of) / h > THRESHOLDS["stale_retire"]:
            out.append(Candidate("stale", [f], f.topic))
    return out
