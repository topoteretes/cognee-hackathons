---
name: discover-os
description: Help a user choose a Linux OS or distro through a short preference interview. Use when the user asks what Linux system, OS, distro, edition, or install path they should use, including goal-first prompts like gaming, stability, privacy, beginner-friendly, performance, aesthetics, or low maintenance.
---

# Discover OS

## Purpose

Help the user decide on an operating system path. This is a discovery interview, not a subsystem router.

Stay on the user's question. If they ask for "a system for gaming", help choose the OS first. Do not introduce package-management, graphics-stack, driver, desktop-environment, or customization pages unless the user asks, or unless one detail is essential to distinguish recommendations.

## First Move

If the user gives only a broad goal, ask a small set of preference-revealing questions before recommending.

Ask no more than three questions at a time. For broad OS-choice prompts, prioritize:

- Hardware class: desktop, laptop, handheld, VM, old PC, or unknown
- GPU vendor when gaming or graphics performance matters: AMD, NVIDIA, Intel, or unknown
- Maintenance preference: low-maintenance/stable, balanced, or performance/rolling

Ask comfort level later only if the first answers do not settle the recommendation.

If the user has already answered enough, recommend directly.

## Recommendation Shape

Lead with the recommendation, then explain the tradeoffs.

Use this structure:

1. Best fit
2. Why it matches the user's stated goal
3. Main tradeoff
4. One or two alternatives only when they meaningfully differ
5. Next question only if needed to decide

Keep wiki routing quiet. Mention a page only when it helps the decision, and prefer distro pages over subsystem pages.

## Gaming Defaults

For gaming-first requests:

- Default to `wiki/distros/fedora/bazzite.md` when the user wants games to work with low maintenance.
- Consider `wiki/distros/arch/cachyos.md` when the user wants performance tuning and accepts rolling-release maintenance.
- Consider `wiki/distros/debian/pop-os.md` when the user has NVIDIA hardware and wants an Ubuntu-family desktop path.

Ask about GPU and device type before going deeper. Do not bring up Flatpak, rpm-ostree, Gamescope, Wayland, Mesa, or drivers in the first answer unless the user asks why a specific distro fits their hardware.

## When To Branch

Only branch out of OS discovery after the OS path is clear:

- Desktop/workflow choice: `wiki/customization/desktop-environments.md`
- GPU, display, Steam, or driver troubleshooting: `wiki/systems/graphics-and-display/index.md`
- App installation or update model: `wiki/systems/package-management/index.md`
- Debugging a current install: switch to Debug Mode from `AGENTS.md`

## Tone

Be concise and preference-driven. Challenge contradictions kindly, such as wanting maximum performance tuning with zero maintenance.
