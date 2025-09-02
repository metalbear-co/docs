---
title: "DB Branching"
description: "How to use mirrord to spin up isolated DB branch for safe development and testing DB migrations"
date: 2025-08-31T00:00:00+03:00
lastmod: 2025-08-31T00:00:00+03:00
draft: false
menu:
  docs:
    parent: "using-mirrord"
toc: true
tags: ["team", "enterprise"]
---


The `db_branches` feature in mirrord lets developers spin up isolated DB branch that mirror the remote DB, while running safely in isolation. This allows schema changes, migrations, and experiments without impacting teammates or shared environments.
Currently, the feature is limited to MySQL databases and does not support schema or data replication.


**When is this useful?**

1. **Running schema migrations safely**  
   Developers can test migrations and schema changes without risking corruption of the remote databases.

2. **Experimenting locally**  
   Developers get a branch of the remote DB connected to their local app automatically - no admin setup required.

3. **Collaborating with teammates**  
   If a branch already exists (with the same ID), mirrord reuses it. Developers can share branches as needed.



## Prerequisites

Before you start, make sure you have:  
1. A MySQL database configured in your remote environment.  
2. Your local application is using environment variables to store DB connection strings.  
3. mirrord installed and working.  

---
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
1. id: If reused, mirrord reattaches to the same branch. Can be used sharing database branch.
2. type: Currently only "mysql" is supported.
3. version: Database engine version.
4. name: Remote database name to clone, the override URL uses 'name' so the connection URL looks like .../dbname.
If name is dropped, override URL points just to the MySQL server; app must select DB manually.
5. ttl_secs: Override for branch TTL (default is 30 minutes).
6. connection.url: Required. The environment variable that contains your DB connection string.

## Running With DB Branches

1. Run your app with mirrord.json configured as defined above:
```
mirrord exec mirrord.json
```
2. mirrord will spin up a new MySQL branch (or reuse an existing one if id matches).
    mirrord doesn’t use the original DB data. It creates a new, empty DB.

3. Override your DB environment variable with the branch's connection URL, so the app connects to the branch, not the source db.
    This design is a safety feature - by always pointing your app to a fresh branch, it ensures that no accidental writes can ever reach the source database.

4. Destroy the branch automatically when TTL expires or after inactivity.

* If an existing branch is reused, mirrord notifies you:
```
A branch with this ID already exists for the target database.
You’re about to use it! Change the ID if you prefer to start with a clean branch.
```