---
title: "Comparisons"
description: "How does mirrord compare to Telepresence, Signadot, Okteto, Tilt, DevSpace, and Bridge to Kubernetes?"
date: 2020-11-16T13:59:39+01:00
lastmod: 2026-10-15T00:00:00+00:00
draft: false
images: []
menu:
  docs:
    parent: "faq"
weight: 130
toc: true
tags: ["oss", "team", "enterprise"]
---

## Why not just use a remote debugger?

When you use a remote debugger, you still have to deploy new code to the cluster. When you plug local code into the cloud with mirrord, you don't have to wait for cloud deployment. Using mirrord is also less disruptive to the cluster, since the stable version of the code is still running and handling requests.

## Why not just run a copy of the cluster on my machine with e.g. minikube?

Our assumption is that some environments are too complex to run wholly on your local machine (or their components are just not virtualizable). If that's the case with your environment, you can only run the microservice you're currently working on locally, but connect it to your cloud environment with mirrord. Note that mirrord can also be used to connect your non-containerized process to your local Kubernetes cluster.

## How is mirrord different from Telepresence?

Both connect code on your machine to a remote cluster. The main differences are:

* **Scope on your machine.** mirrord loads into the process you run, so other processes on your machine aren't affected and you can run [several services side by side](../using-mirrord/multiple-concurrent-sessions.md), each against a different [target](../reference/targets.md). Telepresence connects the whole machine through a network tunnel managed by a privileged daemon, or a container in its Docker mode.
* **Changes to the cluster.** By default, Telepresence injects a Traffic Agent sidecar into the target's pods, which restarts them once, and the sidecar stays in the pods until you remove it. mirrord's [agent](../reference/architecture.md) is short-lived and shares the target pod's network namespace without adding a sidecar or restarting the pod.
* **Sharing a cluster across a team.** Both support [filtering incoming HTTP traffic](../using-mirrord/incoming-traffic/filter-incoming-traffic.md) by header. With [mirrord for Teams](../getting-started/what-is-mirrord.md#mirrord-for-teams), mirrord also [splits queues](../sharing-the-cluster/queue-splitting.md) across nine brokers and [branches databases](../sharing-the-cluster/db-branching.md) across 12 engines, so [concurrent sessions](../sharing-the-cluster/overview.md) don't consume each other's messages or write to each other's data. Telepresence doesn't offer queue splitting or database branching.
* **Support.** mirrord is developed and supported by MetalBear. Telepresence is a community-supported open-source project.

For a feature-by-feature comparison, see [mirrord vs. Telepresence](https://metalbear.com/mirrord/compare/telepresence/).

## How is mirrord different from Signadot?

Signadot creates a sandbox for each change. When the change runs in the cluster, such as a pull request's new image in CI, the sandbox forks the workloads you name: each fork is a copy of the original workload with its own pods, running beside it, and requests reach the fork by a routing key. For local development, a sandbox can route requests to your machine instead of to a fork. mirrord runs your code against the workloads you already have. The main differences are:

* **Changes to the cluster.** Unless you route with Istio or Gateway API, Signadot injects its DevMesh sidecar into each workload that takes part in a sandbox, and each forked workload gets its own copies of the Services that select it. mirrord adds no sidecar and, for local and [CI](../use-cases/mirrord-for-ci.md) sessions, forks nothing.
* **Local development.** `signadot local connect` needs root for its full networking setup, rewrites `/etc/hosts` by default, and doesn't give your process the workload's environment variables or files. To get them, you run two more commands, `signadot sandbox get-env` and `get-files`, load the variables into your shell, and point your code at the downloaded files, which land under `~/.signadot/` rather than the paths your code reads in the pod. mirrord needs no root and no extra steps: your process reads the pod's [environment variables](../using-mirrord/environment-variables.md) and [files](../using-mirrord/file-operations.md) automatically, at the same paths it would use in the cluster.
* **Databases and queues.** With Signadot, an ephemeral database comes from a resource plugin your team writes, and isolating a queue means adding routing-key checks to each consumer or giving each sandbox its own topic. mirrord has built-in [database branching](../sharing-the-cluster/db-branching.md) for 12 engines and [queue splitting](../sharing-the-cluster/queue-splitting.md) for nine brokers, with no changes to consumer code.
* **Where it runs.** Signadot's operator keeps a tunnel open to Signadot's hosted control plane. mirrord's session traffic goes only between your cluster and the developer's machine or CI runner, never through MetalBear's cloud.

Both support per-PR [preview environments](../use-cases/preview-environments.md) and [running tests in CI](../use-cases/mirrord-for-ci.md). For a feature-by-feature comparison, see [mirrord vs. Signadot](https://metalbear.com/mirrord/compare/signadot/).

## How is mirrord different from Okteto?

Okteto runs your code inside the cluster. `okteto up` replaces a Deployment with a development copy and keeps your local files in sync with a development container running there. Okteto also offers a hybrid mode that runs the service locally over SSH tunnels. Okteto is a platform you install in your cluster, and it gives each developer or task its own environment, including per-PR preview environments. By default, each of those environments is a full copy of the application in its own namespace, so cluster costs grow with every developer. Okteto's Divert feature lets you deploy only the services you change, but the shared environment it routes the rest to must itself be deployed by Okteto.

mirrord doesn't copy the application at all. Every developer works against the one [shared cluster](../sharing-the-cluster/overview.md) you already run, so adding developers adds no environments to pay for. Your code runs on your machine, so you use your local debugger and tools directly, with no file sync or development image.

## How is mirrord different from Tilt?

Tilt automates building and deploying: it watches your files, builds container images, and applies them to a cluster. By default it develops against a local cluster such as kind or minikube, and only works against a remote cluster if you explicitly allow it.

mirrord skips the build and deploy. Your local process runs against a remote cluster directly, so a code change takes effect when you restart the process, without building or pushing an image. That makes the loop much shorter, and you debug with your local debugger instead of attaching to a container. It also means you don't need to fit the whole stack into a local cluster on your laptop: you test against the real services, data, and configuration in your [shared cluster](../sharing-the-cluster/overview.md).

## How is mirrord different from DevSpace?

DevSpace is an open-source CLI that turns a container in your cluster into a development container. It can swap the image, sync files in both directions, and forward ports, so your code runs inside the cluster.

mirrord keeps your code running on your machine, so you use your local debugger and IDE directly, with no development image to maintain and no files to sync. It also leaves the target running. By default, DevSpace replaces the target pod with the development version, so everyone else calling that service reaches your container too. With mirrord, the original pod keeps serving traffic, and a [traffic filter](../using-mirrord/incoming-traffic/filter-incoming-traffic.md) sends only your requests to your local code.

## How is mirrord different from Bridge to Kubernetes?

Microsoft retired Bridge to Kubernetes on April 30, 2025. In the [retirement announcement](https://github.com/Azure/Bridge-To-Kubernetes/issues/655), its maintainers named mirrord as an alternative and pointed users to a [mirrord tutorial on the AKS engineering blog](https://blog.aks.azure.com/2024/12/04/mirrord-on-aks). Its approach was the closest to mirrord's: it connected code running on your machine to a cluster. To do that, it replaced the target's container with a remote agent, needed administrator rights on your machine to edit the hosts file, and only supported pods running a single container.

mirrord needs no administrator rights, works with [multi-container pods](../reference/targets.md), and is actively developed. See [mirrord vs. Bridge to Kubernetes](https://metalbear.com/mirrord/compare/bridge-to-kubernetes/) for help moving over.
