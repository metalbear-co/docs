---
title: Traffic Filtering
date: 2020-11-16T12:59:39.000Z
lastmod: 2025-02-24T00:00:00.000Z
draft: false
menu:
  docs:
    parent: using-mirrord
weight: 100
toc: true
tags:
  - open source
  - team
  - enterprise
description: How to filter traffic using mirrord
---

# Traffic Filtering with Mirror vs Steal

By default, mirrord mirrors all incoming traffic into the remote target, and sends a copy to your local process. This is useful when you want the remote target to answer requests, keeping the remote environment completely agnostic to your local code.

Filtering is the same idea whether you’re mirroring or stealing. Declare which HTTP requests you care about, and only those will be delivered to your local process. The difference is what happens to the original request:

`mirror` mode: the remote target still receives and handles the request. A copy is delivered to your local process for testing or inspection.

`mirror` + `http_filter`: the remote target still handles all requests, but only the filtered subset is copied to your local process. Use this when you want to observe a specific subset of endpoints while keeping production behavior untouched.

`steal` mode: all requests are redirected to your local process. Your local code is the one answering everything, and the remote target does not see the requests. This is useful when you want to test how your code responds to real traffic, or when handling all requests locally avoids issues like duplicate database writes.

`steal` + `http_filter`: only the filtered subset of requests are redirected to your local process. Your local code handles those, while the rest continue to the remote target as usual. Use this when you want to test or mutate only specific requests locally, while leaving other traffic untouched.

### Stealing all of the remote target's traffic

If you want all traffic arriving at the remote target to be redirected to your local process, change the `feature.network.incoming` configuration to `steal`:

```json
{
  "feature": {
    "network": {
      "incoming": "steal"
    }
  }
}
```

Run your process with mirrord using the steal configuration, then send a request to the remote target. The response you receive will have been sent by the local process. If you're using one of our IDE extensions, set a breakpoint in the function handling the request - your request should hang when the breakpoint is hit and until you continue the process.

### Filtering a subset of traffic with `mirror` or `steal` mode

For incoming HTTP traffic (including HTTP2 and gRPC), mirrord also supports filtering a subset of the remote target's traffic. You can do this by specifying a filter on either an HTTP header or path. To control whether traffic is duplicated (mirror) or redirected (steal), set the mode field:
`mirror`: the remote target still handles the request, and your local process gets a copy.
`steal`: the request is redirected to your local process, and the remote target does not handle it.
To specify a filter on a header, use the `feature.network.incoming.http_filter.header_filter` configuration:

```json
{
  "feature": {
    "network": {
      "incoming": {
        "mode": "steal", // can also be "mirror"
        "http_filter": {
          "header_filter": "X-My-Header: my-header-value",
          "ports": [80, 8080]
        }
      }
    }
  }
}
```

The `feature.network.incoming.http_filter.ports` configuration lets mirrord know which ports are listening to HTTP traffic and should be filtered. It defaults to `[80, 8080]`.

To specify a filter on a path, use the `feature.network.incoming.http_filter.path_filter` configuration:

```json
{
  "feature": {
    "network": {
      "incoming": {
        "mode": "steal", // can also be "mirror"
        "http_filter": {
          "path_filter": "my/path",
          "ports": [80, 8080]
        }
      }
    }
  }
}
```

Note that both `header_filter` and `path_filter` take regex value, so for example `"header_filter": "X-Header-.+: header-value-.+"` would work.

#### Filtering out healthchecks using a negative look-ahead

The HTTP filters both take "fancy" regexes that support negative look-aheads. This can be useful for avoiding the stealing of Kubernetes liveness, readiness and startup probes.

For filtering out any probes sent to the application by kubernetes, you can use this header filter, to require a user-agent that does not start with "kube-probe":

```json
{
  "feature": {
    "network": {
      "incoming": {
        "mode": "steal", // can also be "mirror"
        "http_filter": {
          "header_filter": "^User-Agent: (?!kube-probe)"
        }
      }
    }
  }
}
```

To avoid filtering requests sent to URIs starting with "/health/", you can set this filter:

```json
{
  "feature": {
    "network": {
      "incoming": {
        "mode": "steal", // can also be "mirror"
        "http_filter": {
          "path_filter": "^(?!/health/)"
        }
      }
    }
  }
}
```

This is common in APIs where different methods on the same endpoint serve different purposes (e.g., `GET /api/items` vs. `POST /api/items`).
If you filter only by path, you might capture a large amount of traffic unintentionally. For example, if your goal is to intercept only `POST` and `PUT` requests while excluding `GET` requests that use the same path, you can apply a method filter like this:


```json
{
  "feature": {
    "network": {
      "incoming": {
        "mode": "steal", // can also be "mirror"
        "http_filter": {
          "method_filter": ["POST","PUT"]
        }
      }
    }
  }
}
```


The `method_filter` is case-insensitive and supports all standard HTTP methods (`GET`, `HEAD`, `POST`, `PUT`, `DELETE`, `CONNECT`, `OPTIONS`, `TRACE`, `PATCH`) as well as non-standard methods.

#### Grouping Filters: Match All or Any

You can group multiple simple filters together using the `all_of` or `any_of` fields:
`all_of`: the request must match all nested filters.
`any_of`: the request must match at least one nested filter.
It has the following rules:
1. Exactly one top-level filter, `http_filter` must contain exactly one of these fields: `header_filter`, `path_filter`, `method_filter`,`all_of`, `any_of`.
2. Combinators must contain a non-empty array of nested filters, example:
```json
"http_filter": {
  "all_of": [ // or "any_of"
    { "header": "..." },
    { "method": "..." }
  ]
}
```
3. Each nested filter (`header`, `path`, `method`) must contain exactly one value, example:
```json
"http_filter": {
  "all_of": [
    { "method": "POST" }
    { "method": "GET" }
    { "path": "/api/v1/orders" }
  ]
}
```

#### Stealing HTTPS traffic with a filter

`feature.network.incoming.http_filter` allows you to steal a subset of HTTP requests. To apply the filter, the mirrord-agent needs to be able to parse the requests stolen from the target. Most commonly, the incluster traffic is encrypted with TLS, but it is decrypted by a service mesh before it gets to the target service. In this case, mirrord is able to parse the requests out of the box.

However, in some cases the traffic is only decrypted by the target service itself. Using an HTTP filter in this case requires some additional setup. Check out the [HTTPS stealing guide](steal-https.md) for more information. Note that this HTTPS stealing requires mirrord Operator, which is part of mirrord for Teams.

### What's next?

1. If your local process reads from a queue, you might want to test out the [copy target feature](copy-target.md), which temporarily creates a copy of the mirrord session target. With its `scaledown` flag it allows you to temporarily delete all replicas in your targeted rollout or deployment, so that none competes with your local process for queue messages.
2. If you don't want to impersonate a remote target - for example, if you want to run a tool in the context of your cluster - check out our [guide on the targetless mode](targetless.md).
3. If you just want to learn more about mirrord, why not check out our [architecture](../reference/architecture.md) or [configuration](https://app.gitbook.com/s/Z7vBpFMZTH8vUGJBGRZ4/) sections?
