---
title: mirrord Operator
description: Install and manage the mirrord Operator for Teams
tags:
  - team
  - enterprise
---

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

#### Feature-specific images

These images are only pulled when the corresponding feature is enabled:

| Image | Default | Tag | Description | Override |
|-------|---------|-----|-------------|----------|
| Kafka splitting sidecar | `ghcr.io/metalbear-co/operator-kafka-proxy` | Same as operator | JVM sidecar for Kafka splitting (only when `operator.kafkaSplittingSidecar.enabled` is true). | `operator.kafkaSplittingSidecar.image` |
| MSSQL tools | `ghcr.io/metalbear-co/mssql-tools` | `latest` | Sidecar for MSSQL DB branching (provides `sqlcmd`, `sqlpackage`, `bcp`). | Env `MSSQL_TOOLS_IMAGE` via `operator.extraEnv` |

#### DB branching default database images

DB branch pods pull a database image matching the engine. These are the defaults when no custom image is specified in the branch config:

| Engine | Default image | Override |
|--------|---------------|----------|
| PostgreSQL | `docker.io/library/postgres:{version}` | `operator.pgBranchConfig` - `dbPod.image` |
| MySQL | `docker.io/library/mysql:{version}` | `operator.mysqlBranchConfig` - `dbPod.image` |
| MongoDB | `docker.io/library/mongo:{version}` | `operator.mongodbBranchConfig` - `dbPod.image` |
| MSSQL | `mcr.microsoft.com/mssql/server:{version}` | `operator.mssqlBranchConfig` - `dbPod.image` |

#### Copying images

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

### GKE Autopilot

In GKE Autopilot the mirrord Operator can be run as a [customer-owned privileged workload](https://docs.cloud.google.com/kubernetes-engine/docs/concepts/about-autopilot-privileged-workloads#customer-owned-privileged-workloads).

Apply the following [WorkloadAllowlist](https://docs.cloud.google.com/kubernetes-engine/docs/how-to/autopilot-privileged-allowlists):

```yaml
apiVersion: auto.gke.io/v1
kind: WorkloadAllowlist
metadata:
  name: mirrord-agent
  annotations:
    autopilot.gke.io/no-connect: "true"
exemptions:
  - autogke-default-linux-capabilities
  - autogke-disallow-hostnamespaces
  - autogke-no-write-mode-hostpath
  - autogke-node-affinity-selector-limitation
matchingCriteria:
  hostPID: true
  containers:
    - name: mirrord-agent
      image: ghcr.io/metalbear-co/mirrord
      command:
        - ./mirrord-agent
      args:
        - "^.*$"
      env:
        - name: "^.*$"
      securityContext:
        capabilities:
          add:
            - SYS_ADMIN
            - SYS_PTRACE
            - NET_ADMIN
        privileged: false
      volumeMounts:
        - name: hostrun
          mountPath: /host/run
        - name: hostvar
          mountPath: /host/var
  volumes:
    - name: hostrun
      hostPath:
        path: /run
    - name: hostvar
      hostPath:
        path: /var
```

**Note:** some Operator configurations might produce mirrord-agent pods that don't match this specification.
In this case you will see mirrord-agent spawn errors in the Operator logs.
To have the correct WorkloadAllowlist embedded in these logs, merge this snippet into your mirrord Operator `values.yaml`:

```yaml
agent:
  annotations:
    cloud.google.com/generate-allowlist: "true"
```

## Verifying the Installation

```bash
mirrord operator status
```

All mirrord clients will now use the Operator automatically when running against the cluster.
