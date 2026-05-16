---
title: Debug Command Output Template
type: recipe
status: seed
last_checked: 2026-05-16
sources: []
tags: [recipe, troubleshooting]
---

# Debug Command Output Template

## Goal

Collect enough system facts to debug without guessing.

## Baseline Commands

```sh
cat /etc/os-release
uname -a
```

## Optional Commands By Area

Package issue:

```sh
# Add the exact failed package-manager command and full output.
```

Graphics issue:

```sh
lspci -k
echo "$XDG_SESSION_TYPE"
```

Networking issue:

```sh
ip link
rfkill list
```

Audio issue:

```sh
pactl info
pactl list short sinks
```

## Privacy Notes

Review command output for hostnames, usernames, local IPs, serial numbers, or tokens before sharing publicly.
