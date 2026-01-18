---
title: The Meta-Prompt
description: Configure AI Agents to Use mirrord
---

[Environment Setup](sing-mirrord-with-ai/the-meta-prompt#environment-Setup)

The Meta-Prompt

Exploring the Generated Files

Testing the Workflow

Try It Yourself

Benefits for the Team

[Wrapping Up]()

## Environment Setup
For this demo, we’ll use the [the MetalBear playground repository](https://github.com/metalbear-co/playground). - It's a simple IP visit counter application written in Go, with a Redis dependency, which makes it ideal for demonstrating how this works.

The architecture looks like this:
![High Aevel Architecture](using-mirrord-with-ai/high-level-architecture.png)

### Here’s what you’ll need to get started:
- Access to a Kubernetes cluster, such as a staging environment
- kubectl configured and ready
- mirrord installed locally
- For this guide, we use Claude Code v2.0.76 as the AI assistant. In the Try it yourself section, we’ll cover other assistants that can be used with the same workflow.

You can follow along using any cluster you already have access to, whether it’s staging or development. The important part is that you’re testing against a real environment.