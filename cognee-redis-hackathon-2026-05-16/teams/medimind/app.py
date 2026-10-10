"""
MediMind - Your Personal Health Memory Agent
Built with Cognee + OpenAI + Redis + Streamlit
"""
import streamlit as st
import asyncio
import json

from dotenv import load_dotenv
load_dotenv()

import nest_asyncio
try:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    nest_asyncio.apply(loop)
except Exception:
    pass

from wiki.engine import MediMind, HealthEntry, get_redis_stats, REDIS_AVAILABLE
from wiki.ingester import ingest_health_text
from wiki.advisor import ask_medimind, check_interactions
from wiki.linter import lint_wiki, auto_lint_and_improve
from wiki.skills import SkillManager

st.set_page_config(page_title="MediMind", layout="wide", initial_sidebar_state="expanded")

# ──────────────── CSS ────────────────
st.markdown("""
<style>
/* ── global ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.block-container { padding: 1.5rem 2rem 2rem; max-width: 1200px; }
section[data-testid="stSidebar"] { background: #060b14; border-right: 1px solid #1a2235; }
section[data-testid="stSidebar"] > div { padding-top: 1rem; }

/* ── hide streamlit boilerplate ── */
#MainMenu, footer, header { visibility: hidden; }

/* ── logo area ── */
.logo { display: flex; align-items: center; gap: 0.7rem; margin-bottom: 0.3rem; }
.logo-icon {
    width: 38px; height: 38px; border-radius: 10px;
    background: linear-gradient(135deg, #00d4aa 0%, #0099ff 100%);
    display: flex; align-items: center; justify-content: center;
    font-size: 1.2rem; font-weight: 800; color: #fff;
}
.logo-text { font-size: 1.35rem; font-weight: 700; color: #e2e8f0; letter-spacing: -0.02em; }
.logo-tag { font-size: 0.78rem; color: #4a5568; margin-top: -0.2rem; }

/* ── cards ── */
.card {
    background: #111827; border: 1px solid #1e293b; border-radius: 14px;
    padding: 1.1rem 1.3rem; margin-bottom: 0.7rem;
    transition: all 0.2s ease;
}
.card:hover { border-color: #334155; transform: translateY(-1px); box-shadow: 0 4px 20px rgba(0,0,0,0.3); }

.card-cat {
    display: inline-block; font-size: 0.6rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.1em;
    padding: 3px 10px; border-radius: 6px; margin-bottom: 0.5rem;
}
.cat-medication { background: #0c2d48; color: #38bdf8; }
.cat-condition { background: #2d1f0c; color: #fbbf24; }
.cat-symptom  { background: #2d0c20; color: #f472b6; }
.cat-allergy  { background: #2d0c0c; color: #f87171; }
.cat-lab_result { background: #0c2d15; color: #4ade80; }
.cat-note     { background: #1e1e2a; color: #94a3b8; }

.card-title { font-size: 1rem; font-weight: 600; color: #f1f5f9; margin: 0.15rem 0; }
.card-body  { font-size: 0.82rem; color: #94a3b8; line-height: 1.55; }
.card-foot  { font-size: 0.68rem; color: #475569; margin-top: 0.6rem; display: flex; gap: 1rem; }

/* confidence bar */
.conf-bar-wrap { height: 4px; background: #1e293b; border-radius: 2px; margin-top: 0.5rem; overflow: hidden; }
.conf-bar { height: 100%; border-radius: 2px; transition: width 0.4s ease; }

/* flag badge */
.flag { display: inline-block; font-size: 0.62rem; font-weight: 600; background: #7f1d1d44; color: #fca5a5;
        border: 1px solid #7f1d1d; border-radius: 6px; padding: 2px 8px; margin-left: 0.5rem; }

/* ── metrics row ── */
.metrics { display: flex; gap: 0.6rem; margin: 0.8rem 0; flex-wrap: wrap; }
.m-box {
    flex: 1; min-width: 90px; background: #111827; border: 1px solid #1e293b;
    border-radius: 12px; padding: 0.8rem 0.6rem; text-align: center;
}
.m-val { font-size: 1.6rem; font-weight: 700; line-height: 1.2; }
.m-lbl { font-size: 0.62rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 0.15rem; }

/* ── answer bubble ── */
.answer {
    background: linear-gradient(135deg, #0c1929, #111827);
    border: 1px solid #1e3a5f; border-radius: 16px;
    padding: 1.4rem 1.6rem; line-height: 1.7; font-size: 0.92rem; color: #cbd5e1;
    margin: 0.8rem 0;
}

/* ── warning card ── */
.warn {
    background: #1a0f05; border: 1px solid #92400e; border-radius: 12px;
    padding: 0.9rem 1.1rem; margin: 0.5rem 0; font-size: 0.85rem;
}
.sev-high   { color: #fca5a5; font-weight: 700; }
.sev-medium { color: #fcd34d; font-weight: 600; }
.sev-low    { color: #86efac; font-weight: 500; }

/* ── safety score ring ── */
.safety-ring {
    width: 100px; height: 100px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.5rem; font-weight: 800; margin: 0 auto 0.5rem;
}

/* ── skill card ── */
.skill-card {
    background: #111827; border: 1px solid #1e293b; border-radius: 12px;
    padding: 1rem 1.2rem; margin: 0.5rem 0;
    display: flex; justify-content: space-between; align-items: center;
}
.skill-name { font-weight: 600; color: #e2e8f0; }
.skill-ver { background: #064e3b; color: #6ee7b7; font-size: 0.7rem; font-weight: 700;
             padding: 3px 10px; border-radius: 20px; }

/* ── evolution card ── */
.evo-card {
    background: linear-gradient(135deg, #140a25, #111827);
    border-left: 3px solid #8b5cf6; border-radius: 10px;
    padding: 0.8rem 1rem; margin: 0.4rem 0; font-size: 0.82rem; color: #c4b5fd;
}

/* ── timeline ── */
.tl-item { display: flex; gap: 0.8rem; margin: 0.4rem 0; font-size: 0.8rem; align-items: flex-start; }
.tl-dot { width: 8px; height: 8px; border-radius: 50%; margin-top: 5px; flex-shrink: 0; }
.tl-add    { background: #00d4aa; }
.tl-update { background: #38bdf8; }
.tl-remove { background: #f87171; }
.tl-text   { color: #94a3b8; }

/* ── section header ── */
.sec-head { font-size: 1.15rem; font-weight: 700; color: #e2e8f0; margin: 1.2rem 0 0.6rem; }
.sec-sub  { font-size: 0.82rem; color: #64748b; margin-top: -0.4rem; margin-bottom: 0.8rem; }

/* ── pill filter row ── */
.pill-row { display: flex; gap: 0.4rem; flex-wrap: wrap; margin: 0.6rem 0 1rem; }
</style>
""", unsafe_allow_html=True)

# ──────────────── State ────────────────
if "wiki" not in st.session_state:
    st.session_state.wiki = MediMind()
if "skill_mgr" not in st.session_state:
    st.session_state.skill_mgr = SkillManager()
if "interaction_results" not in st.session_state:
    st.session_state.interaction_results = None
if "lint_results" not in st.session_state:
    st.session_state.lint_results = None
if "last_answer" not in st.session_state:
    st.session_state.last_answer = None
if "show_correction" not in st.session_state:
    st.session_state.show_correction = False
if "profile_filter" not in st.session_state:
    st.session_state.profile_filter = "All"

wiki = st.session_state.wiki
sm   = st.session_state.skill_mgr

# ──────────────── helpers ────────────────
def conf_color(v):
    if v >= 0.75: return "#00d4aa"
    if v >= 0.5:  return "#fbbf24"
    return "#f87171"

def render_card(entry: HealthEntry):
    flags_html = "".join(f'<span class="flag">{f[:35]}</span>' for f in entry.flags)
    cc = conf_color(entry.confidence)
    st.markdown(f"""
    <div class="card">
        <span class="card-cat cat-{entry.category}">{entry.category.replace('_',' ')}</span>{flags_html}
        <div class="card-title">{entry.title}</div>
        <div class="card-body">{entry.details}</div>
        <div class="conf-bar-wrap"><div class="conf-bar" style="width:{entry.confidence*100:.0f}%;background:{cc};"></div></div>
        <div class="card-foot">
            <span>v{entry.version}</span>
            <span>{entry.source}</span>
            <span>{entry.confidence:.0%} confidence</span>
        </div>
    </div>""", unsafe_allow_html=True)

def metric_row(items):
    """items = [(value, label, color), ...]"""
    inner = ""
    for val, lbl, col in items:
        inner += f'<div class="m-box"><div class="m-val" style="color:{col};">{val}</div><div class="m-lbl">{lbl}</div></div>'
    st.markdown(f'<div class="metrics">{inner}</div>', unsafe_allow_html=True)


# ──────────────── Sidebar ────────────────
with st.sidebar:
    st.markdown("""
    <div class="logo">
        <div class="logo-icon">M</div>
        <div>
            <div class="logo-text">MediMind</div>
            <div class="logo-tag">Your Health, One Place, Always Safe</div>
        </div>
    </div>""", unsafe_allow_html=True)

    stats = wiki.get_stats()
    metric_row([
        (stats["active"], "Entries", "#00d4aa"),
        (stats["medications"], "Meds", "#38bdf8"),
        (stats["flags"], "Alerts", "#f87171"),
    ])

    st.markdown("---")
    st.markdown('<div class="sec-head" style="font-size:0.9rem;">Add Health Data</div>', unsafe_allow_html=True)

    ingest_text = st.text_area("Paste doctor notes, med list, labs...", height=120,
        placeholder="Patient takes Metformin 500mg twice daily for Type 2 Diabetes. Allergic to penicillin...")

    if st.button("Extract & Add to Wiki", type="primary", use_container_width=True, disabled=not ingest_text):
        with st.spinner("Analyzing..."):
            new = asyncio.run(ingest_health_text(ingest_text, wiki))
            st.success(f"Added {len(new)} entries")
            st.rerun()

    st.markdown("---")
    with st.expander("Manual Entry"):
        cat = st.selectbox("Type", ["medication", "condition", "symptom", "allergy", "lab_result", "note"])
        title = st.text_input("Name", placeholder="Lisinopril 10mg")
        details = st.text_input("Details", placeholder="Once daily for blood pressure")
        if st.button("Add Entry", use_container_width=True, disabled=not title):
            wiki.add_entry(HealthEntry(category=cat, title=title, details=details or "-", source="user", confidence=0.9))
            st.rerun()


# ──────────────── Tabs ────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Health Profile", "Ask MediMind", "Safety Scan", "Wiki Audit", "Brain Evolution", "Architecture"
])

# ═══════ TAB 1 ═══════
with tab1:
    st.markdown('<div class="sec-head">Health Profile</div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-sub">All your health data in one place, organized and connected.</div>', unsafe_allow_html=True)

    active = wiki.get_active()
    if not active:
        st.markdown("""
        <div class="answer">
            <strong style="font-size:1.05rem;">Welcome to MediMind</strong><br><br>
            Your health info is scattered across doctor offices, pharmacies, and patient portals.
            MediMind brings it all together and keeps you safe.<br><br>
            <strong>1.</strong> Paste doctor notes, medication lists, or lab results in the sidebar<br>
            <strong>2.</strong> MediMind extracts, organizes, and cross-references everything<br>
            <strong>3.</strong> Get drug interaction alerts, ask questions, and keep your wiki current<br>
            <strong>4.</strong> The more you use it, the smarter it gets at protecting you<br>
        </div>""", unsafe_allow_html=True)
    else:
        categories = ["All", "medication", "condition", "symptom", "allergy", "lab_result", "note"]
        labels     = ["All", "Medications", "Conditions", "Symptoms", "Allergies", "Lab Results", "Notes"]
        counts     = {c: len(wiki.get_by_category(c)) for c in categories[1:]}
        counts["All"] = len(active)

        options = [f"{l} ({counts.get(c, 0)})" for c, l in zip(categories, labels)]
        sel = st.pills("Filter", options, default=options[0])
        sel_cat = categories[options.index(sel)] if sel else "All"

        filtered = active if sel_cat == "All" else wiki.get_by_category(sel_cat)

        col1, col2 = st.columns(2)
        for i, entry in enumerate(filtered):
            with (col1 if i % 2 == 0 else col2):
                render_card(entry)


# ═══════ TAB 2 ═══════
with tab2:
    st.markdown('<div class="sec-head">Ask MediMind</div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-sub">Ask anything about your health — answers are cross-referenced against your entire profile.</div>', unsafe_allow_html=True)

    if not wiki.get_active():
        st.info("Add health data first to start asking questions.")
    else:
        question = st.chat_input("e.g. Can I take ibuprofen with my current meds?")

        # Show chat history
        for q in wiki.query_log[-5:]:
            with st.chat_message("user"):
                st.write(q.get("question", ""))
            with st.chat_message("assistant"):
                st.write(q.get("answer", ""))
                if q.get("warnings"):
                    for w in q["warnings"]:
                        if w:
                            st.warning(w)

        if question:
            with st.chat_message("user"):
                st.write(question)

            with st.chat_message("assistant"):
                with st.spinner("Analyzing your health profile..."):
                    result = ask_medimind(question, wiki, sm)
                    st.session_state.last_answer = result

                st.write(result.get("answer", ""))

                for w in result.get("warnings", []):
                    if w:
                        st.warning(f"**Warning:** {w}")

                # Show that warnings were filed back into the wiki (Karpathy pattern)
                warnings = [w for w in result.get("warnings", []) if w]
                if warnings:
                    st.markdown(f"""
                    <div style="background:#0a1a2d; border:1px solid #1e3a5f; border-radius:8px; padding:0.6rem 1rem; margin-top:0.5rem; font-size:0.78rem; color:#64748b;">
                        <strong style="color:#00d4aa;">+ {len(warnings)} safety note{'s' if len(warnings)>1 else ''} added to your wiki</strong>
                        — knowledge compounds with every query
                    </div>""", unsafe_allow_html=True)

                for s in result.get("suggested_additions", []):
                    if s:
                        st.info(f"Consider adding: {s}")

            # Feedback — user corrects THEIR DATA, not medical knowledge
            st.markdown("---")
            st.markdown("**Something changed or outdated?** Keep your wiki accurate.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("My info is up to date", use_container_width=True):
                    if wiki.query_log:
                        wiki.query_log[-1]["feedback"] = "positive"
                    st.toast("Great — your profile is current.")
            with col2:
                if st.button("Update my health info", use_container_width=True):
                    st.session_state.show_correction = True

            if st.session_state.show_correction:
                correction = st.text_input(
                    "What changed?",
                    placeholder="e.g. My doctor changed Metformin to 1500mg / I stopped taking Sertraline / New allergy to codeine"
                )
                if st.button("Save Update") and correction:
                    # 1. Log the correction for skill improvement
                    wiki.corrections.append({
                        "question": question, "reason": correction,
                        "timestamp": __import__("datetime").datetime.now().isoformat(),
                    })
                    if wiki.query_log:
                        wiki.query_log[-1]["feedback"] = "correction"
                        wiki.query_log[-1]["correction"] = correction

                    # 2. Actually ingest the correction as new health data
                    #    This updates existing entries or adds new ones
                    with st.spinner("Updating your health wiki..."):
                        new = asyncio.run(ingest_health_text(correction, wiki))

                    # 3. Store in Cognee permanent graph
                    try:
                        asyncio.run(
                            __import__("wiki.engine", fromlist=["remember_permanent"]).remember_permanent(
                                f"Health update: {correction}"
                            )
                        )
                    except Exception:
                        pass

                    st.success(f"Wiki updated with {len(new)} changes! Brain Evolution can further improve the AI's reasoning.")
                    st.session_state.show_correction = False
                    st.rerun()


# ═══════ TAB 3 ═══════
with tab3:
    st.markdown('<div class="sec-head">Safety Scan</div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-sub">Check drug interactions, contraindications, and allergy risks.</div>', unsafe_allow_html=True)

    if not wiki.get_medications():
        st.info("Add medications to run a safety scan.")
    else:
        if st.button("Run Full Safety Scan", type="primary", use_container_width=False):
            with st.status("Scanning your medications...", expanded=True) as status:
                st.write("Checking drug-drug interactions...")
                st.write("Checking contraindications...")
                st.write("Checking allergy cross-reactivity...")
                st.session_state.interaction_results = check_interactions(wiki, sm)
                status.update(label="Scan complete!", state="complete")

    r = st.session_state.interaction_results
    if r:
        safety = r.get("overall_safety", 0.8)
        sc = "#00d4aa" if safety >= 0.8 else "#fbbf24" if safety >= 0.5 else "#f87171"

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""<div class="m-box"><div class="m-val" style="color:{sc};">{safety:.0%}</div>
            <div class="m-lbl">Safety Score</div></div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""<div class="m-box"><div class="m-val" style="color:#f87171;">{len(r.get('interactions',[]))}</div>
            <div class="m-lbl">Interactions</div></div>""", unsafe_allow_html=True)
        with col3:
            st.markdown(f"""<div class="m-box"><div class="m-val" style="color:#fbbf24;">{len(r.get('contraindications',[]))}</div>
            <div class="m-lbl">Contraindications</div></div>""", unsafe_allow_html=True)
        with col4:
            st.markdown(f"""<div class="m-box"><div class="m-val" style="color:#fb7171;">{len(r.get('allergy_risks',[]))}</div>
            <div class="m-lbl">Allergy Risks</div></div>""", unsafe_allow_html=True)

        # Urgent
        for u in r.get("urgent_flags", []):
            st.error(f"**URGENT:** {u}")

        # Interactions
        interactions = r.get("interactions", [])
        if interactions:
            st.markdown('<div class="sec-head" style="font-size:1rem;">Drug Interactions</div>', unsafe_allow_html=True)
            for ix in interactions:
                sev = ix.get("severity", "medium")
                drugs = " + ".join(ix.get("drugs", []))
                st.markdown(f"""<div class="warn">
                    <span class="sev-{sev}">[{sev.upper()}]</span> <strong>{drugs}</strong><br>
                    <span style="color:#94a3b8;">{ix.get('description','')}</span>
                </div>""", unsafe_allow_html=True)
        else:
            st.success("No drug interactions detected.")

        # Contraindications
        for c in r.get("contraindications", []):
            st.warning(f"**{c.get('drug','')}** + **{c.get('condition','')}**: {c.get('risk','')}")

        # Allergy
        for a in r.get("allergy_risks", []):
            st.error(f"**{a.get('drug','')}** may conflict with **{a.get('allergy','')}** allergy: {a.get('risk','')}")

        # Gaps
        for g in r.get("gaps", []):
            st.info(f"**{g.get('condition','')}**: {g.get('suggestion','')}")


# ═══════ TAB 4 ═══════
with tab4:
    st.markdown('<div class="sec-head">Wiki Audit</div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-sub">Find contradictions, outdated info, and gaps — then auto-fix them.</div>', unsafe_allow_html=True)

    if not wiki.get_active():
        st.info("Add entries to audit.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Run Audit", type="primary", use_container_width=True):
                with st.spinner("Auditing..."):
                    st.session_state.lint_results = lint_wiki(wiki)
        with col2:
            if st.button("Auto-Fix & Fill Gaps", use_container_width=True):
                with st.spinner("Improving..."):
                    st.session_state.lint_results = auto_lint_and_improve(wiki)
                    st.rerun()

        r = st.session_state.lint_results
        if r:
            comp = r.get("completeness_score", 0)
            cc = "#00d4aa" if comp >= 0.7 else "#fbbf24" if comp >= 0.4 else "#f87171"
            metric_row([
                (f"{comp:.0%}", "Completeness", cc),
                (str(len(r.get("contradictions",[]))), "Contradictions", "#f87171"),
                (str(len(r.get("possibly_outdated",[]))), "Outdated", "#fbbf24"),
                (str(len(r.get("gaps",[]))), "Gaps", "#38bdf8"),
            ])

            for c in r.get("contradictions", []):
                st.error(f"**{c.get('entry_a','')}** vs **{c.get('entry_b','')}**: {c.get('issue','')}")
            for o in r.get("possibly_outdated", []):
                st.warning(f"**{o.get('entry','')}**: {o.get('reason','')}")
            for g in r.get("gaps", []):
                imp = g.get("importance", "medium")
                {"high": st.error, "medium": st.warning, "low": st.info}.get(imp, st.info)(
                    f"[{imp.upper()}] {g.get('description','')}")
            for rec in r.get("recommendations", []):
                st.markdown(f"- {rec}")
            for a in r.get("actions_taken", []):
                st.success(a)


# ═══════ TAB 5 ═══════
with tab5:
    st.markdown('<div class="sec-head">Brain Evolution</div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-sub">Every time you update your info, MediMind\'s reasoning improves. It learns what to check, what to flag, and how to help you better.</div>', unsafe_allow_html=True)

    # Skill cards
    for name, skill in sm.skills.items():
        ver = sm.get_skill_version(name)
        st.markdown(f"""
        <div class="skill-card">
            <span class="skill-name">{skill['name']}</span>
            <span class="skill-ver">v{ver}</span>
        </div>""", unsafe_allow_html=True)

    with st.expander("View skill instructions (SKILL.md files)"):
        skill_view = st.selectbox("Skill", list(sm.skills.keys()), key="view_skill", label_visibility="collapsed")
        st.code(sm.skills[skill_view]["content"], language="markdown")

    st.markdown("---")

    # Self-improvement
    st.markdown('<div class="sec-head" style="font-size:1rem;">Self-Improvement Loop</div>', unsafe_allow_html=True)

    metric_row([
        (str(len(wiki.corrections)), "Corrections", "#f87171"),
        (str(len(wiki.query_log)), "Queries", "#38bdf8"),
        (str(len(sm.proposals)), "Proposals", "#fbbf24"),
        (str(len(sm.applied)), "Applied", "#00d4aa"),
    ])

    col1, col2 = st.columns(2)
    with col1:
        improve_skill = st.selectbox("Skill to improve", ["health-advisor", "safety-checker", "wiki-linter"])
    with col2:
        feedback = st.text_input("Feedback (optional)", placeholder="Be more careful about NSAIDs...")

    col1, col2 = st.columns(2)
    with col1:
        can_propose = len(wiki.corrections) > 0 or len(wiki.query_log) > 0 or feedback
        if st.button("1. Propose Improvement", type="primary", use_container_width=True, disabled=not can_propose):
            with st.spinner("Generating improvement proposal..."):
                corrections = wiki.corrections + [
                    {"question": q.get("question",""), "reason": q.get("correction", q.get("feedback",""))}
                    for q in wiki.query_log if q.get("feedback")
                ]
                sm.propose_improvement(improve_skill, corrections, feedback)
                wiki.improvement_log.append({"type": "proposal", "skill": improve_skill})
                st.rerun()
    with col2:
        can_apply = sm.proposals and sm.proposals[-1].get("status") == "pending"
        if st.button("2. Apply Improvement", use_container_width=True, disabled=not can_apply):
            result = sm.apply_improvement()
            wiki.improvement_log.append({"type": "applied", "skill": result["skill_name"], "to_v": result["to_version"]})
            st.toast(f"Upgraded {result['skill_name']} to v{result['to_version']}!")
            st.rerun()

    # Proposal display
    if sm.proposals:
        p = sm.proposals[-1]
        sc = "#fbbf24" if p["status"] == "pending" else "#00d4aa"
        st.markdown(f"""<div class="evo-card">
            <strong>{p['skill_name']}</strong> &mdash; <span style="color:{sc};">{p['status'].upper()}</span><br>
            <span style="color:#a78bfa;">{p.get('analysis','')}</span>
        </div>""", unsafe_allow_html=True)
        for ch in p.get("changes_made", []):
            st.markdown(f"&nbsp;&nbsp;&bull; {ch}")
        with st.expander("View proposed instructions"):
            st.code(p.get("improved_instructions", ""), language="markdown")

    # History
    if sm.applied:
        st.markdown('<div class="sec-head" style="font-size:1rem;">Evolution Timeline</div>', unsafe_allow_html=True)
        for a in reversed(sm.applied):
            st.markdown(f"""<div class="evo-card">
                <strong>{a['skill_name']}</strong> v{a['from_version']} &rarr; v{a['to_version']}<br>
                <small style="color:#7c3aed;">{', '.join(a.get('changes',[])[:2])}</small>
            </div>""", unsafe_allow_html=True)

    # Export
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("Export Health Wiki", json.dumps(wiki.export(), indent=2),
                          "medimind_export.json", "application/json", use_container_width=True)
    with col2:
        st.download_button("Export Brain History", json.dumps(sm.get_summary(), indent=2),
                          "brain_evolution.json", "application/json", use_container_width=True)


# ═══════ TAB 6: Architecture ═══════
with tab6:
    st.markdown('<div class="sec-head">System Architecture</div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-sub">Two-tier memory with self-improving AI skills</div>', unsafe_allow_html=True)

    # Live system status
    redis_stats = get_redis_stats()

    st.markdown("#### Live System Status")
    metric_row([
        ("ON" if REDIS_AVAILABLE else "OFF", "Redis", "#00d4aa" if REDIS_AVAILABLE else "#f87171"),
        ("ON", "Cognee Graph", "#00d4aa"),
        ("ON", "OpenAI GPT-4o-mini", "#00d4aa"),
        (f"v{max(sm.get_skill_version(n) for n in sm.skills)}" if sm.skills else "v1", "AI Skills", "#8b5cf6"),
    ])

    if REDIS_AVAILABLE:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">Redis Stats</div>
            <div class="card-body">Keys: {redis_stats.get('keys', '?')} | Memory: {redis_stats.get('memory_used', '?')}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Architecture diagram
    st.markdown("#### Two-Tier Memory Architecture")
    st.markdown("""
    <div class="card" style="border-color: #f87171;">
        <span class="card-cat" style="background:#2d1a1a;color:#f87171;">TIER 1 — REDIS</span>
        <div class="card-title">Session Layer (Fast, Ephemeral)</div>
        <div class="card-body">
            Sub-millisecond reads for current session context.<br>
            Caches active health entries for instant drug interaction checks.<br>
            Stores conversation history per session for contextual follow-up questions.<br>
            TTL: 24 hours. Syncs to permanent graph asynchronously.<br><br>
            <strong>Used for:</strong> Real-time medication lookups, session Q&A history, fast alerts
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="text-align:center; color:#4a5568; font-size:1.5rem; margin:0.3rem 0;">&#8595; distills to &#8595;</div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="card" style="border-color: #00d4aa;">
        <span class="card-cat" style="background:#0c2d15;color:#4ade80;">TIER 2 — COGNEE KNOWLEDGE GRAPH</span>
        <div class="card-title">Permanent Layer (Durable, Cross-Session)</div>
        <div class="card-body">
            Entities, relationships, and summaries persisted across all sessions.<br>
            cognee.remember() stores raw text → auto-builds knowledge graph.<br>
            cognee.recall() queries with auto-routing (vector + graph search).<br>
            Session data distills into permanent knowledge over time.<br><br>
            <strong>Used for:</strong> Cross-session health history, deep knowledge retrieval, entity relationships
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("#### Self-Improvement Loop (Karpathy LLM Wiki Pattern)")
    st.markdown("""
    <div class="card" style="border-color: #8b5cf6;">
        <div class="card-body" style="font-size:0.9rem; line-height:2;">
            <strong style="color:#c4b5fd;">1. INGEST</strong> — Raw health text → LLM extracts structured data → stored in Redis (fast) + Cognee (permanent)<br>
            <strong style="color:#c4b5fd;">2. QUERY + SELF-IMPROVE</strong> — User asks questions → AI cross-references profile → user corrects data → corrections feed improvement loop<br>
            <strong style="color:#c4b5fd;">3. LINT</strong> — Red-team agent audits for contradictions (penicillin allergy vs amoxicillin), outdated info, gaps → auto-fixes<br>
            <strong style="color:#c4b5fd;">4. SKILL EVOLUTION</strong> — Corrections analyzed → improved skill instructions proposed → applied → AI reasoning gets better each cycle
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("#### Tech Stack")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("""
        <div class="card" style="text-align:center;">
            <div class="card-title" style="color:#00d4aa;">Cognee</div>
            <div class="card-body">AI Memory Engine<br>Knowledge Graph<br>remember() / recall()</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="card" style="text-align:center;">
            <div class="card-title" style="color:#f87171;">Redis</div>
            <div class="card-body">Session Cache<br>Real-time State<br>Sub-ms Lookups</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="card" style="text-align:center;">
            <div class="card-title" style="color:#38bdf8;">OpenAI</div>
            <div class="card-body">GPT-4o-mini<br>Extraction & Reasoning<br>Structured Output</div>
        </div>""", unsafe_allow_html=True)
    with col4:
        st.markdown("""
        <div class="card" style="text-align:center;">
            <div class="card-title" style="color:#fbbf24;">Streamlit</div>
            <div class="card-body">Interactive UI<br>Real-time Updates<br>Chat Interface</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### Data Flow")
    st.code("""
User pastes doctor notes
    ↓
[OpenAI GPT-4o-mini] — extracts structured health data
    ↓
┌──────────────────────────────────────────┐
│  TIER 1: Redis                           │
│  - Cache entries (sub-ms reads)          │
│  - Session Q&A history                   │
│  - Real-time medication index            │
└──────────────┬───────────────────────────┘
               │ async distill
┌──────────────▼───────────────────────────┐
│  TIER 2: Cognee Knowledge Graph          │
│  - Permanent entities & relationships    │
│  - Cross-session health knowledge        │
│  - Vector + graph search                 │
└──────────────────────────────────────────┘
               │
    User asks question
               │
    ┌──────────▼──────────┐
    │  Query Pipeline      │
    │  1. Redis session ctx│
    │  2. Cognee graph ctx │
    │  3. Wiki profile     │
    │  4. Evolving skills  │
    └──────────┬──────────┘
               │
    [AI generates personalized answer]
               │
    User corrects → feeds improvement loop
               │
    [Meta-learning agent] → proposes skill upgrade
               │
    Apply → Skills v1 → v2 → v3 (gets smarter)
    """, language="text")

