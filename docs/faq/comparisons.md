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
* **Changes to the cluster.** By default, Telepresence injects a Traffic Agent sidecar into the target's pods, which restarts them once, and the sidecar stays until Telepresence is uninstalled. mirrord's [agent](../reference/architecture.md) is short-lived and shares the target pod's network namespace without adding a sidecar or restarting the pod.
* **Sharing a cluster across a team.** Both support [filtering incoming HTTP traffic](../using-mirrord/incoming-traffic/filter-incoming-traffic.md) by header. With [mirrord for Teams](../getting-started/what-is-mirrord.md#mirrord-for-teams), mirrord also [splits queues](../sharing-the-cluster/queue-splitting.md) across nine brokers and [branches databases](../sharing-the-cluster/db-branching.md) across 12 engines, so [concurrent sessions](../sharing-the-cluster/overview.md) don't consume each other's messages or write to each other's data. Telepresence doesn't offer queue splitting or database branching.
* **Support.** mirrord is developed and supported by MetalBear. Telepresence is a community-supported open-source project.

For a feature-by-feature comparison, see [mirrord vs. Telepresence](https://metalbear.com/mirrord/compare/telepresence/).

## How is mirrord different from Signadot?

Signadot creates a sandbox for each change: it forks the workloads you name into new pods in the cluster and routes requests to the forks by a routing key. mirrord runs your code against the workloads you already have. The main differences are:

* **Changes to the cluster.** Unless you route with Istio or Gateway API, Signadot injects its DevMesh sidecar into each workload that takes part in a sandbox, and each forked workload gets its own copies of the Services that select it. mirrord adds no sidecar and, for local and [CI](../use-cases/mirrord-for-ci.md) sessions, forks nothing.
* **Local development.** `signadot local connect` needs root, rewrites `/etc/hosts` by default, and exports the workload's environment variables and files with `get-env` and `get-files`. mirrord needs no root, and your process reads the pod's [environment variables](../using-mirrord/environment-variables.md) and [files](../using-mirrord/file-operations.md) directly.
* **Databases and queues.** With Signadot, an ephemeral database comes from a resource plugin your team writes, and isolating a queue means adding routing-key checks to each consumer or giving each sandbox its own topic. mirrord has built-in [database branching](../sharing-the-cluster/db-branching.md) for 12 engines and [queue splitting](../sharing-the-cluster/queue-splitting.md) for nine brokers, with no changes to consumer code.
* **Where it runs.** Signadot's operator keeps a tunnel open to Signadot's hosted control plane. mirrord's session traffic goes only between your cluster and the developer's machine or CI runner, never through MetalBear's cloud.

Both support per-PR [preview environments](../use-cases/preview-environments.md) and [running tests in CI](../use-cases/mirrord-for-ci.md). For a feature-by-feature comparison, see [mirrord vs. Signadot](https://metalbear.com/mirrord/compare/signadot/).

## How is mirrord different from Okteto?

Okteto runs your code inside the cluster. `okteto up` replaces a Deployment with a development copy and keeps your local files in sync with a development container running there. Okteto also offers a hybrid mode that runs the service locally over SSH tunnels. Okteto is a platform you install in your cluster or have Okteto run in your cloud, and it gives each developer or task its own environment, including per-PR preview environments.

mirrord runs your code on your machine, so you use your local debugger and tools directly, with no file sync or development image. It works against the [shared cluster](../sharing-the-cluster/overview.md) you already run, rather than creating a separate environment for each developer.

## How is mirrord different from Tilt?

Tilt automates building and deploying: it watches your files, builds container images, and applies them to a cluster. By default it develops against a local cluster such as kind or minikube, and only works against a remote cluster if you explicitly allow it.

mirrord skips the build and deploy. Your local process runs against a remote cluster directly, so a code change takes effect when you restart the process, without building or pushing an image.

## How is mirrord different from DevSpace?

DevSpace is an open-source CLI that turns a container in your cluster into a development container. It can swap the image, sync files in both directions, and forward ports, so your code runs inside the cluster.

mirrord keeps your code running on your machine. Nothing in the target's image changes, and there are no files to sync.

## How is mirrord different from Bridge to Kubernetes?

Microsoft retired Bridge to Kubernetes on April 30, 2025. Its approach was the closest to mirrord's: it connected code running on your machine to a cluster. To do that, it replaced the target's container with a remote agent, needed administrator rights on your machine to edit the hosts file, and only supported pods running a single container.

mirrord needs no administrator rights, works with [multi-container pods](../reference/targets.md), and is actively developed. See [mirrord vs. Bridge to Kubernetes](https://metalbear.com/mirrord/compare/bridge-to-kubernetes/) for help moving over.
