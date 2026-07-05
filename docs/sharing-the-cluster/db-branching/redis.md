---
title: Redis
description: Spin up an isolated Redis branch with mirrord - in the cluster or on your own machine
tags:
  - team
  - enterprise
---

This page covers DB branching for Redis. For the general concepts, the full list of config fields, and how a session behaves, see the [DB Branching overview](../db-branching.md).

Redis is the only engine that supports both branch locations:
* `"location": "remote"` (default) provisions a branch pod in the cluster, like the other engines.
* `"location": "local"` spawns a Redis instance on your own machine.

{% hint style="info" %}
Remote Redis branching requires operator `3.168.0`, mirrord CLI `3.217.0`, and operator Helm chart `3.168.0` with the `operator.redisBranching` value set to `true`.
Local Redis branching only requires mirrord CLI `3.180.0` - there are no operator or chart version requirements, since a local branch runs entirely on your machine.
{% endhint %}

### Remote Branches

```json
{
  "feature": {
    "db_branches": [
      {
        "id": "cache-redis",
        "type": "redis",
        "version": "7.2",
        "name": "0",
        "connection": {
          "url": "REDIS_URL"
        },
        "copy": {
          "mode": "empty"
        }
      }
    ]
  }
}
```

The `connection` field describes how mirrord locates the source Redis connection details - a full connection URL or individual parameters (host, port, user, password, database). See [Connection Modes](connection.md) for all supported sources, including Kubernetes Secrets, Google Secret Manager, literal values, and composite environment variables.

#### Database Index

For Redis, the `name` field is the database **index** Redis uses to select a logical database rather than a name, so it must be a valid non-negative number. If omitted, it defaults to index `0`.

#### Copy Modes

Redis copy modes apply only to **remote** Redis branches. A local Redis branch always starts empty. Redis supports two modes:

| Mode | What gets cloned |
| --- | --- |
| `"empty"` (default) | Nothing - a fresh, empty Redis instance |
| `"all"` | Keys from the source Redis instance, optionally filtered with `patterns` |

By default `"all"` copies the entire keyspace. To copy only a subset, add `patterns` - a list of [`SCAN MATCH`](https://redis.io/docs/latest/commands/scan/) glob patterns. Only keys matching at least one pattern are copied.

```json
{
  "copy": {
    "mode": "all",
    "patterns": ["user:*", "session:*"]
  }
}
```

In this example, only keys prefixed with `user:` or `session:` are copied; everything else is left out of the branch.

{% hint style="info" %}
Redis has no schema, so there is no `"schema"` copy mode - only `"empty"` and `"all"` are available. Filtering is done by key pattern rather than by SQL query.
{% endhint %}

### Local Redis

mirrord can spin up a local Redis instance, automatically redirecting your app's Redis traffic to it.

```json
{
  "feature": {
    "db_branches": [
      {
        "type": "redis",
        "location": "local",                     // "remote" (default) or "local"
        "connection": {
          // Use "host" if your app reads Redis as host:port (e.g. REDIS_ADDR=redis:6379)
          // Use "url" if your app reads a full Redis URL (e.g. REDIS_URL=redis://user:pass@redis:6379/0)
          "host": { "type": "env", "variable": "REDIS_ADDR" }
        },
        "local": {                               // Optional runtime config
          "port": 6379,                          // Custom port (default: 6379)
          "runtime": "container",                // "container" (default), "redis_server", or "auto"
          "container_runtime": "docker"          // "docker" (default), "podman", or "nerdctl"
        }
      }
    ]
  }
}
```

mirrord overrides the env variable to point to `localhost:<port>` and cleans up the Redis instance on exit.

Notes on local branches:
* A local branch always starts empty - copy modes do not apply.
* The `id` field is not used for local Redis instances and has no effect on database selection or reuse.
* `local.port`: Sessions that use the same port share a single local Redis database. When a new session starts on that port, it creates a new database instance that replaces the existing one.
