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

You can also set `share = true` at the top level of the configuration file, or set the environment variable `MIRRORD_SHARE=true`. `--share` turns sharing on even when the file sets `share = false`.

mirrord sends the key as it is in the `baggage` header, so a shared session's key can hold only printable ASCII characters other than space, `"`, `%`, `,`, `;`, and `\`. A key such as `feature/checkout` works. mirrord refuses other keys before the session starts.

Before your application starts, mirrord prints the link, the port your application listens on, and where a failure is logged:

```text
Share link: https://<link-host>
Requests to it reach your application while it listens on port 3000, and the service running in the cluster otherwise. The link lasts as long as this session. If the session fails, mirrord stops your application and writes why to the internal proxy log at <log-path>.
Note: people who open this link reach the service running on your machine, and the one running in the cluster whenever a request doesn't reach your machine. Who can open it is set by your cluster's access rules for share links.
```

Until your application listens on the port, requests through the link reach the service running in the cluster. In the IDE extensions, mirrord shows the link in a notification. With `MIRRORD_PROGRESS_MODE=off`, mirrord doesn't print the link.

The link opens only the service you share. If you share `payments`, the link opens the `payments` API.

## Share a change that spans several services

Suppose you changed the frontend `web` and the `payments` service it calls through the cluster. Share `web`, and run `payments` locally with a regular steal session on the same key. You send people only the link that `web` prints.

Run `web` with `--share`, as in [Share one service](#share-one-service). Save `.mirrord/payments.toml`, with an HTTP filter on the key:

```toml
target = "deployment/payments"

[feature.network.incoming]
mode = "steal"
ports = [8080]

[feature.network.incoming.http_filter]
header_filter = "^baggage: .*mirrord-session={{ key }}.*$"
```

Run it in a second terminal, without `--share`:

```bash
mirrord exec --key feature-checkout --config-file .mirrord/payments.toml -- node payments.js
```

Requests through the link carry `baggage: mirrord-session=feature-checkout`. **`web` must forward the `baggage` header on its calls to `payments`**, usually through its tracing or context propagation middleware. Middleware can add its own members to the header: the filter above still matches. Without the header, the call from `web` reaches the cluster's `payments` instead of yours. The filter works for keys made of letters, digits, `-`, and `_`.

A shared session steals only HTTP requests whose `baggage` header is exactly `mirrord-session=<key>`, which is the header share-ingress puts on every request it forwards, replacing any `baggage` the request had. With a custom HTTP filter, it steals requests that match the filter or carry the key. A steal session without `--share` keeps its configured filter, or steals all traffic on its ports when it has none, so give `payments` the filter above rather than `--share`: a shared `payments` would miss calls from `web` whose `baggage` holds other members too.

## Choose the port

The link opens the first port in `feature.network.incoming.ports` that the target's Service exposes. With `ports = [3000, 8080]`, the link opens port 3000, and mirrord steals both ports as usual. If the Service exposes only 8080, the link opens 8080. When the Service exposes none of the ports, mirrord fails with an error that names the Service.

Without `ports`, the link opens one of the ports that the target container declares, that mirrord steals and that the Service leads to, chosen as for preview environments: the port behind the Service's port 80 if the Service has one, otherwise the port behind the Service's first such port. When the Service leads to none of them, mirrord asks you to set `feature.network.incoming.ports`.

## Lifetime

The link lasts as long as the session. Requests through it reach your application while it listens on the port, and the service running in the cluster otherwise. So the cluster's version answers:

* Before your application listens on the port, for example while a dev server is still building.
* After your application stops listening on the port, for example while a dev server restarts its listener when your code changes. Once your application listens again, the link reaches it again.
* On pods behind the Service that run without the session's mirrord agent, for example when the session has agents on fewer pods than the Service selects.

Node.js closes its listener in a way mirrord sees only with `experimental.hook_libc_syscall = true`. Without it, mirrord keeps stealing the port until your Node application exits, so requests through the link hang instead of reaching the cluster's version.

The link stops working when the session ends:

* When you stop the session, or mirrord on your machine crashes, the cluster's version keeps answering for about 30 seconds, until the Operator removes the session. Then the link answers with 404.
* When the Operator closes the session, for example because it lost the mirrord agent, mirrord stops your application and writes why to the internal proxy log, whose path it prints with the link. See [Silence on a live connection](../sharing-the-cluster/sessions.md#silence-on-a-live-connection).

Every session gets a new link. Another running session with the same key and the same target fails with the message `A share link for this key and service already exists`. The message ends with the existing link when you own the running session, and says that another user's session holds it otherwise. A session that you stopped counts only until mirrord's internal proxy exits, `internal_proxy.idle_timeout` after your application, 5 seconds by default. mirrord waits that long so that a wrapper such as `npm run dev` can hand over to the process that serves your application without ending the session. After that, the same command gets a new link. The same key with a different target works.

For an environment that keeps running without your machine, use [Preview Environments](preview-environments.md).
