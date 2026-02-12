---
title: "Multi-Cluster"
description: "Run mirrord across multiple Kubernetes clusters simultaneously"
date: 2026-02-12T00:00:00+00:00
lastmod: 2026-02-12T00:00:00+00:00
draft: false
images: []
menu:
  docs:
    parent: "using-mirrord"
weight: 175
toc: true
tags: ["enterprise"]
---

{% hint style="info" %}
This feature is available to users on the Enterprise pricing plan.
{% endhint %}

Multi-cluster mirrord lets developers intercept traffic from pods running in multiple Kubernetes clusters at the same time, without switching kube contexts or managing multiple sessions. You run `mirrord exec` exactly like before, and the operator handles everything behind the scenes.

**When is this useful?**

1. **Multi-region traffic testing**
   Your service receives traffic in us-east-1, eu-west-1, and eu-west-1. You want to test your local app against traffic from all regions at once.

2. **Centralized access**
   Your security policy requires developers to connect through a management cluster. Developers can't directly reach workload clusters.

3. **Shared environments with multiple clusters**
   Your staging environment spans multiple clusters. You want mirrord to intercept traffic across all of them in a single session.

---

## How It Works

In single-cluster mirrord, the CLI connects to one operator, which creates one agent that intercepts traffic. In multi-cluster, a **Primary** cluster coordinates sessions across multiple **Workload** clusters.

The developer connects to the Primary cluster. The Primary operator creates child sessions on each workload cluster. Each workload cluster's operator spawns an agent locally. Traffic from all clusters flows back to the developer's local application through a single connection.

From the developer's perspective, nothing changes. The same `mirrord exec` command, the same configuration file, the same workflow. The operator decides whether to use single-cluster or multi-cluster mode based on its installation configuration.

---

## Understanding Cluster Roles

Each cluster in a multi-cluster setup takes on one or more roles. A cluster can have multiple roles at the same time (e.g. Primary + Workload + Default).

| Role | What it does | How many |
|------|-------------|----------|
| **Primary** | Entry point for developers. Orchestrates sessions across all other clusters. | Exactly one |
| **Workload** | Runs application pods. Agents intercept traffic here. | One or more |
| **Default** | Handles stateful operations like (env vars, files, DNS, outgoing connections, DB branching etc..). | Exactly one |

### Primary Cluster

The Primary cluster is the developer's entry point. When you run `mirrord exec`, your CLI talks to the Primary cluster's operator. The Primary then orchestrates sessions across all other clusters.

The Primary cluster can also run workloads (it can be both a coordinator and a workload cluster), or it can be configured as management-only if it has no application pods.

### Workload Clusters

Workload clusters are where your application pods run. Each workload cluster has its own mirrord operator that spawns agents and handles traffic interception locally, just like single-cluster mirrord.

### Default Cluster

Some operations need to return consistent data — environment variables, file reads, outgoing connections, and database branching. These are called "stateful operations." The Default cluster is the one cluster designated to handle all of them.

When your app reads `DATABASE_URL`, the request goes to the Default cluster only — you get one answer, not different answers from different clusters. Traffic operations (mirror/steal) still go to all workload clusters.

### Management-Only Mode

If the Primary cluster only orchestrates and doesn't run application workloads, set it to management-only mode (`managementOnly: true`). In this case, you must designate a different cluster as the Default, since stateful operations can't run on a cluster with no application pods.

---

## Session Lifecycle

When the developer runs `mirrord exec`, the CLI connects to the Primary operator and creates a parent session. The Primary operator then creates child sessions on each workload cluster. Each child session is a normal single-cluster session from the remote cluster's perspective — it resolves the target, spawns an agent, and handles traffic locally.

Once all child sessions are ready, the CLI establishes a WebSocket connection. Messages are routed automatically based on the type of operation (see the routing table above).

---

## Database Branching in Multi-Cluster

[Database branching](db-branching.md) works across clusters. The developer connects to the Primary cluster, but the branch is created on the Default cluster.

If Primary is not the Default cluster, a sync controller (`DbBranchSyncController`) on Primary mirrors branch resources to the Default cluster and copies the status back. The developer's CLI waits for the branch to be ready, then passes the branch name via connection parameters when creating the session — the same flow as single-cluster.

If Primary is the Default cluster, no syncing is needed — branching controllers run locally on Primary, just like single-cluster.

---

## SQS Queue Splitting in Multi-Cluster

[SQS queue splitting](queue-splitting.md) works across clusters. The operator on each workload cluster creates its own temporary queue and patches the local workload. The Primary operator passes SQS split configuration to each child session via connection parameters, including the `sqs_output_queues` map for cross-cluster output queue routing.

---

## What's Next?

To set up multi-cluster operator, see the [Multi-Cluster Setup](multi-cluster-setup.md) guide which covers authentication methods, Helm configuration, and RBAC.
