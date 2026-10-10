"""Streamlit UI for the live 3-minute demo.

Run:  streamlit run ui/app.py

Layout: prospect input → Generate → email + score card →
Train on this → SKILL.md diff inline → Regenerate → v2 + score.
"""

import asyncio
import difflib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from brain import config, cognee_client  # noqa: E402
from brain.ingest import ingest_skills, ingest_corpus  # noqa: E402
from brain.writer import generate_email  # noqa: E402
from brain.critic import score_email  # noqa: E402
from brain.feedback import record_run_and_propose, apply_proposal  # noqa: E402
from brain.local_apply import rewrite_writer_skill, reingest_writer, restore_writer_skill  # noqa: E402


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


st.set_page_config(page_title="Cold Email Brain", page_icon="🧠", layout="wide")


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if asyncio._get_running_loop() else asyncio.run(coro)


def init_state():
    defaults = {
        "ready": False,
        "writer_skill": None,
        "critic_skill": None,
        "writer_skill_body_v0": None,
        "writer_skill_body_v1": None,
        "email_v1": None,
        "score_v1": None,
        "email_v2": None,
        "score_v2": None,
        "proposal_id": None,
        "applied": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def read_skill_body(skill_name: str) -> str:
    candidates = [
        config.SKILLS_DIR / skill_name / "SKILL.md",
        config.SKILLS_DIR / "writer" / "SKILL.md",
    ]
    for p in candidates:
        if p.exists():
            return p.read_text()
    return ""


def diff_html(a: str, b: str) -> str:
    lines = list(difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm=""))
    if not lines:
        return "_(no diff — skill body unchanged in the source file. The improvement lives in the graph.)_"
    out = []
    for line in lines:
        if line.startswith("+"):
            out.append(f"<span style='color:#2ecc71'>{line}</span>")
        elif line.startswith("-"):
            out.append(f"<span style='color:#e74c3c'>{line}</span>")
        else:
            out.append(line)
    return "<pre style='font-size:13px'>" + "\n".join(out) + "</pre>"


def score_card(label: str, score_dict: dict):
    score = float(score_dict.get("score", 0) or 0)
    color = "#e74c3c" if score < 0.5 else ("#f39c12" if score < 0.7 else "#2ecc71")
    st.markdown(
        f"<div style='padding:12px;border-radius:8px;background:{color}22;border:1px solid {color}'>"
        f"<b>{label}</b><br>"
        f"<span style='font-size:28px;color:{color}'>{score:.2f}</span>"
        f"<div style='font-size:12px;opacity:.7'>{score_dict.get('fix_suggestion','')}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


def main():
    init_state()
    st.title("🧠 Cold Email Brain")
    st.caption("A self-improving outbound brain — built on Cognee Cloud · Berlin · 2026-06-19")

    with st.sidebar:
        st.header("Setup")
        if st.button("🔌 Connect + ingest brain", type="primary"):
            with st.spinner("Connecting, resetting, ingesting..."):
                restore_writer_skill()
                run(cognee_client.connect())
                run(cognee_client.reset())
                skills = run(ingest_skills())
                writer = skills.get("writer", "writer")
                critic = skills.get("critic", "critic")
                st.session_state.writer_skill = writer
                st.session_state.critic_skill = critic
                st.session_state.writer_skill_body_v0 = read_skill_body("writer")
                stats = run(ingest_corpus())
                st.session_state.ready = True
            st.success(f"Ready. Writer: `{writer}` · Critic: `{critic}`")
            st.json(stats)

        st.markdown("---")
        st.markdown(
            "**Cloud:** "
            + ("✅ connected" if config.cloud_configured() else "⚠️ local")
        )

    if not st.session_state.ready:
        st.info("👈 Click **Connect + ingest brain** to start.")
        return

    st.subheader("1️⃣  Prospect")
    col1, col2 = st.columns(2)
    with col1:
        industry = st.text_input("Branche", value="Dachdecker")
        region = st.text_input("Region", value="Köln")
        team = st.number_input("Team-Größe", min_value=1, max_value=200, value=6)
    with col2:
        process = st.text_input("Aufmaß/Prozess", value="papierbasierte Auftragsabwicklung")
        contact = st.text_input("Ansprechpartner", value="Herr Schmitz")
        prior_call = st.checkbox("Vorher angerufen?", value=True)

    prospect = {
        "id": "live-demo",
        "contact": contact,
        "industry": industry,
        "region": region,
        "team_size": team,
        "process": process,
        "prior_call": prior_call,
    }
    session = config.session_id_for(prospect["id"])

    st.markdown("---")
    st.subheader("2️⃣  Run 1 — a real email Morris sent that got ignored")
    if st.button("📥 Load baseline email + score"):
        with st.spinner("Scoring real email..."):
            email = BASELINE_EMAIL
            score = run(score_email(email, prospect, [st.session_state.critic_skill], session))
            st.session_state.email_v1 = email
            st.session_state.score_v1 = score

    if st.session_state.email_v1:
        c1, c2 = st.columns([3, 1])
        with c1:
            st.text_area("Email v1 (real, sent 2026-06-05, ignored)", st.session_state.email_v1, height=320, key="ev1")
        with c2:
            score_card("Critic score", st.session_state.score_v1)

    st.markdown("---")
    st.subheader("3️⃣  Train the brain — propose + apply")
    if st.session_state.email_v1 and st.button("🎯 Train on this run", type="primary"):
        with st.spinner("Recording SkillRunEntry, proposing rewrite, applying..."):
            res = run(record_run_and_propose(
                skill_id=st.session_state.writer_skill,
                task_text=f"Cold email for {prospect['industry']} in {prospect['region']}",
                result_summary=st.session_state.email_v1[:200],
                score=float(st.session_state.score_v1.get("score", 0)),
                session_id=session,
                fix_suggestion=str(st.session_state.score_v1.get("fix_suggestion", "")),
            ))
            st.session_state.proposal_id = res["proposal_id"]
            # Cloud apply may 404; that's OK, local_apply is the ground truth.
            run(apply_proposal(st.session_state.writer_skill, res["proposal_id"] or ""))
            # Local apply — the ACTUAL skill rewrite.
            fix = str(st.session_state.score_v1.get("fix_suggestion") or "")
            rewrite_writer_skill(critic_fix=fix, persona=prospect)
            new_canonical = run(reingest_writer(config.DATASET))
            st.session_state.writer_skill = new_canonical
            st.session_state.writer_skill_body_v1 = read_skill_body("writer")
            st.session_state.applied = True

    if st.session_state.proposal_id:
        st.success(
            f"✅ Cognee proposal `{st.session_state.proposal_id}` recorded · "
            f"Writer skill re-ingested as `{st.session_state.writer_skill}`"
        )
        st.markdown("**SKILL.md diff (writer skill):**")
        st.markdown(
            diff_html(st.session_state.writer_skill_body_v0 or "", st.session_state.writer_skill_body_v1 or ""),
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.subheader("4️⃣  Run 2 — the brain's rewrite")
    if st.session_state.proposal_id and st.button("✉️ Generate email v2", type="primary"):
        with st.spinner("Writing with improved skill..."):
            email = run(generate_email(prospect, [st.session_state.writer_skill], session))
            score = run(score_email(email, prospect, [st.session_state.critic_skill], session))
            st.session_state.email_v2 = email
            st.session_state.score_v2 = score

    if st.session_state.email_v2:
        c1, c2 = st.columns([3, 1])
        with c1:
            st.text_area("Email v2", st.session_state.email_v2, height=260, key="ev2")
        with c2:
            score_card("Critic score", st.session_state.score_v2)

        d = float(st.session_state.score_v2.get("score", 0)) - float(st.session_state.score_v1.get("score", 0))
        st.markdown(f"## Δ score: **{d:+.2f}**")


if __name__ == "__main__":
    main()
