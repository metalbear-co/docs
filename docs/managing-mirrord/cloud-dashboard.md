---
title: Cloud Dashboard
date: 2026-08-26T00:00:00.000Z
lastmod: 2026-08-26T00:00:00.000Z
draft: false
images: []
linktitle: Cloud Dashboard
menu:
  docs:
    teams: null
weight: 536
toc: true
description: The mirrord usage dashboard, served from the cloud for operators that authenticate with a cloud API key
tags:
  - beta
---

# Cloud Dashboard

If your operator authenticates with a cloud API key rather than a self-hosted license server, you get the usage dashboard at [app.metalbear.com](https://app.metalbear.com) with nothing to deploy in your cluster. It shows the same sessions, users, targets, CI, and adoption views as the [license server dashboard](admin-dashboard.md).

{% hint style="info" %}
The cloud dashboard is in early access and is being rolled out gradually. If you have connected your operator and still don't see it, [get in touch](https://metalbear.com/mirrord/contact/) and we'll turn it on for your organization.
{% endhint %}

## Cloud dashboard vs. license server dashboard

Which one you get depends on how the operator is licensed:

| | Cloud dashboard | [License server dashboard](admin-dashboard.md) |
| --- | --- | --- |
| **Operator credential** | Cloud API key (`cloud.apiKey`) | Self-hosted license server (`license.licenseServer`) |
| **Where you view it** | [app.metalbear.com](https://app.metalbear.com), behind your login | In-cluster, via `kubectl port-forward` |
| **Access control** | Your organization's members, through login | Your cluster networking |
| **Where usage data lives** | mirrord cloud | Your license server's database |
| **Best for** | Teams that can reach the mirrord cloud | Air-gapped or fully self-hosted (Enterprise) installs |

An operator does one or the other, never both. With a license server configured it authenticates there, no identities leave your cluster, and a cloud API key is ignored. With a cloud API key and no license server, it authenticates to the mirrord cloud.

{% hint style="warning" %}
The cloud dashboard needs the operator to reach `analytics.metalbear.com` and `app.metalbear.com`. If you run air-gapped or can't allow that traffic, stay on the [license server dashboard](admin-dashboard.md), which keeps everything inside your cluster.
{% endhint %}

## New customers: set up the cloud dashboard

The onboarding in the app does these steps for you and checks each one. To set it up by hand:

1. Sign in at [app.metalbear.com](https://app.metalbear.com) (or create your organization).

2. Generate a cloud API key, choosing whether to share identity-level usage data: leave it on for per-user detail (usernames and targets), or turn it off to keep telemetry anonymized.

   Copy the key when it appears. It's only shown once.

3. Install the operator with the key:

   ```bash
   helm repo add metalbear https://metalbear-co.github.io/charts
   helm repo update metalbear
   helm install --set cloud.apiKey.key=<YOUR_API_KEY> mirrord-operator metalbear/mirrord-operator
   ```

   {% hint style="info" %}
   In production, don't pass the key inline. Put it in a Kubernetes secret and reference it with `cloud.apiKey.keyRef`, or point at Google Secret Manager with `cloud.apiKey.gsmRef`. See [Cloud API key](operator.md#cloud-api-key).
   {% endhint %}

4. Run a session. Install the mirrord CLI and run one (`mirrord wizard` generates a config to start from).

Once the operator is connected and a session has been recorded, your **Home** page at app.metalbear.com is the usage dashboard.

## Using the dashboard

It's the same interface as the license server dashboard: a **Usage** tab with metric cards and a searchable session-activity table, **Users** and **Targets** analytics, and an **ROI Calculator**. The [Dashboard](admin-dashboard.md#usage-tab) page walks through every view and metric.

Dark mode, your organization, and navigation come from the app around it rather than a standalone app bar. Per-user and per-target detail only appears if identity sharing was on for the API key you installed with; with it off, the same activity shows anonymized.

## Migrating from the license server dashboard

Moving from the license server dashboard to the cloud dashboard means switching the operator's credential from a license server to a cloud API key.

1. Generate a cloud API key at [app.metalbear.com](https://app.metalbear.com), as above.

2. The cloud dashboard starts from the moment your operator begins reporting to the cloud. If you'd rather not start empty, [get in touch](https://metalbear.com/mirrord/contact/) to import your existing license-server history first.

3. In your operator Helm values, add the cloud API key and remove the license-server configuration, then upgrade:

   ```yaml
   # values.yaml
   cloud:
     apiKey:
       keyRef: mirrord-operator-cloud-api-key
   # and remove license.licenseServer
   ```

   ```bash
   helm upgrade mirrord-operator metalbear/mirrord-operator -f values.yaml
   ```

   `license.licenseServer` takes priority over a cloud API key, so it has to go, not just sit unset. Create the referenced secret as shown in [Cloud API key](operator.md#cloud-api-key). If you ran the separate `mirrord-license-server` chart only for its dashboard, uninstall it once the operator is reporting to the cloud.

4. Sign in and run a session. Your usage shows up on the dashboard, along with any history you imported.

{% hint style="warning" %}
Don't migrate an air-gapped or network-restricted deployment. The cloud dashboard needs outbound connectivity to the mirrord cloud; keep those clusters on the [license server dashboard](admin-dashboard.md).
{% endhint %}
