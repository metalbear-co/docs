---
title: File system
date: 2024-12-19T00:00:00.000Z
lastmod: 2024-12-19T00:00:00.000Z
draft: false
menu:
  docs:
    parent: core-features
weight: 122
toc: true
tags:
  - open source
  - team
  - enterprise
description: Read files from your target pod including ConfigMaps, certificates, and service account tokens
---

# File system

mirrord can intercept file operations and redirect them to the target pod's filesystem. This lets your local process read files that only exist in the cluster—TLS certificates, mounted ConfigMaps, service account tokens, and other runtime files.

## How it works

When your app opens a file, mirrord intercepts the system call. Depending on your configuration, it either:
- Opens the file locally (from your machine)
- Opens the file remotely (from the target pod)
- Opens the file remotely for reading and locally for writing

This happens transparently—your code doesn't need to change.

## File system modes

mirrord supports four modes that control how file operations are handled:

### `read` (default)

Remote read access. File reads go to the target pod; writes stay local.

```json
{
  "feature": {
    "fs": "read"
  }
}
```

Use this when your app needs to read config files or certificates from the pod but shouldn't write to the remote filesystem.

### `local`

All file operations stay local. mirrord doesn't intercept filesystem calls.

```json
{
  "feature": {
    "fs": "local"
  }
}
```

Use this when you don't need any remote file access.

### `localwithoverrides`

Mostly local, with specific paths read from the remote. You specify which paths should be remote.

```json
{
  "feature": {
    "fs": {
      "mode": "localwithoverrides",
      "read_only": ["/etc/config/.*", "/var/run/secrets/.*"]
    }
  }
}
```

Use this when you only need a few specific files from the remote pod.

### `write`

Full remote read/write access. Both reads and writes go to the target pod.

```json
{
  "feature": {
    "fs": "write"
  }
}
```

Use this with caution—writes affect the actual files on the remote pod.

## Overriding specific paths

You can override the mode for specific paths using regex patterns:

- **`local`**: always use local filesystem for these paths
- **`read_only`**: read from remote (useful with `localwithoverrides` or `write` mode)
- **`read_write`**: read and write to remote (useful with `read` mode to allow writes for specific paths)
- **`not_found`**: treat these paths as if they don't exist

Example—read from remote by default, but keep source files local:

```json
{
  "feature": {
    "fs": {
      "mode": "read",
      "local": [
        "/Users/.*",
        "/home/.*",
        ".*\\.py",
        ".*node_modules.*"
      ]
    }
  }
}
```

## Default behavior

By default, mirrord reads most files locally but reads certain paths from the remote. This includes files that typically need to come from the cluster environment, while keeping your source code and local config files local.

## Common patterns

### Access mounted ConfigMaps

Your app reads a config file from a volume mount:

```json
{
  "feature": {
    "fs": {
      "mode": "localwithoverrides",
      "read_only": ["/etc/app-config/.*"]
    }
  }
}
```

### Access TLS certificates

Your app needs certificates from the pod:

```json
{
  "feature": {
    "fs": {
      "mode": "localwithoverrides",
      "read_only": [
        "/etc/ssl/certs/.*",
        "/etc/pki/.*",
        "/app/certs/.*"
      ]
    }
  }
}
```

## Security considerations

- **Prefer read-only access**: use `read` mode unless you specifically need to write to the remote filesystem.
- **Be careful with write mode**: writes go to the actual pod and can affect its behavior or state.
- **Don't modify config that triggers side effects**: writing to some config files might trigger behavior changes in the running pod.

## Reference

- [File Operations](../reference/fileops.md) — detailed reference on file system behavior
- [Configuration Options](https://metalbear.com/mirrord/docs/config/options) — full list of fs configuration options
