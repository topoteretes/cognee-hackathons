---
title: CachyOS
type: distro
status: seed
last_checked: 2026-05-16
sources:
  - https://cachyos.org/
  - https://cachyos.org/download/
  - https://wiki.cachyos.org/
  - https://packages.cachyos.org/
  - https://github.com/CachyOS
  - https://github.com/CachyOS/linux-cachyos
  - https://github.com/CachyOS/New-Cli-Installer
  - https://github.com/CachyOS/cachyos-calamares
tags: [distro, arch, cachyos, performance, rolling-release]
---

# CachyOS

## Summary

CachyOS is a performance-focused Arch-based Linux distribution. It emphasizes CPU-optimized package repositories, optimized kernels, scheduler choices, and a streamlined installer while keeping Arch's rolling-release model.

## Official Links

- Homepage: https://cachyos.org/
- Download: https://cachyos.org/download/
- Wiki/docs: https://wiki.cachyos.org/
- Package search: https://packages.cachyos.org/
- GitHub organization: https://github.com/CachyOS
- linux-cachyos: https://github.com/CachyOS/linux-cachyos
- PKGBUILDs: https://github.com/CachyOS/CachyOS-PKGBUILDS
- CachyOS Settings: https://github.com/CachyOS/CachyOS-Settings
- CLI installer: https://github.com/CachyOS/New-Cli-Installer
- Calamares installer: https://github.com/CachyOS/cachyos-calamares
- Forum: https://discuss.cachyos.org/
- Discord: https://discord.gg/cachyos
- Reddit: https://www.reddit.com/r/cachyos/

## Best Fit

- User type: Arch-curious or Arch-comfortable user who wants performance-tuned defaults
- Hardware: modern x86-64 systems that can benefit from v3/v4/Zen4 optimized packages
- Maintenance tolerance: comfortable with rolling-release behavior and Arch-family troubleshooting
- Experience level: intermediate Linux users, performance-minded desktop users, and users who want an easier Arch install path

## Facts

- Family: Arch
- Base distro: Arch Linux
- Package manager: [[../../systems/package-management/pacman]]
- Package repositories: [[../../systems/package-management/cachyos-repositories]]
- Kernel family: [[../../systems/boot-and-init/linux-cachyos]]
- Installers: graphical Calamares-based installer and CLI installer
- Desktop choices: KDE Plasma, GNOME, COSMIC, Hyprland, Sway, Niri, i3, XFCE, and more
- Release model: Arch-family rolling release
- Editions: Desktop Edition and Handheld Edition

## Core Components

- Arch Linux: https://archlinux.org/
- pacman: [[../../systems/package-management/pacman]]
- CachyOS repositories: [[../../systems/package-management/cachyos-repositories]]
- linux-cachyos: [[../../systems/boot-and-init/linux-cachyos]]
- CachyOS installer: [[../../systems/package-management/cachyos-installer]]
- KDE Plasma: [[../../systems/graphics-and-display/kde-plasma]]
- GNOME: [[../../systems/graphics-and-display/gnome]]
- COSMIC: [[../../systems/graphics-and-display/cosmic]]
- Hyprland: [[../../systems/graphics-and-display/hyprland]]
- Sway: [[../../systems/graphics-and-display/sway]]
- Niri: [[../../systems/graphics-and-display/niri]]
- Gamescope: [[../../systems/graphics-and-display/gamescope]]
- Mesa: [[../../systems/graphics-and-display/mesa]]
- NVIDIA driver: [[../../systems/graphics-and-display/nvidia-driver]]

## Install Model

CachyOS offers a Desktop Edition and a Handheld Edition. The Desktop Edition uses an online installer that lets users choose from many desktop environments and window managers. The Handheld Edition provides a GameMode-like experience, preinstalled gaming tools, and official support for devices such as ROG Ally, Steam Deck OLED/LCD, Legion Go, and Lenovo Legion Go S.

The project describes two installation workflows: a graphical Calamares-based installer for guided setup and a CLI installer for users who want more control.

## Package And Update Model

CachyOS uses Arch-family package management with `pacman`, but adds CachyOS repositories that rebuild packages with CPU optimization targets such as x86-64-v3, x86-64-v4, and Zen4, plus LTO and selected PGO/BOLT optimization.

## Customization Model

CachyOS exposes a large set of desktop and window-manager choices during installation. The homepage lists KDE Plasma, GNOME, COSMIC, Hyprland, Sway, Niri, i3, XFCE, and more.

## Navigation

CachyOS navigation depends on the desktop or window manager selected during installation. Use [[../../customization/desktop-navigation]] for shared desktop concepts, then follow the selected [[../../systems/graphics-and-display/kde-plasma]], [[../../systems/graphics-and-display/gnome]], [[../../systems/graphics-and-display/cosmic]], [[../../systems/graphics-and-display/hyprland]], [[../../systems/graphics-and-display/sway]], or [[../../systems/graphics-and-display/niri]] workflow.

## Strengths

- Arch base with easier installation paths
- CPU-optimized package repositories
- Optimized CachyOS kernel family
- Scheduler choices for performance tuning
- Many desktop environment and window-manager choices
- Handheld Edition for gaming devices

## Tradeoffs

- Performance-oriented defaults may add complexity compared with a conservative distro
- Rolling-release Arch base requires update awareness
- CPU-optimized repositories are a distinguishing feature, but may be less universal than generic packages
- Users should understand the difference between CachyOS behavior and stock Arch before following generic Arch advice blindly

## Release Notes

CachyOS is rolling release. Track freshness through the official homepage, wiki, package search, and GitHub repositories.

## Related Pages

- [[index]]
- [[../../systems/package-management/pacman]]
- [[../../systems/package-management/cachyos-repositories]]
- [[../../systems/boot-and-init/linux-cachyos]]
- [[../../systems/package-management/cachyos-installer]]
- [[../../customization/desktop-navigation]]
- [[../../systems/graphics-and-display/kde-plasma]]
- [[../../systems/graphics-and-display/gnome]]
- [[../../systems/graphics-and-display/cosmic]]
- [[../../systems/graphics-and-display/hyprland]]
- [[../../systems/graphics-and-display/sway]]
- [[../../systems/graphics-and-display/niri]]
- [[../../systems/graphics-and-display/gamescope]]
