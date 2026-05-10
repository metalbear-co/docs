---
title: "mirrord up (multiple concurrent sessions)"
description: "How to use mirrord up"
date: 2026-04-014T16:25:00+04:00
lastmod: 2026-04-014T16:25:00+04:00 
draft: false
menu:
  docs:
    parent: "using-mirrord"
weight: 140
toc: true
tags: ["open source", "team", "enterprise"]
---
# Introduction
`mirrord up` allows creating and running multiple mirrord sessions based on configuration defined in a single file — think `docker compose` but for mirrord. This can be useful for cases when you need to debug multiple related microservices and would like to manage their lifecycle together.

# Getting started
Start by creating a `mirrord-up.yaml`:
```yaml
services:
  user-auth-service:
    target:
      path: deployment/test-app
    run:
      command: ["python", "-m", "http.server"]

  stage-user-dashboard-app:
    target:
      path: pod/nginx
    run: 
      command: ["node", "app.js"]
```

This file is the single source of configuration for all running sessions. Each entry in `services` defines a `mirrord` process that will run as part of the `mirrord up` session. 

Now, in the same directory of the `mirrord-up.yaml` file, run
```sh
$ mirrord up
```

This will start all defined services, and they will run in parallel. The `mirrord up` session will be stopped once it's interrupted (`ctrl-c`) or one of the running mirrord sessions shuts down.

Services default to `split` mode, which steals incoming traffic matching an `http_filter`. When no filter is provided, mirrord generates one based on the session key: `baggage: .*mirrord-session={key}.*`.

# Configuration

## Config file (`mirrord-up.yaml`)

### `common`
Common configuration options, applied to all defined services. Currently 3 options are supported:
- [`accept_invalid_certificates`](https://metalbear.com/mirrord/docs/config/options#root-accept_invalid_certificates)
- [`operator`](https://metalbear.com/mirrord/docs/config/options#root-operator)
- [`telemetry`](https://metalbear.com/mirrord/docs/config/options#root-telemetry)

All 3 map directly to their `mirrord.json` counterparts.

### `services`
A map from service ids to a `ServiceConfig`. Each entry in this map defines and configures a mirrord process that will be run as part of the session.

#### `services.*.target`
Specifies the target of the session. Has 2 fields: `path` and `namespace`, which map directly to their `mirrord.json` counterparts.
Examples:
```yaml
# Specify both namespace and path
target:
  path: deployment/test-app
  namespace: test-namespace
```

```yaml
# Namespace only, will be targetless
target:
  namespace: test-namespace
```

```yaml
# Path only, will use default namespace
target:
  path: deployment/test-app
```

#### `services.*.env`
Specifies the environment variable configuration for the given service. Maps directly (1:1) to [`feature.env`](https://metalbear.com/mirrord/docs/config/options#feature-env)

#### `services.*.default_mode`
So far, only `split` is supported. The incoming mode is set to `steal` with http filter.
User-provided filter is used if provided, otherwise defaulting to `baggage: .*mirrord-session={key}.*`.

#### `services.*.http_filter`
Specifies the HTTP filtering configuration for the given service. Maps directly to [`feature.network.incoming.http_filter`](https://metalbear.com/mirrord/docs/config/options#feature-network-incoming)

#### `services.*.ignore_ports` 
List of ports that should be ignored in incoming traffic. Maps directly to [`feature.network.incoming.ignore_ports`](https://metalbear.com/mirrord/docs/config/options#feature-network-incoming)

#### `services.*.messages` 
Specifies queue splitting configuration (Not supported as of now).

#### `services.*.run` 
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

### `-m`, `--mode`
Specifies the network mode for all defined services, overriding `default_mode`. Available options:
- `split`:

Defaults to `split`. For more details, see `services.*.defualt_mode`.

### `--key`
Allows specifying a custom session key. When not supplied, the OS username is used.
