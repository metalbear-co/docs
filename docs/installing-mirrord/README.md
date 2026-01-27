---
title: Installing mirrord
date: 2020-11-16T12:59:39.000Z
lastmod: 2020-11-16T12:59:39.000Z
draft: false
images: []
menu:
  docs:
    parent: ""
weight: 110
toc: true
tags:
  - open source
  - team
  - enterprise
description: How to install mirrord on your local machine
---

# Installing mirrord

mirrord can be installed and used in several ways depending on your development workflow:

- **[CLI](cli.md)** - Install the mirrord command-line tool directly
- **[VS Code](vscode.md)** - Install the mirrord extension for Visual Studio Code and compatible editors (Cursor, Windsurf, etc.)
- **[IntelliJ](intellij.md)** - Install the mirrord plugin for JetBrains IDEs (IntelliJ, PyCharm, GoLand, etc.)
- **[Docker](docker.md)** - Run mirrord with local containers instead of native processes
- **[WSL](wsl.md)** - Set up mirrord on Windows using the Windows Subsystem for Linux

## Requirements

### Local Requirements

For your local machine, you may use any of:
- MacOS (Intel, Apple Silicon)
- Linux (x86_64)
- Windows (x86_64), WSL (x86_64)
  - IDE plugins support for native mirrord for Windows is currently not supported

kubectl needs to be configured on the local machine.

### Remote Requirements

- Docker or containerd runtime (containerd is the most common). If you'd like support for other runtimes to be added, please let us know by [opening an issue on GitHub](https://github.com/metalbear-co/mirrord/issues/new?assignees=&labels=enhancement&template=feature_request.md).
- Linux Kernel version 4.20+

## mirrord for Teams

If you're planning to use [mirrord for Teams](https://app.metalbear.com), you'll also need to install the mirrord Operator. See the [mirrord for Teams](../overview/teams.md) page for installation instructions.
