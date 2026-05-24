---
title: Architecture
date: 2020-11-16T12:59:39.000Z
lastmod: 2020-11-16T12:59:39.000Z
draft: false
images: []
menu:
  docs:
    parent: overview
weight: 120
toc: true
tags:
  - open source
  - team
  - enterprise
description: mirrord's architecture
---

mirrord runs the user's local process unchanged, but rewires its syscalls so file, network, DNS, and environment operations happen in the context of a remote Kubernetes target. This page describes the components involved, how they connect, and what happens during a session.

![mirrord - Architecture](architecture/architecture.svg)

## Components

```
┌────────────────────────────────────────────────────────────────────────┐
│ LOCAL MACHINE                                                          │
│                                                                        │
│  ┌──────────────────────┐         ┌──────────────────────┐             │
│  │ User application     │         │ mirrord CLI          │             │
│  │ ┌──────────────────┐ │         │ - resolves target    │             │
│  │ │  mirrord-layer   │◄┼─────────┤ - starts intproxy    │             │
│  │ │  (LD_PRELOAD /   │ │         │ - sets env + injects │             │
│  │ │   DYLD_INSERT)   │ │         │   layer              │             │
│  │ └────────┬─────────┘ │         └──────────────────────┘             │
│  └──────────┼───────────┘                                              │
│             │ local protocol (TCP / Unix)                              │
│             │                                                          │
│  ┌──────────▼───────────┐                                              │
│  │  mirrord-intproxy    │  Routes messages between layer(s) and agent  │
│  └──────────┬───────────┘                                              │
└─────────────┼──────────────────────────────────────────────────────────┘
              │ mirrord-protocol  (over port-forward
              │                    or operator-managed tunnel)
┌─────────────┼──────────────────────────────────────────────────────────┐
│ CLUSTER     │                                                          │
│  ┌──────────▼───────────┐                                              │
│  │    mirrord-agent     │  Joins target's namespaces, performs         │
│  │  (target node, in    │  remote fs / network / DNS / env             │
│  │   target's netns +   │  operations on the target's behalf           │
│  │   mountns)           │                                              │
│  └──────────────────────┘                                              │
│                                                                        │
│  ┌──────────────────────┐                                              │
│  │  mirrord-operator    │  (Teams only) Manages targets, sessions,     │
│  │   (cluster-wide)     │  policies, queue-splitting, db-branching     │
│  └──────────────────────┘                                              │
└────────────────────────────────────────────────────────────────────────┘
```

### `mirrord-cli`

The user-facing binary. Resolves the target via the Kubernetes API, decides whether to connect through the operator or directly (`operator: false`), launches the intproxy, sets up environment variables (`LD_PRELOAD`/`DYLD_INSERT_LIBRARIES` for the layer, intproxy address), and execs the user's command. Also fronts the IDE extensions — VS Code and JetBrains plugins call into the same CLI.

### `mirrord-layer` / `mirrord-layer-win`

A dynamic library loaded into the user process. On Linux it's a `.so` injected via `LD_PRELOAD`; on macOS a `.dylib` via `DYLD_INSERT_LIBRARIES`; on Windows a `.dll` loaded into a frozen process before execution begins.

The layer hooks libc functions (or the Windows-equivalent low-level APIs) for file, socket, DNS, and exec operations. Each intercepted call is either bypassed to the original implementation (for paths that should stay local) or converted into a protocol request and sent to the intproxy.

### `mirrord-intproxy`

A small local process that sits between the layer(s) and the agent. It exists because:

- The agent connection (port-forward or operator tunnel) is expensive to open per-process. With intproxy, when a target binary forks or execs another mirrord-aware process, the new layer connects to the existing intproxy instead of opening a new agent connection.
- The layer runs inside the user process where it can't do things like long-running async I/O safely. intproxy owns the agent connection and handles the bookkeeping (request/response matching, reconnects, file-handle state, port subscriptions).

intproxy is structured as a set of feature-specific proxies (files, incoming, outgoing, DNS, env) that each manage their own state and route messages to/from the agent.

### `mirrord-agent`

A Rust binary packaged as a container image, run as a Kubernetes pod scheduled on the same node as the target. It joins the target pod's network namespace and mount namespace (`CAP_SYS_ADMIN`) and reads its PID namespace (`CAP_SYS_PTRACE`), giving the agent the same view of networking, filesystem, and process state the target container has.

The agent does the actual work: installing iptables redirections for steal subscriptions, opening outgoing sockets, resolving DNS via the pod's resolver, reading `/proc/<target-pid>/environ`, and accessing the container's filesystem via `/proc/<target-pid>/root`.

Required Linux capabilities:

| Capability | Why |
|---|---|
| `CAP_NET_ADMIN`, `CAP_NET_RAW` | Modify routing tables, set up traffic mirroring/stealing |
| `CAP_SYS_PTRACE` | Read the target pod's environment (`/proc/<pid>/environ`) |
| `CAP_SYS_ADMIN` | Join the target pod's network and mount namespaces |

You can drop any subset via [`agent.disabled_capabilities`](https://metalbear.com/mirrord/docs/config#agent.disabled_capabilities), which will disable the corresponding features.

The agent is **not** privileged — it does not run as root in the cluster sense — and only operates on the targets the user is authorized to access (via Kubernetes RBAC or, for Teams, the operator's policy layer).

### `mirrord-protocol`

Defines the messages exchanged between layer ↔ intproxy ↔ agent: `ClientMessage` (sent by the client side toward the agent) and `DaemonMessage` (sent by the agent back). Serialized with bincode over a TCP connection.

Between the layer and the intproxy there's a separate, lighter local protocol (`mirrord-intproxy-protocol`) with `LayerToProxyMessage` / `ProxyToLayerMessage`.

Backward compatibility is mandatory — the agent, layer, and intproxy ship and upgrade independently, so older clients must keep working against newer agents and vice versa within the supported version window.

### `mirrord-operator` (Teams)

A cluster-wide controller that fronts the agent for Teams users. The operator:

- Resolves targets and authorizes them against the policy layer
- Allows multiple users to attach to the same workload (and coordinates concurrent steal locks via `on_concurrent_steal`)
- Provides session sharing primitives for [queue splitting](../sharing-the-cluster/queue-splitting.md), [DB branching](../sharing-the-cluster/db-branching.md), and [profiles](../sharing-the-cluster/profiles.md)
- Exposes agents over a single tunnel rather than per-user port-forwards
- Records sessions for audit and visibility ([admin dashboard](../managing-mirrord/admin-dashboard.md))

In OSS, intproxy talks directly to the agent via `kubectl port-forward`. With the operator, intproxy talks to the operator, which proxies to the agent.

### `mirrord-external-proxy` (container mode)

For [`mirrord container`](../using-mirrord/local-container.md) and other scenarios where the user process runs inside a separate container/VM, an additional process — the external proxy — sits between the container boundary and the intproxy. The intproxy runs in the same network namespace as the user process; the external proxy stays on the host and forwards messages between intproxy and agent. Most users never interact with it directly.

## Lifecycle of a `mirrord exec` session

1. **CLI invocation** — `mirrord exec -t <target> -- <command>`. CLI loads config, validates it, and resolves the target via the Kubernetes API.
2. **Agent setup**:
   - **OSS path**: CLI creates the agent pod (a `Job`), waits for it to be ready, sets up a port-forward.
   - **Teams path**: CLI authenticates with the operator, opens a session, and gets back a connection.
3. **intproxy start**: CLI spawns intproxy as a local subprocess. intproxy connects to the agent (port-forward or operator tunnel).
4. **Layer injection**: CLI sets `LD_PRELOAD`/`DYLD_INSERT_LIBRARIES`, intproxy address, and config-derived env vars, then execs the user command. The layer initializes immediately on process start.
5. **Initial fetch**: The layer fetches remote env vars from the agent (synchronous, before the user code runs) and sets them on the process.
6. **Runtime operations**: Each hooked syscall becomes a `ClientMessage`. intproxy routes it to the agent, the agent executes, and the response (`DaemonMessage`) flows back. The layer translates the response into what the syscall's caller expects.
7. **Teardown**: When the user process exits, the layer disconnects, intproxy shuts down, and (OSS) the agent pod is deleted, or (Teams) the operator closes the session.

## IDE extensions

The [VS Code extension](../installing-mirrord/vscode.md) and [JetBrains plugin](../installing-mirrord/intellij.md) wrap the same CLI mechanism. They surface a target-picker dialog (when no target is in the config or env), set up the same `LD_PRELOAD`/`DYLD_INSERT_LIBRARIES` injection, and start the debugged process under that environment. From mirrord's perspective there's no difference between a CLI exec and an IDE-launched debug session — the IDE is just a different way of invoking the CLI machinery.

## Related

- [Targets](targets.md) — what kinds of resources can be impersonated
- [Network Traffic](traffic.md) — how incoming, outgoing, and DNS routing work
- [File Operations](fileops.md) — how fs syscalls are intercepted and routed
- [Environment Variables](env.md) — how the env fetch works
- [Sharing the cluster](../sharing-the-cluster/overview.md) — what the operator unlocks
