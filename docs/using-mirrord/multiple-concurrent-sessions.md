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
`mirrord up` allows creating and running multiple related mirrord sessions based on configuration defined in a single file — think `docker compose` but for mirrord. This can be useful for cases when you need to debug multiple related microservices and would like to manage their lifecycle together.

# Getting started
Start by creating a `mirrord-up.yaml`:
```yaml
defaults:
  accept_invalid_certificates: true
  operator: true
  telemetry: true

services:
  user-auth-service:
    target:
      path: deployment/test-app
    env:
      override:
        NODE_ENV: "development"
        AUTH_SERVICE_URL: "http://localhost:8080"
        TOKEN_EXPIRY: "3600"
    mode: split
    http_filter:
      header_filter: "x-session: local"

    ignore_ports: [9090, 9091, 15090]
    run: # used for execution
      command: ["python", "-m", "http.server"]

  stage-user-dashboard-app:
    target:
      path: pod/nginx
    env:
      override:
        APP_NAME: "dashboard-app-123"
        NODE_ENV: "development"

    mode: split
    # http_filter: When not provided, 
    ignore_ports: [9091, 15090]
    run: 
      command: ["bash", "-c", "cd / && python -m http.server 9090"]
```

This file is the single source of configuration for all running sessions. Each entry in `services` defines a mirrord session that will run as part of the `mirrord up` session. The configuration for each service is generated based on the corresponding entry, as well as `defaults` (this applies to all services).

Now, in the same directory, run `mirrord up`. This will start all defined sessions, and they will run in parallel. The `mirrord up` session will be stopped once when interrupted (`ctrl-c`) or one of the running mirrord sessions shuts down.

# Configuration

## Config file (`mirrord-up.yaml`)

### `defaults`
Common configuration options, applied to all defined services. Currently 3 options are supported:
- `accept_invalid_certificates`
- `operator`
- `telemetry`

All 3 map directly to their `mirrord.json` counterparts.

### `services`
A map from service ids to a `ServiceConfig`. Each entry in this map defines and configures a mirrord process that will be run as part of the session.

#### `services.*.target`
Specifies the target of the session. Has 2 fields: `path` and `namespace`, which map directly to their `mirrord.json` counterparts.

#### `services.*.env`
Specifies the environment variable configuration for the given service. Maps directly (1:1) to `feature.env`

#### `services.*.mode`
So far, only `split` is supported. The incoming mode is set to `steal` with http filter.
User-provided filter is used if provided, otherwise defaulting to `baggage: .*mirrord-session={key}.*`.

#### `services.*.http_filter`
Specifies the HTTP filtering configuration for the given service. Maps directly to `feature.network.incoming.http_filter`

#### `services.*.ignore_ports` 
List of ports that should be ignored in incoming traffic. Maps directly to `feature.network.incoming.ignore_ports`

#### `services.*.messages` 
Specifies queue splitting configuration (Not supported as of now).

#### `services.*.run` 
Specifies the command that should be run with mirrord. Has 2 fields:
- `command`: Array of strings containing the command to be run and its CLI arguments.
- `type`: can be either `exec` or `container`, defaults to `exec`. Specifies how mirrord should be run (i.e. with `mirrord exec` or `mirrord container`)


## CLI args

### `-f`, `--config-file`
Allows specifying a different config file, e.g. `mirrord up -f mirrord-up2.yaml`

### `--key`
Allows specifying a custom session key. When not supplied, the OS username is used.
