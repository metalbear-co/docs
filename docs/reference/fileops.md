---
title: "File Operations"
description: "Reference to mirrord's file operations"
date: 2022-06-15T08:48:45+00:00
lastmod: 2022-06-15T08:48:45+00:00
draft: false
images: []
menu:
  docs:
    parent: "reference"
weight: 160
toc: true
tags: ["open source", "team", "enterprise"]
---

mirrord intercepts file syscalls in the local process and routes them to the target pod, so the local app sees the same `/etc/`, `/var/`, mounted ConfigMaps, mounted Secrets, and volume contents the deployed pod does.

For the how-to version, see [Using mirrord → File Operations](../using-mirrord/file-operations.md).

![mirrord - fileops](/reference/fileops/mirrord-fileops.png)

## The four `fs` modes

Set via `feature.fs.mode`:

| Mode | Reads | Writes | Notes |
|---|---|---|---|
| `local` | local | local | mirrord does nothing; no fs syscalls are intercepted. Equivalent to `feature.fs: false`. |
| `localwithoverrides` | local (except overrides) | local (except overrides) | Default is local; paths matching `read_only`, `read_write`, or the [pre-defined remote-by-default list](#default-overrides) go to the remote pod. |
| `read` *(default)* | remote (except overrides) | local | Reads come from the pod; writes stay local. Safest mode; you can't accidentally modify the cluster. |
| `write` | remote (except overrides) | remote | Reads and writes both go to the pod. Use with care; writes hit the real remote filesystem. |

Shorthand: `"fs": "read"`, `"fs": false` (= `local`), `"fs": true` (= `write`).

## Configuration

```json
{
  "feature": {
    "fs": {
      "mode": "read",
      "read_write":  [".+\\.json"],
      "read_only":   ["/etc/config/.+"],
      "local":       ["/tmp/.+", ".+\\.lock"],
      "not_found":   ["\\.config/gcloud"],
      "mapping": {
        "^/home/(?<user>[^/]+)/dev/config/(?<app>[^/]+)": "/mnt/configs/${user}-${app}"
      },
      "readonly_file_buffer": 128000
    }
  }
}
```

| Field | Behavior |
|---|---|
| `mode` | One of `local`, `localwithoverrides`, `read`, `write`. See above. |
| `read_write` | Regex patterns. Matching paths always go to the remote pod, read and write. |
| `read_only` | Regex patterns. Matching paths read from the remote pod; writes go local. |
| `local` | Regex patterns. Matching paths always stay local, regardless of mode. |
| `not_found` | Regex patterns. Matching paths return `ENOENT` to the application. Useful for hiding local files (`~/.aws/credentials`, `~/.config/gcloud`) that would confuse a cluster-context process. |
| `mapping` | Regex → replacement applied to the path **before** routing. Capture groups (`$1`, `${name}`) supported. Useful when local paths don't match remote paths (common on Windows). |
| `readonly_file_buffer` | Buffer size in bytes for read-only remote files. Default `128000` (128 kB). Set `0` to disable buffering. Hard limit 15 MB. |

All pattern lists are case-insensitive. If a path matches more than one list, the **first** match wins; order across lists is not guaranteed, so don't put the same path in two lists.

User patterns are checked first, then the [default overrides](#default-overrides), then the active `mode` as the fallback.

## Default overrides

mirrord ships built-in pattern lists that override the active mode. These exist so the local interpreter, package manager, and home-directory state aren't broken by remote-by-default routing.

| List | Effect | Source |
|---|---|---|
| Local-by-default | Always read locally, regardless of mode | [`unix`](https://github.com/metalbear-co/mirrord/blob/latest/mirrord/layer-lib/src/file/unix/read_local_by_default.rs) · [`windows`](https://github.com/metalbear-co/mirrord/blob/latest/mirrord/layer-lib/src/file/windows/read_local_by_default.rs) |
| Remote-by-default (when mode is `localwithoverrides`) | Read remotely even though mode says local | [`unix`](https://github.com/metalbear-co/mirrord/blob/latest/mirrord/layer-lib/src/file/unix/read_remote_by_default.rs) · [`windows`](https://github.com/metalbear-co/mirrord/blob/latest/mirrord/layer-lib/src/file/windows/read_remote_by_default.rs) |
| Not-found-by-default (under `$HOME`, all modes except `local`) | Always `ENOENT` | [`unix`](https://github.com/metalbear-co/mirrord/blob/latest/mirrord/layer-lib/src/file/unix/not_found_by_default.rs) · [`windows`](https://github.com/metalbear-co/mirrord/blob/latest/mirrord/layer-lib/src/file/windows/not_found_by_default.rs) |

To override a default (for example, to read `/etc/` remotely even though it's local-by-default), add the path to the appropriate user list: `"read_only": ["^/etc/.+"]`.

## inotify and file watches

mirrord does not currently intercept `inotify`/`fanotify` syscalls. Applications watching ConfigMap/Secret mounts for changes won't see remote modifications. Workaround: poll the file's mtime via `stat`.

## Related

- [`feature.fs` config reference](https://metalbear.com/mirrord/docs/config#feature.fs): full schema
- [Using mirrord → File Operations](../using-mirrord/file-operations.md): quick how-to
