---
title: "Incoming Traffic Capture"
description: "How to use mirrord dump to inspect incoming traffic on Kubernetes resource"
date: 2025-08-11T00:00:00+03:00
lastmod: 2025-08-11T00:00:00+03:00
draft: false
menu:
  docs:
    parent: "using-mirrord"
toc: true
tags: ["open source", "team", "enterprise"]
---

`mirrord dump` command lets you inspect incoming traffic to a Kubernetes resource- like a deployment, service, pod, statefulset, directly in your terminal.

When this can be useful?
1. When Debugging incoming traffic: If your service is erroring and you’re not sure why, `mirrord dump` lets you see what's actually hitting the service, including headers like user-id, X-Session-ID, tenant-id so you can mirror only the traffic relevant to you 
2. When Verifying mirroring works: If you suspect mirrord exec isn’t working, you can run mirrord dump. If traffic shows up, mirroring works, so you can rule out that part 


## Prerequisites

Before you start, make sure you have:
1. `kubectl` configured to talk to your target cluster.
2. mirrord installed and able to run (OSS or Teams operator, depending on your setup).
3. Target resource details: e.g. deployment name and port.

## Using `mirrord dump`

1. Run a command like:
   ```
   mirrord dump -t deployment/my-deployment -p 80
    ```
2. mirrord will then:
    - Spawn a mirrord agent (via operator or OSS) in the target pod’s network namespace.
    - Listen for incoming traffic on the specified port.
3. You will see the output of each connection, request, and payload raw in your terminal.
```
Listening for traffic... Press Ctrl+C to stop

New connection established: Connection ID 0 from x.x.x.x:port to y.y.y.y:port
Connection ID 0: 93 bytes
Data: GET /health HTTP/1.1
Host: your-service
...
Connection ID 0 closed
```
4. Hit Ctrl+C to stop the dump session.



