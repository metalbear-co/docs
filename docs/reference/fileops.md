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

mirrord intercepts file syscalls in the local process and routes them to the target pod, so the local app sees the same `/etc/`, `/var/`, mounted ConfigMaps, mounted Secrets, and volume contents the deployed pod does. This page covers what gets intercepted, the four fs modes, the override/pattern system, and the agent-side mechanism.

For the how-to version, see [Using mirrord → File Operations](../using-mirrord/file-operations.md).

![mirrord - fileops](/reference/fileops/mirrord-fileops.png)

## The four `fs` modes

Set via `feature.fs.mode`:

| Mode | Reads | Writes | Notes |
|---|---|---|---|
| `local` | local | local | mirrord does nothing — no fs syscalls are intercepted. Equivalent to `feature.fs: false`. |
| `localwithoverrides` | local (except overrides) | local (except overrides) | Default behavior is local; only paths matching `read_only`, `read_write`, or the [pre-defined remote-by-default list](#default-overrides) go to the remote pod. |
| `read` *(default)* | remote (except overrides) | local | Reads come from the pod; writes stay local. Safest mode — you can't accidentally modify the cluster. |
| `write` | remote (except overrides) | remote | Reads and writes both go to the pod. Use with care — writes hit the real remote filesystem. |

Shorthand: `"fs": "read"`, `"fs": false` (= `local`), `"fs": true` (= `write`).

## Configuration surface

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
| `not_found` | Regex patterns. Matching paths return `ENOENT` to the application — useful for hiding files that exist locally but would confuse a cluster-context process (e.g. `~/.aws/credentials`). |
| `mapping` | Regex → replacement applied to the path **before** routing. Capture groups are supported (`$1`, `${name}`). Useful when local paths don't match remote paths (common on Windows). |
| `readonly_file_buffer` | Buffer size in bytes for read-only remote files. Default `128000` (128 kB). Set `0` to disable buffering. Hard limit 15 MB. |

All pattern lists are case-insensitive. If a path matches more than one list, the **first** match wins — order across lists is not guaranteed, so don't put the same path in two lists.

## Resolution order

For each fs syscall the layer intercepts, mirrord resolves the routing in this order:

1. **`mapping`** — if the path matches a `mapping` entry, replace it before proceeding.
2. **User pattern lists** — `read_write`, `read_only`, `local`, `not_found`. First match wins.
3. **[Default overrides](#default-overrides)** — built-in lists that override the mode for specific paths regardless of user config.
4. **`mode`** — the fallback routing for paths nothing else matched.

## Default overrides

mirrord ships built-in pattern lists that override the active mode. These exist so the local interpreter, package manager, and home-directory state aren't broken by remote-by-default routing.

| List | Effect | Source |
|---|---|---|
| Local-by-default | Always read locally, regardless of mode | [`unix`](https://github.com/metalbear-co/mirrord/blob/latest/mirrord/layer-lib/src/file/unix/read_local_by_default.rs) · [`windows`](https://github.com/metalbear-co/mirrord/blob/latest/mirrord/layer-lib/src/file/windows/read_local_by_default.rs) |
| Remote-by-default (when mode is `localwithoverrides`) | Read remotely even though mode says local | [`unix`](https://github.com/metalbear-co/mirrord/blob/latest/mirrord/layer-lib/src/file/unix/read_remote_by_default.rs) · [`windows`](https://github.com/metalbear-co/mirrord/blob/latest/mirrord/layer-lib/src/file/windows/read_remote_by_default.rs) |
| Not-found-by-default (under `$HOME`, all modes except `local`) | Always `ENOENT` | [`unix`](https://github.com/metalbear-co/mirrord/blob/latest/mirrord/layer-lib/src/file/unix/not_found_by_default.rs) · [`windows`](https://github.com/metalbear-co/mirrord/blob/latest/mirrord/layer-lib/src/file/windows/not_found_by_default.rs) |

To override a default — for example, to read `/etc/` remotely even though it's local-by-default — add it to the appropriate user list: `"read_only": ["^/etc/.+"]`.

## Intercepted syscalls

mirrord hooks the following libc functions on Linux/macOS. The layer intercepts each call, decides local vs. remote based on the [resolution order](#resolution-order), and either bypasses to the original libc function or sends a request to the agent.

| Category | Hooked |
|---|---|
| Open | `open`, `open64`, `openat`, `opendir`, `dirfd` |
| Read | `read`, `readv`, `pread`, `preadv`, `readlink`, `readdir`, `readdir64`, `readdir_r`, `readdir64_r` |
| Write | `write`, `pwrite` |
| Position | `lseek` |
| Metadata | `access`, `stat`, `lstat`, `statx`, `statfs`, `statvfs`, `fstat`, `fstatat`, `fstatfs`, `fchmod`, `fchown`, `fsync` |
| Directory | `mkdir`, `rmdir` |
| Path | `rename`, `unlink`, `unlinkat` |

On macOS the layer also hooks the `_NOCANCEL` and `$INODE64` variants where applicable. The full, current list lives in [`mirrord/layer/src/file/hooks.rs`](https://github.com/metalbear-co/mirrord/blob/latest/mirrord/layer/src/file/hooks.rs).

Windows has its own equivalent hook set in `mirrord-layer-win`.

### Relative path behavior

When a hooked syscall receives a relative path with no anchoring directory fd, the call is **bypassed to libc** (i.e. resolved locally). This avoids ambiguity, since the layer can't know the remote pod's working directory.

`openat` with a valid `dirfd` returned by a previous remote `open` follows the remote directory; with `AT_FDCWD` it behaves like `open`.

### File descriptor disambiguation

`read`, `write`, `lseek`, `stat`, etc. take an fd. The layer maintains a map of fds that belong to remote-opened files. If the fd is a remote one, the call is sent to the agent; otherwise it's bypassed to libc. This means closing and reopening a file with the same path can flip its routing if config or mode changed in between.

## How the agent reads files

```
┌──────────────────────────┐
│ Local process            │
│ ┌──────────────────────┐ │
│ │   mirrord-layer      │ │  Hooks open/read/write/...
│ └──────────┬───────────┘ │  Sends FileRequest to intproxy.
└────────────┼─────────────┘
             │ FileRequest::Open / Read / Write / ...
┌────────────▼─────────────┐
│ mirrord-intproxy         │
└────────────┬─────────────┘
             │
┌────────────▼─────────────┐
│ mirrord-agent            │  Resolves the target container's
│   (target netns + mntns) │  rootfs via `/proc/<pid>/root`
│                          │  and performs the operation
│                          │  against that path.
└──────────────────────────┘
```

The agent uses the container runtime's API (containerd, docker, CRI-O) to get the PID of the target container. It then accesses the container's filesystem through `/proc/<container-pid>/root`, which gives it the view of the mount namespace the container sees — including ConfigMap/Secret mounts and persistent volumes.

The agent does not exec inside the container; it reads/writes from the agent pod with the kernel doing the namespace translation. This is why the agent needs `CAP_SYS_ADMIN` (joining mount/PID namespaces).

### inotify and file watches

mirrord does not currently intercept `inotify`/`fanotify` syscalls. Applications watching ConfigMap/Secret mounts for changes won't see remote modifications. Workaround: poll the file's mtime via `stat`.

## Related

- [`feature.fs` config reference](https://metalbear.com/mirrord/docs/config#feature.fs) — full schema
- [Architecture](architecture.md) — layer / intproxy / agent
- [Using mirrord → File Operations](../using-mirrord/file-operations.md) — quick how-to
