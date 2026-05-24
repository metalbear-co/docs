---
title: Targets
date: 2023-05-08T05:50:11.000Z
lastmod: 2023-05-08T05:50:11.000Z
draft: false
images: []
menu:
  docs:
    parent: reference
weight: 130
toc: true
tags:
  - open source
  - team
  - enterprise
description: Possible targets for mirrord and how to set them
---

A **target** is the Kubernetes resource whose context the local process will impersonate: its network namespace (for incoming/outgoing traffic and DNS), its filesystem (for fs operations), and its environment variables. When a target is specified, the [mirrord-agent](architecture.md#mirrord-agent) runs on the same node as the target pod and joins its namespaces.

For the targetless mode, see [Targetless](../using-mirrord/targetless.md). For the `copy_target` feature, see [Copy Target](../using-mirrord/copy-target.md).

## Supported target kinds

| Kind | OSS | Teams | Notes |
|---|---|---|---|
| `pod` | ✅ | ✅ | The leaf resource. All other kinds resolve to pods. |
| `deployment` | ✅ | ✅ | In OSS: random replica. In Teams: all replicas. |
| `rollout` | ✅ | ✅ | Argo Rollouts. Same replica behavior as deployment. |
| `statefulset` | none | ✅ | Same replica behavior as deployment. |
| `replicaset` | none | ✅ | Same replica behavior as deployment. |
| `service` | none | ✅ | Resolved to backing pods via the Service's selector. |
| `job` | none | ✅ | Requires [`copy_target`](../using-mirrord/copy-target.md). |
| `cronjob` | none | ✅ | Requires [`copy_target`](../using-mirrord/copy-target.md). |
| `targetless` | ✅ | ✅ | No impersonation. See [Targetless](../using-mirrord/targetless.md). |

### Replica handling

When a workload has multiple replicas:

- **OSS** picks one random pod replica for the duration of the session.
- **Teams** binds to all replicas. Incoming traffic from any replica can match your filter, and the agent runs alongside one of them but knows about the rest. This is what enables sharing.

### Container selection

If you don't name a container, mirrord picks the **first container in the pod spec**, skipping containers that look like sidecars/service-mesh proxies (Istio, Linkerd, etc.).

To pin a specific container, append `/container/<name>` to the target path.

## Resource path syntax

```
<kind>/<name>[/container/<container-name>]
```

Examples:

```
pod/api-server-6f9b8c7d-x2mzq
pod/api-server-6f9b8c7d-x2mzq/container/main
deployment/api
deploy/api                                  # short form
rollout/api/container/main
statefulset/postgres-primary
service/checkout
job/nightly-export                          # requires copy_target
cronjob/billing-rollup/container/runner     # requires copy_target
targetless
```

All resource kinds accept both their long and Kubernetes-short forms (`deployment`/`deploy`, `statefulset`/`sts`, etc.) consistent with `kubectl`.

## Specifying a target

There are four ways to specify a target. **Precedence**, highest to lowest:

1. CLI argument (`-t`, `-n`)
2. Environment variable (`MIRRORD_IMPERSONATED_TARGET`, `MIRRORD_TARGET_NAMESPACE`)
3. Configuration file (`target.path`, `target.namespace`)
4. IDE dialog prompt (only if none of the above are set)

### Configuration file

Short form:

```json
{ "target": "pod/lolz/container/main" }
```

Full form (when you need a namespace):

```json
{
  "target": {
    "path": "pod/lolz/container/main",
    "namespace": "lolzspace"
  }
}
```

Targetless with a namespace (for remote networking from a specific namespace):

```json
{
  "target": {
    "path": "targetless",
    "namespace": "bear-namespace"
  }
}
```

The path field maps to [`target.path`](https://metalbear.com/mirrord/docs/config#target.path); the namespace field maps to [`target.namespace`](https://metalbear.com/mirrord/docs/config#target.namespace). When omitted, the namespace defaults to the one in your current `kubectl` context.

### CLI

```bash
mirrord exec -t deploy/api -n production -- my-app
```

### Environment variables

```bash
export MIRRORD_IMPERSONATED_TARGET=deploy/api
export MIRRORD_TARGET_NAMESPACE=production
mirrord exec -- my-app
```

### IDE dialog

If none of the above is set, the VS Code and JetBrains extensions show a target picker. To skip the dialog and run targetless, set the config explicitly to `"target": "targetless"`. Leaving `target` unset triggers the dialog.

## Namespaces

| What | Set via | Default |
|---|---|---|
| Target namespace (where the target lives) | `target.namespace`, `-n`, `MIRRORD_TARGET_NAMESPACE` | The current `kubectl` context namespace |
| Agent namespace (where the agent pod runs) | [`agent.namespace`](https://metalbear.com/mirrord/docs/config#agent.namespace), `-a`, `MIRRORD_AGENT_NAMESPACE` | The target's namespace |

These are independent. You can target a pod in `app-prod` while running the agent in `mirrord-agents` if your cluster RBAC is set up that way.

## Related

- [`target` config reference](https://metalbear.com/mirrord/docs/config#target): full schema
- [Targetless](../using-mirrord/targetless.md): running without a target
- [Copy Target](../using-mirrord/copy-target.md): creating a copy of the target pod (required for `job`/`cronjob` targeting)
- [Sharing the cluster](../sharing-the-cluster/overview.md): how Teams enables multiple users to target the same workload
