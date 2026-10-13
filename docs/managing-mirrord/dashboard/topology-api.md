---
title: Topology API
description: Pull the service map behind the Topology tab as JSON, to feed a developer portal or your own tooling
tags:
  - alpha
  - team
  - enterprise
---

# Topology API

mirrord sessions map your cluster as your team works: every connection a session makes or receives is recorded, so you get a dependency map built from real traffic without declaring anything. The [Topology](topology.md) tab draws that map, and the same data is available as JSON, so you can feed it into Backstage, a service catalog, or your own tooling. You can read it from two places:

| | License server API | Kubernetes API |
| --- | --- | --- |
| **Endpoint** | `GET /api/v1/reports/topology` on the license server | `kubectl get mirrordclusterservicegraph default` |
| **Needs** | [License Server Setup](license-server.md), license server 3.211.0 or newer | Operator 3.211.0 or newer, nothing else |
| **History** | Every connection recorded in the time range you ask for | Only what the operator has seen since it last started |
| **Per connection** | Sessions, unique users, last seen | Last seen |
| **Use it for** | A scheduled sync into a developer portal or catalog | A quick look from inside the cluster |

Both need topology turned on with `operator.topology: true`, see [Turn it on](topology.md#turn-it-on). Both only contain connections that went through a mirrord session, so the same [gaps](topology.md#why-a-connection-is-missing) apply.

{% hint style="info" %}
The [cloud dashboard](cloud.md) draws its Topology tab from your organization's data, but the [Usage API](usage-api.md) does not return it. If your operator runs with a cloud API key, use the Kubernetes API below.
{% endhint %}

## License server API

The license server serves the report the Topology tab is drawn from. It lives on the dashboard port, so enable the dashboard first, see [License Server Setup](license-server.md#quick-start).

From your machine, forward the port and call it:

```bash
kubectl port-forward -n mirrord svc/mirrord-operator-license-server 8050:8050

curl -sSf "http://localhost:8050/api/v1/reports/topology?from=2026-09-01T00:00:00Z"
```

From a job inside the cluster, call the Service directly:

```bash
curl -sSf "https://mirrord-operator-license-server.mirrord.svc:8050/api/v1/reports/topology"
```

The dashboard port serves HTTPS when the license server has TLS configured (`tls.data` or `tls.certManager.enabled` in its Helm values). With a self-signed certificate, pass its CA to `curl` with `--cacert`. Without TLS the port answers plain HTTP, as in the port-forward example above. The chart expects the dashboard to be exposed only behind TLS, so configure it before other workloads call the port across the cluster.

The dashboard port adds the license key to every request itself, so there is no key to send. Unless the dashboard sits behind SAML, that also means the port does not authenticate callers: anything that can reach it can read this report and the rest of the dashboard's data. Limit who can reach it, for example with a NetworkPolicy, as you would for the dashboard itself.

If the dashboard sits behind SAML (`saml.enabled`), the port expects a browser sign-in, and a request without a signed-in session is redirected to your identity provider instead of getting the report. From a script or a scheduled job, read the map from the [Kubernetes API](#kubernetes-api) instead, or call the same endpoint on the license server's own API port with the `x-license-key` header, see [API Endpoints](license-server.md#api-endpoints).

### Query parameters

| Parameter | Format | Default |
| --- | --- | --- |
| `from` | RFC 3339 timestamp, for example `2026-09-01T00:00:00Z` | The beginning of time |
| `to` | RFC 3339 timestamp | Now |

`from` has to be before `to`, otherwise you get a `400`. Write timestamps in UTC with a `Z`. A date on its own, such as `2026-09-01`, is rejected with a `400`. An offset's `+` has to be percent-encoded as `%2B` in the query string, otherwise it arrives as a space and the request is rejected. The range filters by the time a session was reported, not by individual connection, the same as the time range selector on the tab.

### Response

```json
{
  "reportPeriod": {
    "from": "2026-09-01T00:00:00Z",
    "to": "2026-10-06T00:00:00Z"
  },
  "edges": [
    {
      "workload": { "kind": "Deployment", "name": "order-service", "namespace": "shop" },
      "service": { "name": "kafka", "namespace": "infra" },
      "direction": "outgoing",
      "port": 9092,
      "sessionCount": 37,
      "uniqueUsers": 5,
      "lastSeen": "2026-09-24T09:40:15.815508Z"
    },
    {
      "workload": { "kind": "Deployment", "name": "order-service", "namespace": "shop" },
      "service": { "name": "inventory-service", "namespace": "shop" },
      "direction": "outgoing",
      "port": 80,
      "sessionCount": 26,
      "uniqueUsers": 4,
      "lastSeen": "2026-09-24T09:40:15.815508Z"
    },
    {
      "workload": { "kind": "Deployment", "name": "order-service", "namespace": "shop" },
      "service": { "name": "metal-mart-frontend", "namespace": "shop" },
      "direction": "incoming",
      "sessionCount": 22,
      "uniqueUsers": 3,
      "lastSeen": "2026-09-24T09:40:15.815508Z"
    }
  ]
}
```

Each edge connects a session's target (`workload`) and a Kubernetes Service (`service`):

| Field | What it holds |
| --- | --- |
| `workload` | The workload a mirrord session targeted: `namespace`, `kind` (the target's Kubernetes kind, for example `Deployment`) and `name` |
| `service` | The Service on the other end: `namespace` and `name`. When the Service fronts a [preview environment](../../use-cases/preview-environments.md), `preview` holds its `key`, `targetKind` and `targetName` |
| `direction` | `outgoing`: the workload called the Service. `incoming`: a pod behind the Service called the workload |
| `port` | The Service port the workload connected to. Only on `outgoing` edges, and only the lowest port seen |
| `sessionCount` | Sessions, or preview environment runs, in which the connection happened at least once. Not a count of individual connections |
| `uniqueUsers` | Distinct users across those sessions |
| `lastSeen` | When a session last reported the connection |

Read `direction` before drawing an arrow. An `outgoing` edge runs from `workload` to `service`. An `incoming` edge runs from `service` to `workload`, the other way round.

The report holds at most 500 edges for the range, busiest first by `sessionCount`. When the same connection is reported from both ends, it is two edges, one `outgoing` from the caller's session and one `incoming` from the callee's. Merge them yourself if you want one line per dependency. When there are no connections in the range, `edges` is left out rather than sent empty, so read it as `.edges // []`.

`service` is a Service and `workload` is a workload, and their names don't always match. The Service `web-svc` in front of the Deployment `web` appears under both names. The dashboard does not merge them either, see [Reading the map](topology.md#reading-the-map).

### Example: a dependency list for a developer portal

This turns the report into one `caller → callee` line per dependency, with `incoming` edges flipped, duplicates merged, and edges to preview environments left out, since a preview is a temporary copy rather than a dependency:

```bash
curl -sSf "http://localhost:8050/api/v1/reports/topology" | jq -r '
  (.edges // [])
  | map(select(.service.preview | not))
  | map(
      if .direction == "outgoing"
      then {from: "\(.workload.namespace)/\(.workload.name)", to: "\(.service.namespace)/\(.service.name)"}
      else {from: "\(.service.namespace)/\(.service.name)", to: "\(.workload.namespace)/\(.workload.name)"}
      end)
  | unique[]
  | "\(.from) -> \(.to)"'
```

For the [MetalMart](https://github.com/metalbear-co/playground/tree/main/apps/shop) demo shop, part of the output looks like this:

```
shop/metal-mart-frontend -> shop/inventory-service
shop/metal-mart-frontend -> shop/order-service
shop/order-service -> infra/kafka
shop/order-service -> infra/postgres
shop/order-service -> infra/rabbitmq
shop/order-service -> infra/temporal
shop/order-service -> shop/inventory-service
shop/order-service -> shop/payment-service
shop/payment-service -> shop/receipt-service
```

The list also includes callers that aren't your own services, such as an ingress controller or `mirrord-share-ingress` in the `mirrord` namespace. Filter those out by namespace or name before importing.

From there, map each line to your portal's model. In Backstage, for example, the caller is a `Component` and the callee a `dependsOn` entry, either a `Component` or, for a data store or queue, a `Resource`. Use `port` to tell them apart; the [well-known ports](topology.md#well-known-ports) are the ones the dashboard uses.

Run the sync on a schedule. The map grows as your team uses mirrord, and a connection stays in the report for as long as the range you ask for covers it.

## Kubernetes API

The operator also serves the map as a read-only Kubernetes resource, `mirrordclusterservicegraphs`. It is cluster-scoped and holds one object, named `default`:

```bash
kubectl get mirrordclusterservicegraph default -o json
```

```json
{
  "apiVersion": "operator.metalbear.co/v1",
  "kind": "MirrordClusterServiceGraph",
  "metadata": { "name": "default" },
  "spec": {},
  "status": {
    "snapshotAt": "2026-10-06T13:02:03.229496Z",
    "edges": [
      {
        "workload": { "kind": "Deployment", "name": "order-service", "namespace": "shop" },
        "service": { "name": "kafka", "namespace": "infra" },
        "direction": "outgoing",
        "port": 9092,
        "lastSeen": "2026-10-06T10:28:36.390721Z"
      }
    ]
  }
}
```

The edges have the same `workload`, `service`, `direction` and `port` fields as the license server API, and the same rule for reading `direction`. There are no session or user counts.

The graph is built in the operator's memory. It is not stored in etcd, and it starts empty every time the operator restarts, including on upgrades. Treat it as a view of recent activity, not a record. For history, use the license server API.

Reading it needs `get` and `list` on `mirrordclusterservicegraphs`. With topology on, the chart grants that to the `mirrord-operator-user`, `mirrord-operator-user-basic` and `mirrord-operator-ci` ClusterRoles. A service account for a sync job needs a binding to one of those roles, or a role of its own with just those two verbs.

## Errors

| Status | Meaning |
| --- | --- |
| `400` | `from` at or after `to`, or a timestamp that doesn't parse |
| `3xx` | The dashboard sits behind SAML: the proxy redirects a request without a signed-in browser session to your identity provider |
| `403` | From `kubectl`: your user or service account has no `get` on `mirrordclusterservicegraphs`. The chart only grants it while topology is on |
| `404` | From `kubectl`: you asked for a name other than `default` |

On an operator older than 3.211.0, `kubectl` doesn't know the resource at all and reports that the server doesn't have a resource type `mirrordclusterservicegraph`.

An object with no `edges` from `kubectl` means the operator hasn't recorded a connection since it started, or topology is off.
