"""
Debater - Adversarial debate agents that use evolving skills.
The skills improve based on debate outcomes (self-improvement loop).
"""
import json
from openai import OpenAI
from wiki.engine import WikiEntry, DebateWiki
from wiki.skills import SkillManager

client = OpenAI()

CHALLENGER_PROMPT = """{{skill_instructions}}

Given this wiki entry:
Topic: {topic}
Claim: {claim}
Perspective: {perspective}
Evidence: {evidence}
Confidence: {confidence}

Generate a sharp, specific challenge.

Output JSON:
{{"challenge": "your challenge text", "attack_type": "logic|evidence|assumption|scope", "severity": "low|medium|high"}}
"""

DEFENDER_PROMPT = """{{skill_instructions}}

Original claim: {claim}
Evidence: {evidence}
Challenge: {challenge}
Attack type: {attack_type}

Output JSON:
{{"defense": "your defense", "revised_claim": "improved claim or null if original stands", "revised_evidence": "improved evidence or null", "new_confidence": 0.X, "conceded": false}}
"""

MODERATOR_PROMPT = """{{skill_instructions}}

Original Claim: {claim}
Original Evidence: {evidence}
Original Confidence: {confidence}

Challenge: {challenge} (severity: {severity})
Defense: {defense}

Revised claim (if any): {revised_claim}
Revised evidence (if any): {revised_evidence}
Defender's new confidence: {new_confidence}
Defender conceded: {conceded}

Decide: "strengthen", "weaken", "remove", or "split"

Output JSON:
{{"verdict": "strengthen|weaken|remove|split", "final_claim": "...", "final_evidence": "...", "final_confidence": 0.X, "reasoning": "brief explanation"}}
"""


def run_challenger(entry: WikiEntry, skill_mgr: SkillManager) -> dict:
    skill_instructions = skill_mgr.get_instructions("challenger")
    prompt = CHALLENGER_PROMPT.replace("{{skill_instructions}}", skill_instructions)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a debate challenger. Return valid JSON only."},
            {"role": "user", "content": prompt.format(
                topic=entry.topic,
                claim=entry.claim,
                perspective=entry.perspective,
                evidence=entry.evidence,
                confidence=entry.confidence,
            )},
        ],
        temperature=0.7,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def run_defender(entry: WikiEntry, challenge: dict, skill_mgr: SkillManager) -> dict:
    skill_instructions = skill_mgr.get_instructions("defender")
    prompt = DEFENDER_PROMPT.replace("{{skill_instructions}}", skill_instructions)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a debate defender. Return valid JSON only."},
            {"role": "user", "content": prompt.format(
                claim=entry.claim,
                evidence=entry.evidence,
                challenge=challenge["challenge"],
                attack_type=challenge.get("attack_type", "logic"),
            )},
        ],
        temperature=0.5,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def run_moderator(entry: WikiEntry, challenge: dict, defense: dict, skill_mgr: SkillManager) -> dict:
    skill_instructions = skill_mgr.get_instructions("moderator")
    prompt = MODERATOR_PROMPT.replace("{{skill_instructions}}", skill_instructions)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an impartial moderator. Return valid JSON only."},
            {"role": "user", "content": prompt.format(
                claim=entry.claim,
                evidence=entry.evidence,
                confidence=entry.confidence,
                challenge=challenge["challenge"],
                severity=challenge.get("severity", "medium"),
                defense=defense.get("defense", ""),
                revised_claim=defense.get("revised_claim", "null"),
                revised_evidence=defense.get("revised_evidence", "null"),
                new_confidence=defense.get("new_confidence", entry.confidence),
                conceded=defense.get("conceded", False),
            )},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


def run_debate_round(wiki: DebateWiki, topic: str, skill_mgr: SkillManager) -> list[dict]:
    """Run a full debate round. Returns outcomes for skill improvement."""
    entries = wiki.get_entries_by_topic(topic)
    results = []

    for entry in entries:
        if entry.lint_status == "removed":
            continue

        challenge = run_challenger(entry, skill_mgr)
        defense = run_defender(entry, challenge, skill_mgr)
        verdict = run_moderator(entry, challenge, defense, skill_mgr)

        idx = wiki.entries.index(entry)
        v = verdict.get("verdict", "strengthen")

        result = {
            "claim": entry.claim,
            "challenge": challenge,
            "defense": defense,
            "verdict": verdict,
            "action": v.upper(),
        }

        if v == "remove":
            wiki.remove_entry(idx)
        elif v == "strengthen":
            new_entry = WikiEntry(
                topic=entry.topic,
                claim=verdict.get("final_claim", entry.claim),
                perspective=entry.perspective,
                evidence=verdict.get("final_evidence", entry.evidence),
                confidence=min(1.0, verdict.get("final_confidence", entry.confidence + 0.1)),
            )
            new_entry.lint_status = "passed"
            wiki.update_entry(idx, new_entry)
        elif v == "weaken":
            entry.confidence = max(0.1, verdict.get("final_confidence", entry.confidence - 0.2))
            entry.lint_status = "flagged"
            wiki.update_entry(idx, entry)

        results.append(result)

    return results
