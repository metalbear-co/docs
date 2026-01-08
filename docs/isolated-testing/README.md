---
title: Isolated Testing
date: 2024-08-31T13:37:00.000Z
lastmod: 2024-08-31T13:37:00.000Z
draft: false
weight: 180
toc: true
tags:
  - team
  - enterprise
description: Test in isolation with queue splitting and database branching to safely share infrastructure across your team
---

# Isolated Testing

When testing code that interacts with stateful resources like queues and databases, developers face a dilemma. Testing against local mock services lacks realism, but testing against shared cloud resources risks disrupting teammates and corrupting data. Isolated testing features in mirrord solve this by giving each developer their own isolated view of shared infrastructure.

## Why isolated testing matters

**Reduces infrastructure costs**: Instead of provisioning separate environments for each developer, your team can share a single staging cluster. Isolated testing ensures developers don't interfere with each other despite using the same underlying resources.

**Makes testing faster**: Developers can test immediately against real cloud services without waiting for deployments or spinning up complex local environments. Changes are tested in realistic conditions from the first iteration.

**Makes shared infrastructure safer**: Bad changes—whether a faulty database migration or a buggy message processor—stay isolated to the developer's session. Teammates working on the same cluster remain unaffected, and production-like data stays intact.

## How it works

mirrord's isolated testing features create temporary, personal copies of stateful resources that your local application uses instead of the shared versions. These isolated copies are automatically managed by the mirrord Operator and cleaned up when your session ends.

### Queue Splitting

When you enable queue splitting, the mirrord Operator intercepts messages from your queue and routes them to temporary queues based on filters you define. Your local application receives only messages matching your filter, while other messages continue flowing to the deployed service or your teammates' filtered queues.

This allows multiple developers to work on the same queue-based service simultaneously. Each developer can generate test messages knowing they'll receive only their own messages, without stealing work from the deployed application or disrupting colleagues.

[Learn more about Queue Splitting](queue-splitting.md)

### Database Branching

When you enable database branching, mirrord creates a temporary, isolated copy of your database. Your local application's database connection is automatically redirected to this branch instead of the shared database. You can test schema migrations, run experiments, and modify data freely without any risk to the shared environment.

Database branches can be shared with teammates when needed, and they're automatically destroyed after a configurable time-to-live period. This gives you the confidence to test destructive operations knowing they can't escape your isolated branch.

[Learn more about DB Branching](db-branching.md)

## What's next?

Both Queue Splitting and Database Branching require the mirrord Operator to coordinate isolation between team members. If you haven't installed the Operator yet, see the [mirrord Operator guide](../sharing-the-cluster/mirrord-operator.md) to get started.

Once the Operator is installed, explore how to:
- [Split queues](queue-splitting.md) to test message processing in isolation
- [Branch databases](db-branching.md) to safely test schema changes and migrations
