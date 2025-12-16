---
title: Connecting external tools
date: 2025-12-16T12:00:00.000Z
lastmod: 2025-12-16T12:00:00.000Z
draft: false
toc: true
tags:
  - open source
  - team
  - enterprise
description: Using mirrord to allow other tools (such as GUI tools) to use cluster networking
---

# Connecting External Tools

Sometimes you need to use local tools like Web Browsers, Postman, or Database Clients, to interact with services that are only accessible from inside your cluster.

Instead of setting up complex port-forwards or VPNs, you can use `mirrord` to create a lightweight SOCKS5 tunnel. This allows any application that supports SOCKS5 to resolve internal DNS and connect to private cluster services as if it were running inside the cluster itself.

### Prerequisites

* **microsocks**: Install via your package manager.
    * macOS: `brew install microsocks`
    * Ubuntu/Debian: `apt install microsocks`

### Setup

Regardless of which tool you are connecting, the first step is to establish the tunnel.

1. **Run the Proxy:**
   In your terminal, use `mirrord exec` to launch `microsocks`.

   * **Targetless (Default Namespace):**
     ```bash
     mirrord exec microsocks
     ```

   * **Targeting a Deployment:**
     ```bash
     mirrord exec -t deployment/my-deployment microsocks
     ```

   * **Targeting a Namespace:**
     ```bash
     mirrord exec -a my-namespace microsocks
     ```

2. **Verify Output:**
   * `microsocks` typically listens on `127.0.0.1:1080` by default. Ensure the command is running and listening before configuring your tool.
   * Try calling a service health endpoint in your kubernetes cluster using `curl --socks5 socks5h://127.0.0.1:1080 <svc>.<namespace>.svc.cluster.local/health`

### Tool Guides

Once the proxy is running, choose your tool below to configure the connection:

* [Web Browsing](./web-browsing.md) - Using mirrord to browse using cluster networking.
* [Postman](./postman.md) - Send API requests via postman to kubernetes services.