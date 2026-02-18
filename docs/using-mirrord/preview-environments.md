---
title: Preview Environments
date: 2026-02-18T12:28:00.000Z
lastmod: 2026-02-18T12:28:00.000Z
draft: false
images: []
linktitle: Preview Environments
menu:
  docs:
    parent: "using-mirrord"
toc: true
tags:
  - enterprise
description: Ephemeral, Isolated Environments Connected to Your Cluster
---

# Preview Environments

Preview Environments let you deploy a new version of your code into the cluster as an isolated pod that receives traffic from an existing target — without affecting other users or live services. Unlike a regular mirrord session, a preview environment is not tied to a local process. It stays alive for a configurable TTL, making it suitable for sharing with teammates, QA, or product managers who need to validate changes asynchronously.

{% hint style="info" %}
This feature is available to users on the **Enterprise** pricing plan.
{% endhint %}

With a regular mirrord session, the test environment disappears when your local process stops. Preview environments solve this: the code runs in-cluster, so it keeps serving traffic regardless of what's happening on your machine. Multiple preview environments can run side by side, each receiving only the traffic intended for them.

## Prerequisites

1. The mirrord operator must be installed in the cluster with an Enterprise license.
2. Your container image must be pre-built and pushed to a registry accessible by the cluster.

## Configuration

Preview environments are configured through the standard mirrord configuration file. The preview-specific fields live under `feature.preview`:

```json
{
  "key": "my-feature",
  "target": {
    "path": "deployment/my-app",
    "namespace": "staging"
  },
  "feature": {
    "preview": {
      "image": "my-registry/my-app:feature-branch",
      "ttl_mins": 60
    },
    "network": {
      "incoming": {
        "mode": "steal",
        "http_filter": {
          "header_filter": "x-traffic: {{ key }}"
        }
      }
    }
  }
}
```

The `target` specifies which existing workload to clone the pod spec from. The operator creates a new pod using that spec but with your `preview.image` instead. The preview pod runs inside the cluster with native access to the cluster's network, DNS, and environment — there is no need for filesystem or environment variable mirroring.

### Environment key

Each preview environment is identified by a **key** (the `key` field). The key can be referenced in HTTP filters and other fields as the template variable `{{ key }}`, making it easy to scope traffic to a specific preview. If no key is provided, mirrord generates a random UUID automatically.

With the config above, `{{ key }}` is replaced with `my-feature` at load time, so only requests containing the header `x-traffic: my-feature` are routed to the preview pod.

### Traffic modes

Preview environments support the same [incoming traffic modes](../reference/traffic.md) as regular mirrord sessions:

- Filtered steal: requests matching an HTTP filter are redirected to the preview pod instead of the original target. Other traffic is unaffected. This is the most common mode for preview environments.
- Mirroring (filtered or unfiltered): a copy of incoming traffic is sent to the preview pod. The preview pod's responses are discarded — the original target still serves all real traffic. Useful for observing how new code handles production-like requests without any risk of disruption.

{% hint style="warning" %}
Unfiltered stealing is not supported for preview environments. If you use steal mode, you must configure an HTTP filter to scope which requests the preview pod receives.
{% endhint %}

Here is an example using unfiltered mirroring:

```json
{
  "target": {
    "path": "deployment/my-app",
    "namespace": "staging"
  },
  "feature": {
    "preview": {
      "image": "my-registry/my-app:feature-branch"
    },
    "network": {
      "incoming": {
        "mode": "mirror"
      }
    }
  }
}
```

In this mode, all traffic to the target is duplicated to the preview pod, but the original target still serves every response.

## Starting a preview environment

The `mirrord preview start` command creates a preview environment from a config file:

```bash
$ mirrord preview start -f mirrord.json
```

{% hint style="info" %}
To view the entire list of arguments, run `mirrord preview start --help`.
{% endhint %}

The image and target can also be provided via CLI flags (`-i` for image, `-t` for target, `-k` for key), which override the corresponding config file fields.

Once the preview pod is ready, you'll see a summary:

```
  ✓ mirrord preview start
    ✓ configuration loaded
    ✓ connected to operator
    ✓ preview session resource created
    ✓ preview pod is ready
  info:
    * key: my-feature
    * namespace: staging
    * pod: preview-session-deployment-my-app-a1b2c3d4
```

At this point, the preview pod is running in the cluster and receiving traffic according to your config. You can share the key with teammates so they can route their requests to the preview.

## Checking status

Use `mirrord preview status` to see active preview environments:

```bash
$ mirrord preview status
  ✓ mirrord preview status
    ✓ configuration loaded
    ✓ found 2 sessions
  my-feature:
    * preview-pod-deployment-my-app-a1b2c3d4 (deployment/my-app @ staging): running
  another-feature:
    * preview-pod-deployment-api-e5f6g7h8 (deployment/api @ staging): running
```

Sessions are grouped by key. You can filter by key with `-k` or by namespace with `-n`.

## Stopping a preview environment

When you're done, stop the preview environment by key:

```bash
$ mirrord preview stop --key my-feature
  ✓ mirrord preview stop
    ✓ configuration loaded
    ✓ found 1 session to delete
    ✓ all sessions deleted
```

This removes the preview pod and all associated resources from the cluster. If you don't stop it manually, the session will be automatically cleaned up when its TTL expires.

## Current limitations

Preview environments are a new feature, and there are a few limitations we're actively working on. These will be addressed in upcoming releases:

- No in-place updates: you can't update the image or configuration of a running preview session. To deploy a new version, `stop` the existing session and `start` a new one.
- Targetless mode not yet supported: preview environments currently require a target workload to clone the pod spec from. Support for [targetless](targetless.md) preview environments — creating a fresh, isolated pod without an existing target — is not yet available.
