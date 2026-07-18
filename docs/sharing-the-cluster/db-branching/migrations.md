---
title: Schema Migrations
description: Automatically run schema migrations against a mirrord DB branch
tags:
  - alpha
  - team
  - enterprise
---

A DB branch includes the source database's schema as of when it was cloned - or starts with no schema at all, depending on `copy.mode`. Either way, it won't include migrations that exist only in your working tree and haven't been applied to the source database yet.

The `migrations` field closes that gap: mirrord runs your schema migrations against the branch automatically when it's created, so the branch comes up with the schema your code expects.

This page covers the `migrations` field of a DB branch config for MySQL, PostgreSQL, MSSQL, and CockroachDB. For general concepts and the full list of config fields, see the [DB Branching overview](../db-branching.md).

{% hint style="info" %}
Schema migrations require mirrord operator `3.182.0`, mirrord CLI `3.230.0`, and operator Helm chart `3.182.0`.
{% endhint %}

```json
{
  "feature": {
    "db_branches": [
      {
        "type": "pg",
        "version": "17",
        "name": "users-database-name",
        "connection": { "url": "DATABASE_URL" },
        "migrations": {
          "flavor": "flyway",
          "path": "./migrations"
        }
      }
    ]
  }
}
```

| Field | Description |
| --- | --- |
| `flavor` | Selects the migration tool. Currently `flyway`. |
| `path` | Local directory of migration files, resolved relative to your working directory. |
| `image` | *(Optional)* Override the migration runner image. Defaults to `flyway/flyway:12` for `flavor: flyway`. |

Using `migrations` requires the branch's `name` field to be set.

Migrations run while the branch is created, before it becomes ready. If they fail, the session aborts, so your app is never started against a half-migrated branch.

A migration that conflicts with one already applied to the branch fails your session only, the branch itself remains usable.

## Flyway migrations

Set `"flavor": "flyway"` to run migrations with [Flyway](https://documentation.red-gate.com/flyway).

To override the runner image, set `image`:

```json
{
  "migrations": {
    "flavor": "flyway",
    "path": "./migrations",
    "image": "flyway/flyway:12"
  }
}
```
