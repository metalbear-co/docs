---
title: "Sharing the Cluster"
description: >-
  How mirrord makes it possible for developers to use the same cluster
  concurrently.
draft: false
images: []
toc: true
tags:
  - team
  - enterprise
---

# Sharing the Cluster

{% hint style="info" %}
The features in this section require the [mirrord Operator](../managing-mirrord/operator.md), available in the Team and Enterprise plans.
{% endhint %}

When multiple developers use mirrord against the same cluster (e.g. a shared staging environment), they can potentially interfere with each other:

1. One developer stealing traffic from a service blocks others from receiving it
2. A developer targeting a queue consumer steals all messages, starving other sessions
3. Database writes from one developer affect what others see

The mirrord Operator resolves these conflicts by coordinating sessions centrally. Here's how:

### Concurrent HTTP traffic with filters

[Filter incoming traffic](../using-mirrord/incoming-traffic/filter-incoming-traffic.md) by HTTP headers so each developer only steals their own requests. Add a personalized header to your requests and configure mirrord to match it — multiple developers can debug the same service simultaneously.

### Queue splitting

[Queue splitting](queue-splitting.md) lets each developer consume only a subset of messages from a shared queue, based on message properties. No one competes for messages.

### Database isolation

[DB Branching](db-branching.md) creates ephemeral database branches — each developer works against an isolated copy without affecting the shared database.

### Session visibility

[Managing Sessions](sessions.md) — View all active mirrord sessions in the cluster with `mirrord operator status`, and kill problematic ones with `mirrord operator kill`.

### Governance

[Policies](policies.md) let admins define rules — for example, requiring HTTP filters when stealing traffic, or blocking access to sensitive namespaces. [Profiles](profiles.md) standardize mirrord configuration across the team.

### Preview Environments

[Preview Environments](../use-cases/preview-environments.md) let you spin up isolated, ephemeral pods in the cluster for async review and QA — without tying the environment to a developer's local machine.

### Guardrails for destructive actions

Set `MIRRORD_DONT_LOAD=true` on scripts or run configurations (e.g. integration tests) to prevent mirrord from loading. This ensures destructive operations like database resets never accidentally run against remote environments.
