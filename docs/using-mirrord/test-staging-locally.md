# Test staging locally

This section covers the fundamentals of using mirrord to run your local process as if it were running inside your Kubernetes cluster. If you've completed the [Quick Start](../overview/quick-start.md), you're ready to go deeper.

## How mirrord works

When you run your application with mirrord, it intercepts your process at the system call level and redirects operations to a remote target in your cluster. This gives your local process:

- **Network access**: Outgoing connections go through the cluster, and incoming traffic from the target can be mirrored or stolen to your local process
- **Environment variables**: The same env vars your target pod has
- **File system access**: Read (or write) files from the target pod's filesystem

The result: your code runs locally with local tooling (debuggers, hot reload, your IDE), but behaves like it's running in the cluster.

## Choosing a target

Before running mirrord, you need to pick a target—the pod or workload whose context you want to "step into." The target determines:

- Which pod's environment variables you inherit
- Which pod's filesystem you can access
- Where your outgoing network traffic originates from
- Which incoming traffic can be sent to your local process

Specify a target with the `--target` flag:

```bash
# Target a specific pod
mirrord exec --target pod/my-app-7d4b8c6f5-x2k9p npm run dev

# Target a deployment (mirrord picks a pod)
mirrord exec --target deploy/my-app npm run dev
```

Or in a configuration file:

```json
{
  "target": {
    "path": "deploy/my-app",
    "namespace": "staging"
  }
}
```

For full details on targets, see [Targets](../reference/targets.md).

## The three fundamentals

The following pages cover the three core capabilities you'll use in most mirrord sessions:

### [Networking](networking.md)

Your process runs on your machine but connects to cluster services using cluster DNS. Outgoing requests go through the target pod's network context. You can also receive incoming traffic that was destined for the target.

### [Environment variables](environment-variables.md)

Load the target pod's environment variables into your local process—database URLs, feature flags, API keys, and service discovery values all come from the cluster.

### [File system](file-system.md)

Access files from the target pod: TLS certificates, mounted ConfigMaps, service account tokens, and other runtime files your app expects.

## A minimal configuration file

While CLI flags work for quick runs, a configuration file gives you repeatable, shareable settings. Create a `.mirrord/mirrord.json` file in your project:

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

Then run:

```bash
mirrord exec -f .mirrord/mirrord.json npm run dev
```

For the full configuration reference, see [Configuration](../reference/configuration.md).
