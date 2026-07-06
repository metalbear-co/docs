---
title: PostgreSQL
description: Spin up an isolated PostgreSQL branch of your remote database with mirrord
tags:
  - beta
  - team
  - enterprise
---

This page covers DB branching for PostgreSQL. For the general concepts, the full list of config fields, and how a session behaves, see the [DB Branching overview](../db-branching.md).

{% hint style="info" %}
PostgreSQL branching requires operator `3.131.0`, mirrord CLI `3.175.0`, and operator Helm chart `1.40.2` with the `operator.pgBranching` value set to `true`.
{% endhint %}

## Basic Configuration

```json
{
  "feature": {
    "db_branches": [
      {
        "id": "users-pg-db",
        "type": "pg",
        "version": "16",
        "name": "users-database-name",
        "connection": {
          "url": "DATABASE_URL"
        },
        "copy": {
          "mode": "empty"
        }
      }
    ]
  }
}
```

The `connection` field describes how mirrord locates the source database connection details - a full connection URL or individual parameters (host, port, user, password, database). See [Connection Modes](connection.md) for all supported sources, including Kubernetes Secrets, Google Secret Manager, literal values, and composite environment variables.

## Copy Modes

The `copy` field controls what data gets cloned when creating a PostgreSQL branch.

| Mode | What gets cloned | Best for |
| --- | --- | --- |
| `"empty"` (default) | Nothing - an empty database with no schema or data | Workflows where your application initializes the schema or runs migrations as part of startup |
| `"schema"` | Only the table structures (schemas) from the source database, without any data | Testing schema changes or local development where structure is needed but data is not |
| `"all"` | Everything from the source database - both schema and data | A full clone of your environment data for debugging or reproducing production-like scenarios |

{% hint style="warning" %}
Use `"mode": "all"` with caution.
It’s only recommended for very small or empty databases.
Copying large datasets can significantly increase branch creation time and storage usage.
{% endhint %}

### Filtered Data Clone

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

## Custom Dump Arguments

The `dump_args` field lets you override the default arguments passed to `pg_dump`, the tool mirrord uses to copy the source database. It is available in all three copy modes (`empty`, `schema`, and `all`).

When `dump_args` is set, it **replaces** the defaults entirely. If you want to keep the defaults while adding your own flags, include them explicitly. The PostgreSQL defaults are `--no-owner` and `--no-acl`. An empty list (`[]`) removes all default dump arguments.

### Example - exclude a large table from the dump

```json
{
  "copy": {
    "mode": "schema",
    "dump_args": ["--no-owner", "--no-acl", "--exclude-table=audit_logs"]
  }
}
```

This keeps the PostgreSQL defaults and adds `--exclude-table=audit_logs` so `pg_dump` skips the `audit_logs` table.

```json
{
  "copy": {
    "mode": "schema",
    "dump_args": []
  }
}
```

## Connection Settings

`connection_settings` is a map of PostgreSQL settings that mirrord applies to every connection it opens to the source database while building the branch. Each entry is set before any schema dump or data copy runs.

Any PostgreSQL session variable works here (e.g. `role`, `search_path`, custom app settings). For example, if your source database uses [Row-Level Security (RLS)](https://www.postgresql.org/docs/current/ddl-rowsecurity.html) with a policy that reads `current_setting('...')`, mirrord's connection will fail without that setting.

```
ERROR: unrecognized configuration parameter "app.product_id"
```

Setting it through `connection_settings` makes the copy read past the policy:

```json
{
  "feature": {
    "db_branches": [
      {
        "type": "pg",
        "version": "16",
        "connection": { "url": "DATABASE_URL" },
        "connection_settings": {
          "app.product_id": "123456"
        },
        "copy": {
          "mode": "schema",
          "tables": {
            "kudos": { "filter": "product_id = 123456" }
          }
        }
      }
    ]
  }
}
```

These settings only apply while mirrord reads from the source, they are never written into the branch itself.

### Schema Migrations

PostgreSQL branches can run your schema migrations automatically while the branch is created, so it comes up with the schema your code expects. See [Schema Migrations](migrations.md) for setup and examples.

### IAM Authentication

PostgreSQL branches can authenticate to the source database with IAM instead of a password, on both **AWS RDS** and **GCP Cloud SQL**. See [IAM Authentication](iam-authentication.md) for setup and examples.
