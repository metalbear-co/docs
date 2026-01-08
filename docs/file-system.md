---
title: File System
date: 2024-12-19T00:00:00.000Z
lastmod: 2024-12-19T00:00:00.000Z
draft: false
weight: 140
toc: true
tags:
  - open source
  - team
  - enterprise
description: Configure file operations to read and write from local or remote filesystems
---

# File system

mirrord intercepts file operations and lets you control whether each read or write goes to your local machine or the target pod. This gives you flexibility to mix local and remote file access—read certificates from the cluster while writing logs locally, or keep source files local while accessing remote ConfigMaps.

## How it works

When your app opens a file, mirrord intercepts the system call. Depending on your configuration, it either:
- Opens the file locally (from your machine)
- Opens the file remotely (from the target pod)

You can configure this globally or per-path, giving you fine-grained control over exactly which files come from where. This happens transparently, your code doesn't need to change.

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

## Security considerations

- **Prefer read-only access**: use `read` mode unless you specifically need to write to the remote filesystem.
- **Be careful with write mode**: writes go to the actual pod and can affect its behavior or state.
- **Don't modify config that triggers side effects**: writing to some config files might trigger behavior changes in the running pod.

## Reference

- Check out [File Operations](../reference/fileops.md) to see how file operations work under the covers.
- [Configuration Options](https://metalbear.com/mirrord/docs/config/options) provides a full list of file system options.
