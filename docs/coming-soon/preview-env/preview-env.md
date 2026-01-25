---
title: Preview Environments - Coming Soon
lastmod: 2026-01-22T08:48:45.000Z
description: Ephemeral, Isolated Environments Connected to Your Cluster

---

Preview Environments let teams collaborate, validate, and review new code using real traffic, without affecting live services.

A Preview Environment runs **only the new or changed services** in isolated pods inside your Kubernetes cluster. All other dependencies (for example, databases, queues, and upstream services) continue to run in the main cluster, such as staging, and are accessed via mirrord.

Because Preview Environments are not tied to a developer’s local process, they are well suited for:

- Product managers exploring new features before they’re merged
- QA engineers testing changes against realistic traffic and dependencies
- Engineers collaborating on a feature in progress or requesting async feedback

This enables realistic validation workflows without cloning an entire environment and without blocking on a single mirrord session.

{% hint style="info" %}
Preview Environments will be available to users on the **Enterprise** pricing plan.
{% endhint %}

# What Is a Preview Environment?

Today, mirrord sessions are tightly coupled to a developer’s local process. When that process stops, the testing environment disappears.
Preview Environments solve this by allowing you to spin up isolated, temporary pods in the cluster that:

- Run **user-provided container images**
- Match the **configuration and traffic behavior** of an existing mirrord target
- Receive **filtered or duplicated staging traffic** using an environment key
- Stay alive for a **fixed TTL**, independent of any local machine or process

---

## Environment Key

Each Preview Environment is identified by an **environment key**. The key is used to:

- Scope HTTP and queue traffic filtering
- Scope database branches
- Associate multiple preview pods into a single environment
- Share access to the same environment with other developers

If no key is provided, mirrord generates one automatically

---

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

- If `--key` is omitted, mirrord generates a new key and prints it in the output.
- You can add or update pods in an existing Preview Environment by reusing the same environment key

### Targetless Mode

If no target is defined in the mirrord configuration, Preview Environments run in **targetless mode**.

In this mode, mirrord creates a fresh, isolated pod that still participates in traffic filtering via the environment key, without mirroring an existing workload.

--- 

### Managing Preview Environments

1. **Status:** Check the current state of Preview Environments, including which environments are active, which preview pods they contain, and how long they will remain available.
```bash
mirrord preview status
```
2. **Clean:** Manually remove a Preview Environment and its associated preview pods when it is no longer needed.
```bash
mirrord preview clean --key <environment-key>
```

## Preview Environment Workflow

![Preview Environment Workflow](/docs/coming-soon/preview-env/prev-env-new.svg)

### Interested in Preview Environments?
[**Sign up**](https://2dkwjs.share-eu1.hsforms.com/2u8rhMF4WTomds20_JcxHOw) **to get updates and be notified when Preview Environments are available.**


