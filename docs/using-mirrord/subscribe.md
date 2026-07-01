---
title: "Subscribing to Events"
tags:
  - tag: alpha
    primary: true
description: "Stream a session's interception events as JSON with mirrord subscribe"
---
`mirrord subscribe` lets you stream live events from an active mirrord session — HTTP requests, queue messages, and operator notifications as JSON to stdout. It's useful in CI/tests: assert that a request actually got stolen to your local process instead of silently hitting the real service, so a broken interception fails the build instead of
going green.

**When do you receive events?**

* HTTP - you receive an event for each request/response that was routed to or from a target workload by mirrord and matches your subscribed key.
* Queue (Azure Service Bus, Amazon SQS, Kafka) - while queue splitting is active, you receive an event for each message that matches your subscribed key. If no splitting session is active, no events are received.

In both cases: no active mirrord session = no events.

{% hint style="info" %}
This feature is available to users on the Team and Enterprise pricing plans.
{% endhint %}

{% hint style="info" %}
Only **HTTP request/response** events and **Azure Service Bus** / **Amazon SQS** / **Kafka** queue messages are emitted today. HTTP events come from redirected requests/responses; queue events require [queue splitting](../sharing-the-cluster/queue-splitting.md) (Azure Service Bus, Amazon SQS, or Kafka) configured for the session. Kafka Streams consumers are **not** currently supported — only standard Kafka consumers.

Need support for more events? [Open a GitHub issue](https://github.com/metalbear-co/mirrord/issues) or reach out in the [mirrord Slack community](https://metalbearcommunity.slack.com/ssb/redirect)
{% endhint %}

### Prerequisites

* A running session started with a known key: `mirrord exec --key <KEY> ...`. If you don't pass `--key`, the key defaults to your OS username.

### Usage

In one terminal, run the session you want to observe:

```sh
mirrord exec --key my-key -t deployment/my-app -- <cmd>
```

In another, subscribe to its events:

```sh
mirrord subscribe --key my-key
```

The key can also come from the `key` field in your mirrord config (e.g. `mirrord subscribe -f mirrord.json`)

Events stream to stdout, one compact JSON object per line, as the operator intercepts traffic for that key. Status messages go to stderr, so you can pipe events straight into `jq`:

```sh
mirrord subscribe --key my-key | jq 'select(.data.http_request)'
```

You may also pass `--pretty` to pretty-print each event.

### Events

Every event has the same envelope — `service_name`, `timestamp`, and a `data` payload:

```json
{
  "service_name": "my-app",
  "timestamp": "2026-06-17T12:00:00Z",
  "data": {
    "http_request": {
      "method": "GET",
      "uri": "/health",
      "headers": {
        "host": "my-app"
      },
      "version": "HTTP/1.1"
    }
  }
}
```

(examples are pretty-printed for clarity; actual output is compact unless `--pretty` is passed)

To work with just the payload, extract `.data` with `jq`:

```sh
mirrord subscribe --key my-key | jq '.data'
```

**`data` is one of the following (payloads shown on their own):**

* **`http_request`** — an intercepted (stolen) request:

```json
{
  "http_request": {
    "method": "GET",
    "uri": "/health",
    "headers": {
      "host": "my-app"
    },
    "version": "HTTP/1.1"
  }
}
```

* **`http_response`** — the response to a stolen request:

```json
{
  "http_response": {
    "status": 200,
    "version": "HTTP/1.1",
    "headers": {
      "content-type": "application/json"
    }
  }
}
```

* **`queue_message`** — a queue message routed to your session. `queue_type` is `azure_service_bus` or `sqs`. `message_id` and `correlation_id` are included only when the broker provides them (SQS has no `correlation_id`). `properties` is the message's attribute bag, with values stringified: text as-is, and **binary values base64-encoded**.

```json
{
  "queue_message": {
    "queue_type": "azure_service_bus",
    "queue_name": "orders",
    "correlation_id": "trace-123",
    "properties": {
      "tenant": "test"
    }
  }
}
```

An SQS message, where the `payload` attribute was binary (its bytes come back base64-encoded):

```json
{
  "queue_message": {
    "queue_type": "sqs",
    "queue_name": "orders",
    "message_id": "9f2c...",
    "properties": {
      "tenant": "test",
	  "payload": "c29tZSBlcGljIHBheWxvYWQ="
    }
  }
}
```

* **`kafka_message`** — a Kafka message stolen to your session. Kafka uses a **different schema** than `queue_message`: `topic`, `partition`, `offset`, an optional `key`, and `headers` (values stringified — text as-is, binary base64). There is no `queue_type` or `correlation_id`.

```json
{
  "kafka_message": {
    "topic": "orders",
    "partition": 0,
    "offset": 42,
    "key": "order-7",
    "headers": {
      "tenant": "test"
    }
  }
}
```

{% hint style="info" %}
Kafka Streams consumers are not currently supported — only standard Kafka consumers.
{% endhint %}

* **`lagged`** — your consumer fell behind and the operator dropped `count` events:

```json
{
  "lagged": {
    "count": 12
  }
}
```

Lagging takes place whenever the consumer is not able to keep up with the messages and receive them in a timely fashion (e.g. due to a slow network connection). By default, the operator buffers up to 2048 messages (configurable in `values.yaml` through `subscribeEventBufferSize`), and lagging will take place if more than this many messages accumulate in the internal buffer without the consumer receiving them. Note that lagging only affects slow consumers — functioning consumers will continue to receive all events even in the presence of slow peers.

### Direct Kube API access (no mirrord CLI required)

`mirrord subscribe` is a thin wrapper over an operator endpoint that emits [Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events) (`text/event-stream`). You can access it directly through the Kubernetes API, without requiring the mirrord CLI:

```sh
kubectl get --raw \
  "/apis/operator.metalbear.co/v1/events?watch=true&session_key=my-key"
```

or with `kubectl proxy` + `curl`:

```sh
kubectl proxy &
curl -N "http://127.0.0.1:8001/apis/operator.metalbear.co/v1/events?watch=true&session_key=my-key"
```

`watch=true` is necessary to stop the Kube API server from cutting out the stream after \~60s.
