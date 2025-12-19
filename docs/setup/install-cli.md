# Install & Run via CLI

The mirrord CLI lets you run any local process in the context of your Kubernetes cluster.

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

Using Homebrew:

```bash
brew install metalbear-co/mirrord/mirrord
```

Or using the install script:

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

**Local machine:**
- macOS (Intel or Apple Silicon)
- Linux (x86_64)
- Windows (x86_64) or WSL (x86_64)

**Cluster:**
- Docker or containerd runtime
- Linux kernel 4.20+

kubectl must be configured to access your cluster.

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
| `mirrord operator status` | Check operator status (mirrord for Teams) |

## Next steps

- **[Configuration reference](../reference/configuration.md)** — Full list of configuration options
- **[Using mirrord](../using-mirrord/README.md)** — Learn about networking, environment variables, and file system features
- **[Run a Local Container](run-a-local-container.md)** — Run mirrord with a local container instead of a native process
