"""Canonical GTM people roster + name→email resolver.

The company-brain pipeline seeds Person nodes from the Slack workspace
(see ``people.py``). The GTM brain has no Slack — its people come from
three places that all need to collapse onto one node per human:

- **Granola transcripts** name speakers by display name ("Krzysztof
  Pawlak:") with no email.
- **Email threads** and the **calendar** name them by email
  (``krzysztof@gtm-week.com``).
- The **speaker roster** (``apollo_people-export_speakers.csv``) lists
  prospects by name + email + tier.

To make a transcript speaker resolve to the same Person as an email
sender, we keep a small static roster of the GTM-Week staff (the only
people who appear *only* by name in transcripts) and let everyone else
register dynamically as the CSV/email/calendar loaders discover them.
"""

from __future__ import annotations

from .schema import Person

# The GTM-Week organising team — the speakers who appear in transcripts
# by name only and never carry an email inline.
GTM_STAFF: list[Person] = [
    Person(email="artur@gtm-week.com", name="Artur Wala", title="Founder, GTM Tech Week"),
    Person(email="krzysztof@gtm-week.com", name="Krzysztof Pawlak", title="Operations, GTM Tech Week"),
]


def _slug_email(name: str) -> str:
    """Fallback synthetic email for an otherwise-unknown speaker name."""
    slug = "".join(c.lower() if c.isalnum() else "-" for c in name).strip("-")
    slug = "-".join(filter(None, slug.split("-")))
    return f"{slug or 'unknown'}@unknown.local"


class Roster:
    """Resolves a display name to a canonical Person.

    Seed it with the staff roster, then register everyone discovered in
    the CSVs / email headers / calendar so transcript speakers map onto
    the right node. Unknown names get a stable synthetic email rather
    than spawning duplicates per spelling.
    """

    def __init__(self) -> None:
        self._by_name: dict[str, Person] = {}
        self._by_email: dict[str, Person] = {}
        for p in GTM_STAFF:
            self.register(p)

    def register(self, person: Person) -> Person:
        existing = self._by_email.get(person.email.lower())
        if existing is not None:
            # Enrich the existing node with any new non-empty facets.
            for field in ("name", "title", "company_domain", "speaker_tier", "linkedin_url"):
                val = getattr(person, field, None)
                if val and not getattr(existing, field, None):
                    setattr(existing, field, val)
            self._by_name[existing.name.lower()] = existing
            return existing
        self._by_email[person.email.lower()] = person
        self._by_name[person.name.lower()] = person
        return person

    def by_name(self, name: str) -> Person:
        name = name.strip()
        hit = self._by_name.get(name.lower())
        if hit is not None:
            return hit
        person = Person(email=_slug_email(name), name=name)
        return self.register(person)

    def by_email(self, email: str, name: str | None = None) -> Person:
        email = email.strip()
        hit = self._by_email.get(email.lower())
        if hit is not None:
            return hit
        person = Person(email=email, name=name or email.split("@")[0])
        return self.register(person)

    def all(self) -> list[Person]:
        return list(self._by_email.values())
