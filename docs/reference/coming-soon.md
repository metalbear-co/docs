---
title: Coming Soon
date: 2025-04-07T00:00:00.000Z
lastmod: 2025-04-07T00:00:00.000Z
draft: false
images: []
description: Features currently in active development, landing in mirrord soon
---


## Session Visibility in the Browser Extension
The mirrord browser extension is getting a major upgrade: a live session view powered by the mirrord Operator.

Today, the extension lets you inject a header into browser requests to route traffic to your service. The next version goes further - it connects to the Operator and shows every active session across your
cluster in a single popup, grouped by key. A single key can span multiple sessions (for example, when a developer runs multiple services under the same routing context). You'll be able to join any session with
one click, and the extension will automatically update the active key and inject the right header for you.

**What's coming:**

- Live list of all active Operator sessions, grouped by key
- Join or switch sessions in one click, no manual header editing
- Per-browser-tab indicator showing which key is currently active on that tab
- Support for both local sessions and preview environment (remote) sessions in a unified view

Running `mirrord webext` starts a local server that the extension connects to, which then communicates with the cluster to fetch and stream session data in real time.

---

## Multi-Service Session Launcher: `mirrord up`

Working in a monorepo or a service-based architecture often means juggling multiple `mirrord.json` files - one per service, and starting sessions individually. `mirrord up` is a new top-level command designed to replace that workflow.

You define all your services once in a `mirrord-up.yaml` file at the root of your repo. Running `mirrord up` reads that file which allows you to select a service. mirrord then generates the appropriate `mirrord.json` for it and starts the session. 

**Key behaviours:**

- `mirrord up` with no arguments looks for `mirrord-up.yaml` in the current directory
- The `mirrord-up.yaml` format is a simplified schema that maps service names to their targets and any per-service overrides, without requiring you to write a full `mirrord.json` for each one.

---

## RabbitMQ Queue Splitting

Queue splitting - which lets mirrord route a copy of queue messages to your local service instead of (or alongside) the deployed service, is coming to RabbitMQ.

This works the same way as the existing SQS and Kafka queue splitting support: mirrord intercepts messages from a RabbitMQ queue and routes them to your local process based on the filtering rules you configure,
without affecting other consumers or the deployed service.

Configuration will follow the same pattern used for other queue types in `mirrord.json`:

```json
{
"feature": {
    "split_queues": {
    "my-rabbit-queue": {
        "queue_type": "RabbitMQ",
        "message_filter": {
        "header_filter": "baggage: {my-key}"
        }
    }
    }
}
}
```

{% hint style="info" %}
RabbitMQ splitting requires the mirrord Operator and a MirrordWorkloadQueueRegistry CRD configured for your cluster. Setup is identical to the existing queue splitting workflow.
{% endhint %}

---
## MSSQL Database Branching

Database branching - which gives each mirrord session an isolated copy of a database to work against, is being extended to Microsoft SQL Server.

This brings MSSQL in line with the existing MySQL and PostgreSQL support. When you run a session with database branching configured, mirrord automatically creates a branch of your MSSQL database scoped to your
session. Your local service connects to the branch rather than the shared database, so your changes: schema migrations, test data, writes, don't affect other developers or running services.

When the session ends, the branch is cleaned up automatically.

Configuration follows the same pattern as other supported databases:

```json
{
    "feature": {
        "database_branching": {
        "connection": {
            "type": "mssql",
            "connection_string": "Server=my-server;Database=my-db;..."
        }
        }
    }
}
```

## Interested in what's coming?
    Check back here for updates as each one of the new feature ships, or [Subscribe to our newsletter to get updates](https://metalbear.com/#newsletter) and be notified when these features are available.
