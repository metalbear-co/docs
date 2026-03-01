---
title: Welcome
description: mirrord documentation - run local code in the context of your cloud environment
layout:
  title:
    visible: true
  description:
    visible: true
  tableOfContents:
    visible: true
  outline:
    visible: true
  pagination:
    visible: true
---

# mirrord

mirrord plugs your local process into a Kubernetes cluster. Instead of deploying to test, your code runs locally while accessing real cloud traffic, environment variables, file systems, and network. No mocks, no CI cycles, no waiting.

```
┌─────────────────────────────────────────────────────────┐
│  Kubernetes Cluster (staging)                           │
│                                                         │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐         │
│   │ Service A │◄──►│ Service B │◄──►│   DB     │         │
│   └────▲─────┘    └──────────┘    └──────────┘         │
│        │                                                │
│        │  mirrord connects your                         │
│        │  local process here                            │
│        │                                                │
└────────┼────────────────────────────────────────────────┘
         │
    ┌────┴─────┐
    │  Your    │
    │  Laptop  │
    │  (IDE)   │
    └──────────┘
```

<table data-view="cards"><thead><tr><th></th><th></th><th data-hidden data-card-target data-type="content-ref"></th></tr></thead><tbody><tr><td><strong>Quick Start</strong></td><td>Install mirrord and run your first session in minutes.</td><td><a href="getting-started/quick-start.md">getting-started/quick-start.md</a></td></tr><tr><td><strong>What is mirrord?</strong></td><td>Understand how mirrord works and how it's different from alternatives.</td><td><a href="getting-started/what-is-mirrord.md">getting-started/what-is-mirrord.md</a></td></tr><tr><td><strong>Use Cases</strong></td><td>Remocal development, CI/CD integration, preview environments, and more.</td><td><a href="use-cases/local-development.md">use-cases/local-development.md</a></td></tr><tr><td><strong>Guides</strong></td><td>Traffic filtering, queue splitting, DB branching, and other how-to guides.</td><td><a href="using-mirrord/incoming-traffic/README.md">using-mirrord/incoming-traffic/README.md</a></td></tr></tbody></table>

## Open source vs Teams

mirrord's core functionality is free and open source. [mirrord for Teams](https://metalbear.com/mirrord/pricing) adds the mirrord Operator, enabling concurrent cluster usage, advanced traffic control, and organizational governance. Features marked with **\[Teams]** in these docs require a license.
