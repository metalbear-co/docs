---
title: Running mirrord from Cloud Agents
description: Let cloud and background coding agents use mirrord with a CI API key, so that each agent session does not take a seat.
draft: false
toc: true
tags: ["enterprise"]
---

# Cloud Agents

Many coding agents run in the cloud, not on a developer's machine. Examples are Cursor background agents, Claude Code on the web, Codex cloud tasks, Devin, and agent pods that your platform team runs. These agents can use mirrord to run and test their changes against your staging cluster, the same way an agent on a laptop does.

A cloud agent needs a different identity from a developer. By default, mirrord authenticates to the Operator with a user certificate that it creates for each machine. A cloud agent usually starts in a new, short-lived environment for each task. Each environment then registers as a new user and takes up a seat.

To prevent this, give your cloud agents a **CI API key**. Sessions that start with a CI API key don't take up seats. They are machine sessions, and they count towards the concurrent machine sessions of your [plan](https://metalbear.com/mirrord/pricing/). Many agents that run at the same time use many concurrent machine sessions.

## What you need

- The mirrord Operator in the cluster, on the Enterprise plan. You need the Enterprise plan to create a CI API key.
- mirrord CLI version `3.195.0` or later in the agent environment.
- A Linux or macOS agent environment. `mirrord ci` commands don't support Windows.
- Network access from the agent environment to the Kubernetes API of your cluster.

## 1. Give the agent environment access to the cluster

The agent environment needs a [kubeconfig](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/) that points to your staging cluster. Create a Kubernetes [service account](https://kubernetes.io/docs/concepts/security/service-accounts/) for your agents, and do not use the credentials of a developer. Give the service account only the permissions that mirrord needs in the namespaces where the agents work.

Put the kubeconfig in the agent environment with the secrets feature of your agent platform, or build it into the image that the agents start from.

{% hint style="warning" %}
Point cloud agents at a staging or development cluster, not at production.
{% endhint %}

## 2. Create a CI API key

Run this command from a machine that has access to the cluster:

```sh
mirrord ci api-key
```

Save the key as a **secret** environment variable named `MIRRORD_CI_API_KEY` in your agent platform. All your agents can use the same key.

## 3. Run mirrord from the agent

When `MIRRORD_CI_API_KEY` is set, mirrord authenticates every session with the key. You have two options for the commands that the agent runs.

**Use `mirrord ci start` (recommended).** It starts the service in the background, so the agent can run its tests and send requests in the same shell. When the agent is done, it stops the session:

```sh
mirrord ci start --target deployment/my-service --pipeline cloud-agent -- npm run start
# run the tests or send requests to the service
mirrord ci stop
```

Use `--foreground` to keep the service in the foreground. Use `--pipeline`, `--environment`, and `--triggered-by` to label the sessions, for example with the name of the agent or the task.

**Keep `mirrord exec`.** If your agents already run `mirrord exec`, for example from a shared `AGENTS.md` or from the [mirrord agent skills](./ai-skills-plugin.md), you don't have to change it. When `MIRRORD_CI_API_KEY` is set, mirrord runs `mirrord exec` as `mirrord ci start --foreground` and prints a warning. Move to `mirrord ci start` when you can.

The [CI/CD Integration](../use-cases/mirrord-for-ci.md) page has the full reference for `mirrord ci` commands, application logs, and containers.

## 4. Keep agent sessions apart

All the agents that use the same key share one identity. Many agent sessions can also target the same service at the same time. Configure mirrord so that each session gets only its own traffic and data:

- **Incoming traffic:** Use steal mode with an [HTTP filter](../using-mirrord/incoming-traffic/filter-incoming-traffic.md) on a header that is unique to each agent task. Without a filter, one agent session takes all the traffic of the target.
- **Queues:** Use [queue splitting](../sharing-the-cluster/queue-splitting.md), so that each session gets only the messages that match its filter.
- **Databases:** Use [DB branching](../sharing-the-cluster/db-branching.md), so that each session writes to its own branch and not to the shared database.

You can put these settings in a `mirrord.json` file in the repository, and pass the unique header value from an environment variable. For example: `"header_filter": "x-agent-task: {{ get_env(name='AGENT_TASK_ID') }}"`.
