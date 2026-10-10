"""
MediMind Linter - Audits the health wiki for issues, gaps, and outdated info.
"""
import json
from openai import OpenAI
from dotenv import load_dotenv
from wiki.engine import HealthEntry, MediMind

load_dotenv()
client = OpenAI()

LINT_PROMPT = """You are a health wiki quality auditor. Analyze this personal health wiki for issues.

Entries:
{entries_text}

Check for:
1. CONTRADICTIONS: Entries that conflict (e.g., "allergic to penicillin" but taking amoxicillin)
2. OUTDATED: Info that seems stale or needs updating (old dosages, discontinued meds still listed)
3. REDUNDANT: Duplicate or overlapping entries
4. GAPS: Important missing info (e.g., medications without dosage, conditions without treatment)
5. COMPLETENESS: Is the profile comprehensive enough for safe health decisions?

Output JSON:
{{
    "contradictions": [{{"entry_a": "title", "entry_b": "title", "issue": "..."}}],
    "possibly_outdated": [{{"entry": "title", "reason": "..."}}],
    "redundancies": [{{"entries": ["title1", "title2"], "suggestion": "..."}}],
    "gaps": [{{"description": "what's missing", "importance": "high|medium|low"}}],
    "completeness_score": 0.X,
    "recommendations": ["action 1", "action 2"]
}}
"""

FILL_GAP_PROMPT = """Based on this health profile, generate a helpful note to fill a gap.

Current profile entries:
{context}

Gap to fill: {gap}

Generate a reminder/note entry that helps the user address this gap.

Output JSON:
{{"category": "note", "title": "...", "details": "...", "confidence": 0.X}}
"""


def lint_wiki(wiki: MediMind) -> dict:
    entries = wiki.get_active()
    if not entries:
        return {"error": "No entries to lint"}

    entries_text = "\n".join(
        f"[{e.category.upper()}] {e.title}: {e.details} (confidence: {e.confidence:.0%}, v{e.version})"
        for e in entries
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You audit health data for quality and safety. Return valid JSON."},
            {"role": "user", "content": LINT_PROMPT.format(entries_text=entries_text)},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    return json.loads(response.choices[0].message.content)


def fill_gap(wiki: MediMind, gap: str) -> HealthEntry:
    entries = wiki.get_active()
    context = "\n".join(f"- [{e.category}] {e.title}: {e.details}" for e in entries[:15])

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You generate helpful health reminders. Return valid JSON."},
            {"role": "user", "content": FILL_GAP_PROMPT.format(context=context, gap=gap)},
        ],
        temperature=0.4,
        response_format={"type": "json_object"},
    )

    data = json.loads(response.choices[0].message.content)
    entry = HealthEntry(
        category=data.get("category", "note"),
        title=data.get("title", gap[:50]),
        details=data.get("details", ""),
        source="auto_generated",
        confidence=float(data.get("confidence", 0.5)),
    )
    wiki.add_entry(entry)
    return entry


def auto_lint_and_improve(wiki: MediMind) -> dict:
    result = lint_wiki(wiki)
    actions = []

    # Flag contradictions
    for c in result.get("contradictions", []):
        for entry in wiki.get_active():
            if entry.title in (c.get("entry_a", ""), c.get("entry_b", "")):
                entry.flags.append(f"Contradiction: {c.get('issue', '')}")
                entry.status = "flagged"
                actions.append(f"Flagged contradiction: {entry.title}")

    # Fill high-importance gaps
    for gap in result.get("gaps", []):
        if gap.get("importance") in ("high", "medium"):
            new_entry = fill_gap(wiki, gap["description"])
            actions.append(f"Added reminder: {new_entry.title}")

    result["actions_taken"] = actions
    return result
