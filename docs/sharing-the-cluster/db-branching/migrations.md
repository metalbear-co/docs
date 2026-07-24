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

This page covers the `migrations` field of a DB branch config for MySQL, MariaDB, PostgreSQL, CockroachDB, and MSSQL. For general concepts and the full list of config fields, see the [DB Branching overview](../db-branching.md).

{% hint style="info" %}
Minimum versions per capability:

| Capability | mirrord CLI | Operator | Helm chart |
| --- | --- | --- | --- |
| Schema migrations (Flyway, local `path`) | `3.230.0` | `3.182.0` | `3.182.0` |
| Migrations on MariaDB branches | `3.235.0` | `3.186.0` | `3.186.0` |
| Image-native Flyway (`locations`), `container` flavor | `3.238.0` | `3.187.0` | `3.187.0` |
{% endhint %}

## How it works

When your session starts a branch whose config has `migrations`:

1. The operator creates the branch database pod and clones the source schema/data into it, per `copy.mode`. Migrations are not involved in this step.
2. Once the branch database accepts connections, the operator runs your migrations as a one-shot Kubernetes Job next to it. The Job connects to the branch - never to the source database - using the branch's own admin credentials.
3. The branch becomes ready only after the Job succeeds, and your session starts against the fully migrated branch. If the Job fails, your session aborts and mirrord prints the Job's log output, so your app never runs against a half-migrated schema.

When a session reuses an existing branch with a changed migration set, the operator runs a new Job for the delta. A migration that conflicts with one already applied (for example, an edited already-applied Flyway file) fails your session only; the branch stays usable for other sessions.

The `flavor` field selects what the Job runs. Pick by where your migrations live:

| Your migrations are... | Use |
| --- | --- |
| SQL files in the repository you're working in | `flavor: flyway` with `path` |
| SQL files baked into an image your CI publishes | `flavor: flyway` with `image` + `locations` |
| Part of your app's own tooling (a migration script or framework CLI baked into the image) | `flavor: container` |

Using `migrations` requires the branch's `name` field to be set.

The branch's `creation_timeout_secs` covers the whole startup: cloning the source, pulling the migration image, and running the migrations. Raise it if your migrations are slow or your migration image is large.

## Flyway migrations

Set `"flavor": "flyway"` to run versioned SQL files (`V1__create_users.sql`, `V2__add_orders.sql`, ...) with [Flyway](https://documentation.red-gate.com/flyway). Flyway records applied migrations in a `flyway_schema_history` table inside the branch, so re-runs apply only what's new.

Mind the interaction with `copy.mode`: Flyway refuses to migrate a schema that already has objects but no `flyway_schema_history` table. If your source database isn't itself Flyway-managed, use `"copy": { "mode": "empty" }` and let the migrations build the branch schema from scratch. If the source is Flyway-managed, `schema` and `all` copy modes work - the history table comes along with the copy, and the Job applies only your newer files.

| Field | Description |
| --- | --- |
| `path` | Local directory of migration files, resolved relative to your working directory. Mutually exclusive with `locations`. |
| `locations` | Flyway locations inside `image` holding the migration files, for images with the SQL baked in. Mutually exclusive with `path`, and requires `image`. |
| `image` | Migration runner image. Optional with `path` (defaults to `flyway/flyway:12`), required with `locations`. |

### From a local directory

With `path`, mirrord uploads the directory (up to 1 MiB) and the Job runs the stock Flyway image against it. This is the fit when the migration files live in the repository you're working in:

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

### From a migration image

With `locations`, nothing is uploaded: the SQL is already baked into a migration image (typically published by CI), and the Job runs that image with Flyway pointed at the in-image paths. This is the fit when your deployment pipeline already migrates the shared database by running such an image, and previews should run exactly the same artifact:

```json
{
  "migrations": {
    "flavor": "flyway",
    "image": "registry.example.com/my-migrations:latest",
    "locations": ["filesystem:/flyway/sql"]
  }
}
```

`locations` accepts multiple entries, joined into `FLYWAY_LOCATIONS`.

## Container migrations

Set `"flavor": "container"` to run your own image as the migration Job. This is the fit when migrations aren't standalone SQL files but part of your application's own tooling - for example an app image whose setup script runs the framework's migration command:

```json
{
  "migrations": {
    "flavor": "container",
    "image": "registry.example.com/my-app:latest",
    "command": ["bin/migrate"],
    "env": {
      "APP_ENV": "test",
      "DATABASE_URL": "mysql://$(MIRRORD_DB_USER):$(MIRRORD_DB_PASSWORD)@$(MIRRORD_DB_HOST):$(MIRRORD_DB_PORT)/$(MIRRORD_DB_NAME)"
    }
  }
}
```

| Field | Description |
| --- | --- |
| `image` | Full image reference for the migration container, including the tag. |
| `command` | *(Optional)* Entrypoint command override. When unset, the image's own entrypoint runs. |
| `args` | *(Optional)* Entrypoint args override. |
| `env` | *(Optional)* Extra environment variables for the container. |

The container must exit 0 when migrations succeed; any other exit code fails the Job (and your session) with the container's logs as the error.

`command` and `args` are the Kubernetes container `command`/`args`, so anything a pod spec can run works here - as long as it exists inside the image (the container flavor uploads nothing from your machine). Common shapes:

```json
"command": ["/app/bin/migrate"]
```

```json
"command": ["sh", "-c", "/app/bin/migrate && /app/bin/seed"]
```

Chain multiple scripts with `&&` so the first failure stops the chain and fails the Job.

### Reaching the branch from your container

The operator injects the branch connection into the container as environment variables:

| Variable | Value |
| --- | --- |
| `MIRRORD_DB_HOST` | Branch database host. |
| `MIRRORD_DB_PORT` | Branch database port. |
| `MIRRORD_DB_USER` | The branch engine's default admin user. |
| `MIRRORD_DB_PASSWORD` | The branch's root password. Omitted when the branch has none. |
| `MIRRORD_DB_NAME` | The branch database name. |

There are two ways to consume them:

- **Compose variables your tool already reads**, with Kubernetes [`$(VAR)` expansion](https://kubernetes.io/docs/tasks/inject-data-application/define-interdependent-environment-variables/) in `env`, `command`, or `args` - the `DATABASE_URL` example above. This needs no changes to the image.
- **Read them from the environment in your script**: `psql -h "$MIRRORD_DB_HOST" ...` or an updated `db_setup.sh` that prefers `MIRRORD_DB_*` when present.

Note that these are the *branch's* credentials, deliberately not your source database's: the Job needs admin rights on the branch, and it must never touch the shared database.

### Composing the config in CI

A preview pipeline usually decides the image tag and the command when it prepares the config - what mirrord ultimately receives is a plain config like:

```json
{
  "migrations": {
    "flavor": "container",
    "image": "registry.example.com/my-app:build-1234",
    "command": ["bin/migrate"],
    "env": {
      "DATABASE_URL": "mysql://$(MIRRORD_DB_USER):$(MIRRORD_DB_PASSWORD)@$(MIRRORD_DB_HOST):$(MIRRORD_DB_PORT)/$(MIRRORD_DB_NAME)"
    }
  }
}
```

How the pipeline fills those values in is up to it; mirrord config files also support [Tera templating](https://metalbear.com/mirrord/docs/config) for reading them from the environment in place.

## When migrations fail

A failed migration aborts your session, and the error mirrord prints is the Job's own log output - a Flyway error, or whatever your container wrote before exiting non-zero. To dig deeper in the cluster:

- The branch resource records the outcome: `kubectl get branchdatabases -n <namespace>` and look at `status.migrations` (phase, and the error text on failure).
- The Jobs are named `mirrord-migrations-<branch-uid>-<generation>`; `kubectl logs job/<name>` shows the full run, including successful ones.

Failures you may hit: a migration with a SQL error (fix the file; a fresh session re-runs it), an edited already-applied Flyway file on a reused branch (checksum conflict - fails your session only), an image rejected by the admin's `allowedImages` list, or an image that can't be pulled.

## Restricting migration images

Cluster admins can restrict which images are accepted with the per-database `dbPod.allowedImages` list in the operator's Helm values. The list applies to migration images that users supply (`container` flavor and image-native Flyway) the same way it applies to branch database images; a disallowed image fails the migration with a clear error before anything runs.
