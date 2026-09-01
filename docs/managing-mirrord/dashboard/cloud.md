---
title: Cloud Dashboard
date: 2026-09-01T00:00:00.000Z
lastmod: 2026-09-01T00:00:00.000Z
draft: false
images: []
linktitle: Cloud
menu:
  docs:
    teams: null
weight: 535
toc: true
description: Monitor mirrord usage from the hosted MetalBear dashboard
tags:
  - team
  - enterprise
---

# Cloud Dashboard

The mirrord Cloud Dashboard at [app.metalbear.com](https://app.metalbear.com) shows usage for organizations that authenticate the mirrord Operator with a [cloud API key](../operator.md#cloud-api-key). It gives admins a hosted view of mirrord adoption across connected clusters without deploying a separate dashboard service.

{% hint style="info" %}
This page covers the hosted dashboard. For the self-hosted dashboard served by the license server, see [Dashboard](../admin-dashboard.md).
{% endhint %}

## Requirements

To see usage in the Cloud Dashboard, install the mirrord Operator with a cloud API key:

```yaml
cloud:
  apiKey:
    keyRef: mirrord-operator-cloud-api-key
```

Then create the referenced secret in the Operator namespace:

```bash
kubectl create secret generic mirrord-operator-cloud-api-key \
  --namespace mirrord \
  --from-literal=apiKey=<your-api-key>
```

You can also provide the key inline with `cloud.apiKey.key` or from Google Secret Manager with `cloud.apiKey.gsmRef`. See [Cloud API key](../operator.md#cloud-api-key) for the full installation options.

## What You Can See

The Cloud Dashboard uses the usage metrics reported by connected Operators. Depending on your organization's identity sharing setting, the dashboard can show:

* Active and historical mirrord sessions
* Developer usage and adoption trends
* Session duration and frequency
* Target workloads used by mirrord sessions
* Cluster-level usage when `operator.clusterName` is configured

If identity sharing is disabled, usage remains anonymized. The dashboard can still show aggregate usage, but developer and target names are replaced with anonymized identifiers.

## Identity Sharing

Identity sharing is configured when an organization admin creates a cloud API key in the dashboard. When enabled, usage events may include the Kubernetes username, local account display name, hostname, and target namespace, kind, name, and container.

To force anonymized metrics from the Operator regardless of the cloud API key setting, set:

```yaml
cloud:
  anonymizeData: true
```

Changing identity sharing in the dashboard takes effect at the Operator's next cloud token refresh. You do not need to regenerate the key or restart the Operator.

For the complete list of reported fields, see [What data does the mirrord Operator send to MetalBear cloud?](../security.md#what-data-does-the-mirrord-operator-send-to-metalbear-cloud).

## Cloud API Key Management

Cloud API keys are managed from the dashboard under **Settings**. The key value is shown only once, so store it somewhere secure when you create it.

From the same dashboard, organization admins can:

* Generate new cloud API keys
* Choose whether identity sharing is enabled for the key
* Rotate keys
* Revoke keys
* Set a grace window when revoking a key, so existing Operators can be rolled over safely

## Self-Hosted Environments

The Cloud Dashboard is only used by Operators that authenticate directly with MetalBear cloud by using a cloud API key. If the Operator authenticates against a self-hosted [License Server](../license-server.md), the cloud API key is ignored and usage metrics stay in the license server environment.

For air-gapped or fully offline Enterprise deployments, use an offline license certificate instead of a cloud API key. See [Air-gapped / offline clusters](../operator.md#air-gapped--offline-clusters-enterprise).
