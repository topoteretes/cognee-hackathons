# Sherlock Submission Notes

This file is a clean companion to the final filled template in SUBMISSION.md.

## Project

- Team: Sherlock
- Participants: Keenan, Brian, Arsh, Abdoulaye
- Repo: [https://github.com/kklike32/cognee-redis-hackathon](https://github.com/kklike32/cognee-redis-hackathon)
- Coding repo local path: /Users/keenan/Documents/cognee-redis-hackathon
- Deck local path: /Users/keenan/Documents/cognee-redis-hackathon/sherlock_pitch.pptx

## What Sherlock Demonstrates

- Ingest local sources into a competitive intelligence wiki.
- Build and refresh a durable knowledge wiki for Deel.
- Generate cited battle-card briefs for sales deal context.
- Run analyst approve/reject/edit workflows for human-in-the-loop quality control.
- Show Redis cache miss/hit behavior and cache invalidation after approval.

## Verified Entrypoints

- Streamlit app: app/streamlit_app.py
- Ingest pipeline: sherlock/source_intake.py, sherlock/ingest.py
- Battle card generation: sherlock/card_agent.py, sherlock/retrieval.py
- Pending change workflow: sherlock/pending_generator.py, sherlock/pending_changes.py

## Reproduce Demo

```bash
cd /Users/keenan/Documents/cognee-redis-hackathon
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
cp .env.example .env
docker compose up -d redis
python scripts/reset_demo.py
python scripts/ingest_demo_data.py
streamlit run app/streamlit_app.py --server.port 8502
```

Open local app URL: [http://localhost:8502](http://localhost:8502)

## Submission Assets

- Filled submission template: templates/SUBMISSION.md
- GitHub repo: https://github.com/kklike32/cognee-redis-hackathon
- Demo runbook: /Users/keenan/Documents/cognee-redis-hackathon/DEMO_SHOWCASE.md
- Demo video: /Users/keenan/Documents/cognee-redis-hackathon/cognee_demo_video.mov
- Pitch deck generator: /Users/keenan/Documents/cognee-redis-hackathon/scripts/create_pitch.py
- Pitch deck file: /Users/keenan/Documents/cognee-redis-hackathon/sherlock_pitch.pptx

## Final Actions Before You Submit

1. Push your latest repo changes to main.
2. Upload sherlock_pitch.pptx to Google Drive or Slides and copy a share link.
3. Optionally record a short Loom/YouTube demo from the Streamlit flow.
4. Paste links into templates/SUBMISSION.md under Demo and Links.
5. Submit the final markdown content in the hackathon form.