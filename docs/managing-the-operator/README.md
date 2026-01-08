---
title: Managing the Operator
date: 2024-04-01T13:37:00.000Z
lastmod: 2024-04-01T13:37:00.000Z
draft: false
weight: 200
toc: true
tags:
  - team
  - enterprise
description: Administer and monitor the mirrord Operator in your Kubernetes cluster
---

# Managing the Operator

This section covers how to manage and administer the mirrord Operator in your organization. The Operator is the central component that enables team collaboration and concurrent cluster usage. Here you'll find guidance on monitoring Operator performance and usage, understanding security considerations for the Operator deployment, and setting up a License Server to manage seats across multiple clusters.

These guides are intended for cluster administrators and platform teams responsible for maintaining the mirrord Operator in production environments.

## In this section

- **[Monitoring](monitoring.md)** - Configure Operator logging, expose Prometheus metrics, and set up dashboards to track mirrord usage across your organization
- **[Security](security.md)** - Understand the Operator's security model, configure RBAC, enable TLS for agent connections, and harden your deployment
- **[License Server](license-server.md)** - Deploy a self-hosted license server to manage seats across multiple Operators without sending data to mirrord's cloud
