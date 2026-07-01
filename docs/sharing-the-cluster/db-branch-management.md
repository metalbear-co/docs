---
title: DB Branching Management
date: 2025-08-30T21:00:00.000Z
lastmod: 2025-08-30T21:00:00.000Z
draft: false
menu:
  docs:
    parent: db-branching
toc: true
description: How to manage isolated mirrord DB branches for visibility and control
tags:
  - team
  - enterprise
---

# Branch Management

mirrord provides CLI commands to inspect and manage database branches.

1. #### View Branch Status using:

```bash
  mirrord db-branches [(-n|--namespace) namespace] [-A | --all-namespaces] status [name...]
```

* Shows the status of running database branches.
* If specific branch names are provided, mirrord shows their statuses.
* If no names are given, all active branches in the selected namespace (or all namespaces, if --all-namespaces is used) are listed.
* If no branches are active, mirrord returns:`No active DB branch found`

2. #### Destroy Branches using:

```bash
mirrord db-branches [(-n|--namespace) namespace] [-A | --all-namespaces] destroy (--all | name...)
```

* Destroys one or more running database branches.
* Use `--all` to destroy every active branch.
* Use one or more branch names to target specific branches.
* mirrord uses the default namespace, or the namespace specified with `--namespace`.
* To destroy branches across all namespaces, use `--all-namespaces`.
* If no active branches are found, mirrord returns: `Error: No active DB branch found`
