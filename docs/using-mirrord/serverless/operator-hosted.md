---
title: "Operator-Hosted Sessions-Manager"
description: "Run sessions-manager inside the mirrord Operator, so developers can target serverless workloads such as Amazon ECS tasks through your cluster's API server."
tags:
  - alpha
  - enterprise
---

In the Operator-hosted [deployment mode](README.md#deployment-modes), sessions-manager runs inside the mirrord Operator. Enabling it is a Helm value: there's no additional deployment, service or load balancer, and the Operator isn't exposed outside the cluster. At a glance, the setup is:

1. Enable sessions-manager with the `operator.sessionsManager` Helm value ([Enable sessions-manager](#enable-sessions-manager)).
2. Check that developers are bound to one of the built-in Operator roles ([Developer access](#developer-access)).
3. Connect each workload, which maps its identity into the cluster and binds it to the `mirrord-operator-sessions-manager-agent` ClusterRole ([Connecting workloads](#connecting-workloads)).

## Prerequisites

1. An EKS cluster with the mirrord Operator `<OPERATOR_VERSION>+` installed through its Helm chart `<CHART_VERSION>+`, and a mirrord Operator license.
2. `kubectl` and `helm`, with permission to manage the Operator Helm release and cluster RBAC.

---

## How it works

{% hint style="info" %}
This section is for whoever reviews the setup, such as your security team. To start the setup, skip to [Enable sessions-manager](#enable-sessions-manager).
{% endhint %}

```
 developer machine                     EKS VPC                                workload network
┌───────────────────┐  kubeconfig   ┌───────────────────────────────┐      ┌───────────────────────────┐
│ mirrord exec      │─────────────► │ EKS API server endpoint       │      │ application container     │
│ (local process)   │               │   │ aggregated API            │      │ + mirrord remote          │
└───────────────────┘               │   ▼                           │      │   bootstrap (LD_PRELOAD)  │
                                    │ mirrord Operator              │      └─────────────┬─────────────┘
                                    │   (sessions-manager inside)   │                    │ HTTPS, Kubernetes
                                    └───────────────▲───────────────┘                    │ identity
                                                    └────────────────────────────────────┘
```

Every caller reaches sessions-manager the same way it reaches every other Operator feature: through the cluster's API server and the Operator's aggregated API. Both sides authenticate as Kubernetes identities, access is granted with ordinary Kubernetes RBAC, and requests are recorded in the cluster's audit log. There are no shared secrets to create, distribute or rotate.

* **Developers** authenticate with their kubeconfig, exactly like for any other Operator feature.
* **Workloads** authenticate with their platform identity, mapped to a Kubernetes identity. For ECS, the task's IAM role is mapped with an EKS access entry; see [How ECS tasks authenticate](ecs-operator-hosted.md#how-ecs-tasks-authenticate).

The Operator serves three cluster-scoped resources on its existing `operator.metalbear.co/v1alpha1` API:

| Resource | Verb | Used by | Used for |
| --- | --- | --- | --- |
| `serverlessclientassignments` | `proxy` | Developers | Registering and waiting, on a long-lived Server-Sent Events stream, to be paired with a workload. |
| `serverlessagentassignments` | `proxy` | Workloads | Registering and waiting, on a long-lived Server-Sent Events stream, to be paired with a developer. |
| `serverlessdataplanes` | `get` | Both | Opening a WebSocket to the assigned session; the Operator relays mirrord traffic between the two sides. |

Each side of a session registers on its own resource, so RBAC decides which side an identity may act as: a developer bound to the user roles can't register as a workload and be paired with other developers. A registration is named after the environment and service it pairs in, `<environment>.<service>`, so a workload's access can also be limited to specific services with `resourceNames` ([Limiting a workload to specific services](#limiting-a-workload-to-specific-services)).

The Operator receives the caller's identity from the API server, like it does for every other Operator request, and implements no authentication of its own. Each data-plane connection is also bound to its session by a single-use credential delivered with the assignment, so an identity allowed to use `serverlessdataplanes` can't attach to another caller's session.

Both sides only make outbound HTTPS connections, and only to the API server. Neither needs a network path to the other.

---

## Enable sessions-manager

Add `operator.sessionsManager=true` to your existing Operator Helm release:

```bash
helm upgrade mirrord-operator metalbear/mirrord-operator \
  --namespace mirrord \
  --reuse-values \
  --set operator.sessionsManager=true
```

Confirm the Operator now serves the three resources:

```bash
kubectl api-resources --categories=mirrord-serverless
# NAME                          SHORTNAMES   APIVERSION                       NAMESPACED   KIND
# serverlessagentassignments                 operator.metalbear.co/v1alpha1   false        ServerlessAgentAssignment
# serverlessclientassignments                operator.metalbear.co/v1alpha1   false        ServerlessClientAssignment
# serverlessdataplanes                       operator.metalbear.co/v1alpha1   false        ServerlessDataPlane
```

## Developer access

Enabling sessions-manager grants `proxy` on `serverlessclientassignments` and `get` on `serverlessdataplanes` in the chart's `mirrord-operator-user`, `mirrord-operator-ci` and `mirrord-operator-user-basic` ClusterRoles. Developers already bound to one of those roles need no further RBAC changes, and nothing beyond their existing kubeconfig for the cluster:

```bash
aws eks update-kubeconfig --name <CLUSTER_NAME> --region <REGION>
```

If you grant Operator access with your own roles instead, add the two rules above to them. For the developer's `mirrord.json`, see [Using mirrord with a Serverless Workload](README.md#using-mirrord-with-a-serverless-workload).

## Connecting workloads

Enabling sessions-manager also creates the `mirrord-operator-sessions-manager-agent` ClusterRole. It grants only `proxy` on `serverlessagentassignments` and `get` on `serverlessdataplanes`, and none of the user permissions: a workload bound to it can't read, list or modify any other resource in the cluster, and can't register as a developer.

Each workload authenticates as a Kubernetes identity bound to this role. How its identity is mapped, and how it reaches the API server, depends on the platform:

* [Connecting ECS to the Operator](ecs-operator-hosted.md)

{% hint style="info" %}
Bind the chart's role rather than defining your own, unless you need to limit a workload to specific services: it stays in sync with what the Operator requires when you upgrade the chart.
{% endhint %}

### Limiting a workload to specific services

The chart's role lets a workload register under any environment and service. To limit an identity to specific ones, bind it to your own ClusterRole instead, listing each `<environment>.<service>` it may register as in `resourceNames`:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: mirrord-sessions-manager-agent-staging-api
rules:
  - apiGroups: [operator.metalbear.co]
    resources: [serverlessagentassignments]
    resourceNames: [staging.api]
    verbs: [proxy]
  - apiGroups: [operator.metalbear.co]
    resources: [serverlessdataplanes]
    verbs: [get]
```

An identity bound to this role can register as service `api` in environment `staging`, and gets `403 Forbidden` for any other. Data planes are named by per-session IDs, so the `serverlessdataplanes` rule can't be narrowed; each connection is already bound to its session by its single-use credential.

---

## Operating notes

* **Operator restarts and upgrades** end active sessions. Workloads register again on their own; developers rerun `mirrord exec`. If connections are cut during rollouts, raise the chart's `operator.terminationGracePeriodSeconds` (default `25`) to give sessions time to close cleanly.
* **Traffic path**: session traffic flows through the API server. It's suited to development traffic, not to load testing through a mirrord session.
* **Long-lived connections**: a session holds its HTTPS connections open for as long as the developer runs it. The Operator sends a keepalive on each registration stream every 15 seconds, and data-plane connections carry mirrord's own periodic traffic.

{% hint style="warning" %}
Any firewall or proxy between a workload and the API server needs an idle timeout of at least 300 seconds and must not buffer responses.
{% endhint %}

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| `404 Not Found`, or mirrord says the Operator doesn't serve sessions-manager | `operator.sessionsManager` isn't enabled, or the Operator version predates it. |
| `403 Forbidden` on `serverlessclientassignments` for a developer | The developer isn't bound to one of the built-in user roles, or a custom role lacks the two rules ([Developer access](#developer-access)). |
| `403 Forbidden` on `serverlessagentassignments` for a workload bound to a custom role | The role's `resourceNames` doesn't list the workload's `<environment>.<service>` ([Limiting a workload to specific services](#limiting-a-workload-to-specific-services)). |
| The workload registers but the developer is never paired | The workload's service and environment names don't match `target.path` and `target.namespace` in `mirrord.json`. |

For workload-side problems, see the troubleshooting section of your platform's connection guide, such as [Connecting ECS to the Operator](ecs-operator-hosted.md#troubleshooting).

To see registrations and sessions, follow the Operator's logs:

```bash
kubectl -n mirrord logs deployment/mirrord-operator -f | grep -i session
```
