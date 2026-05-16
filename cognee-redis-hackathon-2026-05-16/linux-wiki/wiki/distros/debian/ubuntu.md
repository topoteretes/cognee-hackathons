---
title: Ubuntu
type: distro
status: seed
last_checked: 2026-05-16
sources:
  - https://ubuntu.com/
  - https://ubuntu.com/desktop
  - https://ubuntu.com/download/desktop
  - https://ubuntu.com/tutorials/install-ubuntu-desktop
  - https://help.ubuntu.com/
  - https://documentation.ubuntu.com/release-notes/26.04/
  - https://ubuntu.com/about/release-cycle
  - https://github.com/canonical/ubuntu-desktop-provision
  - https://github.com/canonical/subiquity
tags: [distro, debian, ubuntu, canonical, gnome]
---

# Ubuntu

## Summary

Ubuntu is Canonical's Debian-based Linux distribution for desktop, server, cloud, IoT, and enterprise use. Ubuntu Desktop is a mainstream desktop Linux option with broad hardware support, a large documentation footprint, and many downstream derivatives.

## Official Links

- Homepage: https://ubuntu.com/
- Desktop: https://ubuntu.com/desktop
- Download: https://ubuntu.com/download/desktop
- Install guide: https://ubuntu.com/tutorials/install-ubuntu-desktop
- Official documentation: https://help.ubuntu.com/
- Release notes: https://documentation.ubuntu.com/release-notes/
- Ubuntu 26.04 LTS release notes: https://documentation.ubuntu.com/release-notes/26.04/
- Release cycle: https://ubuntu.com/about/release-cycle
- Releases directory: https://releases.ubuntu.com/
- Ubuntu source packages: https://launchpad.net/ubuntu
- Ubuntu Desktop Provision repo: https://github.com/canonical/ubuntu-desktop-provision
- Subiquity installer repo: https://github.com/canonical/subiquity
- Community: https://discourse.ubuntu.com/
- Organization: https://canonical.com/

## Best Fit

- User type: desktop user, developer, student, server admin, or Linux newcomer who wants a widely documented base
- Hardware: broad PC support, with server, desktop, cloud, ARM, and certified hardware paths
- Maintenance tolerance: low to moderate, especially on LTS releases
- Experience level: approachable for beginners, but deep enough for professional Linux use

## Facts

- Family: Debian
- Base distro: Debian-derived
- Maintainer: Canonical
- Desktop environment: [[../../systems/graphics-and-display/gnome]]
- Package manager: [[../../systems/package-management/apt]]
- App format: [[../../systems/package-management/snap]]
- Additional app format: [[../../systems/package-management/flatpak]]
- Display stack: [[../../systems/graphics-and-display/wayland]] with [[../../systems/graphics-and-display/x11]] compatibility paths
- Install method: ISO download
- Release model: LTS releases every two years, with interim releases between LTS versions

## Core Components

- GNOME: [[../../systems/graphics-and-display/gnome]] / https://www.gnome.org/
- apt: [[../../systems/package-management/apt]]
- Snap: [[../../systems/package-management/snap]] / https://snapcraft.io/
- Flatpak: [[../../systems/package-management/flatpak]]
- Wayland: [[../../systems/graphics-and-display/wayland]]
- X11: [[../../systems/graphics-and-display/x11]]
- Mesa: [[../../systems/graphics-and-display/mesa]]
- NVIDIA driver: [[../../systems/graphics-and-display/nvidia-driver]]
- systemd: [[../../systems/boot-and-init/systemd]]
- GRUB: [[../../systems/boot-and-init/grub]]
- Subiquity: https://github.com/canonical/subiquity
- Ubuntu Desktop Provision: https://github.com/canonical/ubuntu-desktop-provision

## Install Model

Ubuntu Desktop is installed from an ISO. The official install tutorial covers downloading the ISO, creating a bootable USB stick, booting the installer, and installing Ubuntu.

## Package And Update Model

Ubuntu uses Debian-family packaging with `apt` and `.deb` packages, while Canonical also promotes Snap packages through Snapcraft. Ubuntu releases include LTS versions and interim versions. The official release cycle page lists Ubuntu 26.04 LTS as released in April 2026, with standard support through May 2031.

## Customization Model

Ubuntu Desktop uses GNOME with Ubuntu-specific defaults and integrations. Users commonly customize the desktop through Settings, GNOME extensions, themes, snaps, Debian packages, and optional Flatpak setup.

## Navigation

Ubuntu Desktop uses a [[../../systems/graphics-and-display/gnome]]-family workflow. Start with the overview, app search, workspaces, window switching, and keyboard shortcut settings; use [[../../customization/desktop-navigation]] for shared navigation concepts.

## Strengths

- Large user base and documentation ecosystem
- Strong desktop, server, cloud, and enterprise presence
- Stable LTS path for users who prefer fewer major upgrades
- Major upstream base for derivatives such as Pop!_OS and Linux Mint
- Broad software vendor and hardware vendor recognition

## Tradeoffs

- Snap integration is a distinctive Ubuntu choice and can be polarizing for users who prefer only traditional packages or Flatpak
- Ubuntu defaults may differ from Debian and from non-Ubuntu GNOME distributions
- Interim releases bring newer software but require more frequent upgrades than LTS releases
- Downstream derivatives may make different choices for desktop environment, package formats, and update policy

## Release Notes

Ubuntu 26.04 LTS is the latest LTS release checked on 2026-05-16. Track current release data through the official release notes and release cycle pages because Ubuntu has both LTS and interim release streams.

## Related Pages

- [[index]]
- [[../../systems/package-management/apt]]
- [[../../systems/package-management/snap]]
- [[../../systems/package-management/flatpak]]
- [[../../customization/desktop-navigation]]
- [[../../systems/graphics-and-display/gnome]]
- [[../../systems/graphics-and-display/wayland]]
- [[../../systems/graphics-and-display/x11]]
- [[../../systems/graphics-and-display/mesa]]
- [[../../systems/graphics-and-display/nvidia-driver]]
- [[../../systems/boot-and-init/systemd]]
- [[../../systems/boot-and-init/grub]]
