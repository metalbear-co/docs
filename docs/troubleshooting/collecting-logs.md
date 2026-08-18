---
title: Collecting Logs
date: 2026-07-30T00:00:00.000Z
description: How to capture logs from every part of mirrord (layer, internal proxy, and agent) when debugging or reporting an issue
---

mirrord runs in a few places at once: the layer inside your local process, an internal proxy on your machine, and the agent inside the cluster. Each part logs separately, and the [bug report template](https://github.com/metalbear-co/mirrord/issues/new?assignees=&labels=bug&projects=&template=bug_report.yml) asks for the relevant ones. Here is how to capture each.

## Layer logs

The layer is loaded into your application's process. Enable its logs by setting the `MIRRORD_LOG` environment variable, then run mirrord as usual:

```bash
MIRRORD_LOG=mirrord=trace mirrord exec -- <your command>
```

The layer prints its logs to the application's STDERR, alongside your application's own output. When running through an IDE plugin, set `MIRRORD_LOG` in the run configuration's environment variables; the logs appear in the IDE's run console.

## Internal proxy logs

The internal proxy runs on your machine and relays traffic between the layer and the agent. Its logs go to a file in your temporary directory by default (a path like `/tmp/mirrord-intproxy-<timestamp>-<random>.log`). Raise the level with [`internal_proxy.log_level`](https://metalbear.com/mirrord/docs/config/options#internal_proxy-log_level) (defaults to `mirrord=info,warn`), and pick a fixed location with [`internal_proxy.log_destination`](https://metalbear.com/mirrord/docs/config/options#internal_proxy-log_destination):

```json
{
  "internal_proxy": {
    "log_level": "mirrord=trace",
    "log_destination": "/tmp/intproxy.log"
  }
}
```

## Agent logs

The agent runs in the cluster, as a `mirrord-agent-*` pod in the target's namespace (or as an ephemeral container inside the target pod). Raise its log level with [`agent.log_level`](https://metalbear.com/mirrord/docs/config/options#agent-log_level) and read the logs with kubectl:

```bash
kubectl logs -n <namespace> -l app=mirrord
```

Agent pods are cleaned up shortly after the session ends. If the pod disappears before you can read the logs, keep it around longer with [`agent.ttl`](https://metalbear.com/mirrord/docs/config/options#agent-ttl), which controls how many seconds the pod persists after the agent exits:

```json
{
  "agent": {
    "log_level": "mirrord=trace",
    "ttl": 300
  }
}
```

## Operator logs

If you use mirrord for Teams, the Operator produces its own logs in the cluster. See [Monitoring](../managing-mirrord/monitoring.md) for how to configure and collect them.

## What to attach to a report

For most issues, layer logs and internal proxy logs from a failed run are enough. For agent startup and connection problems, add the agent pod's logs and the output of `kubectl describe` on the agent pod. Strip anything sensitive before sharing; log lines can include hostnames, paths, and header names from your environment.
