---
title: Sharing Local Services
description: Share a service running on your machine with an HTTPS link
tags:
  - team
  - enterprise
---

# Sharing Local Services

`mirrord exec --share` prints an HTTPS link to the service running on your machine. Anyone who opens the link reaches your local version while it runs, with nothing to install. Your service keeps using its cluster dependencies through mirrord.

## Prerequisites

* A Team or Enterprise license.
* Your platform team has set up [Share Ingress for Local Sessions](../managing-mirrord/local-share-ingress.md).
* Your Kubernetes roles grant the `get` verb on `sessions` in the `operator.metalbear.co` API group, in the target's namespace. The built-in mirrord user roles grant it. Without it, mirrord fails with an error that names this permission.
* Incoming mode `steal`. Sessions in `mirror` or `off` mode can't be shared.
* `mirrord exec`. `mirrord container` and `mirrord port-forward` can't share a session.
* A Kubernetes target. Sessions with `copy_target` and multi-cluster sessions can't be shared yet.
* A target that a Kubernetes Service of the same name exposes on the shared port, such as `deployment/web` with a Service `web`. The link reaches your session through that Service. Label targets and targetless sessions can't be shared, and a target without such a Service fails with an error that says what to change.

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

Before your application starts, mirrord prints the link, the port your application listens on, and where a failure is logged:

```text
Share link: https://<link-host>
Requests to it reach your application while it listens on port 3000, and the service running in the cluster otherwise. The link lasts as long as this session. If the session fails, mirrord stops your application and writes why to the internal proxy log at <log-path>.
Note: people who open this link reach the service running on your machine, and the one running in the cluster whenever a request doesn't reach your machine. Who can open it is set by your cluster's access rules for share links.
```

Until your application listens on the port, requests through the link reach the service running in the cluster. In the IDE extensions, mirrord shows the link in a notification. With `MIRRORD_PROGRESS_MODE=off`, mirrord doesn't print the link.

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

The link lasts as long as the session. Requests through it reach your application while it listens on the port, and the service running in the cluster otherwise. So the cluster's version answers:

* Before your application listens on the port, for example while a dev server is still building.
* After your application stops listening on the port, for example while a dev server restarts its listener when your code changes. Once your application listens again, the link reaches it again.
* On pods behind the Service that run without the session's mirrord agent, for example when the session has agents on fewer pods than the Service selects.

Node.js closes its listener in a way mirrord sees only with `experimental.hook_libc_syscall = true`. Without it, mirrord keeps stealing the port until your Node application exits, so requests through the link hang instead of reaching the cluster's version.

The link stops working when the session ends:

* When you stop the session, or mirrord on your machine crashes, the cluster's version keeps answering for about 30 seconds, until the Operator removes the session. Then the link answers with 404.
* When the Operator closes the session, for example because it lost the mirrord agent, mirrord stops your application and writes why to the internal proxy log, whose path it prints with the link. See [Silence on a live connection](../sharing-the-cluster/sessions.md#silence-on-a-live-connection).

Every session gets a new link. Another running session with the same key and the same target fails and prints the existing link, with the message `A share link for this key and service already exists`. A session that you stopped counts only until mirrord's internal proxy exits, `internal_proxy.idle_timeout` after your application, 5 seconds by default. mirrord waits that long so that a wrapper such as `npm run dev` can hand over to the process that serves your application without ending the session. After that, the same command gets a new link. The same key with a different target works.

For an environment that keeps running without your machine, use [Preview Environments](preview-environments.md).
