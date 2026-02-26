---
title: Welcome
description: mirrord documentation — run local code in the context of your cloud environment
---

# mirrord

mirrord lets developers run local processes in the context of their cloud environment. Test your code against real cloud services — databases, queues, APIs — without deploying, without mocks, and without disrupting your staging environment.

## What can you do with mirrord?

| Use case | Description |
|----------|-------------|
| **[Local Development with Cloud Context](use-cases/local-development.md)** | Run your code locally while it talks to real cloud services — incoming traffic, outgoing connections, environment variables, and files all come from the cluster |
| **[mirrord for CI](use-cases/mirrord-for-ci.md)** | Run your CI tests against a real cloud environment instead of mocks |
| **[Preview Environments](use-cases/preview-environments.md)** | Spin up isolated, ephemeral environments in your cluster for async review and QA |

## Get started

1. **[Quick Start](getting-started/quick-start.md)** — Install mirrord and run your first session in minutes
2. **[Installing mirrord](installing-mirrord/README.md)** — CLI, VS Code, JetBrains IDEs, and WSL setup guides

## Open source vs Teams

mirrord's core functionality is free and open source. [mirrord for Teams](https://metalbear.com/mirrord/pricing) adds the mirrord Operator — a Kubernetes operator that enables concurrent cluster usage, advanced traffic control, and organizational governance.

Features marked with **[Teams]** in these docs require a mirrord for Teams license.

## Resources

- [GitHub](https://github.com/metalbear-co/mirrord) — Source code and issue tracker
- [Slack community](https://metalbear.com/slack) — Get help and share feedback
- [Configuration reference](reference/configuration.md) — All available config options
