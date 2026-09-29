---
title: Topology
description: See which services your mirrord sessions call, drawn as a map of the cluster
tags:
  - alpha
  - team
  - enterprise
---

# Topology

The **Topology** tab in the dashboard draws the services in your cluster and the connections between them. The map is built from mirrord sessions: when a session opens a connection to a Kubernetes Service, or receives one, the operator records it. There is nothing to declare up front, so the map covers what your developers actually touched, including dependencies nobody wrote down.

## Requirements

- Operator chart 3.211.0 or newer.
- A dashboard, set up either way: [Cloud Setup](cloud.md) or [License Server Setup](license-server.md). With a license server, run the license server from the same release or newer.
- On the cloud dashboard, identity sharing turned on for the operator's API key. Service names only leave the cluster with identity, so with sharing off the tab stays empty.

## Turn it on

Topology is off by default. Set it in the operator's Helm values and upgrade:

```yaml
# values.yaml
operator:
  topology: true
```

```bash
helm upgrade mirrord-operator metalbear/mirrord-operator -f values.yaml
```

With this on, the operator watches every Service and EndpointSlice in the cluster so it can tell which Service an address belongs to. The chart adds read access to EndpointSlices to the operator's ClusterRole for this.

Then run a few sessions. A session reports its connections when it ends, so a new edge shows up on the map shortly after the session that made it stops.

## What gets recorded

- **Outgoing**: the local process connects through mirrord to an address in the cluster, the connection succeeds, and the address belongs to a Service (its cluster IP, or a pod behind it). The edge runs from the session's target to that Service.
- **Incoming**: a request reaches the session's target from a pod behind a Service. The edge runs from the caller to the target. The local process has to be listening on the target's port for mirrord to pass the request through.
- **Preview environments**: connections a preview pod opens or accepts. The preview gets its own node, labelled with its key.

Each edge keeps the number of sessions and users that produced it and when it was last seen. The operator records the address and port only, never the traffic itself.

## Reading the map

Services are grouped by namespace. On a large cluster the map opens with every namespace folded; click one to open it, or use **Expand all**.

Nodes are colored by category:

| Category | How it's decided |
| --- | --- |
| **Entry point** | Discovered, and only ever seen calling other services |
| **Service** | A workload in your cluster |
| **Data store** | Reached on a well-known database port (Postgres, MySQL, Redis, MongoDB, and so on) |
| **Queue** | Reached on a well-known broker port (Kafka, RabbitMQ, NATS, and so on) |
| **Infrastructure** | Reached on a well-known infrastructure port |
| **Preview env** | A preview environment |

Categories come from ports and from which end of a connection a service was on. Service names are never used to guess them, so a Postgres served on a custom port shows up as a plain **Service**. Click a chip in the legend to hide that category.

A node marked **Discovered** was only ever seen as the other end of a connection. No session targeted it, so its counts are summed from the edges pointing at it.

Other controls:

- **Find a service** searches by name. Press `/` to jump to it.
- **Busiest paths** keeps the busiest quarter of the edges lit and dims the rest.
- Click a node to open its details: sessions, users, last seen, and its incoming and outgoing connections. **Copy link** copies a URL that opens the map with that node selected.
- **List** shows the same connections as a table of caller, callee, sessions, users and last seen.
- **Export as PNG** saves the map as an image.
- Press `f` to fit the map to the window and `Esc` to clear the focus.

The time range selector applies here too. A connection only appears if a session made it inside the selected range.

## Why a connection is missing

The map only knows about traffic that went through a mirrord session. If two services talk to each other but no session was part of that conversation, there's no edge. For example, `order-service` calling `payment-service` shows up only when:

- a session targeting `order-service` made that call from the local process, or
- a session targeting `payment-service` received the call from `order-service`, with the local process listening on the port it arrived on.

Some other cases that leave gaps:

- The address doesn't belong to a Service: an external host, or a pod no Service selects.
- The connection failed. Only successful connections count.
- The connection used UDP. Only TCP is recorded.
- The session is still running. Edges are reported when the session ends.
- On the cloud dashboard, the session ran with identity sharing off.

To fill in the map, run sessions against more of your services and exercise the flows you care about while they run.
