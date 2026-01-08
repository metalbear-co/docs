---
title: mirrord Operator
date: 2024-01-10T13:37:00.000Z
lastmod: 2024-01-10T13:37:00.000Z
draft: false
menu:
  docs:
    parent: sharing-the-cluster
weight: 100
toc: true
tags:
  - team
  - enterprise
description: The central component that enables team collaboration and concurrent cluster usage
---

# mirrord Operator

The mirrord Operator is a persistent, centralized component that runs in your Kubernetes cluster. It synchronizes and orchestrates different instances of mirrord, enabling multiple developers to use the same cluster concurrently without conflicts.

## What is the mirrord Operator?

The mirrord Operator is a Kubernetes controller that manages mirrord sessions running in your cluster. When developers run mirrord locally, their mirrord client communicates with the Operator instead of acting directly on the cluster. This central coordination point allows the Operator to:

- Track all active mirrord sessions across your team
- Coordinate traffic distribution between multiple developers targeting the same service
- Enforce policies that prevent destructive or conflicting actions
- Manage queue splitting so developers can share message queues safely
- Provide visibility into who is using which cluster resources

Without the Operator, each developer's mirrord instance would act independently, potentially causing conflicts when multiple people target the same services.

## Why do you need it?

The core value of mirrord is that it cuts iteration time by letting developers run their code against the cluster directly, instead of having to build, push and deploy images. However, in order to properly test new code in the cloud, developers need to be able to not only read or receive traffic from the environment, but also to write or send traffic to it, potentially mutating it.

This raises important questions when multiple developers use the same cluster:

- If one developer steals traffic from a remote service, wouldn't that prevent other users from stealing or mirroring traffic from that same service?
- If a service reads from a queue, wouldn't a developer targeting it with mirrord steal all the messages from the queue, preventing other developers from reading them?
- If a developer writes to a database, wouldn't that affect the data that other developers see when they read from the same database?

These conflicts and more are resolved by the mirrord Operator. By having a centralized component that can synchronize different instances of mirrord, your team can use mirrord against the same cluster without affecting each other.

The Operator is available exclusively in the mirrord Team and Enterprise plans. You can get a license [here](https://app.metalbear.com/).

## Installation

The Operator is installed using Helm and requires elevated permissions to the cluster. Only a cluster administrator needs to perform the installation—once installed, all team members can use it through their regular mirrord clients.

### Requirements

- A mirrord for Teams license (get one [here](https://app.metalbear.com/))
- Helm 3.x installed on your local machine
- Cluster admin permissions for the initial installation

### Installing with Helm

First, add the MetalBear Helm repository:

```bash
helm repo add metalbear https://metalbear-co.github.io/charts
```

Download the accompanying `values.yaml` file:

```bash
curl https://raw.githubusercontent.com/metalbear-co/charts/main/mirrord-operator/values.yaml --output values.yaml
```

Open `values.yaml` and set `license.key` to your mirrord for Teams license key.

Finally, install the chart:

```bash
helm install -f values.yaml mirrord-operator metalbear/mirrord-operator
```

### Verifying the installation

After installing the Operator, you can verify it's working by running:

```bash
mirrord operator status
```

This command displays a list of all currently running mirrord sessions in the cluster. If the command succeeds, the Operator is installed and functioning correctly. All mirrord clients will now automatically use the Operator when running against the cluster.

### Using an internal registry (optional)

If your organization uses an internal container registry, you can configure the Operator to pull images from it instead of GitHub Container Registry. This can reduce startup time, lower ingress costs, and ensure availability even if GitHub's registry experiences downtime.

For detailed instructions on configuring an internal registry, see the [Internal Registry section in the Quick Start guide](../overview/quick-start.md#using-internal-registry-optional).

### OpenShift configuration

If you're running on OpenShift, you'll need to apply a SecurityContextConstraints resource to grant the necessary permissions. The Operator requires `allowHostPID`, host directory volume access, and specific capabilities (`SYS_ADMIN`, `SYS_PTRACE`, `NET_RAW`, `NET_ADMIN`) to function properly.

For the complete OpenShift configuration, see the [OpenShift section in the Quick Start guide](../overview/quick-start.md#openshift).

## What's next?

Now that the Operator is installed, your team can take advantage of its capabilities:

- [Managing multiple sessions](managing-multiple-sessions.md) — View and control active mirrord sessions in your cluster
- [Test concurrently, safely](test-concurrently-safely.md) — Use policies to prevent destructive actions and enforce safe usage patterns
- [Standardise Dev Config](standardise-dev-config.md) — Create reusable configuration profiles for your team
