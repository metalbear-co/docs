---
title: Network Traffic
date: 2022-08-08T08:48:45.000Z
lastmod: 2022-08-08T08:48:45.000Z
draft: false
images: []
menu:
  docs:
    parent: reference
weight: 140
toc: true
tags:
  - open source
  - team
  - enterprise
description: Reference to working with network traffic with mirrord
---

mirrord intercepts the local process's network operations and proxies them through the target pod. This page covers incoming traffic (mirror and steal), outgoing traffic (TCP/UDP/Unix sockets), and DNS resolution.

For the how-to versions, see [Using mirrord → Incoming Traffic](../using-mirrord/incoming-traffic/README.md) and [Outgoing Traffic](../using-mirrord/outgoing-traffic/README.md).

## Incoming traffic

Incoming traffic has three modes, set via `feature.network.incoming.mode`:

| Mode | Behavior |
|---|---|
| `mirror` (default) | The agent sniffs TCP traffic on the target's ports and sends a copy to the local process. The remote pod still receives and responds to every request. Responses from the local process are dropped. |
| `steal` | The agent intercepts TCP traffic and redirects it to the local process. The remote pod stops receiving stolen requests. The local process is now responsible for responding. |
| `off` | Incoming traffic is disabled. The local process doesn't receive cluster traffic on any port. |

Shorthand: `"incoming": "steal"`, `"incoming": "mirror"`, `"incoming": false` (= `off`), `"incoming": true` (= `steal`).

### Steal mode has two sub-modes

When `incoming.mode` is `steal`:

1. **Port stealing** (no HTTP filter set): all TCP traffic on each port the local process listens on is stolen.
2. **HTTP stealing** (HTTP filter set): the agent sniffs the first bytes of each new connection on the listened ports. HTTP requests that match the filter are stolen; everything else is forwarded to the remote pod.

HTTP detection is best-effort and has a timeout (`MIRRORD_AGENT_HTTP_DETECTION_TIMEOUT`).

### HTTP filter types

Set under `feature.network.incoming.http_filter`. Only active when `incoming.mode` is `steal`.

| Filter | Matches |
|---|---|
| `header_filter` | Regex matched against each header as `Header-Name: Header-Value`. Case-insensitive. |
| `path_filter` | Regex matched against the request path, both with and without the query string. |
| `method_filter` | The HTTP method. Case-insensitive. Supports standard and custom methods. |
| `body_filter` | Currently only JSON: `{ "body": "json", "query": "<JSONPath>", "matches": "<regex>" }`. Returns true if any node selected by the JSONPath matches the regex. |
| `header_filter_jq` | A jq expression evaluated against each `Header-Name: Header-Value`. Matches if the expression returns `true`. |
| `all_of` / `any_of` | An array of the above as composite filters. `all_of` requires every entry to match; `any_of` requires at least one. |
| `ports` | When set, the filter applies only to these ports. **When absent, the filter applies to all ports the local process listens on.** |

All regex filters use the [`fancy-regex`](https://docs.rs/fancy-regex/latest/fancy_regex/index.html) crate (supports lookarounds and backreferences).

**Recommended pattern for isolating one developer's session:** match a W3C `baggage` or `tracestate` entry that the caller propagates, e.g. `header_filter: "^baggage: .*mirrord-session=alice.*"`. This works across proxies, service meshes, and tracing-aware clients without requiring custom headers.

**Composite example, POST to a specific endpoint from a specific session:**

```json
{
  "http_filter": {
    "all_of": [
      { "header": "^baggage: .*mirrord-session=alice.*" },
      { "path":   "^/api/v1/orders$" },
      { "method": "POST" }
    ]
  }
}
```

### Other incoming options

| Field | Default | Behavior |
|---|---|---|
| `port_mapping` | `[]` | `[[local, remote]]` pairs. Mirror/steal remote port X and deliver to local port Y. Useful when local code listens on a different port than the cluster service. |
| `listen_ports` | `[]` | `[[remote, local-bind]]` pairs. Forces the local in-process listener to bind to a specific port instead of a random fallback. Useful when listening on a privileged port (e.g. remote 80 → local 4480) without `sudo`. Independent of `port_mapping`. |
| `ignore_ports` | `[]` | Ports to leave local. Common use: skip kubelet health probes when stealing. Mutually exclusive with `ports`. |
| `ports` | unset | If set, only these ports are mirrored/stolen; others stay local. Mutually exclusive with `ignore_ports`. |
| `ignore_localhost` | `false` | If `true`, traffic to `127.0.0.1` is treated as local. |
| `on_concurrent_steal` | `abort` | (Operator only) What to do when another session already has a steal lock on the target: `abort` (fail), `continue` (proceed without stealing), `override` (force-close the existing lock). |
| `tls_delivery` | unset | (Operator only) How mirrord delivers stolen TLS traffic to the local app. See [steal-https](../using-mirrord/incoming-traffic/steal-https.md). |

## Outgoing traffic

Outgoing traffic is forwarded by default for both TCP and UDP. The local process opens what looks like a normal socket; the agent opens the actual connection from inside the target pod and tunnels the bytes back.

```json
{
  "feature": {
    "network": {
      "outgoing": {
        "tcp": true,
        "udp": true,
        "ignore_localhost": false,
        "filter": {
          "local": ["tcp://127.0.0.1:5432", ":53"]
        },
        "unix_streams": "^/var/run/.+"
      }
    }
  }
}
```

| Field | Default | Behavior |
|---|---|---|
| `tcp` | `true` | Forward outgoing TCP through the pod. |
| `udp` | `true` | Forward outgoing UDP through the pod. Only works if the app binds a non-zero port and calls `connect()` before sending. |
| `ignore_localhost` | `false` | Treat `127.0.0.1` traffic as local. |
| `filter.remote` | none | Only matching destinations go through the pod; everything else stays local. |
| `filter.local` | none | Only matching destinations stay local; everything else goes through the pod. (Mutually exclusive with `filter.remote`.) |
| `unix_streams` | none | Regex (or list of regexes) on Unix socket paths. Matching connections are forwarded to the pod; non-matching stay local. |

### Outgoing filter syntax

Each filter entry: `[protocol]://[name|address|subnet/mask]:[port]`. All parts optional.

| Entry | Meaning |
|---|---|
| `tcp://1.1.1.0/24:1337` | TCP only, that subnet, that port |
| `1.1.5.0/24` | Both protocols, that subnet, any port |
| `google.com:7331` | Both protocols, that hostname (resolved), that port |
| `:53` | Both protocols, any host, port 53 |

### The mirror + outgoing gotcha

If `incoming.mode` is `mirror` (default) **and** outgoing is enabled (default) **and** your handler does writes (e.g. a DB insert), every mirrored request causes **two** writes: one from the remote pod, one from your local copy.

Three ways to avoid this:

1. Switch to `steal` mode: only one process handles each request.
2. Disable outgoing traffic if the target services are cluster-internal.
3. Use an outgoing filter to send specific destinations local-only.

## DNS resolution

```json
{
  "feature": {
    "network": {
      "dns": {
        "enabled": true,
        "filter": {
          "local": ["localhost", ":53"]
        }
      }
    }
  }
}
```

When enabled (default), `getaddrinfo` / `gethostbyname` calls in the local process are forwarded to the agent, which resolves them using the target pod's resolver. This is what makes `my-service.default.svc.cluster.local` work from your laptop.

DNS filter syntax is the same as outgoing, minus the protocol: `[name|address|subnet/mask][:port]`. `filter.remote` sends only matching queries to the pod's resolver; `filter.local` keeps only matching queries local.

### Limitations

- **Only works with `getaddrinfo` / `gethostbyname`.** Frameworks that talk to a DNS server directly on port 53 (some Go DNS clients, some custom resolvers) bypass mirrord entirely. If you see resolution errors with such a framework, enable the `fs` feature with `read_only: ["/etc/resolv.conf"]` so the resolver reads the pod's DNS config from the (remote) file system.
- DNS filter currently only applies to `getaddrinfo` / `gethostbyname` paths.

## IPv6

`feature.network.ipv6` (default `false`). Enable if the local app listens on or connects to IPv6 addresses. Off by default because most clusters are IPv4 and turning it on adds extra socket bookkeeping.

## Related

- [`feature.network` config reference](https://metalbear.com/mirrord/docs/config#feature.network): full schema
- [Using mirrord → Incoming Traffic](../using-mirrord/incoming-traffic/README.md)
- [Using mirrord → Outgoing Traffic](../using-mirrord/outgoing-traffic/README.md)
- [Steal HTTPS](../using-mirrord/incoming-traffic/steal-https.md): for `tls_delivery`
