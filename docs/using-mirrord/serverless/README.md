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
Serverless workloads are **experimental**. They're available on request, and behavior, configuration and resource names may change without notice. Don't rely on them for anything beyond development environments. To try them, contact us for a [dedicated CLI binary download link](#required-versions).
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

### Required versions

* **Operator:** version **3.223.0 or later**, installed from the `metalbear/mirrord-operator` Helm chart. Follow the [Operator installation guide](../../managing-mirrord/operator.md), then [enable sessions-manager](operator-hosted.md#enable-sessions-manager).
* **Remote bootstrap:** `ghcr.io/metalbear-co/mirrord-remote-bootstrap:3.223.0`, used in the [ECS task definition](ecs.md#add-the-remote-bootstrap). Bootstrap tags follow Operator release versions, not mirrord CLI versions. Pin a release tag rather than `latest`.
* **CLI:** a dedicated mirrord CLI binary from a download link provided by MetalBear. Download the binary for your platform from that link instead of installing a regular mirrord release by version.

Use the CLI MetalBear supplies for these released components. When upgrading, confirm that the CLI supports the Operator and bootstrap versions you plan to use.

### Application container requirements

The remote bootstrap and the mirrord agent it starts run inside your application container, against the C library that container's image ships. The image must be:

* **Linux on x86-64 or ARM64.**
* **Based on glibc 2.30 or later**, such as Debian 11, Ubuntu 20.04, Amazon Linux 2023 or Red Hat Enterprise Linux 9 and later, or distroless images built on them. Amazon Linux 2, Red Hat Enterprise Linux 8 and Debian 10 ship older versions and aren't supported.
* **Not musl-based**, such as Alpine. The bootstrap is linked against glibc and can't be loaded there.

On an older glibc, the application container stops at startup, with an error that version `GLIBC_2.30` isn't found, required by `libmirrord_remote_bootstrap.so`. Remove the bootstrap from the task, or move the image to a supported base.

To check an image that has a shell, run `docker run --rm --entrypoint ldd <YOUR_APPLICATION_IMAGE> --version`. The first line shows the glibc version, or `musl` for a musl-based image.

***

## Using mirrord with a Serverless Workload

Download the dedicated mirrord CLI binary for your platform from the link [provided by MetalBear](#required-versions), and install it on your `PATH`. Use this binary rather than a regular mirrord release. Then create a `mirrord.json` in your project:

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
