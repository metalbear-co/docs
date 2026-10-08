---
title: Working with API Gateways
description: "Use mirrord with services behind an API gateway such as Kong, Envoy Gateway, Emissary, NGINX, or Traefik"
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

# Working with API Gateways

Many clusters send external traffic through an API gateway, such as Kong, Envoy Gateway, Emissary, NGINX, Traefik, or a gateway your team built. mirrord works with services behind a gateway. In most cases, the gateway needs no change.

## How Traffic Reaches Your Local Process

A request passes through the gateway before it reaches a service:

```
client  ->  API gateway  ->  service pod  ->  your local process
            (auth, routing,   (mirrord
             rate limits,      intercepts
             transforms)       here)
```

mirrord intercepts traffic at the [target](../../reference/targets.md) pod, after the gateway. A request that reaches your local process has already gone through the real gateway. Your local code receives the request as the deployed service would: authenticated, routed, and with every header that the gateway adds.

## Target the Service Behind the Gateway

Target the service that handles the route, not the gateway. To share the service with other developers, steal only the requests that carry your header:

```json
{
  "target": "deployment/orders",
  "feature": {
    "network": {
      "incoming": {
        "mode": "steal",
        "http_filter": {
          "header_filter": "^baggage: .*mirrord-session=local-dev-123.*"
        }
      }
    }
  }
}
```

Then send the request through the gateway, with the header:

```bash
curl -H "baggage: mirrord-session=local-dev-123" https://api.staging.example.com/orders
```

Requests without the header go to the deployed service as usual. For all the filter options, see [Filtering Incoming Traffic](filter-incoming-traffic.md).

## Make Sure the Gateway Forwards the Header

The filter matches only if the header reaches the service. Most gateways forward request headers to the upstream service by default. Check these points if your filter does not match:

- **Use `baggage`.** It is a W3C standard header, and many gateways, service meshes, and tracing libraries keep it.
- **Do not use underscores in a custom header name.** NGINX, including ingress-nginx, drops headers that contain underscores by default (`underscores_in_headers off`). Some gateways, such as Kong, forward them, but hyphens work with all of them.
- **Check header allowlists and transforms.** If the gateway removes unknown headers, or a plugin rewrites them, add your header to the allowlist.
- **See which headers arrive.** Run [`mirrord dump`](inspect-live-traffic.md) on the target to see the real headers that reach the service. Without the mirrord operator, stop your own session on that target first, because two sessions cannot attach to the same pod.

A filter on `baggage` matches past the first service only if each service forwards the header to the next one. To have your AI agent set that up, use the [`mirrord-header-propagation`](https://github.com/metalbear-co/skills/tree/main/skills/mirrord-header-propagation) skill.

## When the Client Cannot Set a Header

Some clients cannot add a header, for example a mobile app or a third-party webhook. In that case, let the gateway add the header for a dedicated test host or route:

- **Kong:** the `request-transformer` plugin, with `add.headers`.
- **NGINX:** `proxy_set_header` in the location block.
- **Envoy Gateway:** a `RequestHeaderModifier` filter with `add` on the HTTPRoute.
- **Emissary-ingress:** `add_request_headers` on the Mapping.
- **Envoy configured directly:** `request_headers_to_add` on the route.

{% hint style="warning" %}
Add the header only on a host or route that is used for testing. If you add it to a shared route, all traffic on that route matches your filter and goes to your local process.
{% endhint %}

For shared preview links, mirrord has a separate component, `mirrord-share-ingress`, that adds the header on the server side, so a plain link works with no extension on the client. See [Preview Environments](../../use-cases/preview-environments.md).

## Call Services Through the Gateway From Local Code

By default, mirrord sends outgoing traffic and DNS queries through the remote pod. Your local process can call the gateway's in-cluster Service address, in the form `<gateway-service>.<namespace>.svc.cluster.local`, or call the services behind it directly. The Service name depends on how the gateway was installed. To find it, run `kubectl get svc -n <gateway-namespace>`. See [Outgoing Traffic](../outgoing-traffic/README.md).

## Gateways That Send Encrypted Traffic to the Service

An HTTP filter needs to read the request. If the gateway sends HTTPS to the service (TLS passthrough or re-encryption), see [Stealing HTTPS Requests](steal-https.md).

## Preview Environments Behind a Gateway

By default, [preview environments](../../use-cases/preview-environments.md) route on the `baggage: mirrord-session=<key>` header. A preview can also use a custom filter. The same rule applies to either: the gateway must forward the header that the filter matches.

## Developing the Gateway Itself

If the gateway is a service that your team builds, for example with Spring Cloud Gateway or a custom Go or Node.js service, target its Deployment like any other service.
