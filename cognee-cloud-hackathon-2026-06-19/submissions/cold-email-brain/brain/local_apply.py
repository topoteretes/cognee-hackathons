"""Apply a skill rewrite locally when the Cognee Cloud `improve` endpoint is unavailable.

Cognee Cloud's `improve` is dev-preview (returns 404 on this instance), so we
honor the proposal by editing the SKILL.md ourselves based on the critic's
concrete fix_suggestion + the persona it targeted, then re-ingest the file as
a fresh skill version. The graph gets a new canonical skill node — that node
is what the v2 generation uses.

This is the "two-step propose-then-apply" cycle from the hackathon README,
just with the apply step happening client-side until the Cloud endpoint ships.
"""

import shutil
from pathlib import Path

import cognee

from . import config
from .ingest import _items


def rewrite_writer_skill(critic_fix: str, persona: dict) -> Path:
    """Append a concrete improvement to the writer SKILL.md based on critic feedback."""
    skill_path = config.SKILLS_DIR / "writer" / "SKILL.md"
    backup = skill_path.with_suffix(".md.v0")
    if not backup.exists():
        shutil.copy(skill_path, backup)

    addendum = _build_addendum(critic_fix, persona)
    # REPLACE the body entirely with a tight playbook — don't append.
    # Appending kept the old wordy instructions which the LLM blended with the new rules,
    # producing structured "Greeting: / Problem:" output. Replacement gives clean prose.
    new_body = (
        "---\n"
        "description: Writer skill — refined from critic feedback after baseline run.\n"
        "allowed-tools: memory_search\n"
        "---\n\n"
        "# Instructions (auto-applied from feedback loop)\n\n"
        + addendum
        + "\n"
    )
    skill_path.write_text(new_body)
    return skill_path


def _build_addendum(critic_fix: str, persona: dict) -> str:
    """Replace the writer skill's body with a tight, natural-language playbook
    learned from feedback. NOT a bullet list of rules — bullet lists make the
    LLM output structured prose instead of a real email. Flowing instructions
    keep the output email-shaped."""

    industry = (persona.get("industry") or "Handwerker").lower()
    trade_pain = {
        "dachdecker": "Aufmaß-Zettel, die bei Regen unbrauchbar werden, Wetter-bedingte Verzögerungen, Witterungsabhängigkeit bei der Terminplanung",
        "maler": "Untergrund-Vorbereitung, Materialaufwand pro qm, Farbton-Mischungen, die nicht dokumentiert werden",
        "fliesen": "Verschnittberechnung, Aufmaß-Skizzen auf Papier, Material- und Werkzeugplanung pro Baustelle",
        "tischler": "Maße auf Zetteln, Stücklisten, Material- und Werkzeugplanung",
        "elektriker": "Stromkreis-Dokumentation, Schaltpläne, Materiallisten",
    }
    pain_phrase = next((v for k, v in trade_pain.items() if k in industry), "Papierkram nach Feierabend, verlorene Notizen, langsame Angebote")

    region = persona.get("region", "Ihrer Region")
    contact = persona.get("contact", "")
    prior = "Da Sie vorher telefonisch nicht erreichbar waren, eröffne mit einem expliziten Hinweis auf den Anrufversuch." if persona.get("prior_call") else "Da kein vorheriger Anruf stattfand, eröffne mit einem konkreten Pattern-Interrupt: ihre Website, ihre Bewertungen, oder ein spezifisches Detail."

    body = (
        "Schreibe kurz (60–80 Wörter), persönlich, deutsch. Dies ist eine ECHTE Outbound-Mail an einen "
        f"{industry.capitalize()}-Betrieb {('in ' + region) if region != '?' else ''}.\n\n"
        f"{prior}\n\n"
        f"Benenne EIN konkretes Trade-Pain in {industry.capitalize()}-Vokabular: {pain_phrase}.\n\n"
        "Eine einzige klare CTA: Frage nach einem 15-Minuten-Demo-Termin mit zwei konkreten Zeit-Vorschlägen "
        "(z.B. Mittwoch 14:00 oder Donnerstag 10:00). KEINE alternativen Pfade wie Website-Besuch oder Rückruf.\n\n"
        "KEIN 5-Schritte-Produkterklärer. KEIN Aufzählungs-Punkt-Format. KEIN 'Bürokram'. KEIN 'Greeting:'/'Problem:'/'Solution:' Labels.\n\n"
        "Die Mail muss klingen wie von einem echten Menschen geschrieben, nicht wie ein KI-Output. "
        f"Adressiere {contact} direkt."
    )

    if critic_fix and len(critic_fix) < 300:
        body += f"\n\nKonkretes Feedback aus dem letzten Run: {critic_fix.strip()}"

    return body


async def reingest_writer(dataset: str) -> str:
    """Re-upload the updated writer SKILL.md so the graph has a new canonical skill node."""
    skill_path = config.SKILLS_DIR / "writer" / "SKILL.md"
    remembered = await cognee.remember(
        str(skill_path),
        dataset_name=dataset,
        content_type="skills",
    )
    items = _items(remembered)
    canonical = next((it["name"] for it in items if it.get("kind") == "skill"), "writer")
    print(f"[local-apply] writer re-ingested -> {canonical}")
    return canonical


def restore_writer_skill():
    """Restore the original writer SKILL.md from the backup. Useful between demo runs."""
    skill_path = config.SKILLS_DIR / "writer" / "SKILL.md"
    backup = skill_path.with_suffix(".md.v0")
    if backup.exists():
        shutil.copy(backup, skill_path)
