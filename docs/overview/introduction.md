---
title: "Introduction"
description: "Learn about mirrord and how it works"
date: 2022-05-26T08:48:57+00:00
lastmod: 2022-05-26T08:48:57+00:00
draft: false
# resources: ["diagram.jpeg"]
images: []
menu:
  docs:
    parent: overview
weight: 100
toc: true
tags: ["open source", "team", "enterprise"]
---

mirrord is a tool that lets developers run local processes in the context of their cloud environment. It makes it incredibly easy to test your code on a cloud environment (e.g. staging) without actually going through the hassle of Dockerization, CI, or deployment, and without disrupting the environment by deploying untested code.

```bash
mirrord exec --target deploy/my-app -- node server.js
```

Your local `server.js` now receives traffic from the cluster, reads remote files, and uses remote environment variables — no deployment needed.

{% hint style="success" %}
**Ready to try it?** Install mirrord in under a minute and run your first session.
**[Get Started →](quick-start.md)**
{% endhint %}

## Why?

Traditionally, software development happens in loops. Developers write and test their code locally, then deploy it to a staging/pre-production environment in the cloud, where they perform additional tests. These tests often fail, because the code is meeting a production-like environment for the first time, and encounters new conditions. The code must then be fixed/rewritten, tested locally again, deployed to staging again, and so on, until the tests on staging pass.

![The Traditional Dev Loop](/docs/overview/introduction/loop.png)

Deployment to staging can be costly for several reasons:

1. It often involves a CI process, which may be slow (because of e.g. a long automated test suite having to pass in order to progress) and sometimes broken.
2. Since staging environments are shared, the environment is occasionally broken when an engineer deploys unstable code.

mirrord removes the costs associated with deployment to staging, by taking 'deployment' out of the process completely. By plugging your local process directly into the staging environment, you can test your code in cloud conditions without having to go through a long CI process, and without the risk of breaking the environment for other developers.

Instead of spending your time running local environments, writing mocks, test fixtures, and so on — why not just test your code on staging itself? We call this approach "remocal" (remote + local) development: your code runs locally, but in the context of your cloud environment.

## How it works

mirrord runs in two places - in the memory of your local process (`mirrord-layer`), and as a pod in your cloud environment (`mirrord-agent`).

![mirrord - Basic Architecture](/docs/reference/architecture/architecture.svg)

When you start your local process with mirrord, it creates a pod in your cloud environment, which listens in on the pod you've passed as an argument. `mirrord-layer` then does the following:

- Override the process' syscalls to:
  - Listen to incoming traffic from the agent, instead of local sockets.
  - Intercept outgoing traffic and send it out from the remote pod, instead of locally.
  - Read and write files to the remote file system.
  - Merge the process' environment variables with those of the remote pod.

The remote part of this logic is handled by the agent, which runs in the network namespace of the remote pod, and can access its file system and environment variables.

For further details, see the [architecture](../reference/architecture.md) section.

## How it's different from other remocal solutions

mirrord is not the first tool to allow you to run your code in the cloud. However, it does it in a way that's completely different from all the other solutions.
While all other remocal solutions use some version of a VPN to connect your local machine (or local Docker container) to the cluster, mirrord works at the level of your local process, overriding its syscalls and proxying them to the cloud.
Similarly, at the cluster level, it runs at the level of the target pod, running on the same node and executing the syscalls received from the client.

This gives mirrord some unique advantages over its alternatives:

- You can configure _exactly_ what functionality happens remotely, and what stays local. For example:
  - You can read some files or environment variables from your local machine and some from the remote pod
  - You can make requests to certain hosts or IPs happen locally, and others be sent out from the remote pod
- At the local level, it doesn't require root access
- At the local level, it takes 15 seconds at most to start up
- At the local level, you can run multiple processes simultaneously, each in the context of a different remote pod
- At the cluster level, it's agnostic to the cluster's network setup - whether it includes a service mesh, a VPN, or anything else
- At the cluster level, it's agnostic to the cluster's size - mirrord has been tested on clusters running 10,000+ pods

## What's next?

- **[Quick Start Guide](quick-start.md)** — Install mirrord and run your first session in under 5 minutes
- **[mirrord for Teams](teams.md)** — Collaborate with shared configurations, policies, and concurrent access
- **[Using mirrord](../using-mirrord/README.md)** — Traffic filtering, queue splitting, IDE extensions, and more
- **[Watch the Demo](https://www.youtube.com/watch?v=ZR7A7cqQcFM)** — See mirrord in action
