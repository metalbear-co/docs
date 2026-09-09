---
title: Usage API
description: Pull your organization's usage data out of the cloud dashboard with a read-only key
tags:
  - alpha
  - team
  - enterprise
---

# Usage API

{% hint style="info" %}
This is the cloud dashboard's data over HTTP. It only has something to return if your operator reports to the cloud, see [Cloud Setup](cloud.md). With a self-hosted license server your usage data never leaves the cluster, so there is nothing here for you.
{% endhint %}

The dashboard at [app.metalbear.com](https://app.metalbear.com) is fine for looking at usage. It is less fine when you want the numbers in Looker, or a weekly script that lists who stopped using mirrord. The usage API returns the same report and trends the dashboard renders, plus the raw session rows the dashboard never shows, behind a key you can give to a cron job.

## Get a key

Go to **Settings** and open **Usage API**. You need to be an organization admin. Generate a key; it is shown once, so copy it then.

![Settings, Usage API tab, before a key exists](../../.gitbook/assets/usage-api-settings.png)

The key starts with `metalbear_key_`, like the operator's key, but it is a different kind of key. It can read usage data and nothing else. If you hand it to an operator, the operator is refused.

The page that shows the new key also shows the calls below, filled in with your key, so you can paste them straight into a terminal.

![A freshly generated key with the curl snippets](../../.gitbook/assets/usage-api-key-generated.png)

One usage key is active per organization. **Rotate** issues a new key and keeps the old one working for a grace period you pick, 0 for immediate. **Revoke** stops it now. The page shows when the key was last used, which is a cheap way to spot a job that silently died.

![The active key with Rotate and Revoke](../../.gitbook/assets/usage-api-key-row.png)

Store it as a secret anyway. With identity sharing on it returns your engineers' usernames and hostnames.

## Get a token

The key is not sent to the data endpoints. Exchange it for a token first. A token lasts ten minutes, which is plenty for one run of a script, so fetch one per run rather than caching it.

```bash
TOKEN=$(curl -sSf -X POST "https://app.metalbear.com/api/v2/token" \
  -H "Content-Type: application/json" \
  -d "{\"apiKey\":\"$USAGE_API_KEY\"}" | jq -r .token)
```

Every call below takes `Authorization: Bearer $TOKEN`.

## Endpoints

All three live under `https://app.metalbear.com/api/v1/usage` and answer JSON.

### Report

```
GET /api/v1/usage/report?from=2026-08-01&to=2026-08-31
```

The object the dashboard is drawn from, for the period you ask for:

| Field | What it holds |
| --- | --- |
| `generalMetrics` | Tier, active users in the period, operator version, the resolved `reportPeriod` |
| `allTimeMetrics` | Session and CI session totals since the organization started reporting |
| `ciMetrics` | CI sessions in the period, peak concurrency, average duration |
| `userMetrics` | One row per engineer: `identifier`, `displayName`, `firstActive`, `lastSeen`, `totalSessionCount`, `totalSessionTimeSeconds`, daily and per-session averages |
| `targetMetrics` | Sessions and unique users per target (`namespace`, `target`) |
| `userTargetMetrics` | The same broken down by engineer and target |
| `authErrorMetrics` | Operator authentication errors, period and all time, by type |
| `adoptionActionItems` | What blocked engineers, a policy, a disabled feature, a bad target name, the license, with how many users hit each |

`ciPipelineMetrics`, `ciProviderMetrics`, `uniqueMachines` and `rejectedConnectionCount` are also present when the operator reports them.

### Trends

```
GET /api/v1/usage/trends?days=30
```

Daily series for charts: `dailySessions` (count and total duration per day), `dailyActiveUsers`, `dailyCiSessions`, and `userAdoption` with `newUsers` and `cumulativeUsers` per day. `days` defaults to 30 and is capped at 3650.

### Sessions

```
GET /api/v1/usage/sessions?from=2026-08-01&to=2026-08-31&limit=1000
```

Raw rows, oldest first, one object per session:

```json
{
  "sessions": [
    {
      "id": 48213,
      "startedAt": "2026-08-26T09:14:02Z",
      "stoppedAt": "2026-08-26T09:34:11Z",
      "durationSeconds": 1209,
      "kind": "exec",
      "clusterId": "35700d83-2c6e-4b8e-9d3d-0f1a6d1a5a9e",
      "user": {
        "id": "yeV7wcVsjhI0",
        "kubernetesUsername": "alice@example.com",
        "clientUsername": "alice",
        "clientHostname": "alice-mbp"
      },
      "target": {
        "namespace": "shop",
        "kind": "Deployment",
        "name": "checkout",
        "container": null
      }
    }
  ],
  "nextCursor": "..."
}
```

`kind` is `exec` for an engineer's session, `ci` for `mirrord ci`, `preview` for a preview environment. `ci` and `preview` rows have no target, so those fields come back `null`.

Pages hold up to `limit` rows, 500 by default and 1000 at most. Every non-empty page carries a `nextCursor`; pass it back as `cursor=` to get the next one. The first page that comes back empty is the end. Cursors are opaque, don't try to build one.

```bash
cursor=""
while :; do
  page=$(curl -sSf -H "Authorization: Bearer $TOKEN" \
    "https://app.metalbear.com/api/v1/usage/sessions?from=2026-08-01&to=2026-08-31&limit=1000&cursor=$cursor")
  rows=$(jq '.sessions | length' <<<"$page")
  [ "$rows" -eq 0 ] && break
  jq -c '.sessions[]' <<<"$page" >> august.jsonl
  cursor=$(jq -r '.nextCursor' <<<"$page")
done
```

## Dates and periods

`from` and `to` accept a date (`2026-08-01`), a timestamp with an offset (`2026-08-01T09:00:00+02:00`), or a timestamp without one, which is read as UTC. A date given as `to` covers that whole day, so `to=2026-08-31` includes August 31. Otherwise the window is half-open: `from` is included, `to` is not. Leave `from` out and it starts at the beginning of time; leave `to` out and it ends now. `from` has to be before `to` or you get a 400.

A session belongs to the period it started in. That is the same rule for the report, the trends and the session rows, so counting the rows for a window gives you the report's numbers for that window. A session that started at 23:50 on August 31 and ended at 00:20 on September 1 is an August session everywhere.

## Identity sharing

The report and the session rows carry engineer identities only while identity sharing is on for your organization, the same switch that decides what the dashboard shows. It is set when the operator's cloud API key is generated and can be changed under **Settings**. With it off, `displayName` and `user.id` are pseudonymous hashes, `kubernetesUsername`, `clientUsername` and `clientHostname` are `null`, and `target` is `null`. A change applies to the next token you fetch, not to one you already hold.

## Errors and limits

| Status | Meaning |
| --- | --- |
| `400` | Bad range: `from` after `to`, or a date outside 1970 to 9999 |
| `401` | No token, a malformed one, or an expired one. Fetch a new token |
| `403` | Right token, wrong door: an operator token on this API, or a usage token on an operator endpoint |
| `429` | Over the limit. `Retry-After` says how many seconds to wait |

The limit is 60 requests a minute per organization, counted across the three endpoints. A full export of a large month is a handful of pages, so a script that pauses on 429 and honours `Retry-After` will not notice it.
