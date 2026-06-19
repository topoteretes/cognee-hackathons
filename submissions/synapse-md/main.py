import json
import os
import re
from pathlib import Path

import cognee

import openai
import redis as redis_lib
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

app = FastAPI(title="Synapse MD API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001"],
    allow_methods=["*"],
    allow_headers=["*"],
)

cases: list[dict] = json.loads(Path("cases.json").read_text())

cognee.config.set_llm_api_key(os.environ["OPENAI_API_KEY"])
cognee.config.set_llm_model("gpt-4o-mini")


class AnalyzeRequest(BaseModel):
    notes: str
    department: str = "General"


class DebateRequest(BaseModel):
    notes: str
    department: str = "General"
    cognee_results: list[str] = []
    matched_cases: list[dict] = []


class QueryRequest(BaseModel):
    question: str


_SKILL_PATH = Path("my_skills/diabetic-retinopathy/SKILL.md")

wiki_state: dict = {
    "run_count": 0,
    "confidence": 64,
    "confidence_history": [],
    "skill_version": 1,
    "baseline_skill": "",
    "current_skill": "",
}


@app.get("/wiki-state")
def get_wiki_state():
    return wiki_state


def tokenize(text: str) -> set[str]:
    return set(re.sub(r"[^\w\s]", " ", text).lower().split())


@app.get("/health")
def health():
    # Check Redis
    try:
        r = redis_lib.from_url(os.environ["REDIS_URL"])
        r.ping()
        redis_status = "ok"
    except Exception as e:
        redis_status = f"error: {e}"

    # Check OpenAI (list models — cheap, no tokens consumed)
    try:
        client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        client.models.list()
        openai_status = "ok"
    except Exception as e:
        openai_status = f"error: {e}"

    return {"redis": redis_status, "openai": openai_status}


@app.get("/test-cognee")
async def test_cognee():
    await cognee.remember(
        "Type 2 Diabetes is associated with diabetic retinopathy. "
        "Annual ophthalmology referral is required per ADA 2024.",
        dataset_name="medical-wiki",
    )
    results = await cognee.recall("diabetes ophthalmology")
    return {"results": results}


@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    # --- keyword matching (always runs) ---
    note_tokens = tokenize(req.notes)
    entities_found: list[str] = []
    matched_cases: list[dict] = []

    for case in cases:
        matched_entities = [
            entity for entity in case["entities"]
            if tokenize(entity) <= note_tokens
        ]
        if matched_entities:
            for e in matched_entities:
                if e not in entities_found:
                    entities_found.append(e)
            matched_cases.append({
                "id": case["id"],
                "department": case["department"],
                "chief_complaint": case["chief_complaint"],
            })

    # --- Cognee memory + recall (fails silently) ---
    cognee_results: list[str] = []
    status = "keyword_only"

    try:
        await cognee.remember(req.notes, dataset_name="medical-wiki")
        await cognee.remember(
            f"Department: {req.department}\n{req.notes}",
            dataset_name="medical-wiki",
            session_id="demo-session",
        )
        results = await cognee.recall(req.notes, session_id="demo-session")
        cognee_results = [
            getattr(r, "text", None) or getattr(r, "answer", None)
            for r in results
            if getattr(r, "text", None) or getattr(r, "answer", None)
        ]
        status = "ingested"
    except Exception:
        pass

    return {
        "entities_found": entities_found,
        "matched_cases": matched_cases,
        "cognee_results": cognee_results,
        "status": status,
    }


@app.post("/publish-wiki")
async def publish_wiki():
    try:
        skill_content = _SKILL_PATH.read_text()
    except Exception:
        skill_content = wiki_state.get("current_skill", "")

    await cognee.remember(skill_content, dataset_name="medical-wiki")

    session_cleaned = False
    try:
        await cognee.forget(dataset="demo-session")
        session_cleaned = True
    except Exception:
        pass

    wiki_state["publish_count"] = wiki_state.get("publish_count", 0) + 1
    version = wiki_state["skill_version"]

    return {
        "published": True,
        "version": version,
        "distilled_to": "permanent_graph",
        "session_cleaned": session_cleaned,
    }


@app.post("/query-wiki")
async def query_wiki(req: QueryRequest):
    try:
        results = await cognee.recall(req.question, session_id="demo-session")
        texts = [
            getattr(r, "text", None) or getattr(r, "answer", None)
            for r in results
            if getattr(r, "text", None) or getattr(r, "answer", None)
        ]
        if not texts:
            return {"answer": "No relevant entries found yet. Run a multi-agent review first to populate the knowledge graph."}

        context = " ".join(texts)
        client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a medical wiki assistant. "
                        "Answer the question based on the knowledge provided. "
                        "Be concise and specific. Max 3 sentences."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Question: {req.question}\nKnowledge: {context}",
                },
            ],
        )
        answer = response.choices[0].message.content.strip()
    except Exception:
        answer = "Wiki query unavailable. Run a multi-agent review first to build the knowledge graph."
    return {"answer": answer}


def connector_prompt(department: str) -> str:
    return (
        "You are the Connector agent in a medical AI system. "
        "Your job is to find hidden cross-department patterns in patient data. "
        f"The patient is currently in {department}. "
        "Check their records from other departments for dangerous conflicts. "
        "Identify causal connections between departments. Be specific and concise. Max 3 sentences."
    )

AGENT_PROMPTS = {
    "connector": "",  # replaced per-request via connector_prompt()

    "skeptic": (
        "You are the Skeptic agent in a medical AI system. "
        "Your job is to challenge the Connector's analysis and find weaknesses, "
        "missing differentials, or alternative explanations. Be direct and critical. "
        "Respond ONLY with valid JSON in this exact shape: "
        "{\"analysis\": \"<your critique in max 3 sentences>\", \"confidence\": <integer 0-100>} "
        "where confidence reflects how certain you are a serious alternative diagnosis exists."
    ),
    "linter": (
        "You are the Linter agent in a medical AI system. "
        "Your job is to check the previous agents' reasoning for logical inconsistencies, "
        "missing safety flags, or protocol violations. "
        "Respond ONLY with valid JSON in this exact shape: "
        "{\"analysis\": \"<your findings in max 3 sentences>\", \"alert\": <true|false>} "
        "where alert is true if any patient safety issue requires immediate clinician review."
    ),
}


def run_agent(client: openai.OpenAI, agent: str, user_message: str) -> str | dict:
    try:
        kwargs: dict = dict(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": AGENT_PROMPTS[agent]},
                {"role": "user",   "content": user_message},
            ],
        )
        if agent in ("skeptic", "linter"):
            kwargs["response_format"] = {"type": "json_object"}
        response = client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        if agent in ("skeptic", "linter"):
            return json.loads(content)
        return content
    except Exception:
        if agent == "skeptic":
            return {"analysis": "Analysis unavailable", "confidence": 50}
        if agent == "linter":
            return {"analysis": "Analysis unavailable", "alert": False}
        return "Analysis unavailable"


@app.post("/debate")
async def debate(req: DebateRequest):
    try:
        context = await cognee.recall(req.notes, session_id="demo-session")
        context_texts = [
            getattr(r, "text", None) or getattr(r, "answer", None)
            for r in context
            if getattr(r, "text", None) or getattr(r, "answer", None)
        ]
        knowledge = req.cognee_results or context_texts

        client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])

        # Round 1 — Connector
        AGENT_PROMPTS["connector"] = connector_prompt(req.department)
        connector_input = (
            f"Department: {req.department}\n"
            f"Clinical notes: {req.notes}\n"
            f"Related cases: {req.matched_cases}\n"
            f"Cognee knowledge: {knowledge}"
        )
        connector_out = run_agent(client, "connector", connector_input)

        # Round 2 — Skeptic challenges Connector
        skeptic_input = (
            f"Clinical notes: {req.notes}\n"
            f"Connector analysis: {connector_out}\n"
            f"Related cases: {req.matched_cases}"
        )
        skeptic_out = run_agent(client, "skeptic", skeptic_input)

        # Round 3 — Linter reviews both
        linter_input = (
            f"Clinical notes: {req.notes}\n"
            f"Connector analysis: {connector_out}\n"
            f"Skeptic challenge: {skeptic_out}\n"
            f"Cognee knowledge: {knowledge}"
        )
        linter_out = run_agent(client, "linter", linter_input)

        # --- Self-improvement loop ---
        skill_improved = False
        skill_score = 0.0

        linter_alert_val = linter_out.get("alert", False)
        linter_analysis = linter_out.get("analysis", "")
        score = 0.3 if linter_alert_val else 0.9
        skill_score = score

        # Snapshot skill before improvement
        try:
            wiki_state["baseline_skill"] = _SKILL_PATH.read_text()
        except Exception:
            wiki_state["baseline_skill"] = ""

        try:
            current_skill = wiki_state["baseline_skill"] or _SKILL_PATH.read_text()

            improve_prompt = (
                "You are improving a medical AI skill definition based on a recent case.\n\n"
                f"Current SKILL.md:\n{current_skill}\n\n"
                f"Clinical case:\n{req.notes}\n\n"
                f"Linter findings: {linter_analysis}\n"
                f"Safety alert raised: {linter_alert_val}\n"
                f"Score: {score}\n\n"
                "Rewrite the SKILL.md to incorporate lessons from this case. "
                "Keep the YAML frontmatter block exactly as-is (lines between the --- delimiters). "
                "Improve the rules to be more specific and add any missing protocols flagged by the linter. "
                "Return ONLY the complete updated SKILL.md content, nothing else."
            )

            improve_client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
            improve_resp = improve_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": improve_prompt}],
            )
            new_skill_text = improve_resp.choices[0].message.content.strip()
            _SKILL_PATH.write_text(new_skill_text)
            skill_improved = True
        except Exception:
            pass

        # Update cumulative wiki state
        wiki_state["run_count"] += 1
        skeptic_confidence = int(skeptic_out.get("confidence", 50))
        wiki_state["confidence_history"].append(skeptic_confidence)
        wiki_state["confidence"] = round(sum(wiki_state["confidence_history"]) / len(wiki_state["confidence_history"]))
        if skill_improved:
            wiki_state["skill_version"] += 1
        try:
            wiki_state["current_skill"] = _SKILL_PATH.read_text()
        except Exception:
            wiki_state["current_skill"] = ""

        return {
            "connector":     {"analysis": connector_out},
            "skeptic":       skeptic_out,
            "linter":        linter_out,
            "wiki_updated":  True,
            "skill_improved": skill_improved,
            "skill_score":   skill_score,
            "wiki_state": {
                "run_count":          wiki_state["run_count"],
                "confidence":         wiki_state["confidence"],
                "confidence_history": wiki_state["confidence_history"],
                "skill_version":      wiki_state["skill_version"],
                "skill_before":       wiki_state["baseline_skill"][:500],
                "skill_after":        wiki_state["current_skill"][:500],
            },
            "status":        "complete",
        }

    except Exception:
        return {
            "connector":     {"analysis": "Analysis unavailable"},
            "skeptic":       {"analysis": "Analysis unavailable", "confidence": 50},
            "linter":        {"analysis": "Analysis unavailable", "alert": False},
            "wiki_updated":  False,
            "skill_improved": False,
            "skill_score":   0.0,
            "status":        "error",
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
