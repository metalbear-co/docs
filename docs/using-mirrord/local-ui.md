---
title: "Local UI"
description: "Launch a local web dashboard that watches every active mirrord session"
date: 2026-04-28T00:00:00+00:00
lastmod: 2026-04-28T00:00:00+00:00
draft: false
menu:
  docs:
    parent: "using-mirrord"
weight: 175
toc: true
tags: ["open source", "team", "enterprise"]
---

`mirrord ui` launches a small local web dashboard that watches every active mirrord session on your machine and, when you're connected to a mirrord operator, every operator session your kubeconfig can see across the cluster. It runs entirely on your laptop. Nothing in your cluster has to change to use it.

## What it shows

- **Local sessions** — each `mirrord exec` you have running locally, with its target, port subscriptions, processes, mirrord version, and a live event stream (file ops, DNS, HTTP requests, outgoing connections).
- **Operator sessions** — a roll-up of every active mirrord session in your cluster, grouped by session key, with target, owner, namespace, and HTTP filter. Useful for seeing what your teammates have running before you start your own session, and for picking a session to ride on from the [mirrord browser extension](incoming-traffic/debug-from-browser.md).

The dashboard updates live over a WebSocket as sessions start and end.

## Prerequisites

- A recent mirrord CLI. The subcommand is available on macOS and Linux.
- A working kubeconfig pointing at a cluster running the [mirrord operator](../managing-mirrord/operator.md), if you want to see operator sessions. Without an operator, the dashboard still works for your own local sessions.

## Running it

```bash
mirrord ui
```

The CLI starts an HTTP + WebSocket server bound to localhost, generates a one-shot auth token, prints the URL, and opens it in your default browser.

```
  mirrord session monitor
    Web UI: http://[::1]:59281?token=...
```

The token is required on every API request, so there's no need to expose the dashboard beyond your machine. Each invocation generates a fresh token.

To pick a different port:

```bash
mirrord ui --port 9000
```

## Authentication

The token is high-entropy and is bound to the running `mirrord ui` process. The first request you make with `?token=...` sets a `mirrord_token` cookie scoped to that origin so subsequent requests don't need to keep the query parameter. Closing `mirrord ui` invalidates the token; the next run mints a new one.

## Browser extension auto-configure

If you have the [mirrord browser extension](incoming-traffic/debug-from-browser.md) installed, opening the Web UI automatically tells the extension which `mirrord ui` daemon to talk to and hands it the session token. No copy/paste, no settings page. From there the extension's Sessions tab shows the same operator sessions you see in the Web UI, with a one-click join.

## Troubleshooting

- **"Failed to bind"** — another process is on the chosen port. Pass `--port <other>`.
- **Empty operator sessions list** — your kubeconfig context isn't pointing at a cluster with the mirrord operator installed, or your user doesn't have permission to read `MirrordOperator.status`. The local sessions panel still works.
- **Dashboard says "unauthorized"** — the token in the URL didn't match. Re-open the URL the CLI printed; don't reuse a URL from a previous run.

## What's next?

- Use the [browser extension](incoming-traffic/debug-from-browser.md) to inject a header that matches an operator session's HTTP filter and route browser traffic to the corresponding local layer.
- Read [Managing Sessions](../sharing-the-cluster/sessions.md) for the operator-side view of the same sessions and how to forcibly stop one.
