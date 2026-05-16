"""
MediMind Ingester - Extracts structured health data, stores in both tiers.
  Tier 1 (Redis): Fast cache for current session
  Tier 2 (Cognee): Permanent knowledge graph for cross-session reasoning
"""
import json
import asyncio
from openai import OpenAI
from dotenv import load_dotenv
from wiki.engine import (
    HealthEntry, MediMind,
    remember_permanent, remember_session,
    redis_log_query,
)

load_dotenv()
client = OpenAI()

EXTRACT_PROMPT = """You are a medical information extraction agent. Given health-related text (doctor notes, medication lists, lab results, symptom descriptions), extract ALL structured health information.

For EACH item found, output:
- category: "medication" | "condition" | "symptom" | "lab_result" | "allergy" | "note"
- title: Short name (e.g., "Metformin 500mg", "Type 2 Diabetes", "Headache")
- details: Full relevant details (dosage, frequency, severity, values, instructions)
- connections: List of related items mentioned (e.g., a medication connected to a condition it treats)
- confidence: How clearly this info is stated (0.0 to 1.0)

Text to analyze:
{text}

Output JSON:
{{"items": [{{"category": "...", "title": "...", "details": "...", "connections": ["..."], "confidence": 0.X}}]}}
"""


def extract_health_data(text: str) -> list[dict]:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You extract medical information into structured data. Return valid JSON."},
            {"role": "user", "content": EXTRACT_PROMPT.format(text=text)},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    try:
        parsed = json.loads(response.choices[0].message.content)
        return parsed.get("items", [])
    except json.JSONDecodeError:
        return []


async def ingest_health_text(text: str, wiki: MediMind) -> list[HealthEntry]:
    """Full two-tier ingestion pipeline."""
    # Step 1: Extract structured claims via LLM
    items = extract_health_data(text)

    # Step 2: Store raw text in BOTH memory tiers
    # Tier 1: Session memory (Redis-backed, fast)
    await remember_session(text, session_id=wiki.session_id)
    # Tier 2: Permanent graph (Cognee, durable)
    await remember_permanent(text)

    # Step 3: Create or UPDATE wiki entries
    # KARPATHY PATTERN: Ingestion should touch existing pages, not just add new ones.
    # If new info contradicts existing entry, update it instead of duplicating.
    new_entries = []
    for item in items:
        new_title = item.get("title", "Unknown")
        new_category = item.get("category", "note")
        new_details = item.get("details", "")

        # Check if a similar entry already exists
        updated_existing = False
        for idx, existing in enumerate(wiki.entries):
            if existing.status == "removed":
                continue
            # Match by title similarity (same medication name, same condition, etc.)
            if (existing.category == new_category and
                _titles_match(existing.title, new_title)):
                # UPDATE existing entry with newer info (wiki evolves)
                updated = HealthEntry(
                    category=new_category,
                    title=new_title,
                    details=new_details,
                    source="ingested",
                    connections=item.get("connections", []),
                    confidence=float(item.get("confidence", 0.7)),
                )
                wiki.update_entry(idx, updated)
                new_entries.append(updated)
                updated_existing = True
                break

        if not updated_existing:
            entry = HealthEntry(
                category=new_category,
                title=new_title,
                details=new_details,
                source="ingested",
                connections=item.get("connections", []),
                confidence=float(item.get("confidence", 0.7)),
            )
            wiki.add_entry(entry)
            new_entries.append(entry)

    return new_entries


def _titles_match(a: str, b: str) -> bool:
    """Check if two entry titles refer to the same thing (fuzzy match on drug/condition name)."""
    # Normalize: lowercase, strip dosage numbers for comparison
    import re
    def normalize(t):
        t = t.lower().strip()
        t = re.sub(r'\d+\s*mg', '', t)  # remove dosages
        t = re.sub(r'\s+', ' ', t).strip()
        return t
    na, nb = normalize(a), normalize(b)
    # Exact match after normalization, or one contains the other
    return na == nb or na in nb or nb in na
