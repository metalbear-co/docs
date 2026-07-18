---
title: MariaDB
description: Spin up an isolated MariaDB branch of your remote database with mirrord
tags:
  - beta
  - team
  - enterprise
---

This page covers DB branching for MariaDB. For the general concepts, the full list of config fields, and how a session behaves, see the [DB Branching overview](../db-branching.md).

{% hint style="info" %}
MariaDB branching requires an operator, mirrord CLI, and operator Helm chart version that ship MariaDB branching, with the `operator.mariadbBranching` value set to `true`.
{% endhint %}

MariaDB is a first-class engine, not a MySQL alias. Branches use MariaDB-native tooling (`mariadb-dump` / `mariadb-admin`) and a MariaDB branch image, so MariaDB-only objects such as sequences and system-versioned (temporal) tables are copied correctly - which a MySQL dump and image mishandle.

## Basic Configuration

```json
{
  "feature": {
    "db_branches": [
      {
        "id": "users-mariadb-db",
        "type": "mariadb",
        "version": "12",
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

MariaDB speaks the MySQL wire protocol, so your application connects to the branch with the same driver it already uses. When mirrord builds the branch connection URL from individual parameters, it uses the `mariadb` scheme.

## Copy Modes

The `copy` field controls what data gets cloned when creating a MariaDB branch.

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

The `dump_args` field lets you customize the arguments passed to `mariadb-dump`, the tool mirrord uses to copy the source database. It is available in all three copy modes (`empty`, `schema`, and `all`).

By default, mirrord passes no arguments to `mariadb-dump`, which then runs with its own built-in defaults (the `--opt` option group). Arguments listed in `dump_args` are passed to the tool as-is. An empty list (`[]`) removes `mariadb-dump`'s built-in defaults.

### Example - single transaction and no table locking

```json
{
  "copy": {
    "mode": "all",
    "dump_args": ["--single-transaction", "--no-tablespaces", "--skip-lock-tables"]
  }
}
```

In this example, `mariadb-dump` runs with `--single-transaction`, `--no-tablespaces`, and `--skip-lock-tables`.

## IAM Authentication

MariaDB branches can authenticate to the source database with IAM instead of a password, on both **AWS RDS** and **GCP Cloud SQL**. See [IAM Authentication](iam-authentication.md) for setup and examples.
