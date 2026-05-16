---
name: wiki-lint
description: Health-check and maintain this Linux wiki. Use when the user asks to lint, audit, review, validate, health-check, clean up, find contradictions, find stale claims, find orphan pages, repair wikilinks, improve cross-references, update index coverage, inspect missing frontmatter, or identify gaps in the wiki. Use local wiki, raw sources, and repo files first; do not web search unless explicitly requested.
---

# Wiki Lint

## Purpose

Find structural, sourcing, freshness, and navigation problems in the Linux wiki, then either report them or make narrowly scoped maintenance edits when asked.

This skill is for wiki health, not Linux troubleshooting or distro ingest. Use `wiki-navigator` for answering user questions and `intergate-os` or `update-os` for adding or refreshing OS/project facts.

## Default Scope

Lint these by default:

- `wiki/**/*.md`
- `wiki/index.md`
- `wiki/log.md`
- local skill instructions only when they affect wiki maintenance

Do not modify `raw/`; sources are immutable.

## First Pass

1. Read `AGENTS.md`, `wiki/index.md`, and the latest entries in `wiki/log.md`.
2. List wiki pages with `rg --files wiki`.
3. Build a quick map of page paths, titles, frontmatter `type`, `status`, `last_checked`, `sources`, and wikilinks.
4. Compare the map against `wiki/index.md`.
5. Search for stale-risk language and unresolved markers before reading deeply:

```bash
rg -n "\b(latest|current|currently|new|recent|now|today|recommended|best|default)\b|TODO|TBD|FIXME|uncertain|stale|missing" wiki
```

## Checks

Prioritize findings by impact:

- Broken wikilinks: `[[target]]` or markdown links that do not resolve to an existing page or heading.
- Missing index coverage: maintained pages not listed from `wiki/index.md`, or index entries pointing nowhere.
- Missing or malformed frontmatter on maintained wiki pages.
- Stale freshness fields: missing `last_checked`, dates older than the surrounding source context, or freshness-sensitive claims without a check date.
- Source gaps: factual claims, commands, install guidance, version statements, or recommendations with no source citation.
- Contradictions: pages that disagree on base distro, package manager, desktop, release model, command behavior, risk, or recommendation tradeoffs.
- Orphans and weak navigation: useful pages with no inbound links from index pages or related concept pages.
- Missing concept pages: repeated important terms without a shared page or index entry.
- Duplication: long repeated explanations that should move to a shared system, customization, troubleshooting, or recipe page.
- Page-shape drift: distro, system, recipe, troubleshooting, profile, and customization pages missing sections required by `AGENTS.md`.
- Privacy leaks: secrets, hostnames, private paths, raw conversation dumps, or long evidence logs in wiki pages or recipes.
- Log gaps: missing `wiki/log.md` entries after major wiki changes.

## Source Rules

- Use local wiki pages, raw sources, and repo files first.
- Do not use web search unless the user explicitly asks for it.
- If a lint finding needs current external verification, mark it as a follow-up instead of guessing.
- Prefer official sources for commands, install steps, release claims, and distro-specific behavior.
- Label community-sourced claims separately from official facts.

## Report Mode

When the user asks for a lint report, audit, review, or dry run, do not edit files unless they explicitly ask for fixes.

Return:

- Critical findings first, with file references and line numbers when possible.
- Then medium and low-priority findings.
- Suggested fixes grouped by page or category.
- Follow-up source checks that would require web access.
- A short note on what was inspected.

## Fix Mode

When the user asks to fix lint issues:

1. Keep edits narrow and DRY.
2. Preserve existing page voice and structure where possible.
3. Add or repair wikilinks instead of duplicating explanations.
4. Update `wiki/index.md` when navigation changes.
5. Update `last_checked` only for pages whose facts were actually re-verified.
6. Append one concise entry to `wiki/log.md` after the lint/fix pass.

Use this log shape:

```md
## [YYYY-MM-DD] lint | <brief summary of lint pass or fixes>
```

## Output Shape

When fixes are made, finish with:

- Pages changed
- Highest-impact issues fixed
- Checks not performed, especially external freshness checks
- Any remaining risks or recommended follow-up lint passes
