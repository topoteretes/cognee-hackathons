# Log

## [2026-05-16] customization | Add distro navigation sections

Added shared desktop navigation guidance, linked it from maintained distro pages, updated the distro template, and taught `intergate-os` to collect launcher, workspace, shortcut, and workflow details during future OS ingests.

## [2026-05-16] skill | Add OS discovery skill

Added `discover-os` for focused distro selection interviews and updated `wiki-navigator` to avoid routing broad OS-choice questions into subsystem pages too early.

## [2026-05-16] skill | Add wiki navigator skill

Added a local `wiki-navigator` skill for routing users to the right wiki entry points before giving Linux discovery, debugging, customization, or package-management guidance.

## [2026-05-16] tooling | Configure ty hook environment

Added root `ty.toml` so ty resolves hook dependencies from `hooks/.venv`.

## [2026-05-16] tooling | Use python-dotenv for hook env files

Added `python-dotenv` as a hook dependency and switched profile env loading to `load_dotenv`.

## [2026-05-16] profile | Clarify hook invocation

Updated profile instructions to run `hooks/user_preference_profile.py` directly with Python instead of wrapping it with project runners.

## [2026-05-16] profile | Add local profile summaries

Allowed ignored local profile summaries under `wiki/profile/` and updated the profile hook to save summaries from Redis-backed profile data.

## [2026-05-16] distro | Add Fedora seed pages

Added Fedora Workstation, Fedora KDE Plasma Desktop, Fedora Silverblue, Fedora Kinoite, and Fedora Media Writer seed pages.

## [2026-05-16] distro | Add CachyOS seed page

Added CachyOS under the Arch family and created seed system pages for CachyOS repositories, linux-cachyos, installer tooling, Sway, and Niri.

## [2026-05-16] distro | Add Bazzite seed page

Added Bazzite under the Fedora family and created seed system pages for Bazzite's atomic, gaming, and app-management components.

## [2026-05-16] distro | Add Ubuntu seed page

Added Ubuntu under the Debian family and created a GNOME system page for Ubuntu Desktop links.

## [2026-05-16] tooling | Move hook Python config under hooks

Removed root-level `uv` project files, added hook-local Python metadata, and simplified profile docs to call the hook directly.

## [2026-05-16] docs | Simplify profile skill commands

Reworked the profile skill to emphasize user-facing actions and moved hook commands into a compact reference block.

## [2026-05-16] tooling | Load profile env files

Updated the profile hook to load Upstash credentials from `.env` or `hooks/.env` and return JSON errors for failed profile commands.

## [2026-05-16] memory | Add profile skill and manager commands

Added a local profile skill and expanded the profile hook with create, select, get, list, and delete commands backed by Upstash.

## [2026-05-16] tooling | Remove local redis client dependency

Simplified the profile hook to use Upstash REST only, avoiding a local `redis` module dependency.

## [2026-05-16] memory | Add Upstash profile storage

Added first-class Upstash REST support for storing generated user preference profiles.

## [2026-05-16] tooling | Add uv project metadata

Added `pyproject.toml` for Python hook dependencies and documented `uv run` usage.

## [2026-05-16] memory | Expand user profile signals

Extended the profile hook to capture technical level, workloads, interests, hardware, comfort level, and Linux preferences.

## [2026-05-16] memory | Add user preference profile hook

Allowed structured user preference profiles in the maintainer rules and added a Redis-friendly profile extraction hook under `hooks/`.

## [2026-05-16] distro | Add Pop!_OS and COSMIC seed pages

Added Pop!_OS under the Debian family and created seed system pages for COSMIC and COSMIC Store.

## [2026-05-16] structure | Convert systems pages to subsystem folders

Moved system topic pages into folders with `index.md` files and added seed pages for common tools under package management, graphics/display, audio, networking, and boot/init.

## [2026-05-16] structure | Add distro family folders and Omarchy seed page

Created distro family indexes under `wiki/distros/` and added Omarchy under the Arch family.

## [2026-05-16] structure | Initial Linux wiki scaffold

Created the starter wiki structure for Linux discovery, debugging, customization, systems, and generic recipes.

## [2026-05-16] tooling | Add wiki lint skill

Added a local wiki-lint skill for structured health checks across links, frontmatter, sources, freshness, contradictions, orphans, index coverage, privacy leaks, and maintenance logs.
