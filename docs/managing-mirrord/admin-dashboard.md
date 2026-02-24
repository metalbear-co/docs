---
title: Admin Dashboard
date: 2026-02-24T00:00:00.000Z
lastmod: 2026-02-24T00:00:00.000Z
draft: false
images: []
linktitle: Admin Dashboard
menu:
  docs:
    teams: null
weight: 535
toc: true
tags:
  - enterprise
description: Admin Dashboard for monitoring mirrord usage
---

# Admin Dashboard

The mirrord Admin Dashboard is a web-based interface for monitoring mirrord usage across your organization. It provides real-time visibility into sessions, users, machines, CI pipelines, and overall adoption trends, all served directly from the license server.

{% hint style="info" %}
This feature is available to users on the Enterprise pricing plan and requires mirrord operator version 3.143.0 or later.
{% endhint %}

## Prerequisites

1. A running [license server](license-server.md) with Helm chart version 1.50.0 or later.
2. The `DASHBOARD_DIR` environment variable set on the license server deployment (this is configured automatically by the Helm chart).
3. Network access to the license server from your browser (via ingress, port-forward, or `mirrord exec`).

## Accessing the Dashboard

The dashboard is served by the license server at the `/dashboard/` path. How you access it depends on your cluster setup:

**Via ingress (recommended for production):**

If your license server is exposed via an ingress or gateway, navigate to:

```
https://<your-license-server-host>/dashboard/
```

**Via kubectl port-forward:**

```bash
kubectl port-forward -n mirrord svc/mirrord-license-server 3000:80
```

Then open [http://localhost:3000/dashboard/](http://localhost:3000/dashboard/) in your browser.

**Via mirrord exec:**

```bash
mirrord exec -- curl "mirrord-license-server.mirrord.svc.cluster.local/dashboard/"
```

{% hint style="info" %}
The dashboard does not require authentication beyond network access to the license server. Access control is handled by your cluster networking and ingress configuration.
{% endhint %}

## Dashboard Overview

The dashboard is organized into several sections:

### Metric Cards

The top row displays five key metrics at a glance:

| Metric | Description |
|--------|-------------|
| **Tier** | Your mirrord license tier and total license count |
| **Total Sessions** | Cumulative number of mirrord sessions across all time |
| **Active Machines** | Number of unique machines that have used mirrord |
| **CI Sessions** | Total CI pipeline sessions, with current or max concurrency |
| **Session Time** | Total cumulative session time across all users |

### User Activity

Below the metrics, a chart shows session distribution across users, paired with a details panel listing each user's total session count. This helps identify your most active mirrord users and understand adoption patterns.

### User Metrics Table

A searchable, sortable table with detailed per-user statistics:

| Column | Description |
|--------|-------------|
| **Identifier** | The user's machine identifier |
| **First Active** | Date of the user's first mirrord session |
| **Last Seen** | Date of the user's most recent session |
| **Sessions** | Total number of sessions |
| **Total Time** | Cumulative session time |
| **Avg Duration** | Average session duration |

The table supports:
- **Search**: Filter users by identifier
- **Sorting**: Click column headers to sort ascending or descending
- **Pagination**: Navigate through pages when there are many users

## Features

### Dark Mode

Toggle between light and dark themes using the moon/sun icon in the top-right corner of the app bar. Your preference is saved in the browser's local storage.

### Manual Sync

Click the **Sync** button in the app bar to manually refresh all dashboard data. The last updated timestamp is displayed next to the button.

### Operator Version

When available, the operator version is displayed below the app bar for quick reference.

## Helm Configuration

The dashboard is enabled by default when using the license server Helm chart version 1.50.0 or later. The Helm chart handles setting the `DASHBOARD_DIR` environment variable and bundling the dashboard assets.

To upgrade your existing license server to include the dashboard:

```bash
helm repo update metalbear
helm upgrade mirrord-operator-license-server metalbear/mirrord-license-server -f ./values.yaml --wait
```

No additional `values.yaml` changes are required for the dashboard itself.

## API Endpoints

The dashboard consumes two API endpoints from the license server. These are also available for programmatic access:

- `GET /api/v1/reports/usage?format=json` returns the full usage report (users, sessions, CI metrics, machines).
- `GET /api/v1/reports/usage/trends?days=30` returns time-series data (daily sessions, active users, CI sessions, user adoption).

Both endpoints require the `x-license-key` header when accessed directly. The dashboard injects this automatically when served by the license server.

For spreadsheet reports (Excel format), see [Getting a Utilisation Report](license-server.md#getting-a-utilisation-report-from-the-license-server).
