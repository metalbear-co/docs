---
title: Feature Matrix 
---

mirrord's advanced features - DB Branching, Queue Splitting, Preview Environments, and Multi-cluster - work across a range of platforms and infrastructure setups. 
Support levels vary by platform. The table below shows the current status for each combination.

### The columns reflect the different contexts in which a feature can be used:
- Standalone: using the feature on its own, with a standard mirrord session. A single developer runs mirrord locally and connects to the cluster directly, without any additional routing or isolation layer.
- Preview Env: using the feature inside a [preview environment](use-cases/preview-environments.md). Each developer or agent gets an isolated slice of the dependency - for example, their own queue partition or database branch — within a shared staging cluster, without affecting others.
- Multi-cluster: using the feature across [multiple clusters](using-mirrord/multi-cluster.md). Traffic, queue messages, or database connections are routed across cluster boundaries, useful when your infrastructure spans more than one cluster.
- mirrord up — using the feature when running multiple services together via [mirrord up](using-mirrord/multiple-concurrent-sessions.md). Similar to how docker compose orchestrates containers, mirrord up lets you define and launch several interdependent microservices in a single `mirrord-up.yaml` file, managing their lifecycle as a group.

 | Feature         | Platform          | Standalone       | Preview Env | Multi-cluster | mirrord up |
  |-----------------|-------------------|------------------|-------------|---------------|------------|
  | **DB Branching**    | **PostgreSQL**        | Beta (remote)    | Alpha       | Alpha         | Planned    |
  |                 | **MongoDB**           | Alpha (remote)   | Alpha       | Alpha         | Planned    |
  |                 | **MySQL**             | Alpha (remote)   | Alpha       | Alpha         | Planned    |
  |                 | **MSSQL**             | Alpha (remote)   | Alpha       | Alpha         | Planned    |
  |                 | **Redis**             | Alpha (local)    | Planned     | Planned       | Planned |
  | **Queue Splitting** | **SQS**               | GA               | Alpha       | Alpha         | Planned    |
  |                 | **Kafka**             | Alpha            | Alpha       | Planned       | Planned    |
  |                 | **Temporal**          | Planned          | Planned     | Planned       | Planned |
  |                 | **Google Pub/Sub**    | Alpha            | Alpha       | Alpha         | Planned    |
  |                 | **Azure Service Bus** | Alpha            | Alpha       | Alpha         | Planned    |
  |                 | **NATS**              | Planned          | Planned     | Planned       | Planned    |
  |                 | **Redis Pub/Sub**     | Planned          | Planned     | Planned.      | Planned |
  | **Preview Env**     | —                 | GA               | —           | Alpha         | Planned    |
  | **Multi-cluster**   | —                 | GA               | Alpha       | —             | Planned    |
  | **mirrord up**      | —                 | GA               | Alpha       | Alpha         | —          |


### Didn't find what you are looking for?
[Open a GitHub issue](https://github.com/metalbear-co/mirrord/issues) or reach out in the [mirrord Slack community](https://metalbearcommunity.slack.com/ssb/redirect) - and tell us what you're working with, we prioritize based on demand.
