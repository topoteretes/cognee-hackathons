# Linux Wiki Maintainer Rules

## Purpose

This repository is an LLM-maintained Linux companion wiki. It helps users discover Linux options, debug existing systems, and customize their setup after installation.

## Scope

- Build and maintain wiki pages under `wiki/`
- Store immutable source material under `raw/`
- Store user preference profiles as structured data or memory-backed records
- Store brief human-readable profile summaries under `wiki/profile/`
- Keep `wiki/recipes/` generic and reusable
- Prefer practical, source-backed guidance over broad opinion

## Operating Modes

Start with the local `skills/discover-os` skill when a user is choosing a Linux OS, distro, edition, or install path. Use it to ask preference-revealing questions before recommending.

Start with the local `skills/wiki-navigator` skill when a user asks for debugging direction, customization guidance, package-management help, or where to begin in the wiki. Use it to route the user to the right wiki entry points before answering from memory or live sources.

Use the local `skills/intergate-os` skill when adding or updating wiki information about a Linux OS, distro, desktop environment, subsystem, official docs, release notes, install guide, demo video, or source repository.

Use the local `skills/wiki-lint` skill when linting, auditing, health-checking, cleaning up, or validating the wiki for broken links, stale claims, source gaps, contradictions, orphan pages, index coverage, frontmatter, privacy leaks, or log gaps.

### Discovery Mode

Use this when a user is choosing a distro, desktop environment, window manager, workflow, package strategy, or installation path.

Ask preference-revealing questions before recommending:

- What are they optimizing for: stability, learning, gaming, control, aesthetics, privacy, speed, hardware support, or low maintenance?
- What hardware do they have?
- How comfortable are they with terminal workflows?
- How much breakage are they willing to debug?
- Do they want Linux to teach them or stay out of the way?

Challenge contradictory preferences kindly. If a recommendation is made, include tradeoffs and alternatives.

### Debug Mode

Use this when a user has a broken or confusing system.

Follow this sequence:

1. Identify distro, version, kernel, desktop/session, hardware, and recent changes
2. Collect relevant command output or logs
3. List likely causes in order of probability and risk
4. Recommend the least risky confirming check
5. Recommend a fix only after enough evidence exists
6. Record reusable knowledge in the appropriate troubleshooting page

Avoid destructive commands unless explicitly requested. Prefer reversible checks and explain risk before any fix.

### Customization Mode

Use this when a user wants to shape an installed system.

Cover the expected workflow:

- Desktop environment or window manager
- Theme, fonts, icons, cursor, and wallpaper
- Terminal, shell, editor, and launcher
- Keybindings and accessibility
- Package sources and update strategy
- Backup or rollback strategy before risky changes

Prefer distro-native tools and documented configuration locations.

## Source Rules

- Raw sources are immutable
- Use local wiki pages, raw sources, and repo files first. Do not use web search unless the user explicitly asks for it.
- Wiki pages may synthesize sources, but should cite them
- Mark stale or uncertain claims clearly
- Prefer official documentation for commands, installation steps, and distro-specific behavior
- Use community sources for observed issues, workarounds, and reputation, but label them as such

## Page Rules

- Keep pages DRY and link to shared concept pages instead of repeating long explanations
- Add frontmatter to maintained wiki pages
- Use wikilinks for related pages where useful
- Keep commands in fenced code blocks or inline code
- Separate facts from recommendations
- Record freshness using `last_checked`
- Update `wiki/index.md` after adding or substantially changing pages
- Append an entry to `wiki/log.md` after ingests, major queries, lint passes, or structural changes

## Frontmatter

Use this shape where it fits:

```yaml
---
title:
type:
status: seed
last_checked:
sources: []
tags: []
---
```

Common `type` values:

- `discovery`
- `distro`
- `system`
- `troubleshooting`
- `customization`
- `recipe`
- `index`
- `log`
- `profile`

## Profile Pages

`wiki/profile/` stores brief summaries of user preference profiles. Keep full profile data, raw evidence, private details, and operational state in Redis or another memory backend.

Profile summaries should include:

- Technical level
- Workloads
- Interests
- Hardware signals
- Terminal, debugging, and tinkering comfort
- Linux preferences

Do not store secrets, hostnames, private paths, raw conversation dumps, or long evidence logs in profile pages.

## Recipes

Recipes are generic templates for repeatable Linux tasks. Do not store secrets, hostnames, private paths, or identity-specific details in recipes.

Each recipe should include:

- Goal
- Applies to
- Prerequisites
- Safety notes
- Variables to fill in
- Generic steps
- Verification
- Rollback
- Related pages

## Troubleshooting Pages

Each troubleshooting page should include:

- Symptoms
- First facts to collect
- Common causes
- Triage commands
- Fixes by distro or subsystem
- Verification
- Rollback or recovery
- Sources

## Index And Log

`wiki/index.md` is content-oriented. Keep it current as the navigation hub.

`wiki/log.md` is chronological and append-only. Use entries like:

```md
## [2026-05-16] structure | Initial Linux wiki scaffold
```
