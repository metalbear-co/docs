---
title: Branch Management
description: How to manage isolated mirrord DB branches for visibility and control
tags:
- beta
- team
- enterprise
---

mirrord provides CLI commands to inspect and manage database branches:

| Command | Purpose |
| --- | --- |
| `mirrord db-branches status [name...]` | Show the status of running database branches |
| `mirrord db-branches destroy (--all \| name...)` | Destroy one or more running database branches |
| `mirrord db-branches connections` | List the currently active DB branch portforwards |

All commands accept `(-n\|--namespace) namespace` to select a namespace and `-A\|--all-namespaces` to operate across all namespaces.

### View Branch Status

```bash
mirrord db-branches [(-n|--namespace) namespace] [-A | --all-namespaces] status [name...]
```

* Shows the status of running database branches.
* If specific branch names are provided, mirrord shows their statuses.
* If no names are given, all active branches in the selected namespace (or all namespaces, if --all-namespaces is used) are listed.
* If no branches are active, mirrord returns:`No active DB branch found`

## Destroy Branches

```bash
mirrord db-branches [(-n|--namespace) namespace] [-A | --all-namespaces] destroy (--all | name...)
```

* Destroys one or more running database branches.
* Use `--all` to destroy every active branch.
* Use one or more branch names to target specific branches.
* mirrord uses the default namespace, or the namespace specified with `--namespace`.
* To destroy branches across all namespaces, use `--all-namespaces`.
* If no active branches are found, mirrord returns: `Error: No active DB branch found`

## List Branch Portforwards

```bash
mirrord db-branches connections
```

* Lists the currently active DB branch portforwards, which are set up automatically while a session is active. See [Portforwards](../db-branching.md#portforwards).
