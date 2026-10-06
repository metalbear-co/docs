---
title: Propagating Headers Across Services
description: Keep your mirrord filter header on requests as they pass between services, so filtered traffic reaches services deeper in the call chain
date: 2026-10-06T00:00:00.000Z
lastmod: 2026-10-06T00:00:00.000Z
draft: false
menu:
  docs:
    parent: using-mirrord
toc: true
tags:
  - oss
  - team
  - enterprise
---

When you [filter incoming traffic](filter-incoming-traffic.md) by header, mirrord only sends your local process the requests that carry that header. That works out of the box for the first service a request reaches. For a service deeper in the call chain, the header has to survive every hop on the way there, and that is up to your application, not mirrord.

## When you need header propagation

Consider a request flowing through three services, where you're running `billing-api` locally with mirrord:

```
client ──(baggage: mirrord-session=alice)──> frontend ──(?)──> billing-api
```

The client adds the header to its request to `frontend`. `frontend` then makes a *new* HTTP call to `billing-api`. Unless `frontend` copies the header from the request it received onto the request it sends, the header is gone, `billing-api` receives an ordinary request, and your filter doesn't match.

You need header propagation when:

* You use an HTTP header filter, **and**
* The service you're running locally isn't the first one the request reaches.

You don't need it when you steal or mirror unfiltered traffic, when you filter by something other than a header, or when the service you're running locally is the entry point for the requests you send.

## Recognizing the problem

Missing propagation looks like mirrord isn't working, even though the session is healthy:

* `mirrord exec` reports that it's ready, and `mirrord operator status` shows your session with the expected filter.
* Requests you send with the header still get handled by the remote target, and nothing reaches your local process.
* Sending the same request with the header **directly** to the service you're running locally does reach your local process.

To confirm, run [`mirrord dump`](inspect-live-traffic.md) against the service you're running locally and send a request through the normal entry point. If the request arrives without your header, a service earlier in the chain is dropping it.

## Use `baggage` and your tracing library

The simplest setup is to filter on the W3C `baggage` header and let OpenTelemetry carry it between services:

```json
{
  "feature": {
    "network": {
      "incoming": {
        "mode": "steal",
        "http_filter": {
          "header_filter": "^baggage: .*mirrord-session=alice.*"
        }
      }
    }
  }
}
```

OpenTelemetry instrumentation extracts `baggage` from each incoming request and adds it to the outgoing requests made while handling it. If your services are already instrumented, they may propagate it with no further changes. The defaults in common setups:

| Stack | What to enable |
| --- | --- |
| Java | The OpenTelemetry Java agent propagates `tracecontext` and `baggage` by default. |
| Python | `opentelemetry-instrument` with the instrumentation packages for your web framework and HTTP client. `baggage` is in the default `OTEL_PROPAGATORS`. |
| Node.js | The OpenTelemetry Node SDK with `@opentelemetry/auto-instrumentations-node`. The default propagators include `baggage`. |
| Go | There's no default propagator in Go. Register one with `otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(propagation.TraceContext{}, propagation.Baggage{}))`, then wrap your server handlers with `otelhttp.NewHandler` and your HTTP clients with `otelhttp.NewTransport`. For gRPC, use the `otelgrpc` stats handlers. |

If you set `OTEL_PROPAGATORS` explicitly, make sure it includes `baggage`.

{% hint style="info" %}
Instrumentation propagates context only for calls made while handling the request. Work handed off to a background thread, job queue or scheduler usually loses the request context, and the header with it, unless you pass the context along explicitly.
{% endhint %}

## Propagating a custom header

If you filter on your own header (for example `x-dev-session: alice`), tracing libraries won't forward it. Each service has to read it from the incoming request and add it to every outgoing call. The best place for this is shared middleware or a shared HTTP client used by all your services, so that every service propagates the header without each team adding it themselves.

Example in Go with Gin, reading the header from the incoming request and forwarding it on outgoing HTTP and gRPC calls:

```go
session := c.GetHeader("x-dev-session")

// Outgoing HTTP request:
req.Header.Set("x-dev-session", session)

// Outgoing gRPC call:
ctx := metadata.AppendToOutgoingContext(c, "x-dev-session", session)
```

Prefer `baggage` if you can. Tracing libraries forward it with little or no extra code, and other mirrord features, including [preview environments](../../use-cases/preview-environments.md) and the [browser extension](debug-from-browser.md), use it by default.

## Beyond HTTP

The same applies when a request triggers a message instead of a direct call. If a service publishes to a queue while handling a request, copy the header into the message's metadata (a Kafka or RabbitMQ header, an SQS message attribute) so that consumers further down the chain can be filtered too. See [Queue Splitting](../../sharing-the-cluster/queue-splitting.md#setting-a-filter-for-a-mirrord-run) for how mirrord filters messages by metadata.

## Check your ingress

The header must also survive the edge of your cluster. Most ingress controllers and load balancers pass request headers through unchanged, but some API gateways, CDNs and WAFs remove headers they don't recognize. If `mirrord dump` on the first service shows the request arriving without your header, check the configuration of whatever sits in front of it.
