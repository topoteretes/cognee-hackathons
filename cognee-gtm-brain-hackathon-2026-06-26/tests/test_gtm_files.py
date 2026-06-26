"""Tests for the GTM brain file source — parsing + the merge anchors.

These exercise the deterministic half of the pipeline (no LLM, no
cognee server): CSV/ICS/markdown parsing and, most importantly, that a
transcript speaker, an email sender, and a calendar attendee all resolve
to the *same* canonical Person/Company node.
"""

from pathlib import Path

import pytest

from gtm_brain.gtm_people import Roster
from gtm_brain.sources.gtm_files import GTMBrainSource

BRAIN = Path(__file__).resolve().parent.parent / "sample_data" / "gtm_brain"


@pytest.fixture
def source() -> GTMBrainSource:
    src = GTMBrainSource(BRAIN, roster=Roster())
    # companies()/people() must run first so cross-refs resolve.
    src.companies()
    src.people()
    return src


def test_company_enrichment_merges_all_tables(source: GTMBrainSource):
    companies = {c.domain: c for c in source.companies()}
    clay = companies["clay.com"]
    assert clay.name == "Clay"
    assert clay.tier == "A"  # from clay_table_sponsor-prospects.csv
    assert clay.icp_fit_score == 96  # from lookalike_features.csv
    assert clay.do_not_approach is False
    assert clay.notes and "anchor" in clay.notes.lower()  # account deep-dive prose

    pavilion = companies["joinpavilion.com"]
    assert pavilion.do_not_approach is True  # from do-not-approach.csv

    woodpecker = companies["woodpecker.co"]
    assert woodpecker.is_past_sponsor is True  # Warsaw renewal seed


def test_deals_link_to_canonical_company_and_event(source: GTMBrainSource):
    deals = {d.name: d for d in source.deals()}
    clay_deal = deals["Clay — co-created GTM-engineering track"]
    assert clay_deal.kind == "sponsorship"
    assert clay_deal.company is not None and clay_deal.company.domain == "clay.com"
    assert clay_deal.event is not None and "London 2027" in clay_deal.event.name

    renewal = deals["Woodpecker — renewal"]
    assert renewal.currency == "PLN"
    assert renewal.amount == 40000


def test_calendar_attendees_resolve_to_people_and_account(source: GTMBrainSource):
    events = {e.uid: e for e in source.calendar_events()}
    clay_call = events["clay-sponsor-2026@gtm-week.com"]
    emails = {a.email for a in clay_call.attendees}
    assert "bruno@clay.com" in emails
    assert clay_call.organizer is not None and clay_call.organizer.email == "artur@gtm-week.com"
    assert clay_call.about_company is not None and clay_call.about_company.domain == "clay.com"
    assert clay_call.starts_at.startswith("2026-06-26")


def test_transcript_speaker_resolves_to_email(source: GTMBrainSource):
    docs = {d.doc_id: d for d in source.conversation_docs()}
    clay_call = docs["granola_clay-sponsor-intro-transcript"]
    speakers = {u.speaker for u in clay_call.utterances}
    # Names in the transcript ("Bruno Estrella:") collapse onto canonical emails.
    assert "bruno@clay.com" in speakers
    assert "artur@gtm-week.com" in speakers
    assert clay_call.source == "granola"
    assert "company:clay.com" in clay_call.extra_tags


def test_same_person_across_transcript_and_email(source: GTMBrainSource):
    """The core merge guarantee: Bruno from the Granola call and Bruno
    from the email thread are one node."""
    docs = {d.doc_id: d for d in source.conversation_docs()}
    call_speakers = {u.speaker for u in docs["granola_clay-sponsor-intro-transcript"].utterances}
    email_speakers = {u.speaker for u in docs["clay-sponsorship-thread"].utterances}
    assert "bruno@clay.com" in call_speakers
    assert "bruno@clay.com" in email_speakers


def test_email_thread_parses_messages_in_order(source: GTMBrainSource):
    docs = {d.doc_id: d for d in source.conversation_docs()}
    thread = docs["keynote-sam-jacobs-thread"]
    assert thread.source == "email"
    assert len(thread.utterances) == 3
    # chronological
    ts = [u.timestamp for u in thread.utterances]
    assert ts == sorted(ts)
    assert "sam@joinpavilion.com" in {u.speaker for u in thread.utterances}


def test_icps_parsed(source: GTMBrainSource):
    icps = {i.name: i for i in source.icps()}
    assert set(icps) == {"speaker", "sponsor"}
    assert icps["sponsor"].one_liner
    assert icps["sponsor"].segments  # sponsor ICP lists sub-segments
