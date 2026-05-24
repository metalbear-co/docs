---
title: Incoming Traffic
description: How mirrord handles incoming network traffic from the cluster
---

mirrord lets your local process receive network traffic that would normally go to a pod in the cluster. There are two main modes (plus `off`):

## Mirroring (default)

mirrord **mirrors** incoming TCP traffic — your local process receives a copy while the remote pod continues to handle it normally. Responses from your local process are dropped. This is a safe, read-only way to observe how your code handles real requests.

## Stealing

In **steal** mode, mirrord intercepts incoming traffic and redirects it to your local process instead of the remote pod. Your local process becomes the one responding to real requests. Useful when you need to test how your code handles and responds to live traffic.

```json
{
  "feature": {
    "network": {
      "incoming": "steal"
    }
  }
}
```

When sharing a cluster, almost always combine `steal` with a [filter](filter-incoming-traffic.md) so you only steal *your* traffic.

For mode semantics, HTTP detection behavior, all configuration fields (`port_mapping`, `ignore_ports`, `on_concurrent_steal`, etc.), and the operator-only options, see the [traffic reference](../../reference/traffic.md#incoming-traffic).

## What's in this section

- **[Filter Incoming Traffic](filter-incoming-traffic.md)** — Steal only a subset of traffic using HTTP header, W3C `baggage`/`tracestate`, path, method, body, or jq filters
  - [Filtering by JSON Body](filtering-by-json-body.md) — Filter based on request body content
  - [Debug from Browser](debug-from-browser.md) — Use the Chrome extension to route browser traffic to your local process
- **[Steal HTTPS Requests](steal-https.md)** **[Teams]** — Decrypt and steal HTTPS traffic using TLS certificates
- **[Inspect Live Traffic](inspect-live-traffic.md)** — Monitor incoming traffic without running a local process
