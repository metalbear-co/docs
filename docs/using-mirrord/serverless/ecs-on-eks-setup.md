---
title: "Amazon ECS Setup"
description: "Step-by-step guide to letting developers target Amazon ECS tasks through the mirrord Operator on EKS: enable sessions-manager, map the ECS task role into the cluster, connect the networks, and add mirrord to the task definition."
tags:
  - alpha
  - enterprise
---

This guide sets up [mirrord for ECS](README.md) for services running on Amazon ECS or Fargate, when you already run the mirrord Operator on an EKS cluster. At a glance, the setup is:

1. Enable sessions-manager in the Operator with the `operator.sessionsManager` Helm value ([Enable sessions-manager in the Operator](#enable-sessions-manager-in-the-operator)).
2. Bind the `mirrord-ecs-workloads` group to the chart's `mirrord-operator-sessions-manager-agent` ClusterRole ([Grant the ECS workload access](#grant-the-ecs-workload-access)).
3. Map the ECS task role into that group with an EKS access entry ([Map the ECS task role into the cluster](#map-the-ecs-task-role-into-the-cluster)).
4. Make the EKS API server's private endpoint reachable and resolvable from the ECS VPC over a Transit Gateway ([Make the EKS API server reachable from ECS](#make-the-eks-api-server-reachable-from-ecs)).
5. Add the mirrord remote bootstrap and its environment variables to the ECS task definition ([Add mirrord to the ECS task](#add-mirrord-to-the-ecs-task)).
6. Give developers their `mirrord.json` ([Configure developers](#configure-developers)).
7. [Verify](#verify) that the task registers and a developer session works.

Enabling sessions-manager doesn't add a deployment, service or load balancer: it's part of the Operator, served through the Operator's existing API. Both the ECS task and developers only make outbound HTTPS connections to the EKS API server endpoint, and neither needs a network path to the other.

## How authentication works

{% hint style="info" %}
This section is for whoever reviews the setup, such as your security team. To start the setup, skip to [Prerequisites](#prerequisites).
{% endhint %}

Both sides authenticate as Kubernetes identities through your EKS API server. Access is granted with ordinary Kubernetes RBAC and recorded in the cluster's audit log. There are no shared secrets to create, distribute or rotate.

**Developers** reach the Operator exactly like for every other mirrord Operator feature: the API server authenticates them from their kubeconfig (for example with `aws eks get-token`), authorizes them with RBAC, and forwards the request to the Operator through its aggregated API.

**The ECS task** does the same thing `aws eks get-token` does, without the AWS CLI:

1. The mirrord remote bootstrap reads the task role's credentials from the ECS container credentials endpoint, through the standard AWS SDK credential chain. They're refreshed automatically.
2. It signs, locally and without any network call, a presigned STS `GetCallerIdentity` request that includes the header `x-k8s-aws-id: <cluster name>`, and sends it to the EKS API server as a bearer token.
3. EKS validates the token with STS, resolves the IAM role, and looks up its [access entry](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html), which gives it a Kubernetes username and groups.
4. Kubernetes RBAC decides whether that identity may use the sessions-manager resources, and the request is forwarded to the Operator.

EKS tokens are valid for 15 minutes. The bootstrap signs a fresh one 5 minutes before the current one expires, which is local and cheap, and retries with backoff if the task role's credentials are briefly unavailable. The API server authenticates a request only when it starts, so the long-lived connections of an ongoing session aren't cut when a token expires; only new requests use the new token.

The task role needs **no IAM permissions** for this: `sts:GetCallerIdentity` is allowed for every AWS identity, and the ECS task never calls STS or EKS APIs itself.

**The Operator** serves two cluster-scoped resources on its existing `operator.metalbear.co/v1alpha1` API:

| Resource | Verb | Used for |
| --- | --- | --- |
| `sessionassignments` | `proxy` | Each side registers and waits, on a long-lived Server-Sent Events stream, to be paired. |
| `sessiondataplanes` | `get` | Each side opens a WebSocket to its assigned session; the Operator relays mirrord traffic between the two. |

The Operator receives the caller's identity from the API server, like it does for every other Operator request, and implements no authentication of its own. Each data-plane connection is also bound to its session by a single-use credential delivered with the assignment, so an identity allowed to use `sessiondataplanes` can't attach to another caller's session.

---

## Prerequisites

Before you start, make sure you have:

1. An EKS cluster with the mirrord Operator `<OPERATOR_VERSION>+` installed through its Helm chart `<CHART_VERSION>+`, and a mirrord Operator license.
2. The cluster's authentication mode set to `API` or `API_AND_CONFIG_MAP`, so access entries can be used. [Map the ECS task role into the cluster](#map-the-ecs-task-role-into-the-cluster) shows how to check and change it.
3. The ECS VPC and the EKS VPC attached to the same Transit Gateway.
4. An IAM **task role** on the ECS service you want to target (`taskRoleArn` in the task definition). This is not the execution role.
5. `kubectl`, `helm` and the AWS CLI, with permission to manage the Operator Helm release, cluster RBAC, EKS access entries, VPC networking and the ECS task definition.
6. On each developer machine: the mirrord CLI and a kubeconfig for the cluster. Developers who already use the mirrord Operator have both.

Throughout this guide, replace:

| Placeholder | Value |
| --- | --- |
| `<CLUSTER_NAME>` | The EKS cluster's name |
| `<REGION>` | The EKS cluster's AWS region |
| `<TASK_ROLE_ARN>` | The ARN of the ECS service's task role |
| `<ECS_VPC_CIDR>` | The CIDR range of the ECS tasks' VPC |
| `<YOUR_SERVICE_NAME>` | A name for the ECS service you target, e.g. `payments` |
| `<YOUR_ENVIRONMENT>` | A name for the environment the ECS service runs in, e.g. `staging` |

`<YOUR_SERVICE_NAME>` and `<YOUR_ENVIRONMENT>` are free-form: they're how a developer names the ECS task they want. They must be identical on the ECS task and in developers' `mirrord.json`.

---

## Enable sessions-manager in the Operator

Add `operator.sessionsManager=true` to your existing Operator Helm release:

```bash
helm upgrade mirrord-operator metalbear/mirrord-operator \
  --namespace mirrord \
  --reuse-values \
  --set operator.sessionsManager=true
```

Confirm the Operator now serves both resources:

```bash
kubectl get --raw /apis/operator.metalbear.co/v1alpha1 | grep -o '"name":"session[a-z]*"'
# "name":"sessionassignments"
# "name":"sessiondataplanes"
```

Enabling it also grants `proxy` on `sessionassignments` and `get` on `sessiondataplanes` in the chart's `mirrord-operator-user`, `mirrord-operator-ci` and `mirrord-operator-user-basic` ClusterRoles. Developers already bound to one of those roles need no further RBAC changes.

It also creates the `mirrord-operator-sessions-manager-agent` ClusterRole, which grants only those two permissions. The ECS task is bound to it in the next step.

## Grant the ECS workload access

Bind the chart's `mirrord-operator-sessions-manager-agent` ClusterRole to a group that the ECS task role will be mapped into in the next step. Save this as `mirrord-ecs-workload-rbac.yaml`:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: mirrord-ecs-workload
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: mirrord-operator-sessions-manager-agent
subjects:
  - apiGroup: rbac.authorization.k8s.io
    kind: Group
    name: mirrord-ecs-workloads
```

and apply it:

```bash
kubectl apply -f mirrord-ecs-workload-rbac.yaml
```

The role grants `proxy` on `sessionassignments` (registering and waiting for sessions, a long-lived request) and `get` on `sessiondataplanes` (connecting to an assigned session, a WebSocket), and nothing else in the cluster: the ECS task can't read, list or modify any other resource. These resources are cluster-scoped, so the binding has to be a ClusterRoleBinding.

{% hint style="info" %}
Bind the chart's role rather than defining your own: it stays in sync with what the Operator requires when you upgrade the chart.
{% endhint %}

## Map the ECS task role into the cluster

An [EKS access entry](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html) tells EKS which Kubernetes identity an IAM role authenticates as.

If the cluster still uses only the `aws-auth` ConfigMap, first allow access entries alongside it. This doesn't change any existing `aws-auth` mapping:

```bash
aws eks describe-cluster --name <CLUSTER_NAME> --region <REGION> \
  --query 'cluster.accessConfig.authenticationMode' --output text

# Only if the above printed CONFIG_MAP:
aws eks update-cluster-config --name <CLUSTER_NAME> --region <REGION> \
  --access-config authenticationMode=API_AND_CONFIG_MAP
```

Then create the access entry for the task role, placing it in the group bound in the previous step:

```bash
aws eks create-access-entry \
  --cluster-name <CLUSTER_NAME> \
  --region <REGION> \
  --principal-arn <TASK_ROLE_ARN> \
  --type STANDARD \
  --username mirrord-ecs-<YOUR_SERVICE_NAME> \
  --kubernetes-groups mirrord-ecs-workloads
```

* `--principal-arn` is the **role** ARN (`arn:aws:iam::<account>:role/<name>`), not an `assumed-role` session ARN, and it must be the task role, not the execution role.
* Don't associate any access policy with this entry. Its permissions come only from the ClusterRoleBinding in the previous step.
* `--username` is how the task appears in the Kubernetes audit log and in `kubectl auth can-i`. Any name works; including the service name makes audit entries easy to attribute.

Check the result by impersonating that identity:

```bash
kubectl auth can-i proxy sessionassignments.operator.metalbear.co \
  --as mirrord-ecs-<YOUR_SERVICE_NAME> --as-group mirrord-ecs-workloads      # yes
kubectl auth can-i get sessiondataplanes.operator.metalbear.co \
  --as mirrord-ecs-<YOUR_SERVICE_NAME> --as-group mirrord-ecs-workloads      # yes
kubectl auth can-i list pods -A \
  --as mirrord-ecs-<YOUR_SERVICE_NAME> --as-group mirrord-ecs-workloads      # no
```

## Make the EKS API server reachable from ECS

The ECS task connects to the cluster's **private** API server endpoint over the Transit Gateway. The private endpoint is a set of network interfaces EKS places in the cluster VPC's subnets; they carry the cluster security group.

### Enable the private endpoint

```bash
aws eks describe-cluster --name <CLUSTER_NAME> --region <REGION> \
  --query 'cluster.resourcesVpcConfig.{private:endpointPrivateAccess,public:endpointPublicAccess}'

# Only if `private` is false:
aws eks update-cluster-config --name <CLUSTER_NAME> --region <REGION> \
  --resources-vpc-config endpointPrivateAccess=true
```

Enabling private access doesn't change public access, so developers who use the public endpoint are unaffected.

### Routing

* The Transit Gateway route table associated with the ECS VPC attachment routes the EKS VPC CIDR to the EKS VPC attachment, and the one associated with the EKS VPC attachment routes `<ECS_VPC_CIDR>` back (static routes or propagation).
* The route tables of the ECS tasks' subnets send the EKS VPC CIDR to the Transit Gateway.
* The route tables of the EKS subnets holding the endpoint interfaces send `<ECS_VPC_CIDR>` to the Transit Gateway.

### Firewalling

* The cluster security group allows inbound TCP 443 from `<ECS_VPC_CIDR>`:

  ```bash
  CLUSTER_SG=$(aws eks describe-cluster --name <CLUSTER_NAME> --region <REGION> \
    --query 'cluster.resourcesVpcConfig.clusterSecurityGroupId' --output text)
  aws ec2 authorize-security-group-ingress --region <REGION> --group-id "$CLUSTER_SG" \
    --protocol tcp --port 443 --cidr <ECS_VPC_CIDR>
  ```

  Use a CIDR rule: a security group in the ECS VPC can only be referenced across a Transit Gateway if security group referencing is turned on for it.
* The ECS tasks' security group allows outbound TCP 443 to the EKS VPC CIDR.
* Network ACLs on both sides, and any firewall or inspection appliance on the Transit Gateway path, allow this traffic and its return traffic.

### DNS

The cluster endpoint's hostname (e.g. `https://ABC123.gr7.<REGION>.eks.amazonaws.com`) resolves to the private endpoint only from inside the EKS VPC. Queried from the ECS VPC, it resolves to the public endpoint instead (or doesn't resolve at all when public access is off), and traffic wouldn't take the Transit Gateway. Forward the name to the EKS VPC's resolver:

1. In the EKS VPC, create a Route 53 Resolver **inbound endpoint**, with a security group allowing DNS (TCP and UDP 53) from `<ECS_VPC_CIDR>`.
2. In the ECS VPC, create a Route 53 Resolver **outbound endpoint** and a **forwarding rule** for the endpoint's hostname (e.g. `ABC123.gr7.<REGION>.eks.amazonaws.com`) that targets the inbound endpoint's IP addresses, and associate the rule with the ECS VPC.

If your organization already centralizes DNS through Resolver endpoints on the Transit Gateway, add the forwarding rule there instead. Either way, from inside the ECS VPC the hostname must resolve to IP addresses within the EKS VPC CIDR.

### Long-lived connections

A session holds its HTTPS connections open for as long as the developer runs it. The Transit Gateway closes TCP connections idle for 350 seconds; the Operator sends a keepalive on each registration stream every 15 seconds, and data-plane connections carry mirrord's own periodic traffic, so sessions stay well within that.

{% hint style="warning" %}
Any firewall or proxy on the path between the ECS task and the EKS API server needs an idle timeout of at least 300 seconds and must not buffer responses.
{% endhint %}

## Add mirrord to the ECS task

The mirrord remote bootstrap library is loaded into your existing application container with `LD_PRELOAD`. It doesn't need to be baked into your image: a non-essential setup container copies it into a shared task volume before the application container starts, the ECS equivalent of a Kubernetes init container.

Collect the cluster's endpoint and certificate authority:

```bash
aws eks describe-cluster --name <CLUSTER_NAME> --region <REGION> \
  --query 'cluster.{endpoint:endpoint,ca:certificateAuthority.data}'
```

Then update the task definition:

```json
{
  "taskRoleArn": "<TASK_ROLE_ARN>",
  "volumes": [
    { "name": "mirrord" }
  ],
  "containerDefinitions": [
    {
      "name": "install-mirrord-remote-bootstrap",
      "image": "ghcr.io/metalbear-co/mirrord-remote-bootstrap:<VERSION>",
      "essential": false,
      "entryPoint": ["/bin/sh", "-c"],
      "command": [
        "cp /opt/mirrord/lib/libmirrord_remote_bootstrap.so /mirrord/libmirrord_remote_bootstrap.so"
      ],
      "mountPoints": [
        { "sourceVolume": "mirrord", "containerPath": "/mirrord" }
      ]
    },
    {
      "name": "app",
      "image": "<YOUR_APPLICATION_IMAGE>",
      "dependsOn": [
        { "containerName": "install-mirrord-remote-bootstrap", "condition": "SUCCESS" }
      ],
      "mountPoints": [
        { "sourceVolume": "mirrord", "containerPath": "/opt/mirrord/lib", "readOnly": true }
      ],
      "environment": [
        { "name": "LD_PRELOAD", "value": "/opt/mirrord/lib/libmirrord_remote_bootstrap.so" },
        { "name": "MIRRORD_REMOTE_SERVICE", "value": "<YOUR_SERVICE_NAME>" },
        { "name": "MIRRORD_REMOTE_ENVIRONMENT", "value": "<YOUR_ENVIRONMENT>" },
        { "name": "MIRRORD_OPERATOR_API_URL", "value": "<CLUSTER_ENDPOINT>" },
        { "name": "MIRRORD_OPERATOR_EKS_CLUSTER_NAME", "value": "<CLUSTER_NAME>" },
        { "name": "MIRRORD_OPERATOR_API_CA_DATA", "value": "<CLUSTER_CA_DATA>" }
      ]
    }
  ]
}
```

| Variable | Value |
| --- | --- |
| `LD_PRELOAD` | The path of the bootstrap library in the shared volume, as above. |
| `MIRRORD_REMOTE_SERVICE` | `<YOUR_SERVICE_NAME>`. Developers target it as `serverless/<YOUR_SERVICE_NAME>`. |
| `MIRRORD_REMOTE_ENVIRONMENT` | `<YOUR_ENVIRONMENT>`. Developers set it as `target.namespace`. |
| `MIRRORD_OPERATOR_API_URL` | The `endpoint` printed above, e.g. `https://ABC123.gr7.<REGION>.eks.amazonaws.com`. |
| `MIRRORD_OPERATOR_EKS_CLUSTER_NAME` | `<CLUSTER_NAME>`. It's signed into the token, and EKS rejects tokens for another cluster. |
| `MIRRORD_OPERATOR_API_CA_DATA` | The `ca` printed above (base64-encoded PEM). The API server's certificate is issued by the cluster's own CA, not a public one. |

{% hint style="warning" %}
Don't also set `MIRRORD_SESSIONS_MANAGER_URL` on the task. It selects a standalone sessions-manager, and the bootstrap refuses to start when both it and `MIRRORD_OPERATOR_API_URL` are set.
{% endhint %}

The token is signed for the AWS region in `AWS_REGION`, which ECS sets on Fargate tasks. Otherwise the bootstrap falls back to `AWS_DEFAULT_REGION`, then to the region in the `MIRRORD_OPERATOR_API_URL` hostname, so an EKS endpoint needs no extra configuration.

Use the remote-bootstrap image version that matches your developers' mirrord CLI version. Because the setup container is non-essential with a `SUCCESS` dependency, a failed copy prevents the application container from starting, so you never silently run without mirrord.

No AWS credentials, access keys or secrets are added to the task: the bootstrap uses the task role credentials ECS already provides.

Register the new task definition revision and update the service to use it. Your application image and your other services are unchanged.

### Writable temporary directory

{% hint style="warning" %}
**Container requirement.** The application container needs a writable temporary directory (`$TMPDIR`, `/tmp` by default) in which files can be executed. The bootstrap extracts the mirrord agent there, and keeps its local socket and the current EKS token there.

If the task definition sets `readonlyRootFilesystem`, add a task volume and mount it at `/tmp` in the application container.
{% endhint %}

### Sharing settings across services

ECS has no cluster-wide environment variables, so every task definition you target needs the variables above. To keep the values that are the same for every service in one place, put them in an [environment file](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/use-environment-file.html) in S3:

```bash
cat > mirrord.env <<EOF
MIRRORD_OPERATOR_API_URL=<CLUSTER_ENDPOINT>
MIRRORD_OPERATOR_EKS_CLUSTER_NAME=<CLUSTER_NAME>
MIRRORD_OPERATOR_API_CA_DATA=<CLUSTER_CA_DATA>
MIRRORD_REMOTE_ENVIRONMENT=<YOUR_ENVIRONMENT>
EOF
aws s3 cp mirrord.env s3://<BUCKET>/mirrord/<CLUSTER_NAME>.env
```

and reference it from each application container instead of listing those variables:

```json
"environmentFiles": [
  { "type": "s3", "value": "arn:aws:s3:::<BUCKET>/mirrord/<CLUSTER_NAME>.env" }
]
```

`LD_PRELOAD` and `MIRRORD_REMOTE_SERVICE` stay in each container's `environment`, since they differ per service. Tasks read the file when they start, so redeploy the services after changing it. The task's **execution role** (not the task role) needs `s3:GetObject` on the file and `s3:GetBucketLocation` on the bucket. On Fargate, environment files need platform version `1.4.0` or later.

## Configure developers

Developers need nothing ECS-specific beyond their existing kubeconfig for the cluster:

```bash
aws eks update-kubeconfig --name <CLUSTER_NAME> --region <REGION>
```

Each developer creates a `mirrord.json` in their project, with `target.path` and `target.namespace` matching `MIRRORD_REMOTE_SERVICE` and `MIRRORD_REMOTE_ENVIRONMENT` on the ECS task:

```json
{
  "operator": true,
  "target": {
    "path": "serverless/<YOUR_SERVICE_NAME>",
    "namespace": "<YOUR_ENVIRONMENT>"
  },
  "key": "<YOUR_SESSION_KEY>",
  "feature": {
    "env": true,
    "network": {
      "outgoing": true,
      "incoming": {
        "mode": "steal",
        "http_filter": {
          "header_filter": "^baggage: .*mirrord-session={{ key }}.*$"
        }
      }
    }
  }
}
```

and runs their service locally:

```bash
mirrord exec -f mirrord.json -- <YOUR_COMMANDLINE>
```

Only requests carrying `baggage: mirrord-session=<YOUR_SESSION_KEY>` reach the local process; other developers and regular traffic hitting the same task are unaffected. [Using mirrord with an ECS Service](README.md#using-mirrord-with-an-ecs-service) explains each field.

---

## Verify

1. **Operator**: sessions-manager is enabled. The `kubectl get --raw` check in [Enable sessions-manager in the Operator](#enable-sessions-manager-in-the-operator) lists both resources.
2. **ECS task registered**: after the new task starts, the Operator logs its registration:

   ```bash
   kubectl -n mirrord logs deployment/mirrord-operator -f | grep -i session
   ```

   With [EKS control plane audit logging](https://docs.aws.amazon.com/eks/latest/userguide/control-plane-logs.html) enabled, requests from the task appear in the audit log with user `mirrord-ecs-<YOUR_SERVICE_NAME>` on resource `sessionassignments`.
3. **Developer session**: `mirrord exec` connects, and a request with the `baggage` header reaches the local process.

## Infrastructure as code

If you manage your infrastructure with Terraform, each step maps to standard resources:

| Step | Terraform resources |
| --- | --- |
| Enable sessions-manager | `helm_release` for the Operator, with `operator.sessionsManager = true` |
| Grant the ECS workload access | `kubernetes_cluster_role_binding_v1` |
| Map the ECS task role | `aws_eks_access_entry` (`type = "STANDARD"`, `kubernetes_groups = ["mirrord-ecs-workloads"]`) |
| Routing | `aws_ec2_transit_gateway_vpc_attachment`, `aws_route` |
| Firewalling | `aws_vpc_security_group_ingress_rule`, `aws_vpc_security_group_egress_rule` |
| DNS | `aws_route53_resolver_endpoint` (inbound and outbound), `aws_route53_resolver_rule`, `aws_route53_resolver_rule_association` |
| ECS task | `aws_ecs_task_definition` |

In CloudFormation, the access entry is `AWS::EKS::AccessEntry`.

---

## Operating notes

* **Operator restarts and upgrades** end active sessions. The ECS task registers again on its own; developers rerun `mirrord exec`. If connections are cut during rollouts, raise the chart's `operator.terminationGracePeriodSeconds` (default `25`) to give sessions time to close cleanly.
* **Traffic path**: session traffic flows through the EKS API server. It's suited to development traffic, not to load testing through a mirrord session.
* **Single task**: a developer's session is served by one registered ECS task. If the service runs several tasks, only requests that land on that task can be stolen or mirrored. For testing, scale the service to one task or route your test traffic to a specific task.
* **Revoking access**: delete the access entry (`aws eks delete-access-entry`) or the `mirrord-ecs-workload` ClusterRoleBinding. New requests are refused immediately; to also end open sessions, restart the Operator.

## Troubleshooting

The ECS task's messages appear in the application container's logs.

| Symptom | Likely cause |
| --- | --- |
| The ECS task logs a connection timeout to the API server | Transit Gateway routes, security groups or NACLs ([Make the EKS API server reachable from ECS](#make-the-eks-api-server-reachable-from-ecs)). |
| The endpoint hostname resolves to public IPs from the ECS VPC | The DNS forwarding rule is missing or not associated with the ECS VPC ([DNS](#dns)). |
| TLS or certificate verification error | `MIRRORD_OPERATOR_API_CA_DATA` is missing or belongs to another cluster. |
| `401 Unauthorized` | No access entry for the role, the access entry uses the execution role instead of the task role, `MIRRORD_OPERATOR_EKS_CLUSTER_NAME` doesn't match the cluster, or the authentication mode is still `CONFIG_MAP`. |
| `403 Forbidden` on `sessionassignments` | The access entry's group isn't `mirrord-ecs-workloads`, or the ClusterRoleBinding is missing. Check with `kubectl auth can-i` ([Map the ECS task role into the cluster](#map-the-ecs-task-role-into-the-cluster)). |
| `404 Not Found`, or mirrord says the Operator doesn't serve sessions-manager | `operator.sessionsManager` isn't enabled, or the Operator version predates it. |
| The ECS task registers but the developer is never paired | `MIRRORD_REMOTE_SERVICE`/`MIRRORD_REMOTE_ENVIRONMENT` on the task don't match `target.path`/`target.namespace` in `mirrord.json`. |
| The application starts without mirrord | The setup container failed or its `dependsOn` condition isn't wired up; check its logs and exit code. |
| `MIRRORD_SESSIONS_MANAGER_URL and MIRRORD_OPERATOR_API_URL are mutually exclusive` | The task sets both; remove `MIRRORD_SESSIONS_MANAGER_URL`. |
| `MIRRORD_OPERATOR_EKS_CLUSTER_NAME is required when MIRRORD_OPERATOR_API_URL is set` (or `MIRRORD_OPERATOR_API_CA_DATA`) | A variable from [Add mirrord to the ECS task](#add-mirrord-to-the-ecs-task) is missing on the task. |
| `no AWS region to sign the EKS token for` | No `AWS_REGION` or `AWS_DEFAULT_REGION`, and `MIRRORD_OPERATOR_API_URL` isn't an EKS endpoint hostname. Set `AWS_REGION`. |
| `No AWS credentials provider found in environment` | The task definition has no `taskRoleArn`. |
| `Token refresh failed, will retry` | Fetching the task role's credentials failed; the current token stays in use while it retries. If it keeps failing for 15 minutes, new requests get `401 Unauthorized`. |
| `Read-only file system` or `Permission denied` under `/tmp` | The application container has no writable temporary directory ([Writable temporary directory](#writable-temporary-directory)). |

To check name resolution and reachability from inside a running task, use [ECS Exec](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-exec.html) if it's enabled for the service. The endpoint hostname must resolve to addresses within the EKS VPC CIDR, and TCP 443 on it must be reachable.

## Reference documentation

* [EKS access entries](https://docs.aws.amazon.com/eks/latest/userguide/access-entries.html)
* [EKS cluster endpoint access control](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html)
* [Route 53 Resolver forwarding rules](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/resolver-forwarding-outbound-queries.html)
* [Security](../../managing-mirrord/security.md)
* [Filtering Incoming Traffic](../incoming-traffic/filter-incoming-traffic.md)
* [Configuration options](https://metalbear.com/mirrord/docs/config/options)
