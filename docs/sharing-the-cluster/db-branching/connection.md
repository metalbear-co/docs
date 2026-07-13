---
title: Connection Modes
description: How mirrord locates your source database connection details for DB branching
tags:
  - team
  - enterprise
---

This page covers the `connection` field of a DB branch config - how mirrord locates the source database connection details. It applies to all database engines. For general concepts and the full list of config fields, see the [DB Branching overview](../db-branching.md).

mirrord supports two ways of specifying how to connect to the source database: a full **connection URL** or **individual connection parameters**.

## Connection URL

Provide a single environment variable that contains the full database connection string:

```json
{
  "connection": {
    "url": "DATABASE_URL"
  }
}
```

The optional `type` field controls where the environment variable is read from (applies to both URL and params modes). It defaults to `"env"` when omitted.

- `"env"` (default): Direct `env` entry in the target pod spec.
- `"env_from"`: From the target pod's `envFrom` field (`secretRef` or `configMapRef`). mirrord replicates the `envFrom` sources onto the init container so it can resolve the variable at runtime.

## Individual Connection Parameters (Params)

Instead of a single connection URL, you can specify each connection parameter separately. This is useful when your application stores host, port, user, password, and database as individual environment variables.

Available parameters: `host`, `port`, `user`, `password`, `database`. Each field is individually optional - mirrord fills in database-specific defaults for any parameters not specified. Non-existent envinroment variables are also filled with defaults. Specify the parameters that your application uses to connect to the database.

```json
{
  "connection": {
    "params": {
      "host": "DB_HOST",
      "port": "DB_PORT",
      "user": "DB_USER",
      "password": "DB_PASSWORD",
      "database": "DB_NAME"
    }
  }
}
```

Defaults
| Database | Port | User |
| --- | --- | --- |
| PostgreSQL | `5432` | `postgres` |
| MySQL | `3306` | `root` |
| MSSQL | `1433` | `sa` |
| MongoDB | `27017` | `root` |
| Redis | `6379` | `default` |
| ClickHouse | `9000` | `default` |

Default for `connection.params.host` is `localhost` for all databases.

#### Custom Parameters

Besides the fixed slots, `params` accepts custom keys for engines that need them: [Google Spanner](spanner.md) declares its `project`/`instance`/`database_id` locators this way, and [generic branches](generic.md) accept **any** key (for example `token`, `org`, `vhost`) - each is injected into the branch container as a `MIRRORD_PARAM_<NAME>` env var. Custom parameters support the same value sources as the fixed slots, and a literal `value` in one is extracted into the credential Secret exactly like the fixed slots.

### Secret Source

Any individual connection parameter can be sourced directly from a Kubernetes Secret instead of an environment variable. This is useful when credentials are stored in Kubernetes Secrets, such as AWS Secrets Manager synced secrets or volume-mounted secret files.

Instead of a plain string (env var name), use an object with `secret`, `key`, and `env_var_name`. The operator reads the Secret and injects the value under `env_var_name` for your local process, so your code can read it with `os.Getenv(...)` (or equivalent) regardless of whether the target pod exposes it:

```json
{
  "connection": {
    "params": {
      "host": "DB_HOST",
      "password": {
        "secret": "rds-credentials",
        "key": "password",
        "env_var_name": "DB_PASSWORD"
      },
      "database": "DB_NAME"
    }
  }
}
```

In this example, `host` and `database` are read from environment variables, while `password` is read directly from the `rds-credentials` Kubernetes Secret (key `password`).

{% hint style="info" %}
The `secret` source is only supported for individual connection parameters, not for the full connection URL.
{% endhint %}

### Google Secret Manager Source

Any connection value can be read from [Google Secret Manager](https://cloud.google.com/secret-manager) instead of an environment variable or a Kubernetes Secret. This is useful when your application already loads its database credentials from Secret Manager at runtime and never puts them in the pod spec.

The branch init container fetches the value when it copies the data, using the target pod's service account through [GKE Workload Identity](https://cloud.google.com/kubernetes-engine/docs/concepts/workload-identity) - the same way [GCP Cloud SQL IAM](iam-authentication.md#gcp-cloud-sql-iam-authentication) works. mirrord and the operator never read the secret themselves.

Unlike the `secret` source, this works for both the full connection URL and individual parameters.

For the full URL, use `type: gcp_secret_manager` with a `secret_ref` (the Secret Manager resource name):

```json
{
  "connection": {
    "url": {
      "type": "gcp_secret_manager",
      "secret_ref": "projects/my-project/secrets/db-url/versions/latest",
      "env_var_name": "DATABASE_URL"
    }
  }
}
```

For an individual parameter, use a `gcp_secret_manager` field with the resource name:

```json
{
  "connection": {
    "params": {
      "host": "DB_HOST",
      "password": {
        "gcp_secret_manager": "projects/my-project/secrets/db-password/versions/latest",
        "env_var_name": "DB_PASSWORD"
      },
      "database": "DB_NAME"
    }
  }
}
```

`env_var_name` is optional. When set, the operator injects the branch connection under that name for your local process, just like the `secret` and literal-value sources, so your code can read it with `os.Getenv(...)` (or equivalent). Without it, the value is only used to build the branch and your app keeps reading its own source.

{% hint style="info" %}
**Setup**: the branch pod inherits the target pod's service account, so that account's Google identity must have `roles/secretmanager.secretAccessor` on the secret. No operator-level permissions are needed.
{% endhint %}

### Literal Value

You can provide a connection parameter as a literal value directly in the config. This is useful when the credential is injected at runtime by an external system and does not appear in the pod spec where mirrord can read it.

Use a field with `value`:

```json
{
  "connection": {
    "params": {
      "host": "DB_HOST",
      "port": "DB_PORT",
      "user": "DB_USER",
      "password": { "env_var_name": "DB_PASSWORD", "value": "my-db-password" },
      "database": "DB_NAME"
    }
  }
}
```

Works for any connection parameter (`host`, `port`, `user`, `password`, `database`). The CLI stores the literal value in a Kubernetes Secret. The operator uses it to connect the branch DB to the source and also injects it under the name you set in `env_var_name` for your local process, so your code can read it with `os.Getenv(...)` (or equivalent) even when the target pod doesn't expose it.

### Composite Environment Variables

Some applications pack multiple connection details into a single environment variable. For example, a target pod might expose:

```yaml
- name: DB_SERVER
  value: "prod-db.internal:5432"
```

Here `host` and `port` live inside the same `DB_SERVER` value. Use `value_pattern` to specify which part of the value belongs to which parameter. The pattern works on both `params` fields and `url` sources.

```json
{
  "connection": {
    "params": {
      "host": {
        "env_var_name": "DB_SERVER",
        "value_pattern": "^(?P<host>[^:]+):\\d+$"
      },
      "port": {
        "env_var_name": "DB_SERVER",
        "value_pattern": "^[^:]+:(?P<port>\\d+)$"
      },
      "user": "DB_USER",
      "password": "DB_PASSWORD",
      "database": "DB_NAME"
    }
  }
}
```

During a session, only the matched part of the value is swapped out: just the host, or just the port. The rest of the string always stays intact, so your app still sees `DB_SERVER` in the `host:port` format it expects.

### Choosing the capture group
The capture group name follows the parameter name - `(?P<host>...)` for the `host` variable, `(?P<port>...)` for the `port` variable.

For single-parameter patterns you can also use `(?P<value>...)` as a generic name, or a plain unnamed group like ([^:]+). If the regex contains more than one unnamed group, the first one is used.

> The regex must contain at least one capture group, otherwise the configuration is rejected.

### Multiple Sources for the Same Parameter

Both `url` and individual `params` fields accept either a single value or an array. This is useful when an application uses several env vars for the same logical connection. For example, separate read/write URLs.

> **Rule:** the **first entry** in the array is used to locate the source database and clone it. During the session, **every entry** is rewritten to point at the branch pod.
> 

```json
{
  "connection": {
    "url": ["DATABASE_WRITE_URL", "DATABASE_READ_URL"]
  }
}
```

The **first entry** is used to locate the source database and clone it. During the session, **every entry** is rewritten to point at the branch pod. In the example above, `DATABASE_WRITE_URL` is read to find the source database, but both `DATABASE_WRITE_URL` and `DATABASE_READ_URL` are redirected to the branch, so the application reads and writes against the same branch instead of pointing reads at the original database.

### Combining arrays with `value_pattern`
If the same connection parameter appears in multiple env vars and each var encodes a composite value, use an array of `value_pattern` objects. 

As with plain arrays, the first entry is used as the source. Even if `WRITE_SERVER` and `READ_SERVER` point to different databases, only `WRITE_SERVER` is cloned. During the session, all entries are rewritten to point at the branch.

For example, when both `WRITE_SERVER` and `READ_SERVER ` hold a `host:port` pair:

```json
{
  "connection": {
    "params": {
      "host": [
        { "env_var_name": "WRITE_SERVER", "value_pattern": "^([^:]+):" },
        { "env_var_name": "READ_SERVER", "value_pattern": "^([^:]+):" }
      ],
      "port": [
        { "env_var_name": "WRITE_SERVER", "value_pattern": ":(\\d+)$" },
        { "env_var_name": "READ_SERVER", "value_pattern": ":(\\d+)$" }
      ],
      "user": ["DB_USER", "DB_READ_USER"],
      "password": ["DB_PASSWORD", "DB_READ_PASSWORD"],
      "database": "DB_NAME"
    }
  }
}
```

The same rule applies: `WRITE_SERVER` (the first entry) is used to extract the source connection. During the session, all entries - `WRITE_SERVER`, `READ_SERVER`, both user vars, and both password vars - are rewritten to point at the branch.
