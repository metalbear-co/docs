---
title: Environment Variables
date: 2022-06-15T08:48:45.000Z
lastmod: 2022-06-15T08:48:45.000Z
draft: false
images: []
menu:
  docs:
    parent: reference
weight: 150
toc: true
tags:
  - open source
  - team
  - enterprise
description: Reference to including remote environment variables
---

mirrord makes the target pod's environment available to the local process. Before the user process starts, the layer requests the env from the agent, which reads `/proc/<target-pid>/environ` inside the target container and returns the filtered set. The layer then applies any user-specified overrides and sets the result on the process.

For the quick how-to, see [Using mirrord → Environment Variables](../using-mirrord/environment-variables.md).

![mirrord - env vars](env/mirrord-env-vars.png)

## Configuration

```json
{
  "feature": {
    "env": {
      "include": "DATABASE_URL;PUBLIC_*",
      "exclude": "SECRET_*",
      "override": {
        "REGION": "us-east-1"
      },
      "env_file": "./.env.local",
      "mapping": {
        ".+_TIMEOUT": "10000"
      },
      "unset": ["AWS_PROFILE"],
      "load_from_process": false
    }
  }
}
```

| Field | Behavior |
|---|---|
| `include` | Allowlist. Supports `*` and `?` wildcards. Mutually exclusive with `exclude`. |
| `exclude` | Denylist applied on top of the [built-in always-excluded list](#always-excluded-variables). Mutually exclusive with `include`. |
| `override` | Key/value pairs set on the local process. Wins over remote values and `env_file`. |
| `env_file` | Dotenv file merged into the remote env. Values override the remote ones. |
| `mapping` | Regex → replacement applied to **values** (not keys). Capture groups allowed. |
| `unset` | Variables removed entirely. Case-insensitive. Required for Go (env can't be modified post-start). |
| `load_from_process` | Fetch env after the user process starts instead of before. WSL+IntelliJ workaround when the remote env is very large. Defaults to `false`. |

`include` and `exclude` are mutually exclusive; setting both causes the layer to panic at startup. When neither is set, the layer requests all variables.

## Always-excluded variables

The agent always strips these from the response, regardless of what `include` requests. This prevents the remote pod's toolchain paths from breaking the local interpreter/runtime.

```
BUNDLER_ORIG_BUNDLER_ORIG_MANPATH    GEM_HOME            PATH
BUNDLER_ORIG_BUNDLER_VERSION         GEM_PATH            PWD
BUNDLER_ORIG_BUNDLE_BIN_PATH         GOMODCACHE          PYTHONPATH
BUNDLER_ORIG_BUNDLE_GEMFILE          GOPATH              RUBYLIB
BUNDLER_ORIG_GEM_HOME                HOME                RUBYOPT
BUNDLER_ORIG_MANPATH                 HOMEPATH            RUST_LOG
BUNDLER_ORIG_PATH                    JAVA_EXE            _JAVA_OPTIONS
BUNDLER_ORIG_RB_USER_INSTALL         JAVA_HOME
BUNDLER_ORIG_RUBYLIB                 JAVA_TOOL_OPTIONS
BUNDLER_ORIG_RUBYOPT
BUNDLER_VERSION
BUNDLE_APP_CONFIG / _BIN_PATH /
  _FORCE_RUBY_PLATFORM / _GEMFILE /
  _GEM_PATH / _PATH / _WITHOUT
CATALINA_HOME                        DOTNET_EnableDiagnostics
CLASSPATH                            DOTNET_STARTUP_HOOKS
```

User-supplied `exclude` patterns are **added to** this list; they do not replace it.

The canonical list lives in [`mirrord-agent/src/env.rs`](https://github.com/metalbear-co/mirrord/blob/latest/mirrord/agent/src/env.rs).

## Equivalent environment variables

Each config field has a matching env var, useful from CLI/CI:

| Config | Env var |
|---|---|
| `feature.env.include` | `MIRRORD_OVERRIDE_ENV_VARS_INCLUDE` |
| `feature.env.exclude` | `MIRRORD_OVERRIDE_ENV_VARS_EXCLUDE` |
| `feature.env.env_file` | `MIRRORD_OVERRIDE_ENV_VARS_FILE` |
| `feature.env.load_from_process` | `MIRRORD_ENV_LOAD_FROM_PROCESS` |

## Related

- [`feature.env` config reference](https://metalbear.com/mirrord/docs/config#feature.env): full schema
- [Using mirrord → Environment Variables](../using-mirrord/environment-variables.md): quick how-to
