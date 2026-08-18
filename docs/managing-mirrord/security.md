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
* Operator activity is logged per session, including the Kubernetes user, the target, and the traffic filter in use. See [Auditing mirrord usage](#how-do-i-audit-mirrord-usage).
* mirrord can run fully air-gapped, with no outbound communication to MetalBear. See [Air-gapped operation](#can-mirrord-run-air-gapped).
* Released container images and CLI binaries carry signed SLSA Build Level 2 provenance, so you can verify what you pulled before installing it. See [How is the Operator built and distributed](#how-is-the-operator-built-and-distributed).
* Missing anything? Feel free to ask us on [Slack](https://metalbear.com/slack) or hi@metalbear.com

## How do I audit mirrord usage?

The Operator logs an event for every session at `INFO` level, which is the default log level. To get these in a form your logging or SIEM stack can ingest, set `operator.jsonLog` to `true` in the Operator Helm chart values.

See [Monitoring](monitoring.md) for the full field reference and for Prometheus, OpenTelemetry, DataDog, Grafana, and fluentd/Elasticsearch integration.

Logged events include `Session Start`, `Session End`, `Port Steal`, `Port Mirror`, `Port Release`, and `Copy Target`. Fields relevant to an audit trail include:

* `client_user` - the Kubernetes user of the client, resolved via Kubernetes RBAC
* `client_hostname`, `client_name`, `client_id` - identity of the machine and client certificate
* `target` - the session's target
* `session_id`, `session_duration` - correlation and length of each session
* `http_filter` - the client's configured HTTP filter

Together with the session start and end times, these fields let you attribute mirrord sessions to individual Kubernetes users and targets, including when several engineers are working against the same service concurrently.

## Can mirrord run air-gapped?

Yes, on the Enterprise plan. Run the [License Server](license-server.md) on-prem to manage seats locally. In this configuration the Operator sends no telemetry or license verification traffic to MetalBear.

## How is the Operator built and distributed?

* The mirrord agent is [open source](https://github.com/metalbear-co/mirrord) and can be audited directly.
* The Operator is distributed as a versioned container image from `ghcr.io/metalbear-co/operator`, installed via our [public Helm charts](https://github.com/metalbear-co/charts). Each chart release pins a matching `appVersion`, so the chart and the images it deploys move together.
* Because you control when you bump the chart version, you control when a new Operator or agent image enters your cluster. Chart releases are public and can be reviewed before you upgrade.
* Released container images and CLI binaries are published with signed [SLSA](https://slsa.dev) Build Level 2 provenance. It is generated by our release pipeline on GitHub Actions, signed through Sigstore, and published alongside the artifact, so you can confirm that what you pulled was built by us from the source you expect.

### Verifying build provenance

Attestations are published to GHCR alongside each image, and to the GitHub release for CLI binaries, under the `metalbear-co` owner. Verify them with [`gh attestation verify`](https://cli.github.com/manual/gh_attestation_verify), for example:

```bash
gh attestation verify \
  oci://ghcr.io/metalbear-co/operator:<version> --owner metalbear-co
```

The same applies to `ghcr.io/metalbear-co/mirrord` and to CLI binaries downloaded from a release. Verification needs a GitHub token with the `read:packages` scope, but no access to MetalBear's organization or repositories.

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
8. cluster_id (the UID of the cluster's `default` namespace, used as a stable, anonymous per-cluster identifier)
9. cluster_name (optional; only sent if you set the `operator.clusterName` Helm value to give the cluster a recognizable label)
10. kubernetes_version (the version of the Kubernetes cluster the Operator is running in)

In the Enterprise offering, this communication can be disabled entirely.

## Are you SOC2/ISO27001 compliant?

Yes, MetalBear is SOC2 Type II and ISO27001 certified.

## How do I configure Role Based Access Control for mirrord for Teams?

mirrord for Teams works on top of Kubernetes' built-in RBAC, with no separate user management. A mirrord user needs two kinds of permissions:

1. **Permissions on the Operator API.** Resources under the `operator.metalbear.co` and `profiles.mirrord.metalbear.co` API groups (plus feature-specific groups), served by the Operator's APIService. The exact minimum is listed [below](#what-are-the-minimum-permissions-a-user-needs).
2. **Regular Kubernetes `get` permission on the workloads they want to target.** The Operator impersonates the calling user and verifies their access to the target before starting a session, so mirrord never grants a user access to a workload they couldn't already read.

You can limit a user's ability to use mirrord on specific targets by limiting their access to the `targets` resource. The specific verbs for rules to our resources can be copied from the examples below.

For your convenience, mirrord for Teams includes built-in ClusterRoles that control access to the Operator API:

- `mirrord-operator-user` for interactive users running mirrord locally.
- `mirrord-operator-ci` for machine sessions in CI runners, such as `mirrord ci` and `mirrord preview`.

Both roles grant access to the same Operator API resources by default, but keeping CI access in a separate role lets you bind and label machine identities independently from human users. To grant access to the Operator API, you can create a ClusterRoleBinding like this:

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

For CI runners, bind the runner's ServiceAccount, Kubernetes group, or other authenticated identity to `mirrord-operator-ci` instead of `mirrord-operator-user`.

To see the latest definition, we recommend checking our [Helm chart](https://github.com/metalbear-co/charts/blob/main/mirrord-operator/templates/cluster-role.yaml).

### What are the minimum permissions a user needs?

If your security team prefers to define its own roles instead of binding the bundled ones, this is the full breakdown of what a mirrord user needs. Rules that only serve a specific capability are marked, and can be dropped if you don't use it.

**Cluster-scoped rules.** These must be granted through a ClusterRole with a ClusterRoleBinding:

```yaml
rules:
# Detecting the Operator and reading its status - required.
- apiGroups:
  - operator.metalbear.co
  resources:
  - mirrordoperators
  verbs:
  - get
  - list
# Obtaining the client credentials mirrord uses to authenticate
# to the Operator - required.
- apiGroups:
  - operator.metalbear.co
  resources:
  - mirrordoperators/certificate
  - mirrordclusteroperatorusercredentials
  verbs:
  - create
# Streaming session events (used by `mirrord subscribe`) - optional.
- apiGroups:
  - operator.metalbear.co
  resources:
  - events
  verbs:
  - get
  - list
  - watch
# Reading cluster-wide mirrord profiles - only needed if you use profiles.
- apiGroups:
  - profiles.mirrord.metalbear.co
  resources:
  - mirrordclusterprofiles
  verbs:
  - get
  - list
```

**Namespace-scopeable rules.** Grant these in the same ClusterRole for cluster-wide access, or as a namespaced Role to restrict users to specific namespaces (see the [next section](#how-do-i-limit-user-access-to-a-specific-namespace)):

```yaml
rules:
# Listing available targets and starting sessions on them - required.
# `proxy` is the verb that actually runs a mirrord session.
- apiGroups:
  - operator.metalbear.co
  resources:
  - targets
  - targets/port-locks
  verbs:
  - get
  - list
- apiGroups:
  - operator.metalbear.co
  resources:
  - targets
  verbs:
  - proxy
# `mirrord operator session kill` and `kill-all` - optional.
# These verbs are not scoped to the caller, see the note below.
- apiGroups:
  - operator.metalbear.co
  resources:
  - sessions
  verbs:
  - delete
  - deletecollection
# The copy target feature. Also required to target Jobs and
# CronJobs, which enable copy target automatically.
- apiGroups:
  - operator.metalbear.co
  resources:
  - copytargets
  verbs:
  - get
  - list
  - create
  - proxy
# Reading namespaced mirrord profiles - only needed if you use profiles.
- apiGroups:
  - profiles.mirrord.metalbear.co
  resources:
  - mirrordprofiles
  verbs:
  - get
  - list
```

The `sessions` verbs apply to every session in their scope, not only to the ones the caller started. A user bound to them can kill another developer's session in that namespace. See [sessions RBAC](../sharing-the-cluster/sessions.md#sessions-rbac) for how to trim this.

Features enabled through Helm values add their own rules on top of the sets above:

| Feature | Enabled by | apiGroup | Resources | Verbs |
| --- | --- | --- | --- | --- |
| [Preview environments](../use-cases/preview-environments.md) | `operator.previewEnv` | `preview.mirrord.metalbear.co` | `previewsessions` | `create`, `delete`, `get`, `list`, `watch` |
| | | `operator.metalbear.co` | `previews` | `get`, `list` |
| [DB branching](../sharing-the-cluster/db-branching.md) | `operator.pgBranching`, `operator.mysqlBranching`, and the other branching values | `dbs.mirrord.metalbear.co` | `branchdatabases` | `create`, `delete`, `get`, `list`, `watch` |
| | `operator.pgBranching`, `operator.mysqlBranching`, `operator.mongodbBranching` | `dbs.mirrord.metalbear.co` | `pgbranchdatabases`, `mysqlbranchdatabases`, `mongodbbranchdatabases`, one per enabled engine | `create`, `delete`, `get`, `list`, `watch` |
| | `operator.dbBranchingLiteralCredentials` | `operator.metalbear.co` | `branchcredentials` | `create` |
| [Queue splitting](../sharing-the-cluster/queue-splitting.md) | `operator.kafkaSplitting`, `operator.sqsSplitting`, and the other splitting values | None | None | None |

Queue splitting adds nothing to the user roles. The queue CRDs are read and written by the Operator alone, and broker credentials (Kafka ACLs, SQS IAM policies, RabbitMQ management access) are configured on the Operator, never per developer. Users only name topics in their mirrord configuration file.

The bundled `mirrord-operator-user` role is templated to contain exactly the rules your enabled features need, so the authoritative reference for your installation is the rendered role in your cluster:

```bash
kubectl get clusterrole mirrord-operator-user -o yaml
```

**Kubernetes permissions on the target.** In addition to the Operator API rules above, the Operator impersonates the calling user and checks that they can access the target. The user needs:

* For a workload target (`deployment`, `pod`, `statefulset`, `replicaset`, `service`, `job`, `cronjob`, or Argo Rollout): `get` on that resource in its namespace.
* For the [targetless mode](https://metalbear.com/mirrord/docs/config#target): `get` on the target namespace.
* For a label-selector target: `list` on pods in the target namespace.

Nothing else on your cluster workloads is required. The user roles carry no `create` or `delete` on Pods, Jobs, or any workload, no `pods/exec`, no `pods/portforward` ([`mirrord port-forward`](../using-mirrord/port-forwarding.md) runs through the same Operator session as any other mirrord command), and no write access of any kind to your workloads. The scale-down for [copy target](../using-mirrord/copy-target.md) and the env injection for [queue splitting](../sharing-the-cluster/queue-splitting.md) are performed by the Operator's own ServiceAccount.

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
