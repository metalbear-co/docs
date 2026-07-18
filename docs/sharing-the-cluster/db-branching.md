---
title: "DB Branching"
description: "How to use mirrord to spin up an isolated DB branch for safe development and testing DB migrations"
date: 2025-08-31T00:00:00+03:00
lastmod: 2025-08-31T00:00:00+03:00
draft: false
menu:
  docs:
    parent: "using-mirrord"
toc: true
tags: ["team", "enterprise"]
---
{% hint style="info" %}
This feature is available to users on the Team and Enterprise pricing plans.
{% endhint %}

The `db_branches` feature in mirrord lets developers spin up an isolated DB branch that mirrors the remote DB, while running safely in isolation. This allows schema changes, migrations, and experiments without impacting teammates or shared environments.
The supported database engines are listed under [Choose Your Database](#choose-your-database) below.

**When is this useful?**

1. **Running schema migrations safely**  
    Developers can test migrations and schema changes without risking corruption of the remote databases.

2. **Experimenting locally**  
    Developers get a branch of the remote DB connected to their local app automatically - no admin setup required.

3. **Collaborating with teammates**  
    If a branch already exists (with the same ID), mirrord reuses it. Developers can share branches as needed.

4. **Validating AI-generated database changes**
    If your AI coding agents need to generate migrations or schema updates, DB branching provides a safe environment to test those changes without risking the shared environment.

## Choose Your Database

Copy modes, version requirements, and engine-specific behavior differ per database. Pick yours to see the full guide:

| Database | Config `type` | Branch location |
| --- | --- | --- |
| [MySQL](db-branching/mysql.md) | `"mysql"` | Remote |
| [PostgreSQL](db-branching/postgresql.md) | `"pg"` | Remote |
| [MSSQL](db-branching/mssql.md) | `"mssql"` | Remote |
| [MongoDB](db-branching/mongodb.md) | `"mongodb"` | Remote |
| [Redis](db-branching/redis.md) | `"redis"` | Remote or local |
| [DynamoDB](db-branching/dynamodb.md) | `"dynamodb"` | Remote |
| [ClickHouse](db-branching/clickhouse.md) | `"clickhouse"` | Remote |
| [CockroachDB](db-branching/cockroachdb.md) | `"cockroachdb"` | Remote |
| [Google Spanner](db-branching/spanner.md) | `"spanner"` | Remote |
| [Generic](db-branching/generic.md) (any other service, using your own image) | `"generic"` | Remote |

## Prerequisites

Before you start, make sure you have:  
1. The minimum operator, mirrord CLI, and operator Helm chart versions for your database engine, with the engine's branching value enabled in the chart. The exact versions are listed at the top of each database page above.  
2. Your local application is using environment variables or Kubernetes Secrets to store DB connection strings or individual connection parameters.  
3. mirrord installed and working.  


## Configuring `db_branches`
Developers define branches in their `mirrord.json`:
```json
{
  "feature": {
    "db_branches": [
      {
        "id": "users-mysql-db",             // Optional
        "location": "remote",               // Optional, default is "remote", Available options [remote | local]
        "type": "mysql",                    // See "Choose Your Database" above for supported values
        "version": "8.0",
        "name": "users-database-name",      // Optional
        "ttl_secs": 60,                     // Optional, mutually exclusive with `ttl_mins`
        "creation_timeout_secs": 20,        // Optional, Defaults to 60 if not specified
        "connection": {
          "url": "DATABASE_URL"
        },
        "copy": {
          "mode": "empty"                   // Defaults to "empty" if not specified
        }
      }
    ]
  }
}
```

### Key Fields

| Field | Description |
| --- | --- |
| `id` | When reused, mirrord reattaches to the same branch as long as the time-to-live (TTL) has not expired. This allows multiple sessions to share the same database branch. To prevent accidental reuse of another user's branch, it is recommended to assign a unique value (for example, a UUID) as the identifier. (The `id` field is not used for local Redis instances and has no effect on database selection or reuse) |
| `location` | Supported values are `remote` and `local`. The default is `remote`, which provisions a branch in the cluster. `local` spawns the branch on your own machine, and is only available for engines whose [Choose Your Database](#choose-your-database) entry lists a local branch location (see [Local Redis](db-branching/redis.md#local-redis)). |
| `type` | The database engine to branch. See the [Choose Your Database](#choose-your-database) table for supported values. |
| `version` | Database engine version. |
| `name` | Remote database name to clone, the override URL uses `name` so the connection URL looks like .../dbname. If name is ommited, the override URL just points to the database server; the application must select the DB manually in that case. For Redis, `name` is the database **index** Redis uses to select a logical database rather than a name, so it must be a valid non-negative number. If omitted, it defaults to index `0`. |
| `ttl_secs` / `ttl_mins` | Override for branch time-to-live (TTL), expressed in seconds or minutes. The two fields are mutually exclusive — set whichever is more convenient. The default is 5 minutes. |
| `connection` | Describes how to locate the source database connection details. Supports a full connection URL or individual connection parameters. See [Connection Modes](db-branching/connection.md) for details. For DynamoDB, `connection` is optional and, since there is no user or password, is only used to point the source client at a custom/VPC endpoint URL (for example `AWS_ENDPOINT_URL_DYNAMODB`); if omitted, the standard regional AWS endpoint is used. |
| `copy.mode` | Allows developers to control how the database is cloned when creating a branch. Available modes and filtering options differ per engine - see the Copy Modes section on your [database's page](#choose-your-database). |
| `copy.dump_args` | (MySQL & PostgreSQL only) Customize the arguments passed to `mysqldump` or `pg_dump`. See [MySQL](db-branching/mysql.md#custom-dump-arguments) or [PostgreSQL](db-branching/postgresql.md#custom-dump-arguments) for details. |
| `creation_timeout_secs` | Override for branch creation timeout, in seconds. If the branch isn't ready within this time, the mirrord session fails and returns a timeout error. Use this field to avoid hanging operations when branch creation takes too long or fails. The default is 60 seconds. Unrecoverable pod failures (for example a bad image reference stuck in `ImagePullBackOff`) fail the branch immediately with the underlying error instead of waiting for this timeout. |
| `iam_auth` | Optional IAM authentication for AWS RDS or GCP Cloud SQL. See [IAM Authentication](db-branching/iam-authentication.md) for details. For DynamoDB, `iam_auth` is **required** when using copy mode `all`, since DynamoDB has no password-based auth. |
| `local.port` | Currently only for Local Redis. Sessions that use the same port share a single local Redis database. When a new session starts on that port, it creates a new database instance that replaces the existing one. |
| `migrations` | (MySQL, PostgreSQL, MSSQL & CockroachDB only) Automatically run schema migrations on the branch so it comes up with the schema your code expects. See [Schema Migrations](db-branching/migrations.md) for details. |

## Running With DB Branches

1. Run your app with mirrord and set the `db_branches` field in [the mirrord configuration file](https://metalbear.com/mirrord/docs/config).

2. mirrord will spin up a database branch according to the following rules:
 - Reusing an existing branch:
    If you provide an ID that matches an existing branch and its TTL hasn’t expired, mirrord will reuse that branch.
    When this happens, mirrord will notify you:
    ```
    A branch with this ID already exists for the target database.
    You’re about to use it! 
    ```
    *This means you’re connecting to an existing branch, not a fresh isolated one.*
 - Creating a new branch:
    If no ID is specified, or if you choose a new, non-existing ID, mirrord will create a fresh, empty database branch.

3. mirrord will override your DB environment variable with the branch's connection URL, so the app connects to the branch, not to the source db.
    This setup reduces the risk of accidental writes reaching the source database by directing activity toward an isolated branch.

4. The branch will be destroyed automatically when the TTL is reached and the branch is not in use (reconnecting to the same branch again extends its lifetime).

---

## Portforwards
When DB branching is enabled, mirrord will also automatically set up portforwards to the branch pod while the session is active. This can be used to, for example, access the branch database with a GUI SQL client like DBeaver or DataGrip. To list currently active DB branch portforwards, run `mirrord db-branches connections`.

---

## FAQ

**Q: Why does my connection time out?**
A: By default, branch databases have SSL disabled. Check if your client is specifically requesting SSL.

**Q: How do I use IAM authentication instead of passwords?**
A: mirrord supports IAM authentication for AWS RDS and GCP Cloud SQL, using the standard credential env vars already present on your target pod. See [IAM Authentication](db-branching/iam-authentication.md) for setup and examples.

## What's next?

Next, pick your database from [Choose Your Database](#choose-your-database) for engine-specific copy modes and configuration, check out [Connection Modes](db-branching/connection.md) for all the ways mirrord can locate your connection details, and see [Branch Management](db-branching/management.md) for CLI commands to inspect and destroy branches.
