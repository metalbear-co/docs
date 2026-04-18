---
title: Working with Local Containers
description: Running mirrord with local containers (Docker, Podman, nerdctl)
---

The common way to use mirrord is on a locally running process. This way you can easily debug it in your IDE, as well as make quick changes and test them out without going through the additional layer of containerization.

However, sometimes you're just not able to run your microservice locally - usually due to complicated dependencies. For these cases, you can run mirrord on a local container instead. To do this, simply run the following command:

```bash
mirrord container --target <target-path> -- <command used to run the local container>
```

For example:

```bash
mirrord container -- docker run nginx
```

In addition to Docker, Podman and nerdctl are also supported.

## Emulated local containers

If the local container you're running with `mirrord container` needs to run under emulation, set its platform explicitly.

This usually comes up on Apple Silicon hosts when you need to run an `amd64` container locally. In that case, set `container.platform` so the container runtime starts the local container with the expected architecture instead of defaulting to the host architecture.

```json5
{
  "container": {
    "platform": "linux/amd64"
  }
}
```

For example, if your machine is `arm64` but the local container image needs to run as `linux/amd64`, this setting tells the container runtime to start that local container as `amd64`.

Local container execution is currently only supported in the mirrord CLI tool. IDE extension support will be added in the future.

## What's next?

1. If you'd like to intercept traffic rather than mirror it so that your local process is the one answering the remote requests, check out [this guide](../using-mirrord/incoming-traffic/filter-incoming-traffic.md). Note that you can even filter which traffic you intercept!
2. If you don't want to impersonate a remote target - for example, if you want to run a tool in the context of your cluster - check out our [guide on the targetless mode](../using-mirrord/targetless.md).
3. If you just want to learn more about mirrord, why not check out our [architecture](../reference/architecture.md) or [configuration](https://metalbear.com/mirrord/docs/config) sections?
