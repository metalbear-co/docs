---
title: Agent Skills for mirrord
---

MetalBear maintains a **mirrord skills plugin** that extends AI coding assistants, such as Cursor and Claude Code with domain-specific knowledge about mirrord. Instead of relying solely on general instructions in `AGENTS.md`, these skills give your AI assistant built-in expertise for mirrord configuration, troubleshooting, and best practices.

{% embed url="https://www.youtube.com/watch?v=zbbJaorZYl0" %}
**See the mirrord agent skills plugin in action**

## What Are mirrord Skills?

Skills are reusable instruction modules that teach AI agents how to work with mirrord. When you install the mirrord skills plugin, your AI assistant can:

- Generate and validate `mirrord.json` configuration files
- Guide you through installation and your first mirrord session
- Help set up mirrord in CI pipelines
- Configure the mirrord operator for team environments
- Help set up [database branching](../using-mirrord/db-branching.md) for your cluster


## Available Skills

| Skill | Purpose |
|-------|---------|
| **mirrord-quickstart** | Guides users from zero to their first working mirrord session. Use when a user is new to mirrord, wants to install it, or needs help running their first session connecting to a Kubernetes cluster. |
| **mirrord-config** | Helps generate, edit, and validate `mirrord.json` configuration files. Use when the user wants to connect their local process to a Kubernetes environment, configure features (env/fs/network), or needs feedback on an existing config. |
| **mirrord-ci** | Helps set up mirrord in CI pipelines for testing against real Kubernetes environments. Use when users want to run end-to-end tests, integration tests, or automated tests in CI using mirrord to connect to staging/shared clusters. |
| **mirrord-operator** | Helps install and configure the mirrord operator for team environments. Use when users ask about operator setup, Helm installation, licensing, or multi-user mirrord deployments. |
| **mirrord-db-branching** | Helps configure mirrord for database branching, enabling isolated database copies for safe development and testing. Use when the user wants to set up MySQL or PostgreSQL branching, configure copy modes, IAM authentication, or manage database branches. |

## Installing the mirrord Skills

The mirrord skills are distributed as a plugin that you install into your AI coding assistant. Installation steps depend on your tool.

Check the [mirrord skills repository](https://github.com/metalbear-co/mirrord-skills) for the latest installation instructions, supported assistants (Cursor, Claude Code and others), and any tool-specific requirements.
