"""End-to-end smoke test of the Cold Email Brain.

Runs the full loop on the demo persona:
  1. connect → reset → ingest skills → ingest corpus
  2. generate email v1 → critic scores it
  3. record SkillRunEntry → propose SKILL.md rewrite → apply
  4. generate email v2 → critic scores it
  5. print before/after for the demo

Usage:  python scripts/run_demo.py
"""

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from brain import config, cognee_client  # noqa: E402
from brain.ingest import ingest_skills, ingest_corpus  # noqa: E402
from brain.writer import generate_email  # noqa: E402
from brain.critic import score_email  # noqa: E402
from brain.feedback import record_run_and_propose, apply_proposal, extract_proposal_text  # noqa: E402
from brain.local_apply import rewrite_writer_skill, reingest_writer, restore_writer_skill  # noqa: E402


DEMO_PROSPECT = {
    "id": "demo-koeln-dach",
    "contact": "Herr Schmitz",
    "industry": "Dachdecker",
    "region": "Köln",
    "team_size": 6,
    "process": "papierbasierte Auftragsabwicklung",
    "prior_call": True,
}

# v1 = a REAL email Morris actually sent that got ignored.
# This is the authenticity move — we don't ask the brain to write a bad email;
# we hand it Morris's real history and say "this didn't work, why, and what should I send instead?"
BASELINE_EMAIL = """Hallo Herr Schmitz,

ich habe vorhin probiert Sie telefonisch zu erreichen, leider ohne Erfolg.

Viele Handwerker, mit denen ich gerade spreche, erzählen, dass die
eigentliche Arbeit super läuft — aber dass sie sich nach Feierabend oder am
Wochenende trotzdem ständig mit dem ganzen Papierkram hinsetzen müssen.

Ich arbeite gerade mit einigen Handwerksbetrieben aus Köln genau daran,
diese Büroarbeit mithilfe von KI, die das Handwerk wirklich kennt, in einer
Lösung weitgehend zu automatisieren.

Das Ganze funktioniert so:

Sie sprechen einfach kurz ins Handy. Die KI legt Kunden und Auftrag an,
schätzt Arbeits- und Materialaufwand und kann das Angebot nach Ihrer
Bestätigung direkt an den Kunden raussenden. Ihr KI-Mitarbeiter BOB weiß
über alle offenen Aufträge Bescheid, kann Emails für Sie schreiben, an
offene Rechnungen erinnern, Angebote anpassen und vieles mehr.

Außerdem können Sie aus dem Programm direkt Ihre Kapazitäten planen, Ihren
Mitarbeitern Aufträge zuweisen, Materialien verwalten, Fortschritte
verfolgen — eigentlich alles, was nicht reines Handwerk ist.

Wenn Sie Ihre Freizeit lieber mit Dingen verbringen wollen, die Ihnen Spaß
machen, rufen Sie mich gerne zurück — oder schauen Sie kurz auf meiner
Website handwerkercrm.de vorbei.

Morris"""


def banner(title: str):
    bar = "=" * 70
    print(f"\n{bar}\n  {title}\n{bar}")


async def main():
    # Always start from the original writer skill — local_apply may have edited it in a prior run.
    restore_writer_skill()
    await cognee_client.connect()
    await cognee_client.reset()

    banner("INGEST: skills + corpus")
    skills = await ingest_skills()
    writer_skill = skills.get("writer", "writer")
    critic_skill = skills.get("critic", "critic")
    print(f"  writer skill: {writer_skill}")
    print(f"  critic skill: {critic_skill}")

    stats = await ingest_corpus()
    print(f"  raw emails:            {stats['n_raw']}")
    print(f"  patterns promoted:     {stats['n_patterns_promoted']}")
    for p in stats["patterns"]:
        print(f"    - {p['hook_type']} / {p['industry']}: avg {p['avg_score']} across {p['n_prospects']} prospects")

    session = config.session_id_for(DEMO_PROSPECT["id"])

    banner("RUN 1: baseline — a real email Morris actually sent (that got ignored)")
    email_v1 = BASELINE_EMAIL
    print(email_v1)
    print()
    score_v1 = await score_email(email_v1, DEMO_PROSPECT, [critic_skill], session)
    print(f"  critic score: {score_v1.get('score')}")
    print(f"  word count:   {score_v1.get('word_count')}")
    print(f"  fix suggestion: {score_v1.get('fix_suggestion')}")

    banner("FEEDBACK: record + propose + apply")
    proposal = await record_run_and_propose(
        skill_id=writer_skill,
        task_text=f"Cold email for {DEMO_PROSPECT['industry']} in {DEMO_PROSPECT['region']}",
        result_summary=email_v1[:200],
        score=float(score_v1.get("score", 0.0)),
        session_id=session,
        fix_suggestion=str(score_v1.get("fix_suggestion", "")),
    )
    print(f"  proposal_id: {proposal['proposal_id']}")

    proposed_body = extract_proposal_text(proposal["raw"])
    if proposed_body:
        print(f"\n  --- proposed new writer skill body ---\n{proposed_body[:600]}\n  ---")

    applied = False
    if proposal["proposal_id"]:
        applied = await apply_proposal(writer_skill, proposal["proposal_id"])
    print(f"  applied via cloud: {applied}")

    banner("LOCAL APPLY: rewriting writer SKILL.md from critic feedback")
    fix = str(score_v1.get("fix_suggestion") or "")
    new_skill_path = rewrite_writer_skill(critic_fix=fix, persona=DEMO_PROSPECT)
    print(f"  wrote: {new_skill_path}")
    writer_skill_v2 = await reingest_writer(config.DATASET)

    banner("RUN 2: post-feedback email")
    email_v2 = await generate_email(DEMO_PROSPECT, [writer_skill_v2], session)
    print(email_v2)
    print()
    score_v2 = await score_email(email_v2, DEMO_PROSPECT, [critic_skill], session)
    print(f"  critic score: {score_v2.get('score')}")

    banner("DELTA")
    print(f"  v1 score: {score_v1.get('score')}")
    print(f"  v2 score: {score_v2.get('score')}")
    delta = float(score_v2.get("score", 0)) - float(score_v1.get("score", 0))
    print(f"  delta:    {delta:+.2f}")

    if delta < 0.2:
        print("\n  ⚠️  Delta too small for a convincing demo. Tune the writer skill base or the corpus.")
    else:
        print("\n  ✅ Demo delta is real. Lock the persona.")


if __name__ == "__main__":
    asyncio.run(main())
