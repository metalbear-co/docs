---
title: "Seamless Multi-Cluster Development"
---

{% hint style="info" %}
This feature is available to users on the Enterprise pricing plan.
{% endhint %}

Multi-cluster mirrord lets developers intercept traffic from pods running in multiple Kubernetes clusters at the same time, without switching kube contexts or managing multiple sessions. You run `mirrord exec` exactly like before, and the operator handles everything behind the scenes.

**When is this useful?**

1. **Multi-region traffic testing**

   Your service receives traffic from multiple regions such as `us-east-1` and `eu-west-1`. You want to validate your local changes against live traffic from all regions simultaneously, without running separate mirrord sessions per cluster.

2. **Centralized access**

   Your organization requires developers to connect through a management cluster, with no direct access to workload clusters. You need mirrord to coordinate traffic interception across clusters while operating from the approved entry point.

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

Some operations need to return consistent data such as environment variables, file reads, outgoing connections, and database branching. These are called "stateful operations." The Default cluster is the one cluster designated to handle all of them.

When your app reads `DATABASE_URL` for example, the request goes to the Default cluster only. You get one answer, not different answers from different clusters. Traffic operations (mirror/steal) still go to all workload clusters.

### Management-Only Mode

If the Primary cluster only orchestrates and doesn't run application workloads, set it to management-only mode (`managementOnly: true`). In this case, you must designate a different cluster as the Default, since stateful operations can't run on a cluster with no application pods.

---

## Session Lifecycle

When the developer runs `mirrord exec`, the CLI connects to the Primary cluster and creates a single parent session. The Primary operator then creates child sessions on each workload cluster. From the perspective of each Workload cluster, each child session behaves exactly like a regular single-cluster session: the operator resolves the target, spawns an agent, and handles the traffic interception.

Once all child sessions are ready, the CLI establishes a unified WebSocket connection to the Primary cluster. Messages are routed automatically based on the type of operation (see the routing table above).

---

## Database Branching in Multi-Cluster

[Database branching](db-branching.md) in multi-cluster mode behaves the same from the developer’s perspective, but may execute on a different cluster internally. The developer connects to the Primary cluster, but the branch is created on the Default cluster.

If the Primary cluster is not the Default cluster, a synchronization controller (`DbBranchSyncController`) runs on the Primary. It mirrors branch resources to the Default cluster and syncs the branch status back to the Primary. The CLI waits waits for the branch to be ready, then passes the branch name via connection parameters when creating the session, same flow as single-cluster.

If the Primary cluster is also the Default cluster, no synchronization is required. The branching controllers operate locally on the Primary, and the flow is identical to single-cluster behavior.

---

## SQS Queue Splitting in Multi-Cluster

[SQS queue splitting](queue-splitting.md) works seamlessly in multi-cluster sessions. Each Workload cluster handles queue splitting independently: its operator creates a temporary queue and patches the target workload locally, just as in single-cluster mode.

During session setup, the Primary cluster operator propagates the SQS split configuration to every child session via connection parameters. This includes the sqs_output_queues mapping, ensuring that messages produced by your local application are routed to the correct cluster-specific output queues.

Queue isolation happens independently in each Workload cluster, while configuration and coordination remain centralized through the Primary cluster.

---

## What's Next?

To set up multi-cluster, see the [Multi-Cluster Setup](multi-cluster-setup.md) guide which covers authentication methods, Helm configuration, and RBAC.
