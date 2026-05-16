"""
MediMind Skills - Uses Cognee's native skill improvement loop.
Skills are Markdown files ingested into the graph via cognee.remember().
Self-improvement uses SkillRunEntry + improve_skill (propose-then-apply).
"""
import json
import asyncio
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI()

SKILLS_DIR = Path(__file__).parent.parent / "my_skills"


async def ingest_skills_to_cognee(dataset_name="medimind-wiki"):
    """Ingest skill markdown files into Cognee's knowledge graph."""
    try:
        import cognee
        result = await cognee.remember(
            str(SKILLS_DIR),
            dataset_name=dataset_name,
            content_type="skills",
        )
        return result
    except Exception as e:
        print(f"Skill ingestion note: {e}")
        return None


async def run_cognee_skill_query(query: str, skill_name: str, session_id: str,
                                  dataset="medimind-wiki"):
    """Run a query through Cognee's agentic completion with a skill."""
    try:
        import cognee
        from cognee import SearchType
        result = await cognee.search(
            query,
            query_type=SearchType.AGENTIC_COMPLETION,
            datasets=dataset,
            skills=[skill_name],
            max_iter=4,
            session_id=session_id,
        )
        return result
    except Exception as e:
        print(f"Cognee skill query note: {e}")
        return None


async def record_skill_run(skill_name: str, task_text: str, result_summary: str,
                            score: float, dataset="medimind-wiki", session_id="default"):
    """Record a skill run and propose improvement using Cognee's native SkillRunEntry."""
    try:
        import cognee
        from cognee.memory import SkillRunEntry

        proposal_result = await cognee.remember(
            SkillRunEntry(
                selected_skill_id=skill_name,
                task_text=task_text,
                result_summary=result_summary,
                success_score=score,
                feedback=-1.0 if score < 0.7 else 1.0,
            ),
            dataset_name=dataset,
            session_id=session_id,
            skill_improvement={
                "skill_name": skill_name,
                "apply": False,
                "score_threshold": 0.9,
            },
        )
        return proposal_result
    except Exception as e:
        print(f"Skill run recording note: {e}")
        return None


async def apply_skill_improvement(skill_name: str, proposal_id: str,
                                    dataset="medimind-wiki"):
    """Apply a proposed skill improvement using Cognee's native improve_skill."""
    try:
        from cognee.modules.memify.skill_improvement import improve_skill
        from cognee.modules.pipelines.layers.resolve_authorized_user_datasets import (
            resolve_authorized_user_datasets,
        )
        from uuid import UUID

        user, datasets = await resolve_authorized_user_datasets(UUID(dataset))
        await improve_skill(
            skill_name,
            dataset=datasets[0],
            user=user,
            proposal_id=proposal_id,
            apply=True,
        )
        return True
    except Exception as e:
        print(f"Skill improvement note: {e}")
        return False


def read_skill_file(skill_name: str) -> str:
    """Read current skill instructions from the markdown file."""
    skill_path = SKILLS_DIR / skill_name / "SKILL.md"
    if skill_path.exists():
        return skill_path.read_text()
    return ""


def get_all_skills() -> dict:
    """Get all skills and their current content."""
    skills = {}
    if SKILLS_DIR.exists():
        for skill_dir in SKILLS_DIR.iterdir():
            if skill_dir.is_dir():
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    content = skill_file.read_text()
                    skills[skill_dir.name] = {
                        "name": skill_dir.name,
                        "content": content,
                        "path": str(skill_file),
                    }
    return skills


# ── Fallback skill manager (works even if Cognee skill APIs aren't available) ──

IMPROVE_PROMPT = """You are a meta-learning agent. Improve this health AI skill based on user corrections and feedback.

Current skill name: {skill_name}
Current instructions:
{current_instructions}

User corrections and feedback:
{corrections}

Analyze what the agent got wrong and write IMPROVED skill instructions.
Keep the same markdown format with YAML front matter.
Be specific — add concrete rules learned from the corrections.

Output JSON:
{{
    "analysis": "what patterns you noticed in the errors",
    "improved_instructions": "the full improved SKILL.md content including YAML front matter",
    "changes_made": ["specific change 1", "specific change 2"],
    "expected_improvement": "what should get better"
}}
"""


class SkillManager:
    """Manages skills with Cognee native APIs, falls back to local file management."""

    def __init__(self):
        self.skills = get_all_skills()
        self.proposals: list[dict] = []
        self.applied: list[dict] = []
        self.cognee_initialized = False

    def get_instructions(self, skill_name: str) -> str:
        """Get skill instructions, reading from file."""
        skill = self.skills.get(skill_name)
        if skill:
            return skill["content"]
        # Try reading directly
        content = read_skill_file(skill_name)
        if content:
            return content
        return ""

    async def init_cognee_skills(self, dataset="medimind-wiki"):
        """Ingest skills into Cognee graph. Call once at startup."""
        if not self.cognee_initialized:
            result = await ingest_skills_to_cognee(dataset)
            self.cognee_initialized = result is not None
            return result

    def propose_improvement(self, skill_name: str, corrections: list[dict],
                           feedback: str = "") -> dict:
        """Generate a proposed skill improvement."""
        current = self.get_instructions(skill_name)

        corrections_text = "\n".join(
            f"- Query: {c.get('question', c.get('entry', '?'))[:60]} | "
            f"Issue: {c.get('reason', c.get('feedback', 'no detail'))}"
            for c in corrections[-10:]
        )
        if feedback:
            corrections_text += f"\n- Direct feedback: {feedback}"

        # Try native Cognee skill improvement first
        try:
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(
                record_skill_run(
                    skill_name=skill_name,
                    task_text=corrections_text[:200],
                    result_summary=f"User provided {len(corrections)} corrections",
                    score=0.4,
                )
            )
            if result:
                # Extract proposal ID if available
                try:
                    for item in result.items:
                        if item.get("kind") == "skill_improvement_proposal":
                            proposal = {
                                "skill_name": skill_name,
                                "proposal_id": item["proposal_id"],
                                "analysis": "Generated via Cognee native skill improvement",
                                "improved_instructions": item.get("proposed_content", current),
                                "changes_made": ["Cognee-generated improvement based on run feedback"],
                                "status": "pending",
                                "proposed_at": datetime.now().isoformat(),
                                "source": "cognee_native",
                            }
                            self.proposals.append(proposal)
                            return proposal
                except Exception:
                    pass
        except Exception as e:
            print(f"Native skill improvement note: {e}")

        # Fallback: use OpenAI to generate improvement
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You improve AI agent skill files. Return valid JSON."},
                {"role": "user", "content": IMPROVE_PROMPT.format(
                    skill_name=skill_name,
                    current_instructions=current,
                    corrections=corrections_text or "No corrections yet.",
                )},
            ],
            temperature=0.4,
            response_format={"type": "json_object"},
        )

        proposal = json.loads(response.choices[0].message.content)
        proposal["skill_name"] = skill_name
        proposal["proposed_at"] = datetime.now().isoformat()
        proposal["status"] = "pending"
        proposal["source"] = "llm_generated"
        self.proposals.append(proposal)
        return proposal

    def apply_improvement(self, idx: int = -1) -> dict:
        """Apply a proposed improvement by rewriting the skill file."""
        if not self.proposals:
            return {"error": "No proposals"}

        proposal = self.proposals[idx]
        skill_name = proposal["skill_name"]
        new_content = proposal.get("improved_instructions", "")

        if not new_content:
            return {"error": "No improved instructions in proposal"}

        # Try native Cognee apply first
        if proposal.get("source") == "cognee_native" and proposal.get("proposal_id"):
            try:
                loop = asyncio.get_event_loop()
                loop.run_until_complete(
                    apply_skill_improvement(skill_name, proposal["proposal_id"])
                )
            except Exception as e:
                print(f"Native apply note: {e}")

        # Write updated skill file
        skill_path = SKILLS_DIR / skill_name / "SKILL.md"
        old_content = skill_path.read_text() if skill_path.exists() else ""

        # Determine version from applied count
        version = len([a for a in self.applied if a["skill_name"] == skill_name]) + 2

        skill_path.write_text(new_content)

        proposal["status"] = "applied"

        record = {
            "skill_name": skill_name,
            "from_version": version - 1,
            "to_version": version,
            "changes": proposal.get("changes_made", []),
            "applied_at": datetime.now().isoformat(),
        }
        self.applied.append(record)

        # Refresh in-memory skills
        self.skills = get_all_skills()

        # Re-ingest updated skills into Cognee
        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(ingest_skills_to_cognee())
        except Exception:
            pass

        return record

    def get_skill_version(self, skill_name: str) -> int:
        return len([a for a in self.applied if a["skill_name"] == skill_name]) + 1

    def get_summary(self) -> dict:
        return {
            "total_proposals": len(self.proposals),
            "applied": len(self.applied),
            "pending": len([p for p in self.proposals if p["status"] == "pending"]),
            "skill_versions": {n: self.get_skill_version(n) for n in self.skills},
            "history": self.applied,
        }
