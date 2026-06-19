"""
MediMind Advisor - Two-tier query: Redis for session context, Cognee for deep knowledge.
Uses evolving skills that improve based on user corrections.
"""
import json
from openai import OpenAI
from dotenv import load_dotenv
from wiki.engine import (
    HealthEntry, MediMind,
    recall_with_session, recall_from_graph,
    redis_get_session_context, redis_log_query,
)
from wiki.skills import SkillManager

load_dotenv()
client = OpenAI()

QUERY_PROMPT = """{{skill_instructions}}

The user has the following health profile in their personal wiki:

MEDICATIONS:
{medications}

CONDITIONS:
{conditions}

SYMPTOMS:
{symptoms}

ALLERGIES:
{allergies}

LAB RESULTS:
{lab_results}

OTHER NOTES:
{notes}

PREVIOUS QUESTIONS THIS SESSION:
{session_context}

ADDITIONAL CONTEXT FROM KNOWLEDGE GRAPH:
{graph_context}

---
User question: {question}

Provide a helpful, accurate response based on their health profile. Be specific to THEIR data.
Cross-reference medications against allergies (check drug FAMILIES, not just exact names).
Check for drug-drug and drug-condition interactions.
Consider their age, living situation, and any risk factors.
Always remind them to consult their doctor for medical decisions.

Output JSON:
{{
    "answer": "your detailed response",
    "warnings": ["any safety warnings or interactions detected"],
    "related_entries": ["titles of relevant wiki entries used"],
    "confidence": 0.X,
    "suggested_additions": ["any info you think is missing from their wiki"]
}}
"""

INTERACTION_PROMPT = """You are a drug interaction and health safety checker. Analyze this health profile thoroughly.

MEDICATIONS:
{medications}

CONDITIONS:
{conditions}

ALLERGIES:
{allergies}

Check for:
1. Drug-drug interactions (even mild ones)
2. Drug-condition contraindications
3. Drug-allergy risks — CHECK DRUG FAMILIES (e.g. penicillin family includes amoxicillin, ampicillin)
4. Duplicate therapies
5. Missing medications (condition listed but no treatment)
6. Dosage concerns given lab values (e.g. kidney function affecting drug clearance)

Output JSON:
{{
    "interactions": [{{"drugs": ["drug1", "drug2"], "severity": "high|medium|low", "description": "..."}}],
    "contraindications": [{{"drug": "...", "condition": "...", "risk": "..."}}],
    "allergy_risks": [{{"drug": "...", "allergy": "...", "risk": "..."}}],
    "duplicates": [{{"entries": ["...", "..."], "explanation": "..."}}],
    "gaps": [{{"condition": "...", "suggestion": "..."}}],
    "overall_safety": 0.X,
    "urgent_flags": ["anything requiring immediate attention"]
}}
"""


def _build_profile(wiki: MediMind) -> dict:
    def fmt(entries):
        if not entries:
            return "None recorded"
        return "\n".join(f"- {e.title}: {e.details}" for e in entries)

    return {
        "medications": fmt(wiki.get_medications()),
        "conditions": fmt(wiki.get_conditions()),
        "symptoms": fmt(wiki.get_symptoms()),
        "allergies": fmt(wiki.get_by_category("allergy")),
        "lab_results": fmt(wiki.get_by_category("lab_result")),
        "notes": fmt(wiki.get_by_category("note")),
    }


async def _get_enriched_context(question: str, wiki: MediMind) -> tuple[str, str]:
    """Get context from both memory tiers."""
    # Tier 1: Redis session context (fast, recent queries)
    session_ctx = redis_get_session_context(wiki.session_id)
    session_text = "\n".join(
        f"Q: {q.get('question', '')} -> A: {q.get('answer', '')[:100]}"
        for q in session_ctx
    ) if session_ctx else "No previous queries this session."

    # Tier 2: Cognee graph context (deep knowledge)
    graph_text = await recall_with_session(question, wiki.session_id)
    if not graph_text:
        graph_text = "No additional graph context available."

    return session_text, graph_text


def ask_medimind(question: str, wiki: MediMind, skill_mgr: SkillManager) -> dict:
    import asyncio
    profile = _build_profile(wiki)
    skill_instructions = skill_mgr.get_instructions("health-advisor")
    prompt = QUERY_PROMPT.replace("{{skill_instructions}}", skill_instructions)

    # Get enriched context from both tiers
    try:
        session_ctx, graph_ctx = asyncio.get_event_loop().run_until_complete(
            _get_enriched_context(question, wiki)
        )
    except Exception:
        session_ctx = "Session context unavailable."
        graph_ctx = "Graph context unavailable."

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a personal health advisor. Return valid JSON. Always recommend consulting a doctor."},
            {"role": "user", "content": prompt.format(
                question=question,
                session_context=session_ctx,
                graph_context=graph_ctx,
                **profile,
            )},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )

    result = json.loads(response.choices[0].message.content)

    # Log to both tiers
    wiki.query_log.append({
        "question": question,
        "answer": result.get("answer", ""),
        "warnings": result.get("warnings", []),
        "confidence": result.get("confidence", 0.5),
    })
    redis_log_query(wiki.session_id, question, result.get("answer", ""))

    # KARPATHY PATTERN: File valuable answers BACK into the wiki as new knowledge
    # This is the key difference from RAG — the wiki grows from queries, not just ingestion
    warnings = result.get("warnings", [])
    if warnings:
        for w in warnings:
            if w:
                note = HealthEntry(
                    category="note",
                    title=f"Safety Note: {w[:50]}",
                    details=f"Discovered during query '{question[:60]}': {w}",
                    source="self_discovered",
                    confidence=result.get("confidence", 0.7),
                )
                # Check if we already have this note to avoid duplicates
                existing_titles = [e.title for e in wiki.get_active()]
                if note.title not in existing_titles:
                    wiki.add_entry(note)

    # Remember Q&A in Cognee for future cross-session context
    try:
        asyncio.get_event_loop().run_until_complete(
            __import__("wiki.engine", fromlist=["remember_session"]).remember_session(
                f"User asked: {question}. Key finding: {result.get('answer', '')[:200]}",
                wiki.session_id,
            )
        )
    except Exception:
        pass

    return result


def check_interactions(wiki: MediMind, skill_mgr: SkillManager) -> dict:
    profile = _build_profile(wiki)
    skill_instructions = skill_mgr.get_instructions("safety-checker")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": skill_instructions + "\nReturn valid JSON."},
            {"role": "user", "content": INTERACTION_PROMPT.format(
                medications=profile["medications"],
                conditions=profile["conditions"],
                allergies=profile["allergies"],
            )},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    return json.loads(response.choices[0].message.content)
