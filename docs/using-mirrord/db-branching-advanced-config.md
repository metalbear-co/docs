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
      "type": "mysql",                    // Available options [mysql|pg|mongodb]
      "version": "8.0",
      "name": "users-database-name",      // Optional
      "ttl_secs": 60,                     // Optional
      "creation_timeout_secs": 20,        // Optional, Defaults to 60 if not specified
      "connection": {
        "url": {
          "type": "env",
          "variable": "DB_CONNECTION_URL" // Required
        }
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
    "type": "env",
    "url": "DATABASE_URL"
  }
}
```

The `type` field controls where the environment variable is read from (applies to both URL and params modes):

- `"env"`: Direct `env` entry in the target pod spec.
- `"env_from"`: From the target pod's `envFrom` field (`secretRef` or `configMapRef`). mirrord replicates the `envFrom` sources onto the init container so it can resolve the variable at runtime.

### Individual Connection Parameters (Params)

Instead of a single connection URL, you can specify each connection parameter separately. This is useful when your application stores host, port, user, password, and database as individual environment variables.

Available parameters: `host`, `port`, `user`, `password`, `database`. Each field is individually optional - mirrord fills in database-specific defaults for any parameters not specified. Specify the parameters that your application uses to connect to the database.

```json
{
  "connection": {
    "type": "env",
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

Instead of a plain string (env var name), use an object with `secret` and `key`:

```json
{
  "connection": {
    "type": "env",
    "params": {
      "host": "DB_HOST",
      "password": { "secret": "rds-credentials", "key": "password" },
      "database": "DB_NAME"
    }
  }
}
```

In this example, `host` and `database` are read from environment variables, while `password` is read directly from the `rds-credentials` Kubernetes Secret (key `password`).

{% hint style="info" %}
The `secret` source is only supported for individual connection parameters, not for the full connection URL.
{% endhint %}

# Copy Modes (MySQL & PostgreSQL)

The `copy` field controls what data gets cloned when creating a database branch. The following modes apply to MySQL and PostgreSQL. For MongoDB copy modes, see [MongoDB Copy Modes](#mongodb-copy-modes) below.

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

MongoDB supports two copy modes:

1. ### Empty Database

`"mode": "empty"` Creates an empty database. This is the default value when the `copy` attribute is not specified.
Best for workflows where your application initializes the collections or runs migrations as part of startup.

2. ### Complete Database

`"mode": "all"` Copies all collections and data from the source database.

{% hint style="warning" %}
Use this option with caution.
It's only recommended for very small or empty databases.
Copying large datasets can significantly increase branch creation time and storage usage.
{% endhint %}

{% hint style="info" %}
MongoDB does not support a `"schema"` copy mode. MongoDB is schema-less, so `"empty"` and `"all"` are the available options.
{% endhint %}

### MongoDB Collection Filters

Developers can customize which collections are copied and apply MongoDB query filters per collection:

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

#### In this example

All collections are copied, but the `users` collection includes only documents for alice and bob, and the `orders` collection includes only documents created after the given timestamp.

Collection filters can also be combined with `"mode": "empty"`, in which case only the specified collections (and their filtered data) are copied.

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
      "connection": { "url": { "type": "env", "variable": "DATABASE_URL" } },
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
      "connection": { "url": { "type": "env", "variable": "DATABASE_URL" } },
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
