---
title: "MetalBear Cloud Sessions-Manager"
description: "Target serverless workloads such as Amazon ECS tasks without the mirrord Operator, through a sessions-manager hosted by MetalBear, with workloads authenticated by a MetalBear API key and developers by `mirrord login`."
tags:
  - experimental
  - enterprise
---

{% hint style="warning" %}
The MetalBear Cloud sessions-manager is **experimental**, and may change without notice. It needs an API key that MetalBear provides on request; see [API key provided by MetalBear](README.md#api-key-provided-by-metalbear).
{% endhint %}

In the MetalBear Cloud [deployment mode](README.md#deployment-modes), sessions-manager is hosted by MetalBear. There's nothing to install in your infrastructure, and you don't need a Kubernetes cluster or the mirrord Operator. Workloads and developers connect to it directly over HTTPS. Workloads authenticate with a MetalBear API key, and developers with their MetalBear account, through `mirrord login`. At a glance, the setup is:

1. Get an API key from MetalBear ([API keys](#api-keys)).
2. Allow outbound HTTPS from your workloads to MetalBear ([Network access](#network-access)).
3. Connect each workload, which sets the API key on it ([Connecting workloads](#connecting-workloads)).
4. Have developers sign in with `mirrord login` ([Developer setup](#developer-setup)).

## Prerequisites

1. An API key `<API_KEY>`, [provided by MetalBear](README.md#api-key-provided-by-metalbear).
2. Outbound HTTPS access from your workloads and from developers' machines to MetalBear.

---

## How it works

{% hint style="info" %}
This section is for whoever reviews the setup, such as your security team. To start the setup, skip to [API keys](#api-keys).
{% endhint %}

```
 developer machine                     MetalBear                                workload network
┌───────────────────┐   HTTPS     ┌──────────────────────────┐   HTTPS     ┌───────────────────────────┐
│ mirrord exec      │───────────► │ sessions-manager         │ ◄───────────│ application container     │
│ (local process)   │             │                          │             │ + mirrord remote          │
└─────────┬─────────┘             │ app.metalbear.com        │             │   bootstrap (LD_PRELOAD)  │
          └─────────────────────► │   (token exchange)       │ ◄───────────┴───────────────────────────┘
                                  └──────────────────────────┘
```

Workloads authenticate with the API key:

1. The API key is set on the workload, in `MIRRORD_SESSIONS_MANAGER_API_KEY`.
2. Before each request that registers with sessions-manager, the workload exchanges the key at `https://app.metalbear.com` for a short-lived token, and presents the token to sessions-manager as `Authorization: Bearer <token>`. The key itself is only ever sent to that exchange, in the request body, over HTTPS, and never to sessions-manager. Neither the key nor the tokens are logged.
3. Sessions-manager verifies the token against MetalBear's signing keys. The token identifies your organization, and every registration is scoped to it: workloads and developers are only ever paired within the same organization.
Developers authenticate with the credentials `mirrord login` stores on their machine when they sign in to their MetalBear account. They never handle the API key.

Each data-plane connection is bound to its session by a single-use credential delivered with the session assignment, so a caller can't attach to another caller's session.

Only API keys issued for serverless workloads are accepted. Other MetalBear credentials, such as the Operator's license key, are refused by sessions-manager.

Both sides only make outbound HTTPS connections. Neither needs a network path to the other, and nothing in your infrastructure accepts inbound connections.

{% hint style="warning" %}
The API key authenticates your organization, not a specific workload: anyone who holds it can register a workload under any service and environment of your organization, and be paired with your developers' sessions. Treat it as a secret, and give it only to the workloads that need it.
{% endhint %}

---

## API keys

MetalBear issues the API key for your organization when you request access. It begins with `metalbear_key_`; mirrord refuses to start with a value that doesn't.

Only workloads use the key; developers don't need it. Store it in a secret store, such as AWS Secrets Manager, rather than in plain configuration or source control. Your platform's connection guide shows how to inject it into the workload, for example [Connecting ECS to MetalBear Cloud](ecs-metalbear-cloud.md#store-the-api-key).

To rotate the key, request a new one, update it wherever it's stored, and restart the workloads, then ask MetalBear to revoke the old one. Once a key is revoked, new registrations with it are refused; sessions that are already open continue until they end.

## Network access

Both workloads and developers' machines need outbound HTTPS (TCP 443) to:

| Host | Used for |
| --- | --- |
| MetalBear's sessions-manager | Registering, and the session's traffic. |
| `app.metalbear.com` | Exchanging the API key for a token, and `mirrord login`. |

Sessions hold their connections open for as long as the developer runs them. Any proxy or firewall on the path must not buffer responses and needs an idle timeout of at least 300 seconds.

## Connecting workloads

Each workload needs one variable, next to the ones that [name the workload](ecs.md#name-the-workload):

| Variable | Value |
| --- | --- |
| `MIRRORD_SESSIONS_MANAGER_API_KEY` | `<API_KEY>`, injected from your secret store. |

The bootstrap connects to MetalBear's sessions-manager by default. Don't set `MIRRORD_OPERATOR_API_URL` or `MIRRORD_OPERATOR_KUBE_CONTEXT`, which select the [Operator-hosted mode](operator-hosted.md) instead.

How to set them depends on the platform:

* [Connecting ECS to MetalBear Cloud](ecs-metalbear-cloud.md)

## Developer setup

Developers need no Kubernetes access and no API key. They sign in to their MetalBear account once:

```bash
mirrord login
```

mirrord stores the credentials on their machine, and uses them for every MetalBear Cloud session. Then they use the `mirrord.json` from [Using mirrord with a Serverless Workload](README.md#using-mirrord-with-a-serverless-workload) without `"operator": true`. With `"operator": true`, mirrord connects through the Operator instead.

---

## Troubleshooting

The workload's messages appear in the application container's logs, and the developer's in mirrord's output.

| Symptom | Likely cause |
| --- | --- |
| `MIRRORD_SESSIONS_MANAGER_API_KEY must hold a MetalBear API key, which begins with metalbear_key_` | The variable holds something else, such as the secret's ARN instead of its value, or has extra whitespace or quotes. |
| `the MetalBear API key was rejected` | The key is mistyped or revoked. |
| `HTTP control plane returned 401 Unauthorized` | `MIRRORD_SESSIONS_MANAGER_API_KEY` isn't set, or the key isn't a serverless workload key, for example an Operator license key. |
| A connection timeout to sessions-manager or `app.metalbear.com` | Outbound HTTPS is blocked ([Network access](#network-access)). |
| The workload registers but the developer is never paired | The workload's service and environment names don't match `target.path` and `target.namespace` in `mirrord.json`, or the developer is signed in to a different organization than the workload's API key belongs to. |
| mirrord on a developer's machine is refused with `401 Unauthorized` | The developer isn't signed in, or their sign-in expired. Run `mirrord login`. |
| `MIRRORD_SESSIONS_MANAGER_URL, MIRRORD_OPERATOR_API_URL and MIRRORD_OPERATOR_KUBE_CONTEXT are mutually exclusive` | The workload sets variables of both modes; keep only those of [Connecting workloads](#connecting-workloads). |
