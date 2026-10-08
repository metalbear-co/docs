---
title: Serverless Workloads
description: >-
  Run a service locally while it takes over the network and environment of a
  workload running outside Kubernetes, such as an Amazon ECS task.
tags:
  - experimental
  - enterprise
---

# Serverless Workloads

{% hint style="warning" %}
Serverless workloads are **experimental**. They're available on request, and behavior, configuration and resource names may change without notice. Don't rely on them for anything beyond development environments. To try them, contact us, and we'll provide the [versions and images](#values-provided-by-metalbear) they need.
{% endhint %}

Some services don't run in Kubernetes, but on platforms such as Amazon ECS and Fargate. mirrord calls these **serverless workloads**. You run such a service **locally** while it takes over the network and environment of the deployed one. There's no image to build or push, and nothing to redeploy.

**When is this useful?**

1.  **Services outside Kubernetes**

    Part of your system runs on ECS and part on Kubernetes. You already use mirrord for the Kubernetes services, and want the same workflow for the others.
2.  **Resources only reachable from the workload**

    Your service talks to databases, queues or internal APIs that are only reachable from its network. Running it locally through mirrord sends its outgoing connections through the serverless workload, so the local process reaches them too.
3.  **Shared staging environments**

    Several developers work on the same service in one environment. Each developer steals only the requests that carry their own session key, so regular traffic and other developers are unaffected.

***

## Components

A serverless workload session has three parts:

* **Your local mirrord**, started with `mirrord exec` as usual.
* **The mirrord remote bootstrap**, a library loaded into the workload's existing application container. It starts a mirrord agent beside your application and registers it, under a service and environment name, with sessions-manager.
* **Sessions-manager**, which pairs your local mirrord with a registered workload and relays mirrord traffic between them. Both sides only make outbound connections to sessions-manager, so neither needs a network path to the other.

Where sessions-manager runs is the [deployment mode](#deployment-modes).

## Deployment Modes

| Mode | Sessions-manager runs | Status |
| --- | --- | --- |
| **Operator-hosted** | Inside the [mirrord Operator](../../managing-mirrord/operator.md) on your EKS cluster, enabled with a Helm value. Both sides reach it through your cluster's API server, and authenticate as Kubernetes identities. | Experimental |
| **MetalBear Cloud** | Hosted by MetalBear, so there's nothing for you to install or operate. | Coming soon |

Developers target a serverless workload the same way, with a `serverless/` target, in every mode. The mode changes how sessions-manager is installed, and how each workload connects and authenticates to it.

## Supported Workloads

| Platform | Operator-hosted | MetalBear Cloud |
| --- | --- | --- |
| [Amazon ECS](ecs.md) | [Supported](ecs-operator-hosted.md) | Coming soon |

## Setting Up

Setup is split by what it touches, so you only redo the parts that change:

1. **Set up your deployment mode, once.** For the Operator-hosted mode, see [Operator-Hosted Sessions-Manager](operator-hosted.md).
2. **Add the remote bootstrap to each workload.** For ECS, see [Amazon ECS](ecs.md).
3. **Connect each workload to your deployment mode.** For ECS with the Operator-hosted mode, see [Connecting ECS to the Operator](ecs-operator-hosted.md).

### Values provided by MetalBear

Serverless workloads aren't part of a regular mirrord release yet. These placeholders in the setup guides stand for builds that MetalBear provides you when you request access:

| Placeholder | Value | Used in |
| --- | --- | --- |
| `<CHART>` | The mirrord Operator Helm chart that supports the `operator.sessionsManager` value, as an OCI reference | [Operator-Hosted Sessions-Manager](operator-hosted.md#enable-sessions-manager) |
| `<CHART_VERSION>` | The version of that chart. Its default Operator image serves sessions-manager, so no image needs to be set. | [Operator-Hosted Sessions-Manager](operator-hosted.md#enable-sessions-manager) |
| `<REMOTE_BOOTSTRAP_IMAGE>` | The mirrord remote bootstrap image, including its tag, that the workload's setup container copies the bootstrap from | [Amazon ECS](ecs.md#add-the-remote-bootstrap) |
| `<MIRRORD_CLI_VERSION>` | The mirrord CLI version developers need to target serverless workloads | [Using mirrord with a Serverless Workload](#using-mirrord-with-a-serverless-workload) |

These builds are matched to each other: use the Operator, remote bootstrap and mirrord CLI from the same set, and upgrade them together when we send you a new one.

***

## Using mirrord with a Serverless Workload

Install mirrord CLI `<MIRRORD_CLI_VERSION>` ([provided by MetalBear](#values-provided-by-metalbear)). Then create a `mirrord.json` in your project:

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

* [`operator: true`](https://metalbear.com/mirrord/docs/config/options#root-operator) together with a `serverless/` target makes mirrord reach sessions-manager through the Operator, using your kubeconfig's current context. This is the Operator-hosted mode: you need nothing else beyond a kubeconfig for the cluster that runs the Operator.
* [`target.path`](https://metalbear.com/mirrord/docs/config/options#target-path) is `serverless/` followed by the service name, and [`target.namespace`](https://metalbear.com/mirrord/docs/config/options#target-namespace) is the environment the service runs in. These are the names your platform team gave the workload when setting it up, not Kubernetes resources or namespaces. Ask them for the values.
* [`key`](https://metalbear.com/mirrord/docs/config/options#root-key) identifies your session. It's substituted into `{{ key }}` in the HTTP filter, so only requests carrying `baggage: mirrord-session=<YOUR_SESSION_KEY>` reach your local process. Regular traffic and other developers' requests keep going to the serverless workload. See [Filtering Incoming Traffic](../incoming-traffic/filter-incoming-traffic.md) for other filters.
* `feature.network.outgoing` sends your local process's outgoing connections through the serverless workload, so they reach whatever the workload can reach.
* `feature.env` gives your local process the serverless workload's environment variables.

Then run your service:

```bash
mirrord exec -f mirrord.json -- <YOUR_COMMANDLINE>
```

To send a request to your local process, add the header to it, for example with `curl -H "baggage: mirrord-session=<YOUR_SESSION_KEY>" ...`. While browsing, the [mirrord browser extension](../incoming-traffic/debug-from-browser.md) can inject the header for you.

For every option, see the [configuration reference](https://metalbear.com/mirrord/docs/config/options).

***

## How It Works

1. **The workload registers.** When the workload starts, the remote bootstrap connects to sessions-manager and registers the workload under its service and environment names.
2. **You start mirrord.** `mirrord exec` connects to sessions-manager and asks for a session with the service and environment in your `mirrord.json`.
3. **Sessions-manager pairs them.** It assigns both sides to the same session and gives each a single-use credential for it.
4. **Both sides open the session's data plane.** Sessions-manager relays mirrord traffic between them. From here, mirrord behaves as it does with a Kubernetes target: incoming requests matching your filter go to your local process, and its outgoing traffic leaves from the serverless workload.

In the Operator-hosted mode, every connection goes through your cluster's API server to the Operator. See [Operator-Hosted Sessions-Manager](operator-hosted.md#how-it-works) for the details.

***

## Limitations

* **One replica per session.** Your session is served by one registered replica of the service, such as one ECS task. If the service runs several, only requests that land on that replica can be stolen or mirrored. For testing, scale the service to one replica or route your test traffic to a specific one.
* **Operator-hosted mode:**
  * **Development traffic only.** Session traffic flows through your cluster's API server. That's fine for development, but don't use a mirrord session for load testing.
  * **Operator restarts end sessions.** Restarting or upgrading the Operator ends active sessions. The workload registers again on its own; rerun `mirrord exec`.
  * **Long-lived connections.** Any proxy or firewall between the workload and the API server must not buffer responses and needs an idle timeout of at least 300 seconds.
