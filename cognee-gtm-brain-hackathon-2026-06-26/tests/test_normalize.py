from datetime import datetime, timezone

from gtm_brain.normalize import Doc, Utterance
from gtm_brain.schema import Person


def _utterance(speaker: str, minute: int, text: str) -> Utterance:
    return Utterance(
        speaker=speaker,
        timestamp=datetime(2026, 5, 28, 10, minute, tzinfo=timezone.utc),
        text=text,
    )


def test_transcript_renders_chronologically_with_speakers():
    doc = Doc(
        source="slack",
        doc_id="T123",
        title="#support: auth bug",
        container="support",
        started_at=datetime(2026, 5, 28, 10, 14, tzinfo=timezone.utc),
        utterances=[
            _utterance("alice@acme.com", 14, "We have an auth bug on login."),
            _utterance("bob@acme.com", 16, "Same issue we hit last month?"),
            _utterance("alice@acme.com", 18, "Yes — I'll patch it today."),
        ],
    )

    body = doc.body()
    assert body.splitlines()[0] == "# #support: auth bug"
    assert "[alice@acme.com, 2026-05-28T10:14] We have an auth bug on login." in body
    assert body.index("alice") < body.index("bob") < body.rindex("alice")


def test_tags_carry_structural_facets():
    doc = Doc(
        source="slack",
        doc_id="T123",
        title="thread",
        container="support",
        started_at=datetime(2026, 5, 28, 10, 14, tzinfo=timezone.utc),
        utterances=[
            _utterance("alice@acme.com", 14, "hi"),
            _utterance("bob@acme.com", 16, "hey"),
            _utterance("alice@acme.com", 18, "again"),
        ],
        project="onboarding",
    )

    tags = doc.tags()
    assert "source:slack" in tags
    assert "slack:support" in tags
    assert "doc:T123" in tags
    assert "speaker:alice@acme.com" in tags
    assert "speaker:bob@acme.com" in tags
    assert tags.count("speaker:alice@acme.com") == 1
    assert "project:onboarding" in tags


def test_participants_dedupes_and_preserves_order():
    doc = Doc(
        source="granola",
        doc_id="M9",
        title="weekly sync",
        container="eng-weekly",
        started_at=datetime(2026, 5, 28, 10, 0, tzinfo=timezone.utc),
        utterances=[
            _utterance("alice@acme.com", 0, "first"),
            _utterance("bob@acme.com", 1, "second"),
            _utterance("alice@acme.com", 2, "third"),
        ],
    )

    assert doc.participants == ["alice@acme.com", "bob@acme.com"]


def test_body_surfaces_reported_issue_candidates():
    doc = Doc(
        source="slack",
        doc_id="T456",
        title="thread",
        container="support",
        started_at=datetime(2026, 5, 28, 10, 14, tzinfo=timezone.utc),
        utterances=[
            _utterance(
                "veljko@topoteretes.com",
                14,
                "There is a bug when calling remember with node sets. It keeps extracting everything.",
            ),
            _utterance("milenko@topoteretes.com", 15, "I'll take a look."),
        ],
    )

    body = doc.body()
    assert "## Reported issue candidates" in body
    assert (
        "- [veljko@topoteretes.com, 2026-05-28T10:14] There is a bug when calling"
        in body
    )


def test_person_identity_is_email():
    veljko = Person(email="veljko@topoteretes.com", name="Veljko Kovac")
    veljko_again = Person(email="veljko@topoteretes.com", name="Veljko")
    milenko = Person(email="milenko@topoteretes.com", name="Milenko Gavric")

    assert veljko.id == veljko_again.id
    assert veljko.id != milenko.id
    assert veljko.metadata["identity_fields"] == ["email"]
