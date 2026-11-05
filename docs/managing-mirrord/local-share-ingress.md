---
title: Share Ingress for Local Sessions
description: Set up share-ingress so developers can share services running on their machines
tags:
  - team
  - enterprise
---

# Share Ingress for Local Sessions

With `mirrord-share-ingress` installed, developers can [share links to services running on their own machines](../use-cases/sharing-local-services.md), not only to [Preview Environments](../use-cases/preview-environments.md#sharing-a-preview-via-a-link). Share-ingress receives the visitor's request from your public ingress, adds the session's `baggage` header, and forwards it over plain HTTP to the target pod, where mirrord steals it for the developer's session.

## Prerequisites

* A Team or Enterprise license. Local sharing doesn't need `operator.previewEnv`.
* The Operator can reach the share-ingress Service, and share-ingress can reach target pod IPs on the shared ports over plain HTTP. Check NetworkPolicy and service mesh rules.
* Wildcard DNS, a wildcard certificate, and access control for the share domain. A random link is not authentication: decide who may open developers' local services, and enforce it at your public ingress or gateway.

## Configure the charts

Use the [Operator installation guide](operator.md) for Helm repository and license setup. Add the share domain to the Operator's values, without `*.`:

```yaml
operator:
  shareIngress:
    shareDomain: share.example.com
```

Configure the share-ingress chart with the same domain, for example in `share-ingress-values.yaml`:

```yaml
namespace: mirrord
shareIngress:
  shareDomain: share.example.com
  notFound:
    redirect: false
```

The example turns the redirect off, so it needs no `appDomain`.

Install or upgrade it, together with the Operator chart:

```bash
helm upgrade --install mirrord-share-ingress metalbear/mirrord-operator-share-ingress --namespace mirrord --values share-ingress-values.yaml
```

The Operator looks for the `mirrord-share-ingress` Service in its own namespace. If share-ingress runs in another namespace, set `operator.shareIngress.serviceUrl` to its internal URL, for example `http://mirrord-share-ingress.share.svc`.

A link that no longer works gets the same 404 page as an expired preview link. To change that page, see `shareIngress.appDomain` and `shareIngress.notFound.redirect` in the [preview setup](../use-cases/preview-environments.md#setup).

## DNS, TLS, and access

Point `*.share.example.com` at your public ingress or gateway, use a wildcard certificate for that domain, keep the visitor's `Host` header, and route requests to `mirrord-share-ingress` port 80. The [preview setup](../use-cases/preview-environments.md#setup) has an NGINX Ingress example; adapt its domain and authentication.

## Errors

Before it creates a link, the Operator checks share-ingress. When a check fails, `--share` fails with one of these messages:

| Message starts with | Cause |
|---|---|
| Can't create a share link: this cluster doesn't have share-ingress set up | `operator.shareIngress.shareDomain` isn't set, or the share-ingress Service name doesn't resolve |
| Can't create a share link: the operator couldn't reach share-ingress | The Service exists, but share-ingress doesn't answer; check that it runs and that NetworkPolicy allows the Operator to reach it |
| Can't create a share link: share-ingress serves share hosts under | The two charts have different `shareDomain` values |
| Can't create a share link: the installed share-ingress doesn't support local share links | The share-ingress chart is older than the Operator chart |
| Can't create a share link: the installed share-ingress (local share version …) is newer than this operator supports | The Operator chart is older than the share-ingress chart; upgrade the Operator |
| Can't create a share link: the operator's share domain | `operator.shareIngress.shareDomain` isn't a valid DNS name |
| Can't create a share link: the operator's share-ingress address isn't a valid URL | `operator.shareIngress.serviceUrl` isn't a valid URL |

After the Operator creates the link, mirrord reads it once from the developer's session, before the application starts. When a read fails, `--share` fails with one of these messages:

| Message starts with | Cause |
|---|---|
| Share links need permission to get `sessions` in the `operator.metalbear.co` API group | The developer's roles don't grant the `get` verb on `sessions` in the target's namespace. The chart's mirrord user roles grant it; add it to roles you manage yourself. See [How do I configure Role Based Access Control](security.md#how-do-i-configure-role-based-access-control-for-mirrord-for-teams) |
| The cluster refused to read this session's share link | Kubernetes refused the read for another reason, such as expired credentials. The message ends with the cluster's reason |
| Reading this session's share link timed out | The cluster didn't answer in time; check the developer's connection to the cluster |
