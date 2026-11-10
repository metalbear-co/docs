---
title: Installing mirrord
description: "How to install mirrord, and what your machine and your cluster need before you start."
---

# Installing mirrord

mirrord can be installed and used in several ways depending on your development workflow:

- **[CLI](cli.md)** - Install the mirrord command-line tool directly
- **[VS Code](vscode.md)** - Install the mirrord extension for Visual Studio Code and compatible editors (Cursor, Windsurf, etc.)
- **[JetBrains IDEs](intellij.md)** - Install the mirrord plugin for JetBrains IDEs (IntelliJ, PyCharm, GoLand, etc.)

For all the IDEs, coding agents, and other tools that mirrord works with, see [mirrord integrations](https://metalbear.com/mirrord/integrations/).

mirrord runs natively on Windows — no WSL needed. If you still prefer to use WSL, see our **[WSL setup guide](wsl.md)**.

## Requirements

For what your machine needs, see [Requirements](../getting-started/install-mirrord.md#requirements).

## Cluster Requirements

For the Kubernetes version, node and feature requirements, see [Cluster Requirements](../getting-started/install-mirrord.md#cluster-requirements).

## mirrord Operator

If you're planning to use [mirrord for Teams](https://app.metalbear.com), you'll also need to install the mirrord Operator in your cluster. See [Install the Operator](../getting-started/install-the-operator.md).
