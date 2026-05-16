---
title: Install Software Template
type: recipe
status: seed
last_checked: 2026-05-16
sources: []
tags: [recipe, packages]
---

# Install Software Template

## Goal

Install software using the safest appropriate source for the distro.

## Variables To Fill In

- `<distro>`
- `<package-name>`
- `<package-manager>`
- `<repository>`

## Generic Steps

1. Identify the distro and package manager
2. Check the official repository first
3. Check whether the project recommends a distro-specific source
4. Avoid mixing package sources unless the tradeoff is explicit
5. Install the package
6. Verify the installed version and executable path

## Verification

```sh
command -v <binary>
<binary> --version
```

## Related Pages

- [[../systems/package-management/index]]
