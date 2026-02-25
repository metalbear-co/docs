---
title: Preview Environments in CI
description: How to automate preview environments in your CI pipeline with PR-based keys and header propagation
date: 2026-02-23T00:00:00.000Z
lastmod: 2026-02-23T00:00:00.000Z
draft: false
toc: true
tags:
  - enterprise
menu:
  docs:
    parent: preview-environments
---

# Preview Environments in CI

This guide explains how to automate [Preview Environments](preview-environments.md) in your CI pipeline. By integrating mirrord preview with your pull request workflow, each PR gets its own ephemeral environment that reviewers can access via a shared URL and a simple header—no local mirrord setup required.

{% hint style="info" %}
This feature is available to users on the **Enterprise** pricing plan.
{% endhint %}

## Flow Overview

1. **On PR open or push:** Your CI builds the image(s), pushes to a registry, runs `mirrord preview start` with a stable key (e.g. `pr-123`), and posts or updates a comment on the PR with the preview URL and the header to use.
2. **Reviewers:** Open the shared URL and send the header (via the [mirrord Browser Extension](browser-extension.md) or `curl`). Traffic matching the header is routed to the preview pod.
3. **On PR merge or close:** CI runs `mirrord preview stop -k <key>` to tear down the preview environment.

## Choosing the Preview Key

Use a deterministic key tied to the PR so that:

- The same key is used across pushes, allowing you to update the PR comment instead of creating duplicates.
- Cleanup is straightforward: when the PR closes, you stop the preview by that key.

**Best practice:** Use the PR number (e.g. `pr-123`) or a sanitized branch name. In GitHub Actions:

```yaml
env:
  PREVIEW_KEY: "pr-${{ github.event.pull_request.number }}"
```

## Automating the PR Comment

Post a comment on the PR that includes:

| Field | Example |
|-------|---------|
| **Preview URL** | `https://myapp.example.com` |
| **Header** | `X-PG-Tenant: pr-123` |

Also include instructions for reviewers:

- Use the [mirrord Browser Extension](browser-extension.md) to set the header for the preview URL, or
- Use `curl -H "X-PG-Tenant: pr-123" https://myapp.example.com/api/...`

**Best practice:** Find an existing comment (e.g. by a marker like `## mirrord Preview Environment`) and update it on each push, instead of creating a new comment every time. This keeps the PR tidy.

## Header Propagation for Backend Testing

When your frontend calls a backend, and the backend calls other services (databases, APIs, queues), the preview header must be propagated so downstream traffic is routed correctly.

### 1. Configure the Header Filter in mirrord

In your `mirrord-preview.json`, use `{{ key }}` in the HTTP filter so only requests with the matching header hit the preview pod:

```json
{
  "target": {
    "path": "deployment/my-backend",
    "namespace": "staging"
  },
  "feature": {
    "preview": {
      "ttl_mins": 120,
      "creation_timeout_secs": 600
    },
    "network": {
      "incoming": {
        "mode": "steal",
        "http_filter": {
          "header_filter": "X-PG-Tenant: {{ key }}"
        }
      }
    }
  }
}
```

### 2. Propagate the Header in Your Application

Read the header from the incoming request, store it in request context, and forward it on all outgoing calls:

- **HTTP:** Add the header to outgoing `http.Request` objects.
- **gRPC:** Add it to `metadata` in the outgoing context.
- **Kafka:** Add it to message headers.
- **SQS:** Add it to message attributes.

Example (Go with Gin): read `X-PG-Tenant`, set it in context, then add it to outgoing HTTP and gRPC calls:

```go
tenant := c.GetHeader("x-pg-tenant")
if tenant != "" {
    c.Set("x-pg-tenant", tenant)
}
// Later, when making outgoing HTTP request:
req.Header.Set("x-pg-tenant", tenant)
// Or for gRPC:
md := metadata.Pairs("x-pg-tenant", tenant)
ctx := metadata.NewOutgoingContext(c, md)
```

If you don't propagate the header, downstream services won't know which preview environment the request belongs to, and traffic may not reach the correct preview pods.

## mirrord Configuration

Create a `mirrord-preview.json` (or similar) per service. The image can be provided via the config file or overridden with `-i` in CI:

```json
{
  "target": {
    "path": "deployment/my-app",
    "namespace": "staging"
  },
  "feature": {
    "preview": {
      "ttl_mins": 120,
      "creation_timeout_secs": 600
    },
    "network": {
      "incoming": {
        "mode": "steal",
        "http_filter": {
          "header_filter": "X-PG-Tenant: {{ key }}"
        }
      }
    }
  }
}
```

In CI, pass the image and key via CLI:

```bash
mirrord preview start \
  -f mirrord-preview.json \
  -i "ghcr.io/org/my-app:preview-pr-123-abc1234" \
  -k "pr-123" \
  --timeout 600
```

## CI Workflow Best Practices

- **Concurrency:** Use a concurrency group per PR so that new pushes cancel in-progress runs and avoid duplicate preview pods:
  ```yaml
  concurrency:
    group: preview-env-${{ github.event.pull_request.number }}
    cancel-in-progress: true
  ```

- **Image tags:** Include both PR number and commit SHA for traceability, e.g. `preview-pr-123-abc1234`.

- **Cleanup:** Always run `mirrord preview stop` when the PR is closed. Use `|| true` so the job doesn't fail if the preview was already stopped or never started:
  ```bash
  mirrord preview stop -k "pr-${{ github.event.pull_request.number }}" || true
  ```

- **Multiple services:** Use the same key for all preview pods in a PR so they form one logical environment. Run `mirrord preview start` once per service, each with `-k "pr-123"`.
