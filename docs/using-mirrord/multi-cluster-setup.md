---
title: "Multi-Cluster Setup"
description: "How to install and configure mirrord for multi-cluster operation"
date: 2026-02-12T00:00:00+00:00
lastmod: 2026-02-12T00:00:00+00:00
draft: false
images: []
menu:
  docs:
    parent: "using-mirrord"
weight: 176
toc: true
tags: ["enterprise"]
---

This guide covers how to set up multi-cluster mirrord. It involves installing the operator on all clusters, choosing an authentication method, and configuring the Primary cluster to connect to remote clusters.

## Prerequisites

Before you start, make sure you have:

1. The mirrord operator Helm chart ready to install on all clusters.
2. `kubectl` access to all clusters.
3. For EKS IAM authentication: AWS CLI and `eksctl` installed.

---

## Authentication Methods

Each remote cluster must specify an `authType` that determines how the Primary operator authenticates to it. The `authType` field is **required** — the Helm chart validates it at install time and fails if it's missing.

### Bearer Token (`authType: bearerToken`)

Uses ServiceAccount tokens that are automatically refreshed via the Kubernetes TokenRequest API. Good for most setups where the Primary cluster can reach the remote cluster's API server.

You generate an initial token manually during setup. After that, the operator auto-refreshes the token before it expires using the TokenRequest API. The refreshed token keeps the same lifetime as the original.

### EKS IAM (`authType: eks`)

For AWS EKS clusters. The Primary operator generates short-lived tokens using its IAM role (via IRSA). No secrets to manage — tokens are generated and refreshed automatically every 10 minutes.

On the Primary cluster, the operator pod gets AWS credentials through IRSA (`sa.roleArn`). It uses those credentials to generate a presigned STS URL, which is sent to the remote cluster as a bearer token. The remote EKS cluster validates the token with AWS STS, then maps the IAM role to a Kubernetes group via an [Access Entry](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html). Kubernetes RBAC on the remote cluster grants permissions to that group.

No Kubernetes Secret is needed — authentication is entirely through IAM.

### mTLS (`authType: mtls`)

For clusters that require client certificate authentication. You provide the client certificate and key in the cluster configuration or Secret.

Certificates are **not** auto-refreshed. You are responsible for rotating them before they expire.

### Fields per Auth Type

| Field | `bearerToken` | `eks` | `mtls` |
|-------|:---:|:---:|:---:|
| `server` | Required | Required | Required |
| `caData` | Optional | Optional | Optional |
| `bearerToken` | Required (initial only, auto-refreshed after) | — | — |
| `region` | — | Required | — |
| `tlsCrt` | — | — | Required |
| `tlsKey` | — | — | Required |

---

## Setting Up Remote Clusters

Every remote cluster needs the mirrord operator installed with `multiClusterMember` enabled. This creates the ServiceAccount, ClusterRoles, and ClusterRoleBindings that the Primary operator needs to manage sessions on that cluster.

### Bearer Token / mTLS Clusters

{% stepper %}
{% step %}

### Install the operator on the remote cluster

```bash
helm install mirrord-operator metalbear/mirrord-operator \
  --set operator.multiClusterMember=true
```

This creates a `mirrord-operator-envoy` ServiceAccount with the necessary RBAC permissions.

{% endstep %}
{% step %}

### Generate an initial token (bearer token auth only)

```bash
kubectl create token mirrord-operator-envoy -n mirrord --duration=24h
```

Save this token — you'll need it when configuring the Primary cluster. This initial token is only needed once during setup. After the Primary operator starts, it auto-refreshes tokens using the TokenRequest API before they expire.

For mTLS, skip this step. Instead, you'll provide the client certificate and key when configuring the Primary cluster.

{% endstep %}
{% endstepper %}

### EKS IAM Clusters

EKS IAM authentication lets the Primary operator authenticate to remote EKS clusters using its AWS IAM role. No Kubernetes Secrets to manage — the operator generates short-lived tokens from its IAM identity.

#### How EKS IAM Authentication Works

The Primary operator pod needs to talk to remote EKS clusters. To do that, it needs a token. Here's how the token gets created and accepted:

1. **The pod gets AWS credentials** — the `sa.roleArn` annotation on the Primary operator's ServiceAccount tells EKS to inject AWS credentials into the pod via IRSA. Now the pod can act as that IAM role.

2. **The pod creates a token** — the operator uses those AWS credentials to generate a presigned `GetCallerIdentity` STS URL. This URL is used as a Kubernetes bearer token that EKS understands.

3. **The remote cluster validates the token** — when the remote EKS cluster receives this token, it calls AWS STS to verify the identity. AWS responds: "This is IAM role X."

4. **EKS maps the IAM role to a Kubernetes group** — the Access Entry on the remote cluster maps that IAM role to a Kubernetes group (e.g. `mirrord-operator-envoy`). Now the operator is authenticated as a member of that group.

5. **Kubernetes RBAC grants permissions** — the ClusterRoleBindings on the remote cluster (created by Helm with `multiClusterMemberIamGroup`) grant the `mirrord-operator-envoy` group the necessary permissions.

#### What Goes Where

| Component | Where | Purpose |
|-----------|-------|---------|
| OIDC Identity Provider | Primary cluster (AWS) | Enables IRSA so the pod can assume an IAM role |
| IAM role + trust policy | AWS IAM | The identity the operator pod assumes. Has no AWS permissions — only used as a Kubernetes identity |
| `sa.roleArn` in Helm | Primary cluster | Annotates the operator's ServiceAccount so the pod gets AWS credentials for the IAM role |
| Access Entry | Each remote EKS cluster (AWS) | Maps the IAM role to a Kubernetes group. Created via `aws eks create-access-entry` |
| `multiClusterMemberIamGroup` in Helm | Each remote cluster | Creates ClusterRoleBindings that grant permissions to the Kubernetes group |

{% hint style="info" %}
The Primary cluster does **not** need an Access Entry. The operator pod runs inside the Primary cluster, so it authenticates using its ServiceAccount — no IAM token needed. The Access Entries are only needed on remote clusters where the pod authenticates from the outside.
{% endhint %}

#### Setup Steps

{% stepper %}
{% step %}

### Associate an OIDC Identity Provider with the Primary cluster

This is a one-time AWS setup. It registers the Primary EKS cluster's OIDC issuer as an IAM Identity Provider, which is what enables IRSA — the mechanism that lets pods assume IAM roles.

```bash
eksctl utils associate-iam-oidc-provider \
  --cluster <PRIMARY_CLUSTER_NAME> --region <REGION> --approve
```

Skip this if already done (e.g. if other workloads in the cluster already use IRSA).

{% endstep %}
{% step %}

### Create the IAM role with a trust policy

Create an IAM role that the operator pod will assume. The trust policy controls who can assume this role — it should only allow the Primary operator's ServiceAccount.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/oidc.eks.<REGION>.amazonaws.com/id/<OIDC_ISSUER_ID>"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "oidc.eks.<REGION>.amazonaws.com/id/<OIDC_ISSUER_ID>:sub": "system:serviceaccount:mirrord:mirrord-operator",
          "oidc.eks.<REGION>.amazonaws.com/id/<OIDC_ISSUER_ID>:aud": "sts.amazonaws.com"
        }
      }
    }
  ]
}
```

You can find the OIDC issuer ID from the Primary cluster:

```bash
aws eks describe-cluster --name <PRIMARY_CLUSTER_NAME> --region <REGION> \
  --query "cluster.identity.oidc.issuer" --output text
# Returns: https://oidc.eks.<REGION>.amazonaws.com/id/<OIDC_ISSUER_ID>
```

{% hint style="info" %}
This IAM role does **not** need any IAM policies attached (no `s3:*`, `sqs:*`, etc.). It has zero AWS permissions. All actual permissions come from Kubernetes RBAC on the remote clusters. The role is only used as an identity.
{% endhint %}

{% endstep %}
{% step %}

### Create an EKS Access Entry on each remote cluster

This is an AWS-level configuration (not a Kubernetes resource). It tells each remote EKS cluster: "When this IAM role authenticates, map it to the `mirrord-operator-envoy` Kubernetes group."

Run this for **each remote EKS cluster**:

```bash
aws eks create-access-entry \
  --cluster-name <REMOTE_CLUSTER_NAME> \
  --principal-arn arn:aws:iam::<ACCOUNT_ID>:role/<IAM_ROLE_NAME> \
  --type STANDARD \
  --kubernetes-groups mirrord-operator-envoy
```

The Access Entry itself doesn't grant any Kubernetes permissions — it only establishes the identity mapping. Permissions come from RBAC (next step).

{% endstep %}
{% step %}

### Install the operator on each remote cluster

Install the operator with `multiClusterMember` and `multiClusterMemberIamGroup`:

```bash
helm install mirrord-operator metalbear/mirrord-operator \
  --set operator.multiClusterMember=true \
  --set operator.multiClusterMemberIamGroup=mirrord-operator-envoy
```

This creates ClusterRoleBindings that grant the `mirrord-operator-envoy` Kubernetes group the permissions needed to manage sessions. The Access Entry (previous step) maps the IAM role to this group, so the Primary operator gets these permissions when it authenticates.

{% endstep %}
{% step %}

### Install the operator on the Primary cluster with `sa.roleArn`

On the Primary cluster, set `sa.roleArn` so the operator pod can assume the IAM role:

```yaml
sa:
  roleArn: "arn:aws:iam::<ACCOUNT_ID>:role/<IAM_ROLE_NAME>"
```

This annotates the operator's ServiceAccount with `eks.amazonaws.com/role-arn`. When the pod starts, EKS injects AWS credentials into the pod automatically. The operator uses these credentials to generate tokens for each remote cluster.

See the [Configuring the Primary Cluster](#configuring-the-primary-cluster) section below for the full Helm values.

{% endstep %}
{% endstepper %}

---

## Configuring the Primary Cluster

Install the operator on the Primary cluster with multi-cluster enabled and all remote clusters configured.

### Helm Values

```yaml
operator:
  multiCluster:
    # Enable multi-cluster mode
    enabled: true

    # Logical name of this cluster (set by you, should match the real cluster name)
    clusterName: "primary"

    # Default cluster for stateful operations (env vars, files, db branching)
    defaultCluster: "cluster-a"

    # Set to true if Primary cluster has no workloads (management-only)
    managementOnly: false

    # Remote cluster configuration
    # Each key should match the real cluster name
    clusters:
      # Bearer token authentication
      cluster-a:
        authType: bearerToken
        server: "https://api.cluster-a.example.com:6443"
        caData: "LS0tLS1CRUdJTi..."
        bearerToken: "eyJhbGciOiJS..."
        isDefault: true

      # EKS IAM authentication
      cluster-b:
        authType: eks
        region: eu-north-1
        server: "https://ABCDEF1234567890.gr7.eu-north-1.eks.amazonaws.com"
        caData: "LS0tLS1CRUdJTi..."

      # mTLS authentication
      cluster-c:
        authType: mtls
        server: "https://api.cluster-c.example.com:6443"
        caData: "LS0tLS1CRUdJTi..."
        tlsCrt: "LS0tLS1CRUdJTi..."
        tlsKey: "LS0tLS1CRUdJTi..."

# Required for EKS IAM auth — gives the pod AWS credentials
sa:
  roleArn: "arn:aws:iam::<ACCOUNT_ID>:role/<IAM_ROLE_NAME>"
```

{% hint style="warning" %}
The cluster key names in the `clusters` map should match the real cluster names. For EKS clusters this is especially important — the operator uses the key as the EKS cluster name when signing IAM tokens.
{% endhint %}

### Where Data Is Stored

When you provide cluster configuration in the Helm values, the chart splits it into two places. Non-sensitive configuration (`server`, `caData`, `authType`, `region`, `isDefault`, `namespace`) goes into the ConfigMap (`clusters-config.yaml`). Sensitive credentials (`bearerToken`, `tls.crt`, `tls.key`) go into a Secret (`mirrord-cluster-<name>`).

For EKS IAM clusters, no Secret is created — everything is in the ConfigMap since authentication is through IAM, not stored credentials.

### Manual Secret Creation

If you prefer to manage secrets outside of Helm values, you can create the Secret manually. The Secret must be labeled with `operator.metalbear.co/remote-cluster-credentials=true` and named `mirrord-cluster-<cluster-name>`. The cluster configuration (server, authType, etc.) still needs to be in the Helm values or the `clusters-config.yaml` ConfigMap.

For bearer token:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: mirrord-cluster-cluster-a
  namespace: mirrord
  labels:
    operator.metalbear.co/remote-cluster-credentials: "true"
type: Opaque
stringData:
  bearerToken: "eyJhbGciOiJS..."
```

For mTLS:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: mirrord-cluster-cluster-c
  namespace: mirrord
  labels:
    operator.metalbear.co/remote-cluster-credentials: "true"
type: Opaque
stringData:
  tls.crt: "LS0tLS1CRUdJTi..."
  tls.key: "LS0tLS1CRUdJTi..."
```

{% hint style="info" %}
EKS IAM clusters do not need a Secret at all. They authenticate using the operator's IAM role and only need the cluster configuration in the ConfigMap.
{% endhint %}

---

## RBAC — How Permissions Work

When the Primary operator connects to a remote cluster, it needs permissions to list targets, create sessions, run health checks, and more. These permissions are set up automatically by the Helm chart on each remote cluster.

The chart creates two ClusterRoles (permission definitions):

| ClusterRole | What it allows | Where it's granted |
|-------------|---------------|-------------------|
| `mirrord-operator-envoy` | General operations: listing targets, managing parent sessions, syncing database branches, reading pods/deployments, health checks | All member clusters |
| `mirrord-operator-envoy-remote` | Creating and managing child sessions | Member clusters only (not Primary) |

A ClusterRole by itself doesn't grant anything — it only defines what actions are possible. ClusterRoleBindings connect the ClusterRole to an identity (a ServiceAccount or a group).

### How Bindings Differ by Auth Type

| Auth type | Identity bound to ClusterRoles | How it's set up |
|-----------|-------------------------------|----------------|
| Bearer token / mTLS | `mirrord-operator-envoy` ServiceAccount | `multiClusterMember=true` creates the bindings |
| EKS IAM | `mirrord-operator-envoy` Kubernetes group | `multiClusterMemberIamGroup=mirrord-operator-envoy` creates the bindings |

For EKS IAM, the Access Entry maps the IAM role to the `mirrord-operator-envoy` Kubernetes group. The ClusterRoleBindings grant permissions to that group. So the chain is: **IAM role -> Access Entry -> Kubernetes group -> ClusterRoleBinding -> ClusterRole -> permissions**.

In practice:

- **Bearer token / mTLS remote**: `multiClusterMember=true`
- **EKS IAM remote**: `multiClusterMember=true` + `multiClusterMemberIamGroup=mirrord-operator-envoy`

---

## Verify the Connection

After installing the operator on all clusters, verify that the Primary can reach all remote clusters:

```bash
kubectl --context <PRIMARY_CLUSTER> get mirrordoperators operator -o yaml
```

Look for the `status.connected_clusters` section:

```yaml
status:
  connected_clusters:
  - connected:
      license_fingerprint: S1hgumDqNoyDar...
      operator_version: 3.137.0
    lastCheck: "2026-01-27T09:22:55.824115967+00:00"
    name: cluster-a
  - connected:
      license_fingerprint: S1hgumDqNoyDar...
      operator_version: 3.137.0
    lastCheck: "2026-01-27T09:22:55.766848498+00:00"
    name: cluster-b
```

Each connected cluster should show `license_fingerprint` and `operator_version`. If a cluster is not connected, you'll see an `error` field instead.

---

## Token Refresh

| Auth type | Refresh mechanism | Notes |
|-----------|------------------|-------|
| Bearer Token | Automatic via TokenRequest API | Refreshed before expiration. Only the initial token is manual. |
| EKS IAM | Automatic every 10 minutes | Tokens are presigned STS URLs, valid for 15 minutes. No Secrets involved. |
| mTLS | **Not auto-refreshed** | You must rotate certificates manually before they expire. |

---

## FAQ

**Q: Do developers need to know about multi-cluster?**
A: No. The developer experience is identical to single-cluster. Developers run `mirrord exec` as usual and the operator handles everything.

**Q: Can the Primary cluster also run workloads?**
A: Yes. By default, the Primary cluster participates as a workload cluster. Set `managementOnly: true` only if the Primary has no application pods.

**Q: What happens if a remote cluster is unreachable?**
A: The session creation will fail. The operator reports connection errors in the `MirrordOperator` status (see Verify the Connection above).

**Q: Can I mix authentication methods?**
A: Yes. Each remote cluster can use a different `authType`. You can have some clusters using bearer tokens, others using EKS IAM, and others using mTLS.

**Q: Do I need the same operator version on all clusters?**
A: It's recommended. Version mismatches may cause compatibility issues.

**Q: Does the IAM role need AWS permissions?**
A: No. The IAM role used for EKS IAM authentication has zero AWS permissions. It's only used as an identity. All actual permissions come from Kubernetes RBAC on the remote clusters via the Access Entry and ClusterRoleBindings.
