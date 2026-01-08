---
title: Targeting Modes
date: 2024-12-19T00:00:00.000Z
lastmod: 2024-12-19T00:00:00.000Z
draft: false
weight: 150
toc: true
tags:
  - open source
  - team
  - enterprise
description: Different ways to select what your local process connects to in Kubernetes
---

# Targeting Modes

When you run mirrord, you typically specify a target—the pod or workload whose context you want to "step into." The target determines which environment variables you inherit, which filesystem you access, and where your network traffic originates from.

## Standard targeting

The most common way to use mirrord is to target an existing pod or workload:

```bash
# Target a specific pod
mirrord exec --target pod/my-app-7d4b8c6f5-x2k9p npm run dev

# Target a deployment (mirrord picks a pod automatically)
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

This gives your local process:
- Environment variables from the target pod
- File system access to the target pod's files
- Network access through the target pod
- Incoming traffic from the target (mirrored or stolen)

For full details on target types and selection, see [Targets](../reference/targets.md).

## Alternative targeting modes

Sometimes the standard approach doesn't fit your use case. mirrord supports two alternative modes:

### Run Without a Target

Run mirrord without impersonating any pod. Useful for new applications that haven't been deployed yet, or for running tools like Postman in your cluster's network context. [Learn more](run-without-target.md).

### Clone a Remote Pod

Create a temporary copy of a pod to use as your target instead of the original. Useful when the original pod is unreliable (keeps crashing) or when you need to scale down a workload to avoid conflicts (e.g., competing for queue messages). [Learn more](clone-remote-pod.md).
