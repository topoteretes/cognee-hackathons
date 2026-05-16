---
title: Omarchy
type: distro
status: seed
last_checked: 2026-05-16
sources:
  - https://omarchy.org/
  - https://learn.omacom.io/2/the-omarchy-manual
  - https://github.com/basecamp/omarchy
  - https://github.com/basecamp/omarchy/releases
  - https://www.youtube.com/watch?v=L3EafsSCv80
tags: [distro, arch, hyprland, omarchy]
---

# Omarchy

## Summary

Omarchy is an opinionated Arch Linux and Hyprland-based distribution by DHH. It emphasizes a beautiful, keyboard-first, developer-oriented Linux setup with preconfigured applications, themes, hotkeys, and an Omarchy menu/CLI.

## Official Links

- Homepage: https://omarchy.org/
- Manual: https://learn.omacom.io/2/the-omarchy-manual
- ISO: https://iso.omarchy.org/omarchy-3.8.0.iso
- GitHub: https://github.com/basecamp/omarchy
- Releases: https://github.com/basecamp/omarchy/releases
- Demo video: https://www.youtube.com/watch?v=L3EafsSCv80
- Demo embed: https://www.youtube-nocookie.com/embed/L3EafsSCv80
- Discord: https://discord.gg/tXFUdasqhY
- Workstations: https://omarchy.org/workstations/
- Maintainer: https://dhh.dk
- Organization: https://37signals.com

## Best Fit

- User type: developer or power user who wants an opinionated, keyboard-first system
- Hardware: best treated as a dedicated-machine install unless using advanced/manual paths
- Maintenance tolerance: comfortable with Arch-family rolling updates and occasional troubleshooting
- Experience level: better for users who are willing to learn tiling-window-manager workflows

## Facts

- Family: Arch
- Base distro: Arch Linux
- Window manager: [[../../systems/graphics-and-display/hyprland]]
- Package manager: [[../../systems/package-management/pacman]]
- Community package source: AUR
- Install method: ISO
- Default workflow: keyboard-first through hotkeys, app launcher, Omarchy Menu, and CLI

## Core Components

- Arch Linux: https://archlinux.org/
- Hyprland: [[../../systems/graphics-and-display/hyprland]] / https://hypr.land/
- Waybar: [[../../systems/graphics-and-display/waybar]] / https://github.com/Alexays/Waybar
- Walker: https://github.com/abenz1267/walker
- Mako: [[../../systems/graphics-and-display/mako]] / https://github.com/emersion/mako
- Hyprlock: [[../../systems/graphics-and-display/hyprlock]] / https://wiki.hypr.land/Hypr-Ecosystem/hyprlock/
- Hypridle: https://wiki.hypr.land/Hypr-Ecosystem/hypridle/
- Alacritty: https://alacritty.org/
- Neovim: https://neovim.io/
- btop: https://github.com/aristocratos/btop
- pacman: [[../../systems/package-management/pacman]] / https://wiki.archlinux.org/title/Pacman
- Arch package search: https://archlinux.org/packages/
- Arch User Repository: https://aur.archlinux.org/

The Omarchy manual says themes style the desktop, terminal, Neovim, btop, Mako notifications, Waybar top bar, Walker launcher, and Hyprlock lock screen.

## Install Model

The official manual describes Omarchy as ISO-installed and designed for a dedicated drive. The install flow can wipe the selected drive, so backups matter before installation.

The manual says Secure Boot and/or TPM must be turned off for installation.

## Package And Update Model

Omarchy follows the Arch ecosystem and uses Omarchy tooling for system-level updates. The GitHub release notes say existing installations update through `Update > Omarchy` in the Omarchy Menu.

The homepage currently promotes Omarchy 3.8, while GitHub releases show `v3.8.1` as the latest release checked on 2026-05-16. Track ISO version and latest GitHub release separately.

## Customization Model

Omarchy customization is centered around the Omarchy Menu, hotkeys, themes, Hyprland configuration, and dotfiles under `~/.config`. The manual documents themes, hotkeys, terminal choices, development tools, shell tools, screenshots, reminders, monitors, fonts, and the `omarchy` CLI.

## Navigation

Omarchy is a keyboard-first [[../../systems/graphics-and-display/hyprland]] system. Start with the Omarchy Menu, hotkeys, launcher, workspaces, and terminal workflow; use [[../../customization/desktop-navigation]] for shared navigation concepts and [[../../customization/window-managers]] for tiling-window-manager context.

## Strengths

- Fast path to an integrated Arch + Hyprland setup
- Strong keyboard-first workflow
- Developer-oriented defaults
- Cohesive theming across desktop tools
- Official manual covers daily use, customization, and troubleshooting

## Tradeoffs

- Opinionated defaults may not fit users who want to assemble their own system
- Arch-family rolling updates can require troubleshooting
- Hyprland and keyboard-first workflows may be unfamiliar to new Linux users
- Dedicated-drive install model is higher commitment than trying a typical live desktop distro

## Common Issues

- Update breakage
- Display scaling differences between 1x and 2x displays
- Caps Lock behavior differs from normal expectations because it is used for compose behavior
- VM and Apple hardware paths require extra care or user-driven guides

## Debugging Notes

The manual points users toward `omarchy-debug` for sharing system information and `omarchy-reinstall` for reinstalling default configs and packages when recovery is needed.

## Related Pages

- [[index]]
- [[../../systems/package-management/index]]
- [[../../systems/package-management/pacman]]
- [[../../systems/graphics-and-display/index]]
- [[../../customization/desktop-navigation]]
- [[../../systems/graphics-and-display/hyprland]]
- [[../../systems/graphics-and-display/waybar]]
- [[../../systems/graphics-and-display/mako]]
- [[../../systems/graphics-and-display/hyprlock]]
- [[../../customization/window-managers]]
