---
title: Schema Migrations
description: Automatically run your schema migrations on a mirrord DB branch
tags:
  - alpha
  - team
  - enterprise
---

The `migrations` field runs your schema migrations against the branch automatically, so the branch comes up with the schema your code expects. It is supported for **MySQL**, **PostgreSQL**, **MSSQL**, and **ClickHouse** branches, and requires `name` to be set.

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

`flavor` selects the migration tool. `path` is a local directory of migration files, resolved relative to your working directory.

Migrations run while the branch is created, before it becomes ready. If they fail, the session aborts, so your app is never started against a half-migrated branch.

A migration that conflicts with one already applied to the branch fails your session only—the branch itself remains usable.

## Flyway migrations

Set `"flavor": "flyway"` to run migrations with [Flyway](https://documentation.red-gate.com/flyway).

By default the operator runs mirrord's own Flyway image (`ghcr.io/metalbear-co/flyway`), which includes ClickHouse support.
To override the image, specify `image` in the configuration:

```json
{
  "migrations": {
    "flavor": "flyway",
    "path": "./migrations",
    "image": "flyway/flyway:11-alpine"
  }
}
```
