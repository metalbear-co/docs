---
title: High Availability
date: 2026-01-12T00:00:00.000Z
lastmod: 2026-01-12T00:00:00.000Z
draft: false
images: []
linktitle: High Availiability
menu: null
docs: null
teams: null
weight: 505
toc: true
tags:
  - enterprise
description: High availability for mirrord Operator in Enterprise Tier
---

# High Availability

Starting from chart version `1.40.1`, mirrord Operator is by default highly available.
This means that mirrord sessions should survive transient failures in the cluster,
with respect to the set of advanced mfT features used by the session (see [advanced features](#advanced-featues) section).
This includes failures of nodes where the mirrord Operator pods are running.

High availability is implemented in a lightweight fasion, by saving sessions' state in the cluster's builtin etcd database (as [Custom Resources](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/)). Therefore, no persistent volume is required. At startup, the operator restores and resumes saved sessions.

{% hint style="info" %}
This feature is available to users on the Enterprise pricing plans.
{% endhint %}

## Multiple replicas

By default, mirrord Operator workload runs with a single replica.
Starting from chart version `1.40.3`, this can be configured with `operator.replicas` setting in the chart.

Regardless of the configured scale, only one replica acts as a leader, and serves mirrord sessions.
Any additional replicas wait in a standby mode, ready to acquire leadership and resume work, in case of current leader's failure.
Configuring the operator to run with multiple replicas allows for smoother leadership transitions,
since the new leader candidates are already running.

## Advanced featues

Not all of the advanced mfT features have yet been migrated to highly available sessions.
The table below summarizes the current state of development.

| Feature         | HA | Chart version |
| --------------- | ---| ------------- |
| SQS splitting   | ✅ | `1.40.3`      |
| Kafka splitting | ❌ |               |
| Copy target     | ❌ |               |
| DB branching    | ❌ |               |
