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

The cloud dashboard is the mirrord usage dashboard served from [app.metalbear.com](https://app.metalbear.com), for operators that authenticate to the mirrord cloud with a **cloud API key** instead of running a self-hosted license server. It shows the same sessions, users, targets, CI, and adoption views as the [self-hosted dashboard](admin-dashboard.md), so there is nothing to deploy inside your cluster to view them.

{% hint style="info" %}
The cloud dashboard is in early access and is rolling out to organizations gradually. If you do not see it after connecting your operator, [reach out](https://metalbear.com/mirrord/contact/) and we will enable it for your organization.
{% endhint %}

## Cloud dashboard vs. license server dashboard

There are two ways to get the usage dashboard. Pick the one that matches how your operator is licensed:

| | Cloud dashboard | [License server dashboard](admin-dashboard.md) |
| --- | --- | --- |
| **Operator credential** | Cloud API key (`cloud.apiKey`) | Self-hosted license server (`license.licenseServer`) |
| **Where you view it** | [app.metalbear.com](https://app.metalbear.com), behind your login | In-cluster, via `kubectl port-forward` |
| **Access control** | Your organization's members, through login | Your cluster networking |
| **Where usage data lives** | mirrord cloud | Your license server's database |
| **Best for** | Teams that can reach the mirrord cloud | Air-gapped or fully self-hosted (Enterprise) installs |

An operator uses **one** of these, never both: when a license server is configured, the operator authenticates to it and no identities leave your cluster, and any cloud API key is ignored. When a cloud API key is configured and no license server is set, the operator authenticates to the mirrord cloud.

{% hint style="warning" %}
The cloud dashboard needs the operator to reach `analytics.metalbear.com` and `app.metalbear.com` for outbound telemetry. If you run air-gapped or cannot allow that traffic, stay on the [license server dashboard](admin-dashboard.md), which keeps all data inside your cluster.
{% endhint %}

## New customers: set up the cloud dashboard

The quickest path is the guided onboarding in the app, which walks you through the same steps below and verifies each one.

1. **Sign in.** Go to [app.metalbear.com](https://app.metalbear.com) and sign in (or create your organization).

2. **Generate a cloud API key.** In the onboarding wizard's **Install the Operator** step, click **Generate API Key**. Before generating, decide whether to share identity-level usage data:

   * **Leave it checked** to give your dashboard per-user detail (usernames and targets).
   * **Uncheck it** to keep telemetry anonymized, in which case the dashboard shows activity without attributing it to named users or targets.

   Copy the key when it is shown. It is only shown once.

3. **Install the operator with the key.**

   ```bash
   helm repo add metalbear https://metalbear-co.github.io/charts
   helm repo update metalbear
   helm install --set cloud.apiKey.key=<YOUR_API_KEY> mirrord-operator metalbear/mirrord-operator
   ```

   {% hint style="info" %}
   For production, don't pass the key inline. Store it in a Kubernetes secret and reference it with `cloud.apiKey.keyRef`, or point at Google Secret Manager with `cloud.apiKey.gsmRef`. See [Cloud API key](operator.md#cloud-api-key).
   {% endhint %}

4. **Verify the operator connected.** Back in the wizard, click **Verify Installation**. Once the operator has exchanged the key for a token at least once, it reports **Operator connected**.

5. **Run your first session.** Install the mirrord CLI and run a session (the wizard's `mirrord wizard` command generates a config to start from). As soon as the first session is recorded, your **Home** page in app.metalbear.com becomes the usage dashboard.

The dashboard appears once the operator is connected and at least one session has been recorded, a dashboard with nothing in it would have nothing to show.

## Using the dashboard

The cloud dashboard is the same interface as the self-hosted one: a **Usage** tab with metric cards and a searchable session-activity table, **Users** and **Targets** analytics views, and an **ROI Calculator**. For a full walkthrough of each view and metric, see [Dashboard](admin-dashboard.md#usage-tab).

Two differences from the self-hosted dashboard:

* **It follows the app.** Dark mode, your organization, and navigation come from app.metalbear.com rather than a standalone app bar.
* **Identity detail depends on consent.** Per-user and per-target detail appears only if identity sharing was enabled on the API key you installed with (step 2). With it off, the same activity is shown anonymized.

## Migrating from the license server dashboard

If you run a self-hosted license server today and want to move to the cloud dashboard, the move is per operator: you switch its credential from a license server to a cloud API key.

1. **Get a cloud API key** from [app.metalbear.com](https://app.metalbear.com), as in step 2 above.

2. **(Optional) Bring your history across.** By default the cloud dashboard starts accumulating usage from the moment your operator begins reporting to the cloud. If you would rather not start from zero, [contact us](https://metalbear.com/mirrord/contact/) to import your existing license-server dashboard history into your organization before you switch.

3. **Reinstall the operator with the cloud API key** and remove the license-server configuration. In your Helm values, add `cloud.apiKey` and drop `license.licenseServer`:

   ```bash
   helm upgrade --set cloud.apiKey.key=<YOUR_API_KEY> mirrord-operator metalbear/mirrord-operator
   ```

   Because an operator uses a license server **or** the cloud but never both, leaving a license server configured would keep the operator on license-server auth and the cloud API key would be ignored. If you were running the separate `mirrord-license-server` chart only for its dashboard, you can uninstall it once the operator is reporting to the cloud.

4. **Confirm.** Sign in to app.metalbear.com and run a session. Your usage should appear on the dashboard (plus any history you imported in step 2).

{% hint style="warning" %}
Do not migrate an air-gapped or network-restricted deployment. The cloud dashboard requires outbound connectivity to the mirrord cloud; keep those clusters on the [license server dashboard](admin-dashboard.md).
{% endhint %}
