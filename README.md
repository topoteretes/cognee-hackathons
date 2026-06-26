# Cognee Hackathons

This repository is the home of Cognee's hackathon events. Each hackathon lives
in its own subfolder and contains everything needed to participate: the
challenge brief, setup instructions, starter skills or templates, examples,
and a submission template.

Cognee is an open-source AI memory platform that transforms raw data into
persistent knowledge graphs for AI agents. Our hackathons invite builders to
push that idea further — composing memory, agents, and tooling into systems
that learn, remember, and improve over time.

## Hackathons

| Date | Hackathon | Partner | Folder |
|------|-----------|---------|--------|
| 2026-02-07 | AI Hack Night: Build on a Prebuilt AI-Memory Knowledge Graph | Qdrant, Distil Labs, DigitalOcean | [`ai-memory-hackathon-2026-02-07`](./ai-memory-hackathon-2026-02-07) |
| 2026-04-25 | Cognee Daytona Moss Hackathon: PR Rescue Arena | Daytona, Moss | [`cognee-daytona-moss-hackathon-2026-04-25`](./cognee-daytona-moss-hackathon-2026-04-25) |
| 2026-05-16 | AI-Memory Hackathon: Building your own Agent LLM Wiki | Redis | [`cognee-redis-hackathon-2026-05-16`](./cognee-redis-hackathon-2026-05-16) |
| 2026-06-16 | Cognee Company Brain: Slack + Granola Knowledge Graph | — | [`cognee-companybrain-hackathon-2026-06-16`](./cognee-companybrain-hackathon-2026-06-16) |
| 2026-06-19 | Cognee Cloud Hackathon: Build Your Company Brain | — | [`cognee-cloud-hackathon-2026-06-19`](./cognee-cloud-hackathon-2026-06-19) |
| 2026-06-26 | Cognee GTM Brain (Warsaw): Merge Accounts, Deals & Conversations into One Graph | modelguide | [`cognee-gtm-brain-hackathon-2026-06-26`](./cognee-gtm-brain-hackathon-2026-06-26) |

## Repository Layout

Every hackathon folder is named `<hackathon-name>-<YYYY-MM-DD>` and starts with
a `README.md` covering the event overview, setup, schedule, and prizes.

Brief-style hackathons follow this layout:

```text
<hackathon-name>-<YYYY-MM-DD>/
  README.md         # event overview, setup, schedule, prizes
  challenge/        # detailed challenge brief
  skills/           # starter skills or scaffolding
  templates/        # submission template
  examples/         # reference implementations or before/after examples
```

Some hackathons were full standalone project repos before being archived here.
Those folders preserve their original project structure (source code,
`pyproject.toml`, Docker files, notebooks, sample data, etc.) alongside their
`README.md`. Start from each folder's `README.md` either way.

## Participating

1. Pick the hackathon folder for the event you are joining.
2. Read its `README.md` for setup, schedule, and judging criteria.
3. Follow the quickstart to get Cognee (and any partner tools) running.
4. Build, demo, and submit using the template in `templates/`.

## Links

- [Cognee on GitHub](https://github.com/topoteretes/cognee)
- [Cognee Documentation](https://docs.cognee.ai/)
- [Discord Community](https://discord.gg/NQPKmU5CCg)
