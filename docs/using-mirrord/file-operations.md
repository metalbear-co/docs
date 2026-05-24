---
title: File Operations
description: Control which files your local process reads and writes remotely
draft: false
toc: true
tags: ["open source", "team", "enterprise"]
---

By default, mirrord redirects most file reads from your local process to the remote pod. When your code opens `/etc/config/app.yaml`, it reads the remote pod's copy. Writes stay local. Your local process sees the same configuration files, certificates, and mounted volume data the deployed application does.

Some paths (language runtimes, package managers, home-directory state, temp files) are always read locally. See the [full default list](https://github.com/metalbear-co/mirrord/blob/main/mirrord/layer-lib/src/file/unix/read_local_by_default.rs) or the [reference](../reference/fileops.md#default-overrides).

## Choosing a mode

| Mode | Reads | Writes | Use when |
|---|---|---|---|
| `read` *(default)* | remote | local | You want remote config but don't want to risk writing to remote files |
| `local` | local | local | You don't need any remote files |
| `localwithoverrides` | local (except overrides) | local (except overrides) | You need just a few specific remote files |
| `write` | remote | remote | Your app needs to write to a remote volume |

```json
{ "feature": { "fs": { "mode": "read" } } }
```

## Common patterns

**Reading specific files remotely (rest stay local)**

```json
{
  "feature": {
    "fs": {
      "mode": "localwithoverrides",
      "read_only": ["/etc/config/.*", "/var/secrets/.*"]
    }
  }
}
```

**Writing to a specific remote path**

```json
{
  "feature": {
    "fs": {
      "read_write": ["/mnt/shared/uploads/.*"]
    }
  }
}
```

Be careful — this modifies the actual remote pod's filesystem.

**Keeping specific paths local even in `read` mode**

```json
{
  "feature": {
    "fs": {
      "local": ["/tmp/.*", ".*\\.lock"]
    }
  }
}
```

**Hiding files that confuse a cluster-context process**

If your local home dir has files (`.aws/credentials`, `.gcloud/`) that hijack auth when the process expects cluster auth:

```json
{
  "feature": {
    "fs": {
      "not_found": ["\\.aws/credentials", "\\.config/gcloud"]
    }
  }
}
```

## Common scenarios

- **App reads config from a mounted ConfigMap** — default `read` mode handles this; no config needed.
- **App writes logs locally** — default already writes locally; no change needed.
- **App watches files with `inotify` for ConfigMap updates** — won't work; mirrord doesn't intercept inotify. Poll mtime via `stat` instead.

For the full pattern resolution order, the complete list of intercepted syscalls, the default-override lists, path mapping (useful on Windows), and the readonly buffer setting, see the [file operations reference](../reference/fileops.md).
