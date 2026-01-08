---
title: Networking
date: 2024-12-19T00:00:00.000Z
lastmod: 2024-12-19T00:00:00.000Z
draft: false
weight: 120
toc: true
tags:
  - open source
  - team
  - enterprise
description: Control how your local process communicates over the network
---

# Networking

When you run with mirrord, your local process gets network access as if it were running inside the cluster. This means your code can call internal services, resolve cluster DNS names, and optionally receive incoming traffic—all without deploying.

## The basics

mirrord provides three fundamental networking capabilities:

**Incoming traffic:** Your local process can receive traffic destined for the target pod. Traffic can be mirrored (duplicated to your local process while the pod handles it normally) or stolen (redirected to your local process instead of the pod). This is useful for testing your code against real requests or debugging specific traffic flows.

**Outgoing traffic:** Your local process can reach services that are only accessible from inside the cluster. When your app makes an outgoing connection (e.g., to `http://payment-service:8080`), mirrord routes the request through the target pod. Network policies, service discovery, and internal DNS all work as expected.

**DNS resolution:** Cluster service names resolve correctly because mirrord forwards DNS queries to the cluster. When your app looks up `payment-service.payments.svc.cluster.local`, mirrord resolves it using the cluster's DNS, returning the in-cluster IP.

## Advanced traffic control

Beyond the basics, mirrord provides fine-grained control over network behavior:

### Filter Incoming Traffic

Control which incoming requests reach your local process using HTTP header, path, or method filters. [Learn more](filter-incoming-traffic.md).

### Control Outgoing Traffic

Choose which outgoing connections go through the cluster and which stay local—useful when you want to connect to a local database while accessing cluster services. [Learn more](control-outgoing-traffic.md).

### Capture HTTPS Requests

When your target pod handles TLS termination directly, mirrord for Teams lets you steal and filter HTTPS traffic. [Learn more](capture-https-requests.md).

### Port Forwarding

Forward traffic from a local port to any destination accessible from the target pod, similar to `kubectl port-forward`. [Learn more](port-forwarding.md).

### Monitor Live Traffic

Use `mirrord dump` to inspect incoming traffic to a Kubernetes resource directly in your terminal—useful for debugging and verifying traffic patterns. [Learn more](monitor-live-traffic.md).

### Debug from Browser

Automatically inject HTTP headers into browser requests during your mirrord session, making it easy to test header-based routing. [Learn more](debug-from-browser.md).
