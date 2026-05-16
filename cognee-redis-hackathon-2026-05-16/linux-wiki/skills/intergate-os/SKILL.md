---
name: intergate-os
description: Collect and organize public source links and key facts from a Linux OS, distro, desktop, or Linux project homepage or source repository before adding it to this wiki. Use when Codex is given an OS homepage, GitHub/GitLab/Codeberg repo, official docs page, or equivalent canonical source and needs to extract official docs, manuals, demo videos, install guides, ISO/download links, release notes, community links, screenshots, project ownership, component/tool links, and basic positioning for distro discovery pages. If no homepage or source repo is provided, ask the user for one before proceeding.
---

# Intergate OS

## Purpose

Collect the important source links and starter facts for a Linux OS or distro before writing wiki pages.

This skill is for source discovery and extraction, not live system debugging.

## Required Input

Start from at least one canonical project source:

- OS or distro homepage
- Official GitHub, GitLab, Codeberg, or source repository
- Official docs or manual page
- Official download or release page

If the user only gives a distro name, vague description, screenshot, video, or third-party article, ask for the official homepage or source repo before doing the main extraction.

## Collect These Links

For each OS or distro, look for:

- Homepage
- Official docs or manual
- Install guide
- Download or ISO page
- Demo video, intro video, tour, or screenshots
- GitHub, GitLab, Codeberg, or other source repo
- Release notes or changelog
- Community links such as Discord, forum, Matrix, Reddit, Mastodon, or mailing list
- Workstation, hardware, or compatibility pages
- Sponsoring organization, parent project, or maintainer page
- Official links for core tools and components the OS uses

## Extract These Facts

Keep the first pass concise:

- Name
- Tagline or short positioning
- Base distro or family
- Desktop environment or window manager
- Package manager
- Core components and tools
- Install method
- Release model or update channel if obvious
- Desktop navigation model, such as launcher, overview, workspaces, tiling, hotkeys, gaming mode, or keyboard-first workflow
- Target users
- Major tradeoffs
- Anything freshness-sensitive, such as latest release or ISO version

## Component Links

Create a concise component list when the source names specific tools. Prefer official project sites or source repositories.

Common component categories:

- Base distro
- Desktop environment or window manager
- Display server, compositor, bar, launcher, notification daemon, lock screen, idle manager
- Terminal, shell, editor, file manager, browser
- Package manager, community package source, app store, Flatpak/Snap/AppImage support
- Audio, networking, graphics, boot, snapshot, backup, or rollback tools
- Theme system, dotfiles, config manager, or OS-specific CLI
- Navigation and workflow docs for launchers, workspaces, hotkeys, tiling, gaming mode, or desktop shortcuts

For example, an Arch + Hyprland distro might link Arch Linux, Hyprland, Waybar, Walker, Mako, Hyprlock, Alacritty, Neovim, `pacman`, and AUR.

If a component is important beyond one distro, also consider whether it needs a page or link from `wiki/systems/`.

## Where To Put It

Before editing, tell the user which pages should receive the information:

- `wiki/distros/<name>.md` for the main distro page
- `wiki/customization/<name>.md` for themes, keybindings, workflow, dotfiles, or desktop behavior
- `wiki/customization/desktop-navigation.md` for shared launcher, workspace, shortcut, and navigation concepts
- `wiki/troubleshooting/<name>.md` for project-specific support commands or known failure modes
- `wiki/recipes/<name>-install-template.md` for a generic install checklist
- `wiki/discovery/*.md` for recommendation logic
- `wiki/index.md` for navigation
- `wiki/log.md` for the maintenance entry

Do not create user profile pages.

## Source Preference

Prefer sources in this order:

1. Official homepage
2. Official manual or docs
3. Official source repo
4. Official release notes
5. Official demo video or project media
6. Community pages and reviews

Label community opinion separately from official project facts.

## Output Before Writing

When the user asks to review before adding anything, respond with:

- Links found
- Facts extracted
- Component/tool links found
- Suggested wiki pages
- Open questions or uncertain claims

## Boundaries

- Do not invent missing links
- Do not treat marketing claims as neutral facts
- Do not rely on stale release data without checking current sources
- Do not add broad Linux concepts to a distro page if they belong in `wiki/systems/`
- Keep OS-page navigation sections concise and link to shared desktop, window-manager, or customization pages instead of duplicating shortcut tables across distros
