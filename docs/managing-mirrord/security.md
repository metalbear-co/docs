---
title: Security
date: 2022-07-10T08:48:57.000Z
lastmod: 2024-03-01T00:00:00.000Z
draft: false
images: []
linktitle: Security
menu:
  docs:
    teams: null
weight: 510
toc: true
tags:
  - team
  - enterprise
description: Security in mirrord for Teams
---

{% hint style="info" %}
This discussion is only relevant for users on the Team and Enterprise pricing plans.
{% endhint %}

Love using mirrord but need help getting your security team on board? Talk to one of our technical experts!

<a href="https://metalbear.com/mirrord/demo/" class="button primary">Get Security Support</a>

You can also visit our [Trust Center](https://trust.metalbear.com) for an overview of MetalBear's security posture, certifications, and compliance documentation.

## I'm a Security Engineer evaluating mirrord for Teams, what do I need to know?

* mirrord for Teams is completely on-prem. The only data sent to our cloud is analytics and license verification (see [details below](#what-data-does-the-mirrord-operator-send-to-metalbear-cloud)) which can be customized or disabled upon request. The analytics don't contain PII or any sensitive information.
* mirrord does not require root permissions on the user's machine.
* mirrord for Teams uses Kubernetes RBAC, meaning it doesn't add a new attack vector to your cluster.
* Communication between the mirrord client and the mirrord Operator takes place over your existing Kubernetes API. If you’ve configured your cluster to encrypt this communication (as is commonly done), then mirrord for Teams’ client-server communication is encrypted as well.
* mirrord for Teams defines a new CRD that can be used to limit access and use of mirrord, with plans of more fine-grained permissions in the future.
* The operator requires permissions to create a pod with the following capabilities in its Kubernetes namespace:
  * `CAP_NET_ADMIN` - for modifying routing tables
  * `CAP_SYS_PTRACE` - for reading the target pod's environment variables
  * `CAP_SYS_ADMIN` - for joining the target pod's network namespace
* The operator requires exclusions from the following gatekeeper policies:
  * `runAsNonRoot` - to access target pod's filesystem
  * `HostPath volume`/`Sharing the host namespace` - to access target pod's file system and networking
* mirrord doesn't copy remote files or secrets to the local filesystem. The local app is given access to them in memory only. See [below](#does-mirrord-reduce-secret-sprawl-on-developer-machines) for what that does and doesn't guarantee, including [when debug logging changes it](#debug-and-trace-logging-writes-remote-values-to-disk).
* Operator activity is logged per session, including the Kubernetes user, the target, and the traffic filter in use. See [Auditing mirrord usage](#how-do-i-audit-mirrord-usage).
* mirrord can run fully air-gapped, with no outbound communication to MetalBear. See [Air-gapped operation](#can-mirrord-run-air-gapped).
* Missing anything? Feel free to ask us on [Slack](https://metalbear.com/slack) or hi@metalbear.com

## Does mirrord reduce secret sprawl on developer machines?

Usually, yes. A common pattern for local development against cloud dependencies is to copy credentials for services like databases and message queues into a local `.env` file so the application can reach them from a developer's machine. Those credentials then persist on laptops, get shared between engineers, and are rarely rotated.

With mirrord, the local process joins the target pod's network context and reads environment variables and files from the target in memory. The developer's machine never needs a persistent copy of those credentials, which removes a class of long-lived local secret.

**Understand the access boundary before relying on this.** Authorization is enforced at the level of the *target workload*, not the individual Secret. The Operator impersonates the calling user and will only operate on pods or deployments the user has `get` permissions for, but there is no separate authorization check against the Secrets that workload references. A user who is allowed to target a workload can therefore read its environment variables and mounted files, including values sourced from Secrets they would not be able to `get` directly.

The practical control is target scope: grant mirrord access only to targets whose secret material is acceptable for that user, using the `resourceNames` and namespaced-role approaches described [below](#how-do-i-configure-role-based-access-control-for-mirrord-for-teams). Note that the [env and file policies](../sharing-the-cluster/policies.md) are documented as convenience features and are explicitly not security controls, so they should not be used as the boundary.

Note also that the local application can still write values to disk itself. mirrord controls how the values reach the process, not what the process does with them.

### Debug and trace logging writes remote values to disk

At default log levels mirrord does not write remote environment variables or file contents to disk. If mirrord is configured to log to a file at `debug` or `trace` level, it can, because those levels record the values being passed to the local process.

Treat this as a real operational control, not a footnote:

* Any mirrord debug/trace log file produced against a target with sensitive configuration should be handled as secret material, including when it is attached to a support ticket or a bug report. If we ask you for debug logs, review them before sending.
* This is a client-side setting on the developer's machine. The Operator cannot enforce it, and the [env and file policies](../sharing-the-cluster/policies.md) are convenience features rather than security controls, so they will not prevent it either.
* If you need verbose logs while troubleshooting against a sensitive target, prefer reproducing against a target whose configuration is not sensitive, and delete the logs afterwards.

## How do I audit mirrord usage?

The Operator logs an event for every session at `INFO` level, which is the default log level. To get these in a form your logging or SIEM stack can ingest, set `operator.jsonLog` to `true` in the Operator Helm chart values.

**Enable this before you need it.** JSON logging is off by default, and turning it on is not retroactive: sessions that ran before you enabled it leave no ingestible record. If mirrord usage needs to be auditable, set it at install time.

See [Monitoring](monitoring.md) for the full field reference and for Prometheus, OpenTelemetry, DataDog, Grafana, and fluentd/Elasticsearch integration.

Logged events include `Session Start`, `Session End`, `Port Steal`, `Port Mirror`, `Port Release`, and `Copy Target`. Fields relevant to an audit trail include:

* `client_user` - the Kubernetes user of the client, resolved via Kubernetes RBAC
* `client_hostname`, `client_name`, `client_id` - identity of the machine and client certificate
* `target` - the session's target
* `session_id`, `session_duration` - correlation and length of each session
* `http_filter` - the client's configured HTTP filter

These are session-scoped records, not a per-request delivery log. `http_filter` captures the filter a client *configured* when it began stealing on a port, so together with `client_user`, `target`, and the session start/end times you can establish which users held an active session against a given target during a given window, and what each had subscribed to. That is sufficient to attribute access and to narrow an investigation to a set of users when several engineers are working against the same service concurrently.

It is not sufficient to prove which individual requests were delivered to which client. mirrord does not log per-request routing decisions, so if you need request-level evidence you will need to correlate these logs with your application or ingress telemetry.

## Can mirrord run air-gapped?

Yes, on the Enterprise plan. Run the [License Server](license-server.md) on-prem to manage seats locally. In this configuration the Operator sends no telemetry or license verification traffic to MetalBear.

## How is the Operator built and distributed?

* The mirrord agent is [open source](https://github.com/metalbear-co/mirrord) and can be audited directly. The Operator is closed source.
* The Operator is distributed as a versioned container image from `ghcr.io/metalbear-co/operator`, installed via our [public Helm charts](https://github.com/metalbear-co/charts). Each chart release pins a matching `appVersion`, so the chart and the images it deploys move together.
* Because you control when you bump the chart version, you control when a new Operator or agent image enters your cluster. Chart releases are public and can be reviewed before you upgrade.

For our vulnerability disclosure and customer notification process, see the [Trust Center](https://trust.metalbear.com).

## What data does the mirrord Operator send to MetalBear cloud?

mirrord for Teams is completely on-prem. The Operator communicates with MetalBear servers over an encrypted TLS connection only for license verification and anonymous usage metrics. The fields shared are:

1. User ID (randomly generated hash, stored on user machine)
2. Duration of session
3. Organization name
4. mirrord License Hash (of organization)
5. instance_id (generated on runtime per Operator pod)
6. subscription_id (generated uuid)
7. organization_id (generated uuid)

In the Enterprise offering, this communication can be disabled entirely.

## Are you SOC2/ISO27001 compliant?

Yes, MetalBear is SOC2 Type II and ISO27001 certified.

## How do I configure Role Based Access Control for mirrord for Teams?

mirrord for Teams works on top of Kubernetes' built-in RBAC with the following resources, `mirrordoperators`, `mirrordoperators/certificate`, `targets`, and `targets/port-locks` under the `operator.metalbear.co` apiGroup. The first two resources are required at a cluster level, and the last two can be allowed at a namespace level.

You can limit a user's ability to use mirrord on specific targets by limiting their access to the `target` resource. The specific verbs for rules to our resources can be copied from the examples below.

For your convenience, mirrord for Teams includes a built-in ClusterRole called `mirrord-operator-user`, which controls access to the Operator API. To grant access to the Operator API, you can create a ClusterRoleBinding like this:

```yaml

apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: mirrord-operator-rolebinding
subjects:
- kind: User
  name: jim
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: mirrord-operator-user
  apiGroup: rbac.authorization.k8s.io
```

In addition, the Operator impersonates any user that calls its API, and thus only operates on pods or deployments for which the user has `get` permissions.

To see the latest definition, we recommend checking our [Helm chart](https://github.com/metalbear-co/charts/blob/main/mirrord-operator/templates/cluster-role.yaml).

### How do I limit user access to a specific namespace?

Create a ClusterRoleBinding between the user and the `mirrord-operator-user-basic` role, then create a [namespaced role](https://github.com/metalbear-co/charts/blob/main/mirrord-operator/templates/namespaced-role.yaml) (easiest via Helm chart by specifying `roleNamespaces`) and bind create RoleBinding in the namespace.

### How do I limit user access to a specific target?

If the user doesn't have `get` access to the targets, then they won't be able to target them with mirrord. However, if you want to allow `get` access to targets but disallow using mirrord on them, we recommend creating a new role based on the `mirrord-operator-user` namespaced role above, and adding a `resourceNames` field to the `targets` resource. This will limit the user to only using the Operator on the specified targets. For example:

```yaml
- apiGroups:
  - operator.metalbear.co
  resources:
  - targets
  resourceNames:
  - "deployment.my-deployment"
  - "pod.my-pod"
  - "rollout.my-argo-rollout"
  verbs:
  - proxy
```

## How can I prevent users in my team from stealing or mirroring traffic from a target?

You can define [policies](../sharing-the-cluster/policies.md) that prevent stealing (or only prevent stealing without setting a filter) and/or mirroring for selected targets. Let us know if there are more features you would like to be able to limit using policies.

## How can I prevent users from using mirrord without going through the Operator?

When the mirrord CLI starts, it checks if an Operator is installed in the cluster and uses it if it's available. However, if the user lacks access to the Operator or if the Operator doesn't exist, mirrord attempts to create an agent directly.

To prevent clients from attempting to create an agent without the Operator, you can add the [following key](https://metalbear.com/mirrord/docs/config#operator) to the mirrord configuration file:

```json
{
  "operator": true
}
```

To prevent mirrord clients from directly creating agents at the cluster level, we recommend disallowing the creation of pods with extra capabilities by using [Pod Admission Policies](https://kubernetes.io/tasks/configure-pod-container/enforce-standards-namespace-labels/). Apply a baseline or stricter policy to all namespaces while excluding the mirrord namespace.

Note: before adding a new Pod Admission Policy, you should make sure it doesn't limit any functionality required by your existing workloads.

By default the in-cluster traffic between the operator and its agents isn't encrypted nor authenticated. To ensure encryption and authentication you can enable TLS protocol for the operator–agent connections. You can do this in the operator [Helm chart](https://github.com/metalbear-co/charts/blob/main/mirrord-operator/values.yaml) by setting `agent.tls` to true or manually by setting `OPERATOR_AGENT_CONNECTION_TLS=true` in the operator container environment. TLS connections are supported from agent version 3.97.0.

## Security hardening with the mirrord operator

Here is a quick checklist you may wish to follow in order to improve the security posture of your cluster when using the operator:

### Enabling TLS

TLS can be enabled between the operator and mirrord agents to encrypt the traffic they send to each other. From the [section above](security.md#how-can-i-prevent-users-from-using-mirrord-without-going-through-the-operator):

> By default the in-cluster traffic between the operator and its agents isn’t encrypted nor authenticated. To ensure encryption and authentication you can enable TLS protocol for the operator–agent connections. You can do this in the operator [Helm chart](https://github.com/metalbear-co/charts/blob/main/mirrord-operator/values.yaml) by setting `agent.tls` to true or manually by setting `OPERATOR_AGENT_CONNECTION_TLS=true` in the operator container environment. TLS connections are supported from agent version 3.97.0.

### Reducing access to the mirrord namespace

Users have no need to access to the namespace where mirrord resources are created. By default, this is the `mirrord` namespace.

### Using a certificate for mirrord APIService

By using either your own certificate or one provided by a certificate manager, you can secure access to mirrord's APIService - you will need to set `insecureSkipTLSVerify` to `false` in the mirrord-operator Helm chart.

_NB: If you are using a certificate manager, make sure you set up reminders for certificate renewal._

### Set up network policies for communication

Access to the operator can be further restricted by setting up [network policies](https://kubernetes.io/concepts/services-networking/network-policies/) in the cluster to limit the operator to communicate only with mirrord agents (this is not possible if running agents in [ephemeral mode](https://metalbear.com/mirrord/docs/config#agent.ephemeral)).

