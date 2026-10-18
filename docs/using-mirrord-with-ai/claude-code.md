---
title: How to Let Claude Code Test Its Changes Against Your Staging Cluster
description: Set up Claude Code to run the code it writes against the real services in your staging Kubernetes cluster with mirrord, with no deploy and no mocks to maintain.
draft: false
toc: true
tags: ["oss", "team", "enterprise"]
---

Claude Code can write a change to a microservice in a few minutes. To check that the change works, it needs the things that the service talks to: the other services, the queues, the database, and the configuration of the real environment. On a laptop, those are missing or mocked, so Claude Code can only check that the code compiles and that the unit tests pass.

mirrord closes that gap. Claude Code runs the service on your machine, and mirrord connects the process to a pod in your staging cluster. The process gets the pod's environment variables, DNS, network access, and incoming traffic. Claude Code can then run the service and its tests against the real services in staging, read the real responses, and fix what breaks before you review the change. Nothing is built or deployed.

This also works when many developers and Claude Code sessions test against the same staging cluster at the same time. With the mirrord Operator, each session gets only its own requests, its own queue messages, and its own database branch, so the sessions do not break each other or the deployed services.

This guide sets this up in about five minutes.

## What you need

- Claude Code.
- A kubeconfig with access to a **staging or development** cluster.
- A service that runs in that cluster, and its source code on your machine.

## 1. Install the mirrord CLI

macOS and Linux:

```sh
brew install metalbear-co/mirrord/mirrord
```

Or with the install script:

```sh
curl -fsSL https://raw.githubusercontent.com/metalbear-co/mirrord/main/scripts/install.sh | bash
```

Check the install with `mirrord --version`, and check cluster access with `kubectl get pods -n <namespace>`.

## 2. Add the mirrord skills to Claude Code

In Claude Code, run:

```
/plugin marketplace add metalbear-co/skills
/plugin install mirrord@mirrord-skills
```

The plugin gives Claude Code skills for mirrord: how to find a target, write a valid `mirrord.json`, run a session, and use the features for shared clusters. Claude Code loads the right skill when your prompt needs it. See [Agent Skills for mirrord](./ai-skills-plugin.md) for the full list.

## 3. Tell Claude Code how to test in this repository

Add a short section to the `CLAUDE.md` file at the root of the repository. Claude Code reads this file at the start of each session.

```markdown
## Testing against staging

ALWAYS test changes to <service> against the staging cluster with mirrord before you report them as done.

- Target: deployment/<service> in namespace <namespace>, kubecontext <staging-context>
- Run the service: mirrord exec -f .mirrord/mirrord.json -- <command that starts the service>
- Run the integration tests: mirrord exec -f .mirrord/mirrord.json -- <test command>
- Send test requests with the header `x-dev-user: <your-name>`, so that only your requests reach your local process.
- NEVER target a production cluster.
```

To generate this section and the config files for many services at once, use the [meta-prompt](./the-meta-prompt.md).

## 4. Let Claude Code write the mirrord config

The `mirrord-config` skill from step 2 writes `mirrord.json` and validates it against the schema. Ask Claude Code to use it:

```
Use the mirrord-config skill to create .mirrord/mirrord.json for <service>.
Target deployment/<service> in namespace <namespace>, and pin the kubecontext to
<staging-context>. Steal only the requests that carry the header
x-dev-user: <your-name>, as an exact match. Read env vars and files from the pod.
```

Check that the result has these two settings:

```json
{
  "kube_context": "<staging-context>",
  "feature": {
    "network": {
      "incoming": {
        "mode": "steal",
        "http_filter": { "header_filter": "^x-dev-user: <your-name>$" }
      }
    }
  }
}
```

`kube_context` pins the session to the staging cluster. Without it, mirrord uses your current kubecontext, so the same command runs against another cluster after you switch contexts.

The `http_filter` matters on a shared cluster. Only requests that carry your header go to the process on your machine, and all other requests keep going to the deployed service, so your session does not break staging for the rest of the organization. The filter is a regular expression, so the `^` and `$` must stay: without them, a filter for `ann` also matches `anna`. If you only want to read traffic and not answer it, ask for `mirror` mode.

## 5. Let Claude Code run mirrord without a prompt each time

Claude Code asks for approval before it runs a shell command. To let it run mirrord sessions without a prompt each time, add this to `.claude/settings.json` in the repository:

```json
{
  "permissions": {
    "allow": ["Bash(mirrord exec:*)", "Bash(mirrord ls:*)"]
  }
}
```

Keep other commands on approval while you get used to the workflow.

## 6. Ask Claude Code to make and test a change

Some prompts to start with:

- "Add a `currency` field to the `/orders` response. Then run the service with mirrord and call `/orders` on staging with my header to check the new field."
- "Run the integration tests for this service against staging with mirrord, and fix what fails."
- "Before you change the payment client, run the service with mirrord and print the real response from the payments service, so you see the actual schema."

Claude Code runs `mirrord exec`, sends requests with your header, reads the responses and logs, and changes the code until the result is correct. The first session on a cluster takes longer, because mirrord starts its agent pod.

## More than one developer or agent on the same cluster

Open-source mirrord works on any cluster. When several developers or several Claude Code sessions test against the same service at the same time, the cluster needs the mirrord Operator, which is part of mirrord for Teams. With the Operator, each session gets only the requests that match its own header filter, and it can also get:

- its own branch of a staging database ([DB branching](../sharing-the-cluster/db-branching.md)), so its writes do not change the shared data
- only its own messages from a shared queue ([queue splitting](../sharing-the-cluster/queue-splitting.md)) for Kafka, SQS, RabbitMQ, and other brokers
- a [preview environment](../use-cases/preview-environments.md) that keeps the change running after the session ends, for review

If the cluster has no license, Claude Code can start a seven-day Enterprise trial itself with `mirrord operator install --no-browser`, and give you a link to claim it. See [Agent-Started Trials](./agent-started-trials.md).

## If a session does not start

- **Claude Code cannot connect to the mirrord agent.** Check that `kubectl get pods -n <namespace>` works from the same terminal. Then check that you can create pods in the namespace where mirrord starts its agent. Without the Operator, that is the current namespace of your kubecontext, not the target's namespace, unless you set `agent.namespace` in the config. Tell Claude Code to stop and report the error after two failures, not to retry in a loop.
- **The requests do not reach the local process.** Check that the requests carry the exact header in `header_filter`. The filter is a regular expression, matched against the request headers.
- **The service reads a file that is not on your machine.** mirrord reads files from the pod by default with `"fs": "read"`. Change the `fs` setting if the service must read local files.

For other errors, see [Common Issues](../troubleshooting/common-issues.md).

## Related

- [Agent Skills for mirrord](./ai-skills-plugin.md)
- [Configure AI agents to use mirrord](./the-meta-prompt.md) (the meta-prompt)
- [metalbear.com/agents.md](https://metalbear.com/agents.md), instructions written for agents
- [mirrord integrations](https://metalbear.com/mirrord/integrations/), setup for Codex, Cursor, GitHub Copilot, and other agents
