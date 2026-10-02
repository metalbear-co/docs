---
title: Targeting Amazon ECS Tasks
description: >-
  Run a service locally while it takes over the network, environment and
  identity of a matching Amazon ECS task, through the mirrord Operator on your
  EKS cluster.
tags:
  - alpha
  - enterprise
---

# Targeting Amazon ECS Tasks

Some services can't run in Kubernetes: they run on Amazon ECS or Fargate, next to the EKS cluster where you already run the mirrord Operator. With mirrord for ECS you run such a service **locally** while it takes over the network, environment and identity of a matching ECS task. There's no image to build or push, and nothing to redeploy.

The ECS task runs a small mirrord component inside its existing application container. Both the task and your local mirrord connect to the mirrord Operator through your EKS API server, and the Operator pairs them and relays mirrord traffic between them. You keep using the kubeconfig you already use for the Operator.

**When is this useful?**

1.  **Services on ECS, Operator on EKS**

    Part of your system runs on ECS and part on EKS. You already use the mirrord Operator for the Kubernetes services, and want the same workflow for the ECS ones.
2.  **Resources only reachable from the task**

    Your ECS service talks to databases, queues or internal APIs that are only reachable from its VPC. Running it locally through mirrord sends its outgoing connections through the task, so the local process reaches them too.
3.  **Shared staging environments**

    Several developers work on the same ECS service in one environment. Each developer steals only the requests that carry their own session key, so regular traffic and other developers are unaffected.

{% hint style="info" %}
mirrord for ECS has to be enabled in the mirrord Operator and set up on each ECS service you want to target. If you're a platform engineer setting it up, see [Amazon ECS Setup](ecs-on-eks-setup.md).
{% endhint %}

***

## Using mirrord with an ECS Service

You don't need anything ECS-specific on your machine beyond a kubeconfig for the EKS cluster that runs the mirrord Operator. If you already use the Operator there, you have one.

Create a `mirrord.json` in your project:

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

* [`operator: true`](https://metalbear.com/mirrord/docs/config/options#root-operator) together with a `serverless/` target makes mirrord reach the ECS task through the Operator, using your kubeconfig's current context.
* [`target.path`](https://metalbear.com/mirrord/docs/config/options#target-path) is `serverless/` followed by the service name, and [`target.namespace`](https://metalbear.com/mirrord/docs/config/options#target-namespace) is the environment the service runs in. These are names your platform team chose when setting up the ECS service, not Kubernetes resources or namespaces. Ask them for the values.
* [`key`](https://metalbear.com/mirrord/docs/config/options#root-key) identifies your session. It's substituted into `{{ key }}` in the HTTP filter, so only requests carrying `baggage: mirrord-session=<YOUR_SESSION_KEY>` reach your local process. Regular traffic and other developers' requests keep going to the ECS task. See [Filtering Incoming Traffic](../incoming-traffic/filter-incoming-traffic.md) for other filters.
* `feature.network.outgoing` sends your local process's outgoing connections through the ECS task, so they reach whatever the task can reach.
* `feature.env` gives your local process the ECS task's environment variables.

Then run your service:

```bash
mirrord exec -f mirrord.json -- <YOUR_COMMANDLINE>
```

To send a request to your local process, add the header to it, for example with `curl -H "baggage: mirrord-session=<YOUR_SESSION_KEY>" ...`. While browsing, the [mirrord browser extension](../incoming-traffic/debug-from-browser.md) can inject the header for you.

For every option, see the [configuration reference](https://metalbear.com/mirrord/docs/config/options).

***

## How It Works

The mirrord Operator hosts **sessions-manager**, the service that pairs a developer's local mirrord with an ECS task and relays mirrord traffic between them. It's part of the Operator and is turned on with a Helm value, so there's no additional deployment, service or load balancer.

```
 developer machine                     EKS VPC                                ECS VPC
┌───────────────────┐  kubeconfig   ┌───────────────────────────────┐      ┌───────────────────────────┐
│ mirrord exec      │─────────────► │ EKS API server endpoint       │      │ application container     │
│ (local process)   │               │   │ aggregated API            │      │ + mirrord remote          │
└───────────────────┘               │   ▼                           │      │   bootstrap (LD_PRELOAD)  │
                                    │ mirrord Operator              │      └─────────────┬─────────────┘
                                    │   (sessions-manager inside)   │                    │ HTTPS, IAM-derived
                                    └───────────────▲───────────────┘                    │ bearer token
                                                    │          Transit Gateway           │
                                                    └────────────────────────────────────┘
```

A session goes through these steps:

1. **The ECS task registers.** When the task starts, the mirrord remote bootstrap, loaded into the application container, connects to the EKS API server and registers the task under its service and environment names. It authenticates with a token derived from the task's IAM role.
2. **You start mirrord.** `mirrord exec` connects to the same EKS API server with your kubeconfig and asks for a session with the service and environment in your `mirrord.json`.
3. **The API server authenticates both sides.** It authorizes each one with Kubernetes RBAC and forwards the requests to the Operator.
4. **The Operator pairs them.** It assigns both sides to the same session and gives each a single-use credential for it.
5. **Both sides open the session's data plane.** Each one opens a WebSocket to the session through the API server, and the Operator relays mirrord traffic between them. From here, mirrord behaves as it does with a Kubernetes target: incoming requests matching your filter go to your local process, and its outgoing traffic leaves from the ECS task.

Both sides only make outbound HTTPS connections, and only to the EKS API server. Neither side needs a network path to the other, and the Operator isn't exposed outside the cluster. For how each side authenticates, see [How authentication works](ecs-on-eks-setup.md#how-authentication-works).

***

## Limitations

* **One ECS task per session.** Your session is served by one registered ECS task. If the service runs several tasks, only requests that land on that task can be stolen or mirrored. For testing, scale the service to one task or route your test traffic to a specific task.
* **Development traffic only.** Session traffic flows through the EKS API server. That's fine for development, but don't use a mirrord session for load testing.
* **Operator restarts end sessions.** Restarting or upgrading the Operator ends active sessions. The ECS task registers again on its own; rerun `mirrord exec`.
* **Long-lived connections.** Any proxy or firewall between the ECS task and the EKS API server must not buffer responses and needs an idle timeout of at least 300 seconds.

***

## What's Next?

To set up mirrord for ECS, see the [Amazon ECS Setup](ecs-on-eks-setup.md) guide, which covers the Helm value, RBAC, the EKS access entry, the network path and the ECS task definition.

{% content-ref url="ecs-on-eks-setup.md" %}
[ecs-on-eks-setup.md](ecs-on-eks-setup.md)
{% endcontent-ref %}
