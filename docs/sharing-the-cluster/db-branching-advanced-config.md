---
title: "DB Branching"
description: "Learn how to use mirrord’s advanced configuration options for database branching"
date: 2025-08-31T00:00:00+03:00
lastmod: 2025-08-31T00:00:00+03:00
draft: false
menu:
  docs:
    parent: "using-mirrord"
toc: true
tags: ["team", "enterprise"]
---


These settings give additional flexibility in how mirrord handles database branches.

```json
{
  "db_branches": [
    {
      "id": "users-mysql-db",            // Optional
      "type": "mysql",                    // Available options [mysql|pg|mssql|mongodb]
      "version": "8.0",
      "name": "users-database-name",      // Optional
      "ttl_secs": 60,                     // Optional
      "creation_timeout_secs": 20,        // Optional, Defaults to 60 if not specified
      "connection": {
        "url": "DB_CONNECTION_URL"
      },
      "copy": {
        "mode": "empty"                   // Optional, Defaults to "empty" if not specified
      }
    }
  ]
}
```

# Branch Creation Timeout

`creation_timeout_secs`
Defines how long (in seconds) mirrord waits for a database branch to become ready after creation.
If the branch isn’t ready within this time, mirrord session fails, exists and returns a timeout error.
Use this field to avoid hanging operations when branch creation takes too long or fails.
Default value is 60 seconds.

# Connection Modes

mirrord supports two ways of specifying how to connect to the source database: a full **connection URL** or **individual connection parameters**.

### Connection URL

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

### Individual Connection Parameters (Params)

Instead of a single connection URL, you can specify each connection parameter separately. This is useful when your application stores host, port, user, password, and database as individual environment variables.

Available parameters: `host`, `port`, `user`, `password`, `database`. Each field is individually optional - mirrord fills in database-specific defaults for any parameters not specified. Specify the parameters that your application uses to connect to the database.

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

Both `url` and individual `params` fields accept either a single value or an array. This is useful when an application uses several env vars for the same logical connection (for example, separate read/write URLs):

```json
{
  "connection": {
    "url": ["DATABASE_WRITE_URL", "DATABASE_READ_URL"]
  }
}
```

The **first entry** is used to locate the source database and clone it. During the session, **every entry** is rewritten to point at the branch pod. In the example above, `DATABASE_WRITE_URL` is read to find the source database, but both `DATABASE_WRITE_URL` and `DATABASE_READ_URL` are redirected to the branch, so the application reads and writes against the same branch instead of pointing reads at the original database.

Arrays also compose with `value_pattern` for composite setups. For example, when both `WRITE_SERVER` and `READ_SERVER` hold `host:port`:

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

# Copy Modes (MySQL, PostgreSQL & MSSQL)

The `copy` field controls what data gets cloned when creating a database branch. The following modes apply to MySQL, PostgreSQL, and MSSQL. For MongoDB copy modes, see [MongoDB Copy Modes](#mongodb-copy-modes) below.

1. ### Empty Database

`"mode": "empty"` Creates an empty database with no schema or data, this is the default value when the `copy` attribute is not specified.
Best for workflows where your application initializes the schema or runs migrations as part of startup.

2. ### Database Schemas

`"mode": "schema"` Copies only the table structures (schemas) from the source database, without any data.
Useful for testing schema changes or local development where structure is needed but data is not.

3. ### Complete Database

`"mode": "all"` Copies everything from the source database - both schema and data.
This is helpful when you want a full clone of your environment data for debugging or reproducing production-like scenarios.
{% hint style="warning" %}
Use this option with caution.
It’s only recommended for very small or empty databases.
Copying large datasets can significantly increase branch creation time and storage usage.
{% endhint %}

4. ### Filtered Data Clone

Developers can customize what gets copied per table. This allows copying only specific rows or subsets of data using SQL query filters.

```Json
{
  "copy": {
    "mode": "schema",                   // Or "empty" as explained below
    "tables": {
      "users": {
        "filter": "name = 'alice' OR name = 'bob'"
      },
      "orders": {
        "filter": "created_at > 1759948761"
      }
    }
  }
}
```

#### In this example

The schema for all tables is cloned.
The `users` table copy includes only rows for `alice` and `bob`.
The `orders` table copy includes only rows created after a certain timestamp.

Filtering can also be combined with `"mode": "empty"`, in which case only the specified tables (and their filtered data) are copied, while all others are excluded.

Note: Filtering is not compatible with `"mode": "all"`.
If both are specified, mirrord ignores the `tables` configuration.

# MongoDB Copy Modes

MongoDB supports two copy modes. The copy mode sets the **default behavior** for all collections.
When combined with [collection filters](#mongodb-collection-filters), the mode determines what happens to collections that are _not_ listed in the filter. Filtered collections always receive only the matching documents.

1. ### Empty Database

`"mode": "empty"` Creates an empty database. This is the default value when the `copy` attribute is not specified.
Best for workflows where your application initializes the collections or runs migrations as part of startup.

When combined with collection filters: only the filtered collections are created (with matching documents). All other collections are **not created**.

2. ### Complete Database

`"mode": "all"` Copies all collections and data from the source database.

When combined with collection filters: all collections are fully copied, but filtered collections receive **only matching documents** instead of the full data.

{% hint style="warning" %}
Use this option with caution.
It's only recommended for very small or empty databases.
Copying large datasets can significantly increase branch creation time and storage usage.
{% endhint %}

{% hint style="info" %}
MongoDB does not support a `"schema"` copy mode. In relational databases, `"schema"` copies table structures without data. MongoDB is schema-less and collections don't have a predefined structure separate from their documents, so `"empty"` and `"all"` are the available options.
{% endhint %}

### MongoDB Collection Filters

Developers can customize which collections are copied and apply MongoDB query filters per collection.

The copy mode controls the **baseline** (what happens to collections not mentioned in your filters):

| Mode | Unfiltered collections | Filtered collections |
|------|----------------------|---------------------|
| `"empty"` | Not created | Created with matching documents only |
| `"all"` | Fully copied (all documents) | Copied with matching documents only |

#### Example: `"mode": "all"` with filters

```json
{
  "copy": {
    "mode": "all",
    "collections": {
      "users": {
        "filter": "{\"name\": {\"$in\": [\"alice\", \"bob\"]}}"
      },
      "orders": {
        "filter": "{\"created_at\": {\"$gt\": 1759948761}}"
      }
    }
  }
}
```

All collections are copied, but the `users` collection includes only documents for alice and bob, and the `orders` collection includes only documents created after the given timestamp.

#### Example: `"mode": "empty"` with filters

```json
{
  "copy": {
    "mode": "empty",
    "collections": {
      "users": {
        "filter": "{\"name\": {\"$in\": [\"alice\", \"bob\"]}}"
      }
    }
  }
}
```

Only the `users` collection is created, containing documents for alice and bob. All other collections are not created. This is useful when you only need a subset of reference data and your application handles the rest through migrations.

# IAM Authentication

mirrord supports IAM authentication for **AWS RDS** and **GCP Cloud SQL**. Credentials are read from the **target pod's environment**, just like connection URLs.

{% hint style="info" %}
**Default environment variables**: If you do not specify custom credential sources, mirrord automatically looks for standard environment variables in the target pod (e.g., `AWS_REGION`, `GOOGLE_APPLICATION_CREDENTIALS`). You only need additional configuration if your pod uses non-standard variable names.
{% endhint %}

## AWS RDS IAM Authentication

### Minimal Configuration

Uses the standard AWS environment variables already present in the target pod.

```json
{
  "db_branches": [
    {
      "type": "pg",
      "version": "16",
      "connection": { "url": "DATABASE_URL" },
      "iam_auth": { "type": "aws_rds" }
    }
  ]
}
```

### Default AWS environment variables

mirrord reads the following variables from the **target pod**, not from your local shell.

| Field | Default fallback |
|-------|------------------|
| `region` | `AWS_REGION`, `AWS_DEFAULT_REGION` |
| `access_key_id` | `AWS_ACCESS_KEY_ID` |
| `secret_access_key` | `AWS_SECRET_ACCESS_KEY` |
| `session_token` | `AWS_SESSION_TOKEN` |

### Custom AWS environment variables

Use this only if your pod uses non-standard variable names.

```json
{
  "iam_auth": {
    "type": "aws_rds",
    "region": { "type": "env", "variable": "MY_CUSTOM_REGION" },
    "access_key_id": { "type": "env", "variable": "MY_ACCESS_KEY" },
    "secret_access_key": { "type": "env", "variable": "MY_SECRET_KEY" }
  }
}
```

## GCP Cloud SQL IAM Authentication

### Minimal Configuration

Uses the standard `GOOGLE_APPLICATION_CREDENTIALS` file path from target pod

```json
{
  "db_branches": [
    {
      "type": "pg",
      "version": "17",
      "connection": { "url": "DATABASE_URL" },
      "iam_auth": { "type": "gcp_cloud_sql" }
    }
  ]
}
```

### Default GCP environment variables

| Field | Default fallback |
|-------|------------------|
| `credentials_path` | `GOOGLE_APPLICATION_CREDENTIALS` |
| `project` | `GOOGLE_CLOUD_PROJECT`, `GCP_PROJECT`, `GCLOUD_PROJECT` |

### Custom GCP credentials

You can override the default behavior in one of the following ways.

**Option 1: Inline JSON credentials**
Load the service account JSON directly from an environment variable.

```json
{
  "iam_auth": {
    "type": "gcp_cloud_sql",
    "credentials_json": { "type": "env", "variable": "GOOGLE_APPLICATION_CREDENTIALS_JSON" }
  }
}
```

**Option 2: Custom credential file path**

Read credentials from a file path provided via an environment variable (for example, a mounted Kubernetes Secret).

```json
{
  "iam_auth": {
    "type": "gcp_cloud_sql",
    "credentials_path": { "type": "env", "variable": "MY_GCP_CREDENTIALS_PATH" }
  }
}
```

{% hint style="warning" %}
Use either `credentials_json` OR `credentials_path`, not both.
{% endhint %}

#### Required Database Settings

GCP Cloud SQL requires TLS.
Make sure your `DATABASE_URL` includes: `sslmode=require`
