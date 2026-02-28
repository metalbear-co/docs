---
title: mirrord Operator
description: Install and manage the mirrord Operator for Teams
tags:
  - team
  - enterprise
---

# mirrord Operator

The mirrord Operator is a Kubernetes operator that runs persistently in your cluster and manages mirrord sessions. It's the central component that enables all **[Teams]** features.

## Why the Operator?

In the open-source version of mirrord, each session is standalone - mirrord injects itself into the local process and creates an agent pod directly. This works well for individual use, but doesn't support coordination between users.

The Operator solves this by acting as a centralized control plane:

- **Better security** - Users no longer need permissions to create privileged pods. Only the Operator does. Permissions are managed through Kubernetes RBAC.
- **Concurrent use** - The Operator coordinates multiple mirrord sessions on the same cluster, preventing conflicts.
- **Advanced features** - Support for [policies](../sharing-the-cluster/policies.md), [profiles](../sharing-the-cluster/profiles.md), [queue splitting](../sharing-the-cluster/queue-splitting.md), [DB branching](../sharing-the-cluster/db-branching.md), and more.

![mirrord for Teams - Architecture](/docs/overview/teams/operator-architecture.svg)

## Installation

You'll need a mirrord for Teams license. [Register here](https://app.metalbear.com) to get started.

### Helm

Add the MetalBear Helm repository:

```bash
helm repo add metalbear https://metalbear-co.github.io/charts
```

Download the accompanying `values.yaml`:

```bash
curl https://raw.githubusercontent.com/metalbear-co/charts/main/mirrord-operator/values.yaml --output values.yaml
```

Set `license.key` to your key, then install:

```bash
helm install -f values.yaml mirrord-operator metalbear/mirrord-operator
```

### Using an Internal Registry (Optional)

Using an internal registry reduces startup time, ingress costs, and removes dependency on GitHub's registry.

We recommend [regctl](https://regclient.org/) for copying multi-arch images:

```sh
# Get the operator image version
IMAGE_VERSION=$(helm show chart metalbear/mirrord-operator | grep 'appVersion:' | awk '{print $2}')

# Copy operator image
regctl image copy ghcr.io/metalbear-co/operator:$IMAGE_VERSION your-registry/operator:$IMAGE_VERSION

# Get and copy agent image
AGENT_IMAGE_VERSION=$(regctl image config ghcr.io/metalbear-co/operator:$IMAGE_VERSION | jq -r '.config.Labels."metalbear.mirrord.version"')
regctl image copy ghcr.io/metalbear-co/mirrord:$AGENT_IMAGE_VERSION your-registry/mirrord:$AGENT_IMAGE_VERSION
```

Then set in your `values.yaml`:

```yaml
operator:
  image: your-registry/operator
agent:
  image:
    registry: your-registry/mirrord
```

### OpenShift

Apply the following SecurityContextConstraints:

```yaml
kind: SecurityContextConstraints
apiVersion: security.openshift.io/v1
metadata:
  name: scc-mirrord
allowHostPID: true
allowPrivilegedContainer: false
allowHostDirVolumePlugin: true
allowedCapabilities: ["SYS_ADMIN", "SYS_PTRACE", "NET_RAW", "NET_ADMIN"]
runAsUser:
  type: RunAsAny
seLinuxContext:
  type: MustRunAs
users:
  - system:serviceaccount:mirrord:mirrord-operator
  - system:serviceaccount:mirrord:default
```

## Verifying the Installation

```bash
mirrord operator status
```

All mirrord clients will now use the Operator automatically when running against the cluster.
