---
title: Environment Variables
description: Control which environment variables are loaded from the remote pod
draft: false
toc: true
tags: ["open source", "team", "enterprise"]
---

By default, mirrord imports the target pod's environment variables into your local process. Use this when your local code needs the same database URLs, API keys, or service discovery values as the cluster.

## Quickstart

No config needed. Running `mirrord exec -t pod/my-pod -- node server.js` already loads the remote env.

To verify, print a known variable from the pod:

```bash
mirrord exec -t pod/my-pod -- env | grep DATABASE_URL
```

## Common patterns

**Only specific variables**

```json
{ "feature": { "env": { "include": "DATABASE_URL;REDIS_URL" } } }
```

**Block certain variables**

```json
{ "feature": { "env": { "exclude": "SECRET_*;LEGACY_*" } } }
```

(`include` and `exclude` are mutually exclusive — pick one.)

**Override a value locally**

```json
{ "feature": { "env": { "override": { "REGION": "us-east-1" } } } }
```

**Merge in a local `.env`**

```json
{ "feature": { "env": { "env_file": "./.env.local" } } }
```

**Remove a variable that confuses your tooling**

```json
{ "feature": { "env": { "unset": ["AWS_PROFILE"] } } }
```

This is the right fix when something like `AWS_PROFILE` from your shell makes the SDK ignore the remote credentials. `unset` is also the only way to strip variables when running Go (Go can't modify its env after start).

## Gotchas

- mirrord always strips toolchain variables (`PATH`, `HOME`, `JAVA_HOME`, `GOPATH`, `PYTHONPATH`, `CLASSPATH`, etc.) so your local interpreter doesn't break. You can't get these from the remote pod — they're considered local. See the [reference](../reference/env.md#always-excluded-variables) for the full list.
- Variables set with `os.setenv()` (or equivalent) inside the running pod **won't appear** — mirrord reads `/proc/<pid>/environ`, which is fixed at process start.

For mechanism, full schema, post-fetch transformation order, and the complete excluded list, see the [environment variables reference](../reference/env.md).
