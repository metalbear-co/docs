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
This feature is only relevant for users on the Team and Enterprise pricing plans.
{% endhint %}

The `db_branches` feature in mirrord lets developers spin up an isolated DB branch that mirrors the remote DB, while running safely in isolation. This allows schema changes, migrations, and experiments without impacting teammates or shared environments.
Currently, the feature is limited to MySQL databases and does not support schema or data replication.


**When is this useful?**

1. **Running schema migrations safely**  
   Developers can test migrations and schema changes without risking corruption of the remote databases.

2. **Experimenting locally**  
   Developers get a branch of the remote DB connected to their local app automatically - no admin setup required.

3. **Collaborating with teammates**  
   If a branch already exists (with the same ID), mirrord reuses it. Developers can share branches as needed.

   --- 

## Prerequisites

Before you start, make sure you have:  
1. Minimum versions installed: Operator `3.12.0`, mirrord CLI `3.160.0` and operator Helm chart `1.37.0` with `operator.mysqlBranching` value set to `true`.
2. Your local application is using environment variables to store DB connection strings.  
3. mirrord installed and working.  


## Configuring `db_branches`
Developers define branches in their `mirrord.json`:
```json
{
  "db_branches": [
    {
      "id": "users-mysql-db", // Optional
      "type": "mysql",
      "version": "8.0",
      "name": "users-database-name",   // Optional
      "ttl_secs": 60,                 // Optional
      "connection": {
        "url": { 
            "type": "env", 
            "variable": "DB_CONNECTION_URL"  // Required
        }
      }
    }
  ]
}
```
Key Fields
1. `id`: When reused, mirrord reattaches to the same branch as long as the time-to-live (TTL) has not expired. This allows multiple sessions to share the same database branch. To prevent accidental reuse of another user’s branch, it is recommended to assign a unique value (for example, a UUID) as the identifier
2. `type`: Currently only "mysql" is supported.
3. `version`: Database engine version.
4. `name`: Remote database name to clone, the override URL uses `name` so the connection URL looks like .../dbname.
If name is ommited, the override URL just points to the MySQL server; the application must select the DB manually in that case.
5. `ttl_secs`: Override for branch time-to-live (TTL). The default is 5 minutes. The maximum allowed is 15 minutes. If you set a value above 15, mirrord will automatically fall back to 15 minutes.
6. `connection.url`: The environment variable that contains your DB connection string.

## Running With DB Branches

1. Run your app with mirrord and set the `db_branches` field in [the mirrord configuration file](https://metalbear.com/mirrord/docs/config).

2. mirrord will spin up a MySQL branch according to the following rules:
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
