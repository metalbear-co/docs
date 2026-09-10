---
title: Agent-Started Trials
description: How an AI coding agent starts a mirrord for Teams trial, and how to claim the organization it creates
draft: false
toc: true
tags: ["team", "enterprise"]
---

Some things an agent needs on a shared cluster only work with mirrord for Teams: branching a database so its writes don't reach everyone else's data, splitting a queue so it doesn't eat messages other people need, or stealing traffic from a target another session already holds.

On a cluster with no license, an agent that follows [metalbear.com/agents.md](https://metalbear.com/agents.md) can start a trial itself rather than stopping and waiting for you to sign up. It ends up with a working cluster and you end up with a link to claim.

## What the agent does

It posts to the signup endpoint. No authentication, no credit card:

```bash
curl -fsS -X POST https://app.metalbear.com/api/v1/agent/signup \
  -H 'content-type: application/json' \
  -d '{"agent": "claude-code", "developer_email": "you@example.com", "cluster_hint": "staging"}'
```

`developer_email` and `cluster_hint` are optional and unverified. They exist so you can recognize the organization as yours on the claim page.

The response is a **provisional organization** carrying an Enterprise trial license, good for seven days from the signup:

```json
{
  "organization_id": "...",
  "api_key": "...",
  "license_type": "enterprise-trial",
  "trial_ends_at": "2026-09-17T12:00:00+00:00",
  "claim_code": "mbclaim_...",
  "claim_url": "https://app.metalbear.com/claim?code=mbclaim_...",
  "instructions_url": "https://metalbear.com/agents.md"
}
```

The agent installs the Operator with that key as `cloud.apiKey.key` (see [Cloud API key](../managing-mirrord/operator.md#cloud-api-key)), then gives you the `claim_url`.

## Claiming the organization

Open the claim URL and sign in. What happens next depends on the account you use.

| You sign in as | Result |
| --- | --- |
| A new account with no organization | A new organization is created for you, keeping the trial's expiry date |
| An admin of an existing organization | The agent's cloud API key moves into your existing organization |
| A member of an existing organization who is not an admin | Rejected. Ask an admin to open the link |

Claiming also deletes the provisional organization, so the cluster keeps working against your real one without reinstalling anything.

An existing organization that already holds an active Operator cloud API key will reject the claim rather than replace the key it has. Revoke or rotate the existing key first, under **API Keys**. Read-only keys are a different scope and don't collide, so they can stay.

## Until it is claimed

A provisional organization is not a stuck state for the agent. The trial license works, so the cluster is usable straight away. What is missing is a person:

- **Nobody can administer it.** Billing, seats, and members all need a human owner, and the first person to claim it becomes that owner.
- **It expires with the trial.** An unclaimed organization reaches `trial_ends_at` with nobody able to renew or convert it.

Claim codes are single-use. Once one has been claimed, opening the same link from a different organization fails rather than silently joining it. Reopening it as the same admin who claimed it is harmless.

## If you already have an organization

You don't need any of this. Generate a cloud API key under **API Keys** and give it to the agent, or install the Operator yourself following the [dashboard setup guide](../managing-mirrord/dashboard/cloud.md). Signing up again creates a second organization you then have to clean up.
