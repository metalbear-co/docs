---
title: Sharing Local Services
description: Share a service running on your machine with an HTTPS link
tags:
  - team
  - enterprise
---

# Sharing Local Services

`mirrord exec --share` prints an HTTPS link to the service running on your machine. Anyone who opens the link reaches your local version, with nothing to install, until you stop the session. Your service keeps using its cluster dependencies through mirrord.

## Prerequisites

* A Team or Enterprise license.
* Your platform team has set up [Share Ingress for Local Sessions](../managing-mirrord/local-share-ingress.md).
* Your Kubernetes roles grant the `get` verb on `sessions` in the `operator.metalbear.co` API group, in the target's namespace. The built-in mirrord user roles grant it. Without it, mirrord fails with an error that names this permission.
* Incoming mode `steal`. Sessions in `mirror` or `off` mode can't be shared.
* `mirrord exec`. `mirrord container` and `mirrord port-forward` can't share a session.
* A Kubernetes target. Sessions with `copy_target` and multi-cluster sessions can't be shared yet.

## Share one service

Save this as `.mirrord/web.toml`, with the target and port of your web service:

```toml
target = "deployment/web"

[feature.network.incoming]
mode = "steal"
ports = [3000]
```

Run your application with `--share`:

```bash
mirrord exec --share --key feature-checkout --config-file .mirrord/web.toml -- node server.js
```

You can also set `share = true` at the top level of the configuration file. `--share` turns sharing on even when the file sets `share = false`.

Before your application starts, mirrord prints the link, the port it waits for, and where a failure is logged:

```text
Share link: https://<link-host>
It routes to your application once it listens on port 3000, and ends when your application stops listening on that port or exits. If the link fails, mirrord stops your application and writes why to the internal proxy log at <log-path>.
Note: people who open this link reach the service running on your machine. Who can open it is set by your cluster's access rules.
```

Until your application listens on the port, the link answers with 404. In the IDE extensions, mirrord shows the link in a notification and in the mirrord log.

The link opens only the service you share. If you share `payments`, the link opens the `payments` API.

## Share a change that spans several services

Suppose you changed the frontend `web`, and it calls `payments` through the cluster. Run both locally with the same key, each with `--share`.

Save `.mirrord/payments.toml`:

```toml
target = "deployment/payments"

[feature.network.incoming]
mode = "steal"
ports = [8080]
```

Run it in a second terminal:

```bash
mirrord exec --share --key feature-checkout --config-file .mirrord/payments.toml -- node payments.js
```

Send people the link that `web` prints. Requests through that link carry `baggage: mirrord-session=feature-checkout`. **Each service must forward the `baggage` header, unchanged, on its calls to the next service**, usually through its tracing or context propagation middleware. Without it, the call from `web` reaches the cluster's `payments` instead of yours.

`payments` prints a link too. You can ignore it, or use it to call the `payments` API directly.

A shared session steals only HTTP requests whose `baggage` carries its key. With a custom HTTP filter, it steals requests that match the filter or carry the key. A steal session without `--share` keeps its configured filter, or steals all traffic on its ports when it has none.

To run `payments` without `--share` and without a second link, give it an explicit filter instead:

```toml
[feature.network.incoming.http_filter]
header_filter = "^baggage: .*mirrord-session={{ key }}.*$"
```

This filter works for keys made of letters, digits, `-`, and `_`.

## Choose the port

The link opens the first port in `feature.network.incoming.ports`. With `ports = [3000, 8080]`, the link opens port 3000, and mirrord steals both ports as usual.

Without `ports`, the target container must declare exactly one port that mirrord steals. Otherwise, mirrord asks you to set `feature.network.incoming.ports`.

## Lifetime

The link stops working when:

* You stop the session, or mirrord on your machine crashes.
* Your application stops listening on the port. This includes a dev server that restarts its listener when your code changes. The session keeps running, but the link doesn't come back. mirrord doesn't print that it ended. Restart the session to get a new link.

  Node.js closes its listener in a way mirrord sees only with `experimental.hook_libc_syscall = true`. Without it, the link stays until your Node application exits, and requests to it hang.
* The Operator loses the mirrord agent on the pod that the link opens, usually within a minute. mirrord stops your application and writes why to the internal proxy log, whose path it prints with the link. See [Silence on a live connection](../sharing-the-cluster/sessions.md#silence-on-a-live-connection).

If you stop the session before your application listens on the port, for example with Ctrl-C while a dev server is still building, the link is removed after the internal proxy's idle timeout, `internal_proxy.idle_timeout`, 5 seconds by default. mirrord waits that long so that a wrapper such as `npm run dev` can hand over to the process that serves your application without losing the link.

Every session gets a new link. Another session with the same key and the same target fails and prints the existing link, with the message `A share link for this key and service already exists`. This includes a session that you start within the idle timeout after you stopped one that never listened. The same key with a different target works.

For an environment that keeps running without your machine, use [Preview Environments](preview-environments.md).
