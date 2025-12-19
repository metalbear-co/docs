---
title: Core Features
date: 2024-12-19T00:00:00.000Z
lastmod: 2024-12-19T00:00:00.000Z
draft: false
weight: 115
toc: true
tags:
  - open source
  - team
  - enterprise
description: Run your local process with the network, environment, and files of a pod in your cluster
---

# Core Features

This section covers the fundamentals of using mirrord to run your local process as if it were running inside your Kubernetes cluster. If you've completed the [Quick Start](../overview/quick-start.md), you're ready to go deeper.

## Overview

When you run your application with mirrord, it intercepts your process at the system call level and redirects operations to a remote target in your cluster. This gives your local process:

- **Network access**: Outgoing connections go through the cluster, and incoming traffic from the target can be mirrored or stolen to your local process. [Learn more](networking.md)
- **Environment variables**: The same env vars your target pod has. [Learn more](environment-variables.md).
- **File system access**: Read (or write) files from the target pod's filesystem. [Learn more](file-system.md).

The result: your code runs locally with local tooling (debuggers, hot reload, your IDE), but behaves like it's running in the cluster.

## Choosing a target

Before running mirrord, you need to pick a target—the pod or workload whose context you want to "step into." The target determines:

- Which pod's environment variables you inherit
- Which pod's filesystem you can access
- Where your outgoing network traffic originates from
- Which incoming traffic can be sent to your local process

Specify a target with the `--target` flag:

```bash
# Target a specific pod
mirrord exec --target pod/my-app-7d4b8c6f5-x2k9p npm run dev

# Target a deployment (mirrord picks a pod)
mirrord exec --target deploy/my-app npm run dev
```

Or in a configuration file:

```json
{
  "target": {
    "path": "deploy/my-app",
    "namespace": "staging"
  }
}
```

For full details on targets, see [Targets](../reference/targets.md).

## A minimal configuration file

While CLI flags work for quick runs, a configuration file gives you repeatable, shareable settings. Create a `.mirrord/mirrord.json` file in your project:

```json
{
  "target": {
    "path": "deploy/my-app",
    "namespace": "staging"
  },
  "feature": {
    "network": {
      "incoming": "mirror",
      "outgoing": true
    },
    "fs": "read",
    "env": true
  }
}
```

Then run:

```bash
mirrord exec -f .mirrord/mirrord.json npm run dev
```

For the full configuration reference, see [Configuration](../reference/configuration.md).
