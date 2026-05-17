# Synapse MD — Submission

## Idea
A self-evolving medical knowledge wiki that breaks down 
department silos in hospitals. Doctors input charts as usual. 
AI agents connect fragmented records across departments, 
detect hidden patterns, and automatically update a wiki 
that gets smarter with every case.

## Self-improvement Loop
1. Doctor inputs clinical notes → stored in Redis session memory
2. Cognee distills notes into permanent knowledge graph
3. Three agents debate: Connector links cross-department patterns,
   Skeptic validates statistically, Linter checks ADA 2024 guidelines
4. Linter scores the run — missing referral = low score (0.3)
5. SkillRunEntry records feedback → Cognee proposes SKILL.md rewrite
6. improve_skill(apply=True) upgrades the diagnostic rules
7. Wiki confidence score rises with each case accumulated

## Before/After Evidence

### Baseline Run
- Wiki v18, Confidence 64%, basic diabetes monitoring rules

Recorded feedback:
```
error_type: MissingReferralError
error_message: "Patient has HbA1c 10.1% and blurry vision, but no ophthalmology referral was generated."
feedback: "Critical gap in care. High HbA1c with visual symptoms requires immediate specialist referral per ADA guidelines."
success_score: 0.3
```

### Improved Run
- Wiki v20, Confidence 81%, ADA 2024 §4.2 ALERT triggered
- Score: 0.9 (ADA 2024 guidelines fully met, ophthalmology referral automatically triggered)

## SKILL.md Evolution

**Before:**
```
Patients with Type 2 Diabetes require regular monitoring.
Vision complaints should be noted.
```

**After:**
```
[RULE 4.2 - CRITICAL]
IF Patient(Type == "DM2") AND
(HbA1c > 10.0% OR Symptoms == "vision blur")
THEN TRIGGER_IMMEDIATE_REFERRAL(
Department == "Ophthalmology")
```

## Redis → Cognee Distillation

- **What stays in Redis:** Raw clinical text, chat history, and transient logs for the current session
- **What gets promoted:** High-fidelity medical entities (HbA1c 10.1%, Type 2 Diabetes) and diagnostic rules
- **How distillation quality improved:** Baseline run dumped raw notes; Improved run maps clinical terminology into structured medical knowledge graph using Cognee ontology

## Tech Stack
- Frontend: Next.js
- Backend: FastAPI
- Memory: Redis (session) + Cognee (permanent knowledge graph)
- AI: OpenAI GPT-4
- Skills: my_skills/diabetic-retinopathy/SKILL.md
