---
title: Preview Environment - Coming soon
lastmod: 2026-01-22T08:48:45.000Z
description: Ephemral and Isolated Environment in the Cluster
---

Preview Environments enable teams to collaborate, validate, and review new code using real traffic without impacting live services.

They provide an ephemral, isolated environment in the cluster where new versions of services can run independently of a developer’s local machine. This makes Preview Environments suitable for async feedback, cross-team reviews, and realistic validation workflows that go beyond a single mirrord session.

{% hint style="info" %}
This feature will be available to users on the Enterprise pricing plan.
{% endhint %}

# What Is a Preview Environment?

Today, mirrord sessions are tightly coupled to a developer’s local process. Once that process stops, the testing environment disappears.
Preview Environments provide a simple way to spin up isolated, temporary remote pods that:
- Run user-provided images in the cluster
- Match the configuration and traffic behavior of an existing mirrord target
- Receive filtered or duplicated production traffic using an environment key
- Remain alive for a fixed TTL, independent of any local process

### Key 
Each Preview Environment is identified by an environment key.
The key is used to:
- Scope HTTP and queue traffic filtering
- Enable to associate multiple preview pods into a single environment
- Enable sharing access with other developers
- If a key is not provided, mirrord generates one automatically


## Starting a Preview Environment

Create a new Preview Environment using a mirrord configuration file and a container image:
```bash
mirrord preview start --config-file <mirrord.json> --image <code-image> --key <key>
```
Example output:
```bash
Creating preview environment: <key>
Deploying pod... done.
Preview environment is live!


  Environment key:  <key>
  Pods:
    • preview-svc-env-users-7f9d8c7df8
  TTL expires in: 59m 58s
  ```

- If --key is omitted, mirrord generates a new key and prints it in the output.
- You can add or update pods in an existing Preview Environment by reusing the same environment key

### Targetless Mode
If no target is defined in the configuration, mirrord operates in targetless mode and creates a fresh isolated pod that participates in traffic filtering via the environment key.

### Managing Preview Environments

1. **Status:** 
Check the current state of Preview Environments, including which environments are active, which preview pods they contain, and how long they will remain available.
```bash
mirrord preview status
```
2. **Clean:** Manually remove a Preview Environment and its associated preview pods when it is no longer needed.
```bash
mirrord preview clean --key <environment-key>
```

## Preview Environment Workflow

![Preview Environment Workflow](preview-env-flow.png)

