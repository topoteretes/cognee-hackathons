---
title: Bazzite
type: distro
status: seed
last_checked: 2026-05-16
sources:
  - https://bazzite.gg/
  - https://docs.bazzite.gg/
  - https://github.com/ublue-os/bazzite
  - https://universal-blue.org/
  - https://docs.bazzite.gg/Installing_and_Managing_Software/
  - https://docs.bazzite.gg/General/Updates_Rollbacks_and_Rebasing/
tags: [distro, fedora, atomic, gaming, bazzite, universal-blue]
---

# Bazzite

## Summary

Bazzite is a Fedora Atomic and Universal Blue-based gaming-focused operating system for desktop PCs, handhelds, tablets, laptops, and home theater PCs. It aims to provide a SteamOS-like or gaming-optimized Linux experience on broader hardware.

## Official Links

- Homepage: https://bazzite.gg/
- Download: https://bazzite.gg/#download
- Documentation: https://docs.bazzite.gg/
- FAQ: https://faq.bazzite.gg/
- GitHub: https://github.com/ublue-os/bazzite
- Universal Blue: https://universal-blue.org/
- Developer eXperience images: https://dev.bazzite.gg/
- Discord: https://discord.bazzite.gg/
- Discourse: https://universal-blue.discourse.group/
- Reddit: https://www.reddit.com/r/Bazzite/
- Press kit: https://press.bazzite.gg/

## Best Fit

- User type: Linux gamer, handheld PC owner, HTPC user, or desktop user who wants an image-based Fedora Atomic gaming setup
- Hardware: desktops, laptops, Steam Deck, Framework hardware, Lenovo Legion Go, ASUS ROG Ally, and other supported handhelds
- Maintenance tolerance: comfortable with image-based updates, rebasing, and Flatpak/container-first software installation
- Experience level: approachable for gaming users, but especially strong for users who accept Fedora Atomic-style workflows

## Facts

- Family: Fedora
- Base: Fedora Atomic / Universal Blue
- Desktop options: [[../../systems/graphics-and-display/kde-plasma]] and [[../../systems/graphics-and-display/gnome]]
- Gaming session: [[../../systems/graphics-and-display/gamescope]] / Steam Gaming Mode on supported images
- Package/update model: image-based updates with [[../../systems/package-management/rpm-ostree]]
- App model: [[../../systems/package-management/flatpak]], [[../../systems/package-management/bazaar]], [[../../systems/package-management/homebrew]], and containers
- Container workflow: [[../../systems/package-management/distrobox]]
- Install method: hardware/use-case-specific ISO download form
- Security features: SELinux, Secure Boot support, signed container images, and LUKS full-disk encryption

## Core Components

- Fedora Atomic Desktop: https://fedoraproject.org/atomic-desktops/
- Universal Blue: https://universal-blue.org/
- rpm-ostree: [[../../systems/package-management/rpm-ostree]]
- Flatpak: [[../../systems/package-management/flatpak]]
- Bazaar: [[../../systems/package-management/bazaar]]
- Homebrew: [[../../systems/package-management/homebrew]]
- Distrobox: [[../../systems/package-management/distrobox]]
- KDE Plasma: [[../../systems/graphics-and-display/kde-plasma]]
- GNOME: [[../../systems/graphics-and-display/gnome]]
- Gamescope: [[../../systems/graphics-and-display/gamescope]]
- Steam: [[../../systems/graphics-and-display/steam]]
- Lutris: [[../../systems/graphics-and-display/lutris]]
- Waydroid: [[../../systems/graphics-and-display/waydroid]]
- Mesa: [[../../systems/graphics-and-display/mesa]]
- NVIDIA driver: [[../../systems/graphics-and-display/nvidia-driver]]
- SELinux: https://selinuxproject.org/

## Install Model

Bazzite's homepage uses a hardware and use-case selection form to generate the correct ISO. It asks about device class, GPU vendor, desktop environment, and whether the user wants Steam Gaming Mode.

Existing Fedora Atomic Desktop users can rebase to Bazzite without reinstalling. The homepage recommends removing layered packages first:

```sh
rpm-ostree reset
```

The homepage also notes Secure Boot must be disabled for installation in some flows, but can be re-enabled after enrolling Bazzite's MOK key and completing installation.

## Package And Update Model

Bazzite is image-based. After updates, the previous operating system deployment is retained so users can select it at boot or roll back. The homepage says Bazzite images are retained in repositories for ninety days.

The docs recommend software installation in this order:

- Bazzite Portal for tailored installers
- Bazaar App Store for Flatpak apps
- Homebrew for command-line tools
- Containers for other Linux package ecosystems
- AppImage for portable apps
- rpm-ostree package layering only when needed, because layered packages can break future upgrades until removed

## Customization Model

Bazzite offers KDE Plasma and GNOME variants, plus Steam Gaming Mode for supported handheld and HTPC images. The KDE path is built from Fedora Kinoite, while the GNOME path is built from Fedora Silverblue.

Gaming-focused customization includes Steam, Lutris, Decky Loader support, Waydroid, controller support, hardware-specific handheld tooling, and Game Mode/desktop variants.

## Navigation

Bazzite navigation depends on the image selected during download: KDE Plasma, GNOME, or a Steam Gaming Mode-oriented flow. Use [[../../customization/desktop-navigation]] for shared desktop concepts, then follow the selected [[../../systems/graphics-and-display/kde-plasma]], [[../../systems/graphics-and-display/gnome]], or [[../../systems/graphics-and-display/gamescope]] path.

## Strengths

- Gaming-first defaults with Steam and Lutris preinstalled
- Strong handheld and HTPC story
- Fedora Atomic/uBlue rollback and rebase model
- KDE, GNOME, and Steam Gaming Mode choices
- Built-in driver and hardware support for many gaming devices
- Secure Boot support, SELinux, signed container images, and LUKS encryption

## Tradeoffs

- Atomic/image-based workflow differs from traditional package-managed distros
- rpm-ostree layering is available but not the preferred everyday software path
- Steam Gaming Mode hardware support varies by GPU and device
- NVIDIA and Intel GPU support in Steam Gaming Mode/HTPC scenarios can be beta or limited according to the homepage
- Users coming from normal Fedora or Ubuntu may need to learn rebasing, rollback, Flatpak-first apps, and container workflows

## Release Notes

Bazzite is updated through image builds rather than a traditional single-version distro release page. Track freshness through the official docs, GitHub repository, image tags, and project news.

## Related Pages

- [[index]]
- [[../../systems/package-management/rpm-ostree]]
- [[../../systems/package-management/flatpak]]
- [[../../systems/package-management/bazaar]]
- [[../../systems/package-management/homebrew]]
- [[../../systems/package-management/distrobox]]
- [[../../customization/desktop-navigation]]
- [[../../systems/graphics-and-display/kde-plasma]]
- [[../../systems/graphics-and-display/gnome]]
- [[../../systems/graphics-and-display/gamescope]]
- [[../../systems/graphics-and-display/steam]]
- [[../../systems/graphics-and-display/lutris]]
- [[../../systems/graphics-and-display/waydroid]]
- [[../../systems/graphics-and-display/mesa]]
- [[../../systems/graphics-and-display/nvidia-driver]]
