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

#### Remove all default dump arguments

```json
{
  "copy": {
    "mode": "schema",
    "dump_args": []
  }
}
```

## Roles, Permissions, and Credentials

A branch pod is a fresh PostgreSQL instance, so mirrord recreates the source database's roles in it before restoring the schema. How much of them it recreates is controlled by the operator's Helm values, per cluster:

```yaml
operator:
  pgBranchConfig:
    dbPod:
      roles: "empty" # or "full"
```

`empty` (the default) creates each source role as a bare `NOLOGIN` shell - just enough for schema statements that reference roles (policies, user mappings) to restore. The copy strips table ownership and grants, and your app connects through mirrord's env overrides as the branch superuser.

`full` recreates roles with their real attributes (`LOGIN`, `CREATEDB`, connection limits) and `GRANT role TO role` memberships, and the copy keeps table ownership and grants. The branch then enforces the same permissions as the source: a table your role cannot read in the source stays unreadable in the branch. This is useful when your flows depend on role membership or you want branch testing to match production permission behavior. In `full` mode, mirrord's env overrides only redirect the connection address, so the app keeps using its own user and password. This applies to connections configured with individual `params`; a single URL-shaped variable is still replaced whole, with the branch superuser's credentials inside, so apps reading one `DATABASE_URL` connect as the superuser in every mode.

### The source user's password

The user declared in the branch's `connection` config can log into the branch with its real password, in both modes. This is useful when your application loads its credentials at runtime (from a secret manager, for example) instead of reading env vars - the credentials it already holds simply work against the branch. Only a salted password hash is written into the branch, never the plaintext.

In `empty` mode this login is a superuser on the throwaway copy; in `full` mode it has the role's real permissions.

### Which credentials does my app end up using?

Two things decide it: the `roles` setting, and where your app gets its database credentials when it runs. Apps that read them from env vars get mirrord's rewritten values; apps that fetch them at runtime from somewhere mirrord cannot rewrite - a secret manager like AWS Secrets Manager or Google Secret Manager, Vault, or a config service - keep using the source credentials they fetched.

| `roles` | Connection config | Where the app gets its credentials | App connects to the branch as |
| --- | --- | --- | --- |
| `empty` (default) | `params` or `url` | env vars | `postgres` superuser, mirrord's branch password |
| `empty` (default) | `params` or `url` | fetched at runtime (secret manager, Vault, ...) | the declared user, its real password (superuser on the branch) |
| `full` | `params` | env vars | the declared user, its real password, real permissions (mirrord leaves user/password vars untouched) |
| `full` | `params` | fetched at runtime (secret manager, Vault, ...) | the declared user, its real password, real permissions |
| `full` | `url` | env vars | `postgres` superuser (the URL var is replaced whole) |
| any | IAM auth | any | `postgres` superuser (IAM tokens are short-lived, so no source login is created) |

The "Connection config" column is how the branch's `connection` is declared in the mirrord config: individual `params` (host, user, password, ...) or a single `url` variable. In `empty` mode the two behave identically. In `full` mode only `params` lets the app keep its own user and password - a `url` variable is one opaque value, so mirrord can only replace it whole, with the superuser credentials inside.

The `postgres` superuser login with mirrord's branch password is available in every configuration. Roles other than the declared connection user never get a password (PostgreSQL does not expose them); to act as one of them, connect as the superuser and use `SET ROLE`.

### Limits

- PostgreSQL never exposes role passwords (they live in a superuser-only catalog), so roles other than the declared connection user restore without one and cannot log in. To act as another role, connect as the branch superuser and use `SET ROLE`.
- Roles are recreated when a branch is created. Changing the Helm value or rotating the source password affects new branches, not ones already running.
- Cloud control-plane roles (`rdsadmin`, `cloudsqladmin`, and similar) are skipped.

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

## IAM Authentication

PostgreSQL branches can authenticate to the source database with IAM instead of a password, on both **AWS RDS** and **GCP Cloud SQL**. See [IAM Authentication](iam-authentication.md) for setup and examples.
