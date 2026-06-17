---
title: "Subscribing to Events"
description: "Stream a session's interception events as JSON with mirrord subscribe"
date: 2026-06-17T00:00:00+00:00
lastmod: 2026-06-17T00:00:00+00:00
draft: false
menu:
  docs:
    parent: "using-mirrord"
weight: 180
toc: true
tags:
  - team
  - enterprise
---

`mirrord subscribe` streams a session's interception events from the operator to stdout as JSON.
It's useful in CI/tests: assert that a request actually got stolen to your local process
instead of silently hitting the real service, so a broken interception fails the build instead of
going green.

{% hint style="info" %}
Requires mirrord for Teams (the mirrord Operator).
{% endhint %}

## Prerequisites

- A running session started with a known key: `mirrord exec --key <KEY> ...`. If you don't pass
  `--key`, the key defaults to your OS username.

## Usage

In one terminal, run the session you want to observe:

```sh
mirrord exec --key my-key -t deployment/my-app -- <cmd>
```

In another, subscribe to its events:

```sh
mirrord subscribe --key my-key
```

Events stream to stdout, one compact JSON object per line, as the operator intercepts traffic for
that key. Status messages go to stderr, so you can pipe events straight into `jq`:

```sh
mirrord subscribe --key my-key | jq 'select(.data.http_request)'
```

Pass `--pretty` to pretty-print each event. The key can also come from the `key` field in your
mirrord config (`-f`).

## Events

Each event is `{ "service_name", "timestamp", "data": { ... } }`, where `data` is one of:

```json
{"service_name":"my-app","timestamp":"2026-06-17T12:00:00Z","data":{"http_request":{"method":"GET","uri":"/health","headers":{"host":"my-app"},"version":"HTTP/1.1"}}}
```
```json
{"service_name":"my-app","timestamp":"2026-06-17T12:00:00Z","data":{"http_response":{"status":200,"version":"HTTP/1.1","headers":{"content-type":"application/json"}}}}
```
```json
{"service_name":"orders","timestamp":"2026-06-17T12:00:00Z","data":{"queue_message":{"queue_type":"azure_service_bus","queue_name":"orders","correlation_id":"trace-123","properties":{"tenant":"test"}}}}
```

If your consumer falls behind, the operator drops the oldest events and tells you how many:

```json
{"service_name":"","timestamp":"2026-06-17T12:00:00Z","data":{"lagged":{"count":12}}}
```

{% hint style="info" %}
Only **HTTP request/response** events and **Azure Service Bus** queue messages are emitted today.
HTTP events come from requests/responses intercepted in steal mode; queue events require
[Azure Service Bus queue splitting](../sharing-the-cluster/queue-splitting.md) configured for the
session.
{% endhint %}

## Without the CLI

`mirrord subscribe` is a thin client over an operator endpoint that emits
[Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
(`text/event-stream`). You can hit it directly through the Kubernetes API — handy from a language
without a mirrord client:

```sh
kubectl get --raw \
  "/apis/operator.metalbear.co/v1/events?watch=true&session_key=my-key"
```

or with `kubectl proxy` + `curl`:

```sh
kubectl proxy &
curl -N "http://127.0.0.1:8001/apis/operator.metalbear.co/v1/events?watch=true&session_key=my-key"
```

Each event arrives as a `data: <json>` line (lines starting with `:` are keep-alives). `watch=true`
is necessary to stop the Kube API server from cutting out the stream after ~60s.
