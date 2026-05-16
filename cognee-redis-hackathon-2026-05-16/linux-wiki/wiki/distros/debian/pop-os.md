---
title: Pop!_OS
type: distro
status: seed
last_checked: 2026-05-16
sources:
  - https://system76.com/pop/
  - https://system76.com/pop/download
  - https://system76.com/cosmic
  - https://github.com/pop-os
  - https://github.com/pop-os/pop
  - https://github.com/pop-os/cosmic-epoch
  - https://support.system76.com/articles/install-pop/
tags: [distro, debian, ubuntu, pop-os, cosmic, system76]
---

# Pop!_OS

## Summary

Pop!_OS is a System76 Linux distribution focused on productivity, customization, security, and System76 hardware integration. The current Pop!_OS 24.04 LTS line ships with [[../../systems/graphics-and-display/cosmic]], System76's Rust-based desktop environment.

## Official Links

- Homepage: https://system76.com/pop/
- Download: https://system76.com/pop/download
- Install docs: https://support.system76.com/articles/install-pop/
- COSMIC homepage: https://system76.com/cosmic
- GitHub organization: https://github.com/pop-os
- Pop!_OS source management repo: https://github.com/pop-os/pop
- COSMIC Epoch repo: https://github.com/pop-os/cosmic-epoch
- COSMIC project board: https://github.com/orgs/pop-os/projects/23/views/1
- Community chat: https://chat.pop-os.org/
- Organization: https://system76.com/

## Best Fit

- User type: desktop Linux user who wants a polished productivity-focused OS with strong System76 integration
- Hardware: System76 computers first, but downloadable for other compatible PCs
- Maintenance tolerance: comfortable with Ubuntu-family LTS behavior plus System76's Pop!_OS repositories and COSMIC updates
- Experience level: approachable for desktop users, with enough depth for developers and power users

## Facts

- Family: Debian
- Base distro: Ubuntu
- Desktop environment: [[../../systems/graphics-and-display/cosmic]]
- Package manager: [[../../systems/package-management/apt]]
- App store: [[../../systems/package-management/cosmic-store]]
- App formats: `.deb` packages and [[../../systems/package-management/flatpak]]
- Display stack: [[../../systems/graphics-and-display/wayland]]
- Install method: ISO download
- Maintainer: System76

## Core Components

- Ubuntu compatibility: [[index]]
- COSMIC: [[../../systems/graphics-and-display/cosmic]] / https://system76.com/cosmic
- COSMIC Epoch: https://github.com/pop-os/cosmic-epoch
- apt: [[../../systems/package-management/apt]]
- COSMIC Store: [[../../systems/package-management/cosmic-store]]
- Flatpak: [[../../systems/package-management/flatpak]]
- Wayland: [[../../systems/graphics-and-display/wayland]]
- Mesa: [[../../systems/graphics-and-display/mesa]]
- NVIDIA driver: [[../../systems/graphics-and-display/nvidia-driver]]

## Install Model

Pop!_OS is installed from an ISO. The official download page provides separate images for generic Intel/AMD graphics, newer NVIDIA graphics, ARM, and ARM with NVIDIA. The System76 install docs describe downloading the ISO, writing it to a flash drive, and installing it on chosen hardware.

The official download page says Secure Boot should be disabled in BIOS to install Pop!_OS.

## Package And Update Model

Pop!_OS is Ubuntu-compatible and uses the Debian/Ubuntu package ecosystem. System76 says tools compatible with Ubuntu can run on Pop!_OS.

Pop!_OS 24.04 LTS includes COSMIC Desktop. The `cosmic-epoch` repository says Pop!_OS 22.04 users can upgrade with:

```sh
pop-upgrade release upgrade -f
```

The same repository says COSMIC Epoch is no longer receiving updates on Pop!_OS 22.04 because the latest fixes and features are only available on newer distributions such as Pop!_OS 24.04.

## Customization Model

Pop!_OS 24.04 centers customization around COSMIC. System76 describes COSMIC as supporting panels, applets, theming, tiling, launcher, app library, keyboard shortcuts, and dynamic or pinned workspaces.

## Navigation

Pop!_OS 24.04 uses [[../../systems/graphics-and-display/cosmic]] for desktop navigation. Start with COSMIC's launcher, app library, workspaces, tiling controls, and keyboard shortcut settings; use [[../../customization/desktop-navigation]] for the shared navigation vocabulary.

## Strengths

- Polished desktop distribution from a Linux hardware company
- Ubuntu software compatibility
- Separate NVIDIA-focused install image
- Full-disk encryption and privacy-oriented positioning from System76
- COSMIC provides tiling, theming, applets, launcher, and workspace customization

## Tradeoffs

- Pop!_OS behavior can differ from stock Ubuntu because System76 maintains its own OS components and repositories
- COSMIC is a major desktop transition from older Pop!_OS GNOME-based releases
- Users on Pop!_OS 22.04 should not treat COSMIC Epoch as the active test target anymore
- Best hardware experience is likely on System76 machines, though the OS is downloadable for other PCs

## Release Notes

The official download page says Pop!_OS 24.04 LTS includes COSMIC Desktop, replaces several GNOME apps with COSMIC apps, replaces Pop!_Shop with COSMIC Store, and lists key components including COSMIC Epoch 1, Linux kernel 6.17.9, Mesa 25.1.5-1, and NVIDIA Driver 580.

## Related Pages

- [[index]]
- [[../../systems/package-management/apt]]
- [[../../systems/package-management/flatpak]]
- [[../../systems/package-management/cosmic-store]]
- [[../../customization/desktop-navigation]]
- [[../../systems/graphics-and-display/cosmic]]
- [[../../systems/graphics-and-display/wayland]]
- [[../../systems/graphics-and-display/mesa]]
- [[../../systems/graphics-and-display/nvidia-driver]]
