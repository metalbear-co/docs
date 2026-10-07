---
title: Agent Skills for mirrord
tags:
  - oss
  - team
  - enterprise
description: "Install the mirrord skills plugin to give AI coding assistants like Cursor and Claude Code domain-specific knowledge of how to work with mirrord."
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
- Help set up [database branching](../sharing-the-cluster/db-branching.md) for your cluster
- Configure [queue splitting](../sharing-the-cluster/queue-splitting.md) for Kafka topics
- Make your services [propagate the baggage header](../use-cases/preview-environments-in-ci.md#header-propagation-for-backend-testing) across HTTP, gRPC, and queues, so filters, preview environments, and queue splitting follow a request end to end, and get a report of every hop where the header is still dropped
- Create [preview environments](../use-cases/preview-environments.md), ad hoc or per-PR in CI
- [Chaos test](../use-cases/chaos-testing.md) your app with per-session latency and connection-error rules


## Available Skills

For the full list of skills, what each one covers, and example prompts, see <a href="https://github.com/metalbear-co/skills/#mirrord-agent-skills" target="_blank" rel="noopener noreferrer">mirrord Agent Skills</a> in the <a href="https://github.com/metalbear-co/skills/" target="_blank" rel="noopener noreferrer">metalbear-co/skills</a> repository.

## Installing the mirrord Skills

The mirrord skills are distributed as a plugin that you install into your AI coding assistant. Installation steps depend on your tool.

### Claude Code

Run these commands in Claude Code:

```bash
/plugin marketplace add metalbear-co/skills
/plugin install mirrord@mirrord-skills
```

### Codex

Add the marketplace:

```bash
codex plugin marketplace add metalbear-co/skills
```

Then install the `mirrord` plugin from `/plugins`. The plugin includes all the skills.

### Cursor, Gemini CLI, and Other Agent Skills Agents

For any agent that supports [Agent Skills](https://agentskills.io), run:

```bash
npx skills add metalbear-co/skills
```

### OpenCode and Other Agents That Read a Skills Directory

The install script writes the skill folders to disk. By default, it writes them to `~/.config/opencode/skills/`:

```bash
curl -fsSL https://raw.githubusercontent.com/metalbear-co/skills/main/install.sh | sh
```

To install for a different agent, download the script and pass a target:

```bash
sh install.sh --agent codex     # ~/.agents/skills
sh install.sh --agent claude    # ~/.claude/skills
sh install.sh --dest <dir>      # any other directory
```

Restart the agent after you install. Run the script again to update the skills. It replaces only the `mirrord-*` folders.

For the latest instructions, see the <a href="https://github.com/metalbear-co/skills/#installation" target="_blank" rel="noopener noreferrer">mirrord skills repository</a>.

## Agents That Don't Support Agent Skills

GitHub Copilot and Cline read repository rules files instead of Agent Skills. The skills repository ships drop-in equivalents carrying the same core content in its <a href="https://github.com/metalbear-co/skills/tree/main/ports" target="_blank" rel="noopener noreferrer">ports directory</a>: copy `ports/github-copilot/copilot-instructions.md` into your repository's `.github/` folder, or `ports/cline/.clinerules` into the repository root.
