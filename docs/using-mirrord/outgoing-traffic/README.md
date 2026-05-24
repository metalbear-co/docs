---
title: Outgoing Traffic
description: How mirrord handles outgoing network traffic from your local process
---

By default, mirrord intercepts outgoing network requests from your local process and routes them through the remote pod. Your local code can access cluster-internal services like databases, APIs, and message brokers, as if it were running inside the cluster.

This works through three mechanisms:

1. **Environment variables**: your local process inherits the remote pod's env, so connection strings and hostnames point to the right places.
2. **DNS resolution**: mirrord resolves DNS queries in the pod's context, so cluster-internal hostnames (like `my-service.default.svc.cluster.local`) resolve correctly.
3. **Network interception**: outgoing TCP and UDP connections are sent from the remote pod, giving your local process access to resources that are only reachable from within the cluster.

Both outgoing TCP and UDP forwarding are enabled by default.

{% hint style="warning" %}
If mirrord is configured to **mirror** incoming traffic (the default), both the remote pod and your local process may make outgoing API calls for the same incoming request. If those calls are write operations (e.g. database inserts), this leads to duplicates. Use [`steal` mode](../incoming-traffic/README.md), disable outgoing traffic, or use an [outgoing filter](filter-outgoing-traffic.md) to avoid it.
{% endhint %}

For the full config surface (TCP/UDP toggles, `ignore_localhost`, filter syntax, Unix-socket forwarding), the DNS-resolution caveats, and IPv6 support, see the [traffic reference](../../reference/traffic.md#outgoing-traffic).

## What's in this section

- **[Filter Outgoing Traffic](filter-outgoing-traffic.md)**: control which outgoing connections go through the cluster and which stay local
