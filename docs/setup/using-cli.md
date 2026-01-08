---
description: Install the mirrord CLI and run local processes in the context of your Kubernetes cluster
---

# Using the CLI

The mirrord CLI lets you run any local process in the context of your Kubernetes cluster. The CLI is the most flexible way to use mirrord. It works with any editor or IDE, can be integrated into shell scripts and CI pipelines, and gives you direct access to all mirrord options. No plugins or extensions required.

If you use VS Code or IntelliJ, the IDE extensions provide a more integrated experience with target selection UI and one-click enablement. See [Using VS Code](using-vscode.md) or [Using IntelliJ](using-intellij.md).

## Installation

{% tabs %}
{% tab title="macOS" %}

Using Homebrew:

```bash
brew install metalbear-co/mirrord/mirrord
```

Or using the install script:

```bash
curl -fsSL https://raw.githubusercontent.com/metalbear-co/mirrord/main/scripts/install.sh | bash
```

{% endtab %}

{% tab title="Linux" %}

Using the install script:

```bash
curl -fsSL https://raw.githubusercontent.com/metalbear-co/mirrord/main/scripts/install.sh | bash
```

{% endtab %}

{% tab title="Windows" %}

Using Chocolatey:

```powershell
choco install --pre mirrord
```

For WSL, see [Run on WSL](run-on-wsl.md) for detailed setup instructions.

{% endtab %}
{% endtabs %}

## Requirements

mirrord uses your local kubectl configuration to connect to your cluster. Before running mirrord:

1. **kubectl must be installed** and available in your PATH
2. **You must be authenticated** to a Kubernetes cluster
3. **Your current context** will be used — check with `kubectl config current-context`

To switch contexts, use `kubectl config use-context <context-name>`.

## Basic usage

Run a local process in the context of a remote pod:

```bash
mirrord exec --target pod/my-pod-name my-command
```

For example, to run a Python app while connected to a pod:

```bash
mirrord exec --target pod/api-pod-7d4b8c6f5-x2k9p python main.py
```

You can also target deployments (mirrord picks a pod automatically):

```bash
mirrord exec --target deploy/my-app npm run dev
```

## Using a configuration file

For more control, create a configuration file at `.mirrord/mirrord.json`:

```json
{
  "target": {
    "path": "deploy/my-app",
    "namespace": "staging"
  },
  "feature": {
    "network": {
      "incoming": "mirror",
      "outgoing": true
    },
    "fs": "read",
    "env": true
  }
}
```

Then run with the `-f` flag:

```bash
mirrord exec -f .mirrord/mirrord.json npm run dev
```

## Common commands

| Command | Description |
|---------|-------------|
| `mirrord exec --target <target> <command>` | Run a process with mirrord |
| `mirrord exec --help` | Show all exec options |
| `mirrord ls` | List available targets in your cluster |

## Next steps

mirrord has many configuration options for controlling networking, environment variables, and file system behavior. See the [configuration reference](../reference/configuration.md) for the full list, or head to [Using mirrord](../using-mirrord/README.md) to learn how these features work.

If you need to run a container instead of a native process (for example, due to complex dependencies), see [Run a Local Container](run-a-local-container.md).
