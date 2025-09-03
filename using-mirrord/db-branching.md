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


## Configuring `mirrord db branches`
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
1. id: When reused, mirrord reattaches to the same branch as long as the time-to-live (TTL) has not expired. This allows multiple sessions to share the same database branch. To prevent accidental reuse of another user’s branch, it is recommended to assign a unique value (for example, a UUID) as the identifier
2. type: Currently only "mysql" is supported.
3. version: Database engine version.
4. name: Remote database name to clone, the override URL uses 'name' so the connection URL looks like .../dbname.
If name is ommited, the override URL just points to the MySQL server; the application must select the DB manually in that case.
5. ttl_secs: Override for branch time-to-live (TTL) (default is 5 minutes, maximum is 15 min).
6. connection.url: The environment variable that contains your DB connection string.

## Running With DB Branches

1. Run your app 'mirrord exec' with mirrord.json configured as defined above:

2. mirrord will spin up a new MySQL branch (or reuse an existing one if the id matches and the ttl has not expired).
    mirrord doesn’t use the original DB data. It creates a new, empty DB.
    If an existing branch is reused, mirrord notifies you:
    ```
    A branch with this ID already exists for the target database.
    You’re about to use it! Change the ID if you prefer to start with a clean branch.
    ```
3. mirrord will override your DB environment variable with the branch's connection URL, so the app connects to the branch, not to the source db.
    This design is a safety feature - by always pointing your app to a fresh branch, it ensures that no accidental writes can ever reach the source database.

4. The branch will be destroyed automatically when the TTL is reached and the branch is not in use (reconnecting to the same branch again extends its lifetime).
