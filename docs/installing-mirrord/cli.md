---
title: CLI
date: 2020-11-16T12:59:39.000Z
lastmod: 2020-11-16T12:59:39.000Z
draft: false
images: []
menu:
  docs:
    parent: installing-mirrord
weight: 111
toc: true
tags:
  - open source
  - team
  - enterprise
description: Installing and using the mirrord CLI tool
---

# CLI

The mirrord CLI is the core tool for running mirrord from the command line. It can be used standalone or is automatically managed by the IDE extensions.

## Installation

{% tabs %}
{% tab title="MacOS/Linux" %}

To install the CLI, run:

```bash
brew install metalbear-co/mirrord/mirrord
```

or

```bash
curl -fsSL https://raw.githubusercontent.com/metalbear-co/mirrord/main/scripts/install.sh | bash
```
{% endtab %}

{% tab title="Windows" %}
To install the CLI, run:

```powershell
choco install --pre mirrord
```
{% endtab %}
{% endtabs %}

## Usage

To use mirrord to plug a local process into a pod/deployment in the cluster configured with kubectl, run:

```bash
mirrord exec --target <target-path> <command used to run the local process>
```

For example:

```bash
mirrord exec --target pod/app-pod-01 python main.py
```

Or, if you'd rather run a local container than a native process, run:

```bash
mirrord container --target <target-path> -- <command used to run the local container>
```

For example:

```bash
mirrord container -- docker run nginx
```

Use `mirrord exec --help` or `mirrord container --help` to get all possible commands and arguments.

## Interactive Setup

You can use `mirrord wizard` to generate a config file interactively. This walks you through common use cases and helps you create a configuration tailored to your needs.

## Listing Targets

To see available targets in your cluster:

```bash
mirrord ls
```

This will list all pods, deployments, and other resources that mirrord can target.

## Configuration

The CLI reads its configuration from a mirrord config file. By default, it looks for `.mirrord/mirrord.json` in the current directory. You can specify a different config file with the `-f` flag:

```bash
mirrord exec -f my-config.json --target pod/app-pod python main.py
```

Configuration options are documented in the [configuration reference](https://app.gitbook.com/s/Z7vBpFMZTH8vUGJBGRZ4/options).

## Verifying Installation

To verify mirrord is installed correctly:

```bash
mirrord --version
```

To check connectivity to your cluster and the mirrord Operator (if using mirrord for Teams):

```bash
mirrord operator status
```

{% hint style="info" %}
**Got it working? Stuck?** Either way, [come say hi in Slack](https://metalbear.com/slack)
{% endhint %}
