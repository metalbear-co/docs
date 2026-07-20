---
title: "mirrord up (multiple concurrent sessions)"
tags:
  - alpha
  - oss
  - team
  - enterprise
description: "How to use mirrord up"
date: 2026-04-014T16:25:00+04:00
lastmod: 2026-04-014T16:25:00+04:00 
draft: false
menu:
  docs:
    parent: "using-mirrord"
weight: 140
toc: true
---
## Introduction
`mirrord up` allows creating and running multiple mirrord sessions based on configuration defined in a single file — think `docker compose` but for mirrord. This can be useful for cases when you need to debug multiple related microservices and would like to manage their lifecycle together.

## Getting started

The fastest way to get a valid `mirrord-up.yaml` is the interactive wizard:
```sh
$ mirrord up init
```
It prompts for common settings and walks you through one or more services, then writes the file (default: `./mirrord-up.yaml`). The generated file contains only the values you set; everything left at its default is omitted. See [`mirrord up init`](#mirrord-up-init) below for details.

To write the file by hand instead, start with:
```yaml
services:
  user-auth-service:
    run:
      command: ["python", "-m", "http.server"]

  stage-user-dashboard-app:
    target:
      path: pod/nginx
    run: 
      command: ["node", "app.js"]
```

This file is the single source of configuration for all running sessions. Each entry in `services` defines a `mirrord` process that will run as part of the `mirrord up` session. You can leave out `target.path` (or the whole `target`) and `mirrord up` will infer it from the service id — see the `services.*.target` section below.

Now, in the same directory of the `mirrord-up.yaml` file, run
```sh
$ mirrord up
```

This will start all defined services, and they will run in parallel. The `mirrord up` session will be stopped once it's interrupted (`ctrl-c`) or one of the running mirrord sessions shuts down.

Services default to `split` mode, which steals incoming traffic matching an `http_filter`. When no filter is provided, mirrord generates one based on the session key: `baggage: .*mirrord-session={key}.*`.

## Configuration

### Queue Splitting

`mirrord up` supports queue splitting automatically for every service in `split` mode. You don't need to add any special configuration.

Before starting the session, set up queue splitting for the target and enable the relevant queue-splitting feature in the mirrord operator. Follow the [Queue Splitting guide](../sharing-the-cluster/queue-splitting.md) for the target's `MirrordSplitConfig` and broker-specific prerequisites.

Start the services with a session key, for example:

```sh
$ mirrord up --key checkout-debug
```

Messages intended for this session must contain `mirrord-session=checkout-debug`.
The marker is matched in broker-specific message metadata: SQS message attributes, Google Cloud Pub/Sub attributes,
Azure Service Bus application properties, or Temporal headers. For Redis Pub/Sub and BullMQ, it is matched in the message payload.

Queue splitting is available in `mirrord up` for Amazon SQS, Google Cloud Pub/Sub, Azure Service Bus, Redis Pub/Sub, Temporal, and BullMQ.
Kafka and RabbitMQ aren't supported yet in `mirrord up`.

{% hint style="info" %}
Only messages containing the session key (`checkout-debug` in this case) are routed to your local session. All other messages continue to the deployed target.
{% endhint %}

### Config file (`mirrord-up.yaml`)

#### `common`
Common configuration options, applied to all defined services. Currently 3 options are supported:
- [`accept_invalid_certificates`](https://metalbear.com/mirrord/docs/config/options#root-accept_invalid_certificates)
- [`operator`](https://metalbear.com/mirrord/docs/config/options#root-operator)
- [`telemetry`](https://metalbear.com/mirrord/docs/config/options#root-telemetry)

All 3 map directly to their `mirrord.json` counterparts.

#### `services`
A map from service ids to a `ServiceConfig`. Each entry in this map defines and configures a mirrord process that will be run as part of the session.

##### `services.*.target`
Specifies the target of the session. Has 2 fields: `path` and `namespace`, which map directly to their `mirrord.json` counterparts.

When `path` is omitted, `mirrord up` infers it from the service id (the key in the `services` map) by searching the cluster for a deployment, statefulset, rollout, or pod with that name. If a match is found, it's used automatically, otherwise `mirrord up` prompts you to pick a namespace and workload, and offers to save the choice back to `mirrord-up.yaml` so future runs skip the prompt.

To run a service without a target (outgoing traffic only), set `target: none`.

Examples:
```yaml
# Specify both namespace and path
target:
  path: deployment/test-app
  namespace: test-namespace
```

```yaml
# Path only, will use default namespace
target:
  path: deployment/test-app
```

```yaml
# Path omitted: inferred from the service id, searching `test-namespace`
target:
  namespace: test-namespace
```

```yaml
# Targetless — outgoing traffic only
target: none
```

Omitting the `target` field entirely is equivalent to an empty mapping: the path is inferred from the service id in the default namespace.

##### `services.*.env`
Specifies the environment variable configuration for the given service. Maps directly (1:1) to [`feature.env`](https://metalbear.com/mirrord/docs/config/options#feature-env)

##### `services.*.default_mode`
So far, only `split` is supported. The incoming mode is set to `steal` with http filter.
User-provided filter is used if provided, otherwise defaulting to `baggage: .*mirrord-session={key}.*`.

##### `services.*.http_filter`
Specifies the HTTP filtering configuration for the given service. Maps directly to [`feature.network.incoming.http_filter`](https://metalbear.com/mirrord/docs/config/options#feature-network-incoming)

##### `services.*.ignore_ports` 
List of ports that should be ignored in incoming traffic. Maps directly to [`feature.network.incoming.ignore_ports`](https://metalbear.com/mirrord/docs/config/options#feature-network-incoming)

##### `services.*.run` 
Specifies the command that should be run with mirrord. Has 2 fields:
- `command`: Array of strings containing the command to be run and its CLI arguments.
- `type`: can be either `exec` or `container`, defaults to `exec`. Specifies how mirrord should be run (i.e. with `mirrord exec` or `mirrord container`)

Examples:
```yaml
run:
  type: container
  command: ["docker", "run", "my-app"]
```

```yaml
run:
  # `type` defaults to `exec`, no need to specify explicitly
  command: ["node", "app.js"]
```

## CLI args

### `-f`, `--config-file`
Allows specifying a different config file, e.g. `mirrord up -f mirrord-up-custom.yaml`

### `--key`
Allows specifying a custom session key. When not supplied, the OS username is used.

## `mirrord up init`

Interactive wizard that generates a skeleton `mirrord-up.yaml`. It does not query the cluster; workload inference and prompting happen later, when you run `mirrord up`.

```sh
$ mirrord up init [-o path/to/mirrord-up.yaml]
```

Flow:
1. **Common settings** — prompts for `operator`, `accept_invalid_certificates`, and `telemetry`. Only values you change from the default are written.
2. **Services** — loops one service at a time, prompting for name, target, HTTP filter, ignore ports (with presets for Istio/Linkerd sidecars), env overrides, run type (`exec`/`container`), and the local command. For the target you choose to infer it from the service name (looked up when you run `mirrord up`), specify one explicitly, or run without a target. Repeats until you answer "no" to *Add another service?*.
3. **Preview and save** — prints the generated YAML, asks whether to save, then for a filename (re-asking if you decline to overwrite an existing file).
