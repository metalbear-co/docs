---
title: Collecting Logs
date: 2026-09-27T00:00:00.000Z
description: Where each mirrord component writes its logs, how to raise the log level, and what to include in a bug report
tags:
  - oss
  - team
  - enterprise
---

A mirrord session runs several processes: the CLI, the layer loaded into your application, the internal proxy on your machine, the agent in the cluster, and the operator if you use mirrord for Teams. Each one logs on its own. When something misbehaves, the logs from the component that failed are what we need to help you.

## CLI and layer

The CLI and the layer read their log level from the `MIRRORD_LOG` environment variable and write to stderr. The value follows the `RUST_LOG` convention:

```bash
MIRRORD_LOG=mirrord=trace mirrord exec -- <your command>
```

To write layer logs to files instead of mixing them into your application's stderr, set `MIRRORD_LAYER_LOG_PATH` to a directory. mirrord creates one file per process, named `mirrord-layer_<timestamp>_<process>_pid<pid>`:

```bash
MIRRORD_LOG=mirrord=trace MIRRORD_LAYER_LOG_PATH=/tmp/mirrord-logs mirrord exec -- <your command>
```

{% hint style="info" %}
`MIRRORD_LAYER_LOG_PATH` requires mirrord `3.188.0` or later. On Windows, `3.245.0` and later also write crash reports and memory dumps to this directory (or to `%TEMP%\mirrord` when it is not set).
{% endhint %}

## Internal proxy

The internal proxy runs on your machine and relays traffic between the layer and the agent. It always writes to a file. By default the file lives in your temporary directory and is named `mirrord-intproxy-<timestamp>-<random>.log`.

Raise the level and pick a fixed location in your mirrord config:

```json
{
  "internal_proxy": {
    "log_level": "mirrord=trace",
    "log_destination": "/tmp/mirrord-intproxy.log"
  }
}
```

`log_level` defaults to `mirrord=info,warn`. When you run with `mirrord container`, the external proxy logs the same way through `external_proxy.log_level` and `external_proxy.log_destination`, with files named `mirrord-extproxy-<timestamp>-<random>.log`.

## Agent

The agent runs in the cluster, in the target's namespace, as a pod labeled `app=mirrord` with a container named `mirrord-agent`. Set its level in your mirrord config:

```json
{
  "agent": {
    "log_level": "mirrord=trace",
    "ttl": 60
  }
}
```

`ttl` keeps the agent pod around for that many seconds after the session ends (default `1`), so you have time to read its logs:

```bash
kubectl logs -n <target namespace> -l app=mirrord -c mirrord-agent
```

If you run the agent as an ephemeral container (`agent.ephemeral: true`), it lives on the target pod itself, under a container named `mirrord-agent-<random suffix>`. Look the name up, then read its logs:

```bash
kubectl get pod -n <target namespace> <target pod> -o jsonpath='{.spec.ephemeralContainers[*].name}'
kubectl logs -n <target namespace> <target pod> -c mirrord-agent-<suffix>
```

## Operator

For mirrord for Teams, the operator logs cover session creation, licensing, and cluster-side features:

```bash
kubectl logs --namespace mirrord deployment/mirrord-operator
```

The level is `info` by default. Raise it with `operator.logLevel` in the Helm chart values, or with the `RUST_LOG` environment variable on the operator container:

```yaml
operator:
  logLevel: mirrord=debug,operator=debug
```

See [Monitoring](../managing-mirrord/monitoring.md) for JSON logging and shipping operator logs to your logging stack.

## IDEs

The VS Code extension and the JetBrains plugin start the same CLI, so everything above applies. Log level and file locations for the layer come from the run configuration's environment variables, and the proxy and agent settings come from the mirrord config file the session uses.

### VS Code

- Extension logs: open the **Output** panel and pick **mirrord** from the dropdown. Use **Developer: Set Log Level...** from the command palette to raise the level for that channel.
- Layer logs: add `MIRRORD_LOG` and `MIRRORD_LAYER_LOG_PATH` to the `env` block of your launch configuration.
- Extension version: the Extensions view lists it next to the mirrord entry.

### JetBrains IDEs

- Plugin logs: go to **Help → Show Log in Finder** (or **Show Log in Explorer** on Windows). The plugin writes to the IDE log under the `mirrord` category.
- Layer logs: add `MIRRORD_LOG` and `MIRRORD_LAYER_LOG_PATH` to the environment variables of your run configuration.
- Plugin version: **Settings → Plugins → Installed**, under mirrord.

## What to include in a bug report

When you [open an issue](https://github.com/metalbear-co/mirrord/issues/new?assignees=&labels=bug&projects=&template=bug_report.yml) or ask on [Slack](https://metalbear.com/slack), attach:

- The layer, internal proxy, and agent logs from a run that reproduces the problem, at `mirrord=trace`
- Your mirrord config, with secrets removed
- Output of `mirrord --version`, and of `mirrord operator status` if you use the operator
- The agent version. It matches the CLI version unless you set `agent.image`, in which case take the tag from that image
- The extension or plugin version if you run from an IDE
- Your operating system and version, and the local process you ran (language, runtime, version)
- The steps you took and what you expected to happen

Trace logs record what your process did, including command line arguments and request contents. Read through them and redact anything sensitive before you share them in a public issue or channel.
