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
  - teams
---

# Cloud Dashboard

If your operator authenticates with a cloud API key rather than a self-hosted license server, you get the usage dashboard at [app.metalbear.com](https://app.metalbear.com) with nothing to deploy in your cluster. It shows the same sessions, users, targets, CI, and adoption views as the [license server dashboard](admin-dashboard.md).

{% hint style="info" %}
The cloud API key needs operator chart 3.179.0 or newer; identity detail (usernames and targets) needs 3.193.0 or newer.
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

An operator does one or the other, never both: configure a license server and it authenticates there, no identities leave your cluster, and a cloud API key is ignored.

{% hint style="warning" %}
The cloud dashboard needs the operator to reach `analytics.metalbear.com` and `app.metalbear.com`.
{% endhint %}

## New customers: set up the cloud dashboard

The onboarding in the app does these steps for you and checks each one. To set it up by hand:

1. Sign in at [app.metalbear.com](https://app.metalbear.com) (or create your organization).

2. Generate a cloud API key (organization admins only, under **API Keys**). Identity sharing is pre-ticked: with it on, the dashboard shows real usernames and service names instead of hashes. It's your organization's choice; turn it off to keep telemetry anonymized.

   Copy the key when it appears. It's only shown once, and regenerating replaces the current key.

   {% hint style="info" %}
   `cloud.anonymizeData: true` in the operator's Helm values overrides identity sharing: telemetry stays anonymized even with consent granted.
   {% endhint %}

3. Install the operator with the key:

   ```bash
   helm repo add metalbear https://metalbear-co.github.io/charts
   helm repo update metalbear
   helm install --set cloud.apiKey.key=<YOUR_API_KEY> mirrord-operator metalbear/mirrord-operator
   ```

   {% hint style="info" %}
   In production, don't pass the key inline. Put it in a Kubernetes secret and reference it with `cloud.apiKey.keyRef`, or point at Google Secret Manager with `cloud.apiKey.gsmRef`. See [Cloud API key](operator.md#cloud-api-key).
   {% endhint %}

4. Install the mirrord CLI and run a session (`mirrord wizard` generates a config to start from).

Once the operator is connected and a session has been recorded, your **Home** page at app.metalbear.com is the usage dashboard.

## Using the dashboard

It's the same interface as the license server dashboard: a **Usage** tab with metric cards and a searchable session-activity table, **Users** and **Targets** analytics, and an **ROI Calculator**. The [Dashboard](admin-dashboard.md#usage-tab) page walks through every view and metric.

Dark mode, your organization, and navigation come from the app around it rather than a standalone app bar. Per-user and per-target detail only appears if identity sharing was on for the API key you installed with; with it off, the same activity shows anonymized.

## Enabling on an existing install

If your operator already runs with a license key (no license server), add the API key to its Helm values and upgrade:

```yaml
# values.yaml
cloud:
  apiKey:
    keyRef: mirrord-operator-cloud-api-key
```

```bash
helm upgrade mirrord-operator metalbear/mirrord-operator -f values.yaml
```

Existing `license.*` values stay as they are. Create the referenced secret as shown in [Cloud API key](operator.md#cloud-api-key), or use `gsmRef` or an inline `key` instead. The key is read at startup, so the upgrade's pod restart is what picks it up.

Your existing anonymized usage is already on the dashboard; it doesn't start from zero. From the upgrade forward, sessions carry identity (if sharing is on). Usernames also fill in on historical sessions once each developer runs a session with the key in place, since names resolve per user across all time; per-service detail for old sessions doesn't backfill.

## Migrating from the license server dashboard

A self-hosted license server is different: an operator configured with `license.licenseServer` authenticates only against it and ignores a cloud API key entirely, so switching means removing that setting.

1. Generate a cloud API key at [app.metalbear.com](https://app.metalbear.com), as above.

2. In your operator Helm values, add `cloud.apiKey` as shown in the previous section and remove `license.licenseServer`, then upgrade.

3. Sign in and run a session. Your usage shows up on the dashboard. Usage recorded by the license server stays in its database; if you want that history on the cloud dashboard, [get in touch](https://metalbear.com/mirrord/contact/) and we'll import it. Once the operator is reporting to the cloud, the `mirrord-license-server` chart can be uninstalled if you only ran it for the dashboard.

{% hint style="warning" %}
Don't migrate an air-gapped or network-restricted deployment. The cloud dashboard needs outbound connectivity to the mirrord cloud; keep those clusters on the [license server dashboard](admin-dashboard.md).
{% endhint %}
