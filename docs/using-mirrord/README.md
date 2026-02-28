---
title: Using mirrord
description: Guides for mirrord's features - traffic control, targets, containers, and more
---

# Using mirrord

This section covers the features you use to control how mirrord connects your local process to the cluster.

### Traffic

- **[Incoming Traffic](incoming-traffic/README.md)** - Mirror or steal traffic from the cluster to your local process
- **[Outgoing Traffic](outgoing-traffic/README.md)** - Control how your local process reaches cluster services
- **[Port Forwarding](port-forwarding.md)** - Forward ports between your machine and the cluster

### Targets and execution modes

- **[Run Without a Target](targetless.md)** - Run mirrord without impersonating a specific pod
- **[Copy Target](copy-target.md)** **[Teams]** - Work against a copy of a pod instead of the live one
- **[Local Containers](local-container.md)** - Run mirrord with Docker, Podman, or nerdctl instead of a native process

### Tools

- **[Connecting Tools to the Cluster](connecting-tools/README.md)** - Use browsers, Postman, and other tools with cluster networking
