---
name: profile
description: Manage Linux user preference profiles for personalized wiki discovery, debugging, and customization. Use when the user wants to create, select, inspect, list, or delete a profile, or when profile-backed personalization is requested.
---

# Profile

## Purpose

Maintain user preference profiles as structured memory records, with brief summaries under `wiki/profile/`.

Profiles help the Linux wiki agent personalize recommendations using:

- Technical level
- Workloads, such as programming, gaming, video editing, design, or office work
- Interests, such as theming, window managers, privacy, automation, or desktop polish
- Hardware signals
- Terminal, debugging, and tinkering comfort
- Linux desktop, distro, and display preferences

## Storage

Profiles live in Redis through `hooks/user_preference_profile.py`.
Credentials come from `.env`, `hooks/.env`, or the shell.

Keep full profile data and raw evidence in Redis. Write only short summaries under `wiki/profile/`.

## User Flow

When the user asks to use profiles:

- `create`: ask a few short questions if needed, then create or overwrite the named profile
- `select`: switch the active profile to the named profile
- `show`: display the active profile or a named profile
- `list`: show available profiles and which one is active
- `delete`: remove the named profile; if it was active, clear the active profile

Keep the UX conversational. Do not expose command details unless the user asks.

## Hook

Use `hooks/user_preference_profile.py` to read and write profile state in Redis.
Run the hook directly with `python hooks/user_preference_profile.py`; do not wrap it with project runners such as `uv run`.
Prefer the action names `create`, `select`, `get`, `list`, and `delete`.

The hook should be the path for reading Redis-backed profile data. Treat `wiki/profile/` as the readable summary layer, not the source of truth.

## Behavior

When creating a profile, collect concise preference evidence from the user.
Ask about role/workload, technical comfort, interests, hardware, and maintenance tolerance if missing.

When selecting a profile, confirm the selected profile id.

When deleting a profile, delete only the requested profile id. If it was selected, clear the active selection.

When answering Linux discovery, debugging, or customization questions, use the selected profile to tailor tradeoffs and recommendations.
