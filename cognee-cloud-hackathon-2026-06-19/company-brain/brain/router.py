from dataclasses import dataclass
from brain.facts import Fact
from brain.drift import Candidate
from brain.config import trust, THRESHOLDS

@dataclass
class Decision:
    action: str            # merge|override|retire|hold|quarantine|park|keep_both
    path: str              # heuristic|judge
    winner: Fact | None
    loser: Fact | None
    reason: str
    candidate: Candidate

def _newest(facts): return max(facts, key=lambda f: f.date)
def _oldest(facts): return min(facts, key=lambda f: f.date)

def route(c: Candidate, as_of: str, judge_fn=None) -> Decision:
    if c.kind == "redundancy":
        keep = _newest(c.facts)
        drop = _oldest(c.facts)
        return Decision("merge", "heuristic", keep, drop,
                        "identical value; merged, both sources kept", c)

    if c.kind == "stale":
        f = c.facts[0]
        return Decision("retire", "heuristic", None, f,
                        f"age {f.age_days(as_of)}d exceeds 2x refresh horizon", c)

    if c.kind == "contradiction":
        new, old = _newest(c.facts), _oldest(c.facts)
        hard = [f for f in c.facts if f.hard]
        soft = [f for f in c.facts if not f.hard]
        # stakes: a hard fact challenged by a lower-trust source -> HOLD the hard fact
        if hard and soft and trust(soft[0].source) < trust(hard[0].source):
            return Decision("hold", "heuristic", hard[0], soft[0],
                            "hard policy not overridden by lower-trust source", c)
        gap = abs(trust(new.source) - trust(old.source))
        newer_by = new.age_days(as_of) - old.age_days(as_of)  # negative => new is more recent
        # provenance: a no-source loser -> override toward the sourced/newer one
        if trust(old.source) == 0 and trust(new.source) > 0:
            return Decision("override", "heuristic", new, old,
                            "unsourced value superseded by sourced, newer value", c)
        if gap >= THRESHOLDS["contradiction_trust_gap"] or (newer_by <= -THRESHOLDS["recency_days"] and not new.hard):
            return Decision("override", "heuristic", new, old,
                            "newer and/or more-trusted value wins", c)
        # grey band -> ask judge; no judge -> park
        if judge_fn is not None:
            verdict = judge_fn(f"Do these conflict and should '{new.value}' replace '{old.value}'?")
            if verdict is True:
                return Decision("override", "judge", new, old, "judge: newer value wins", c)
            if verdict is False:
                return Decision("keep_both", "judge", None, None, "judge: not a real conflict", c)
        return Decision("park", "judge", None, None, "no confident call; quarantined for human", c)

    return Decision("park", "judge", None, None, "unclassified", c)
