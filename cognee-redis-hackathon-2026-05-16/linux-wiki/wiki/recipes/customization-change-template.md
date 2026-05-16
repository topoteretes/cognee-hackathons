---
title: Customization Change Template
type: recipe
status: seed
last_checked: 2026-05-16
sources: []
tags: [recipe, customization]
---

# Customization Change Template

## Goal

Apply a reversible customization change.

## Variables To Fill In

- `<desktop-or-window-manager>`
- `<config-path>`
- `<setting-name>`
- `<new-value>`

## Generic Steps

1. Identify the active desktop, session, or window manager
2. Locate the relevant config file or settings tool
3. Record the current value
4. Apply the smallest change
5. Reload the affected component
6. Verify the visible result

## Rollback

Restore the recorded previous value or move the edited config aside and restart the affected component.

## Related Pages

- [[../customization/customization-template]]
