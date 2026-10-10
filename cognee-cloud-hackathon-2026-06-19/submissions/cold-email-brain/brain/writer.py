"""Writer: generate a cold email for a prospect using the writer skill + brain context."""

import cognee
from cognee import SearchType

from . import config
from ._text import coerce_text


async def generate_email(prospect: dict, skill_names: list[str], session_id: str) -> str:
    """Run the AGENTIC_COMPLETION search with the writer skill to produce an email body."""
    task = (
        "Schreibe eine kurze Outbound-E-Mail (deutsch, unter 150 Wörter) für diesen Prospect.\n"
        "Nur den Mailtext, keinen Betreff, keine Signatur außer 'Morris'.\n\n"
        f"Prospect:\n{_format_prospect(prospect)}"
    )

    result = await cognee.search(
        task,
        query_type=SearchType.AGENTIC_COMPLETION,
        datasets=[config.DATASET],
        skills=skill_names,
        max_iter=4,
        session_id=session_id,
    )
    return coerce_text(result)


def _format_prospect(prospect: dict) -> str:
    fields = [
        f"Branche: {prospect.get('industry', '?')}",
        f"Region: {prospect.get('region', '?')}",
        f"Mitarbeiter: {prospect.get('team_size', '?')}",
        f"Aufmaß/Auftragsabwicklung: {prospect.get('process', '?')}",
        f"Vorheriger Anruf: {'ja' if prospect.get('prior_call') else 'nein'}",
        f"Ansprechpartner: {prospect.get('contact', '—')}",
    ]
    return "\n".join(fields)
