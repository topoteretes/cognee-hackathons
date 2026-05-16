---
title: Fedora Workstation
type: distro
status: seed
last_checked: 2026-05-16
sources:
  - https://fedoraproject.org/
  - https://fedoraproject.org/workstation/
  - https://fedoraproject.org/workstation/download/
  - https://docs.fedoraproject.org/
  - https://docs.fedoraproject.org/en-US/fedora/latest/release-notes/
  - https://discussion.fedoraproject.org/
  - https://src.fedoraproject.org/
tags: [distro, fedora, workstation, gnome]
---

# Fedora Workstation

## Summary

Fedora Workstation is Fedora's flagship desktop edition. The Fedora Project describes it as the edition featuring the latest GNOME desktop.

## Official Links

- Fedora homepage: https://fedoraproject.org/
- Workstation page: https://fedoraproject.org/workstation/
- Download: https://fedoraproject.org/workstation/download/
- Documentation: https://docs.fedoraproject.org/
- Release notes: https://docs.fedoraproject.org/en-US/fedora/latest/release-notes/
- Fedora Discussion: https://discussion.fedoraproject.org/
- Fedora source packages: https://src.fedoraproject.org/
- Fedora Forge: https://forge.fedoraproject.org/
- Fedora Magazine: https://fedoramagazine.org/
- Fedora Media Writer: https://github.com/FedoraQt/MediaWriter
- Sponsor relationship: https://docs.fedoraproject.org/en-US/project/sponsors/

## Best Fit

- User type: desktop Linux user, developer, GNOME user, or user who wants current upstream Linux technologies
- Hardware: modern desktop or laptop with at least the Fedora-recommended install resources
- Maintenance tolerance: moderate, with roughly twice-yearly major Fedora releases
- Experience level: approachable for desktop users, especially those comfortable with current Linux software

## Facts

- Family: Fedora
- Maintainer: Fedora Project
- Sponsor: Red Hat
- Desktop environment: [[../../systems/graphics-and-display/gnome]]
- Package manager: [[../../systems/package-management/dnf]]
- App model: RPM packages and [[../../systems/package-management/flatpak]]
- Display stack: [[../../systems/graphics-and-display/wayland]] with [[../../systems/graphics-and-display/x11]] compatibility
- Installer media tool: [[../../systems/package-management/fedora-media-writer]]
- Release model: regular Fedora releases, generally around two major releases per year

## Core Components

- GNOME: [[../../systems/graphics-and-display/gnome]]
- dnf: [[../../systems/package-management/dnf]]
- Flatpak: [[../../systems/package-management/flatpak]]
- Wayland: [[../../systems/graphics-and-display/wayland]]
- X11: [[../../systems/graphics-and-display/x11]]
- Mesa: [[../../systems/graphics-and-display/mesa]]
- NVIDIA driver: [[../../systems/graphics-and-display/nvidia-driver]]
- systemd: [[../../systems/boot-and-init/systemd]]
- GRUB: [[../../systems/boot-and-init/grub]]
- Fedora Media Writer: [[../../systems/package-management/fedora-media-writer]]

## Install Model

Fedora Workstation is downloaded as a live ISO. The download page recommends Fedora Media Writer for writing the image to a USB flash drive so users can boot a live system and then install Fedora.

The Fedora Workstation download page checked on 2026-05-16 lists Fedora Workstation 44 with a release date of Tuesday, April 28, 2026.

## Package And Update Model

Fedora Workstation uses RPM packages managed by `dnf`. It also has strong Flatpak support for desktop applications. Fedora is upstream-focused and tends to ship newer Linux desktop technologies than long-term-support distributions.

## Customization Model

Fedora Workstation uses GNOME as its default desktop. Users commonly customize through GNOME Settings, GNOME extensions, Flatpak apps, Fedora repositories, and COPR/community packages when appropriate.

## Navigation

Fedora Workstation uses the upstream [[../../systems/graphics-and-display/gnome]] desktop workflow. Start with the overview, app search, workspaces, window switching, and keyboard shortcut settings; use [[../../customization/desktop-navigation]] for shared navigation concepts.

## Strengths

- Strong upstream GNOME experience
- Current kernel, desktop, and developer tooling
- Large Fedora documentation and community ecosystem
- Good base for developers who want current Linux packages
- Clear relationship to Fedora Atomic desktops and RHEL-family ecosystems

## Tradeoffs

- Shorter release cadence than LTS distributions
- Some proprietary codecs, drivers, or third-party software may require extra repositories or setup
- Defaults are closer to upstream GNOME than highly customized beginner distros
- Users who want rollback-oriented desktops may prefer Fedora Silverblue or Kinoite

## Related Pages

- [[index]]
- [[../../systems/package-management/dnf]]
- [[../../systems/package-management/flatpak]]
- [[../../systems/package-management/fedora-media-writer]]
- [[../../customization/desktop-navigation]]
- [[../../systems/graphics-and-display/gnome]]
- [[../../systems/graphics-and-display/wayland]]
- [[../../systems/graphics-and-display/x11]]
- [[../../systems/graphics-and-display/mesa]]
- [[../../systems/graphics-and-display/nvidia-driver]]
- [[../../systems/boot-and-init/systemd]]
- [[../../systems/boot-and-init/grub]]
