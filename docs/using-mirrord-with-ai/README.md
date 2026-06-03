---
title: Using mirrord with AI Agents
description: Configure AI coding agents to test code changes against your cluster using mirrord
draft: false
toc: true
tags: ["open source", "team", "enterprise"]
---

AI coding models don’t have the full context of your application — external dependencies, environment variables, and the way services interact in production. The code they generate might look correct in isolation, but things often break once you try integrating it with the rest of your system.

If you're using tools like Claude Code, Cursor, or Codex, mirrord lets you safely test AI-generated code in a real, production-like Kubernetes environment in seconds, instead of relying on mocks or waiting for CI/CD to reveal integration issues.

Here are some ways you can connect mirrord to your AI coding workflow:

- **[Agent skills for mirrord](./ai-skills-plugin.md)** - Install skills that give your AI assistant built-in mirrord expertise.
- **[Configure AI Agents to Use mirrord](./the-meta-prompt.md)** - A prompt generator that creates project-specific `AGENTS.md` files and configurations automatically, saving hours of manual setup across multiple services.
