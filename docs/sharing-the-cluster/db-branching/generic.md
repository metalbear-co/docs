---
title: Generic
description: Branch any stateful service with mirrord by supplying your own container image
tags:
  - alpha
  - team
  - enterprise
---

This page covers generic DB branching - for databases, caches, and other stateful services that mirrord has no built-in engine for (InfluxDB, Valkey, an internal service, and so on). For the general concepts, the full list of config fields, and how a session behaves, see the [DB Branching overview](../db-branching.md).

A generic branch runs the container image you supply and always starts **empty**: there are no copy modes, no IAM authentication, and a single redirected port. It is the fallback that unblocks you when no first-class engine exists - engines with built-in support offer copy modes, schema handling, and better errors, so prefer them when available.

{% hint style="info" %}
Generic branching requires operator `<OPERATOR_VERSION>`, mirrord CLI `<CLI_VERSION>`, and operator Helm chart `<CHART_VERSION>` with the `operator.genericBranching` value set to `true`.

If the operator doesn't support generic branching (older version, or the Helm value is off), the session fails immediately with a clear "operator does not support generic db branching" error rather than timing out.
{% endhint %}

## How It Works

Because mirrord doesn't know the engine, you declare the connection parameters your service needs under `connection.params` - the fixed slots (`host`, `port`, `user`, `password`, `database`) plus **any custom key** (for example `token`, `org`, `vhost`). The operator resolves each declared parameter from the target pod and injects it into the branch container as an env var named `MIRRORD_PARAM_<NAME>` (a Secret-backed parameter arrives as a `secretKeyRef` - the operator never reads its value).

You reference these in `command`, `args`, and `env` using Kubernetes' native `$(VAR)` syntax, so the branch bootstraps itself with the **same values the app already uses**. mirrord then only rewrites the app's `host`/`port` vars to point at the branch - the app's credential vars stay untouched, and they're valid against the branch because it was bootstrapped with those same values.

Two built-in variables are always available alongside the parameters: `MIRRORD_BRANCH_ID`, and `MIRRORD_DATABASE_NAME` when the shared `name` field is set. Use `$$(...)` for a literal `$(...)`.

## Basic Configuration

| Field | Description |
| --- | --- |
| `image` | *(Required)* Full image reference for the branch container, including the tag. The shared `version` field is not allowed - the tag lives here. |
| `port` | *(Required)* The port the branched service listens on. Used for the default readiness probe and as the port the app is redirected to. |
| `command` / `args` | *(Optional)* Entrypoint override for the branch container. Values may reference `$(MIRRORD_PARAM_<NAME>)`. |
| `env` | *(Optional)* Extra environment variables for the branch container, with the same `$(VAR)` references. Keys must not start with `MIRRORD_PARAM_`. |
| `readiness` | *(Optional)* Readiness check for the branch container. Defaults to a TCP probe on `port`. See [Readiness](#readiness). |

How you feed the params into the branch depends entirely on how *your image* bootstraps itself - some images take startup flags (use `args`), others read well-known env vars on first boot (use `env`). The two examples below show one of each.

## Example: Valkey (bootstrap via `args`)

The app reads a composite `VALKEY_ADDR=valkey-main:6379` env var and a `VALKEY_PASSWORD` that comes from a Kubernetes Secret. Valkey (like Redis) is configured through command-line flags, so the branch passes the app's real password to `--requirepass`:

```json
{
  "feature": {
    "db_branches": [
      {
        "type": "generic",
        "id": "my-valkey-branch",
        "ttl_secs": 600,
        "image": "valkey/valkey:8-alpine",
        "port": 6379,
        "connection": {
          "params": {
            "host": { "env_var_name": "VALKEY_ADDR", "value_pattern": "^(?P<host>[^:]+):" },
            "port": { "env_var_name": "VALKEY_ADDR", "value_pattern": ":(?P<port>[0-9]+)$" },
            "password": "VALKEY_PASSWORD"
          }
        },
        "args": ["valkey-server", "--requirepass", "$(MIRRORD_PARAM_PASSWORD)"]
      }
    ]
  }
}
```

When the session starts:

1. The operator resolves `VALKEY_PASSWORD` from the target pod - since the pod reads it from a Secret, it arrives on the branch container as a `secretKeyRef` under the name `MIRRORD_PARAM_PASSWORD`. The kubelet expands `$(MIRRORD_PARAM_PASSWORD)` in the args when the container starts, so the branch requires the **same password the app already uses** - and the secret value never appears in the pod spec.
2. The default TCP probe on `6379` passes and the branch turns Ready.
3. Locally, only the host and port *fragments* of `VALKEY_ADDR` are rewritten in place (the `value_pattern` captures), so the app still sees the `host:port` shape it expects - now pointing at the branch. `VALKEY_PASSWORD` is untouched and just works.

## Example: InfluxDB (bootstrap via `env`)

The app reads `INFLUXDB_URL` plus token/org/bucket vars. InfluxDB's image isn't configured through flags - it bootstraps through its own **first-boot setup mechanism**: when the official `influxdb` image starts with `DOCKER_INFLUXDB_INIT_MODE=setup`, its entrypoint creates the initial admin user, organization, bucket, and API token from the other `DOCKER_INFLUXDB_INIT_*` env vars before serving traffic.

{% hint style="info" %}
The `DOCKER_INFLUXDB_INIT_*` names are **InfluxDB's** convention, not mirrord's - they're documented on the [influxdb Docker image](https://hub.docker.com/_/influxdb). mirrord's job is only to fill them: the three `$(MIRRORD_PARAM_*)` references carry the app's real token/org/bucket into the setup, while `MODE`/`USERNAME`/`PASSWORD` are plain literals (a throwaway admin login the app never uses). Check your own image's docs for its equivalent bootstrap knobs.
{% endhint %}

```json
{
  "feature": {
    "db_branches": [
      {
        "type": "generic",
        "id": "my-influx-branch",
        "ttl_secs": 600,
        "image": "docker.io/library/influxdb:2.7",
        "port": 8086,
        "connection": {
          "params": {
            "host": { "env_var_name": "INFLUXDB_URL", "value_pattern": "https?://(?P<host>[^:/]+)" },
            "port": { "env_var_name": "INFLUXDB_URL", "value_pattern": ":(?P<port>[0-9]+)" },
            "token": { "secret": "influx-creds", "key": "token" },
            "org": "INFLUXDB_ORG",
            "bucket": "INFLUXDB_BUCKET"
          }
        },
        "env": {
          "DOCKER_INFLUXDB_INIT_MODE": "setup",
          "DOCKER_INFLUXDB_INIT_USERNAME": "admin",
          "DOCKER_INFLUXDB_INIT_PASSWORD": "mirrord-branch",
          "DOCKER_INFLUXDB_INIT_ADMIN_TOKEN": "$(MIRRORD_PARAM_TOKEN)",
          "DOCKER_INFLUXDB_INIT_ORG": "$(MIRRORD_PARAM_ORG)",
          "DOCKER_INFLUXDB_INIT_BUCKET": "$(MIRRORD_PARAM_BUCKET)"
        },
        "readiness": { "type": "http_get", "path": "/health" }
      }
    ]
  }
}
```

When the session starts:

1. The operator creates (or reuses, by `id`) a branch pod running `influxdb:2.7`, with the setup env filled from the params resolved off the target pod: `token` straight from the `influx-creds` Kubernetes Secret (as a `secretKeyRef`), `org` and `bucket` from the pod's env vars. The image's setup mode then creates that same org, bucket, and admin token on first start.
2. The `http_get` probe on `/health` passes once setup finished and the server is up - only then does the branch turn Ready.
3. Locally, the host/port fragments of `INFLUXDB_URL` are rewritten to point at the branch (the URL shape and scheme survive). `INFLUXDB_TOKEN`, `INFLUXDB_ORG`, and `INFLUXDB_BUCKET` are untouched - and they're valid against the branch, because it was bootstrapped with those exact values.

## Readiness

The branch only turns Ready - and your session only proceeds - once the branch container's readiness probe passes. Because mirrord doesn't know your service, you can pick the probe that actually proves it's up:

| Type | Config | Ready when |
| --- | --- | --- |
| `tcp` *(default)* | `{ "type": "tcp" }` | The branch `port` accepts a TCP connection. No config needed - this is what you get when `readiness` is omitted. |
| `http_get` | `{ "type": "http_get", "path": "/health", "port": 8086 }` | An HTTP GET on `path` returns a 2xx/3xx. `port` defaults to the branch `port`. |
| `exec` | `{ "type": "exec", "command": ["valkey-cli", "ping"] }` | The command, run *inside* the branch container, exits 0. |

The probe runs every 2 seconds (first check after 3 seconds). The first success marks the branch Ready; if it never succeeds, the session fails once [`creation_timeout_secs`](../db-branching.md#key-fields) elapses.

Prefer a probe that captures "actually usable", not just "process started": a plain TCP probe can pass while an image is still initializing. The InfluxDB example uses `http_get` on `/health` precisely so the branch isn't Ready until the setup bootstrap has completed - with only the TCP default, the app could connect before its org and token exist.

## Connection

The `connection` must use **params mode**. URL mode is rejected for generic branches, because rewriting a whole URL requires knowing the engine's scheme and credential layout - for URL-shaped env vars, extract `host` and `port` with [`value_pattern`](connection.md#composite-environment-variables) as in the example above. All the other sources from [Connection Modes](connection.md) work (Kubernetes Secrets, literal values, multiple sources), except `gcp_secret_manager`, which is not supported for generic branches.

Declaring neither `host` nor `port` is allowed - the branch is still created and bootstrapped, but nothing is redirected (mirrord warns about this at config load).

## What Generic Branches Don't Do

* **No data or schema copy** - branches always start empty. If your service is useless empty, it needs a first-class engine.
* **No IAM authentication.**
* **A single redirected port** - multi-port and cluster-shaped services (services that advertise their own addresses to clients) are out of scope.

If you find yourself writing a generic config for a common engine, that's a strong signal for us to build first-class support for it - let us know!

## Slow Images and Timeouts

Arbitrary images often pull and boot slower than the built-in engines. If branch creation times out, raise [`creation_timeout_secs`](../db-branching.md#key-fields). A bad image reference does not burn the whole timeout: the operator detects `ImagePullBackOff`-style failures and fails the branch immediately with the kubelet's message.

## Security

* Generic branching is **off by default** (`operator.genericBranching` in the Helm chart) because it lets users who can create branches run arbitrary container images as branch pods. Enabling it is an explicit admin decision per cluster.
* Admins can restrict which images users may run with an `allowedImages` glob list in the generic branch config (Helm `genericBranchConfig`). When the field is absent, all images are allowed. A branch using an image outside the list fails immediately with an error naming the image - it does not wait for the creation timeout:

```yaml
operator:
  genericBranching: true
  genericBranchConfig:
    dbPod:
      allowedImages:
        - "docker.io/library/*"
        - "ghcr.io/my-org/*"
```

* Generic branch pods run under the namespace **default service account**, never the target's (which would let a user-chosen image impersonate the workload's cloud identity) and never the operator's. The service account token is **not mounted** into the branch pod at all - the container has zero Kubernetes API access even in clusters where roles were bound to the default SA. Branch pods are plain unprivileged pods, so cluster admission policies (PSA, OPA/Kyverno) apply as usual.
* Values written directly into `args` are visible in the pod spec to anyone with pod-read access. Reference secrets via `$(MIRRORD_PARAM_*)` instead of inlining them - the `secretKeyRef` mechanism exists precisely so secret values never appear in the pod spec.
* For images in private registries, set `imagePullSecrets` in the generic branch config, as with the other engines.
