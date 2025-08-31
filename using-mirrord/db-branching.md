---
title: "DB Branching"
description: "How to use mirrord to spin up isolated DB branche for safe development and testing DB migrations"
date: 2025-08-31T00:00:00+03:00
lastmod: 2025-08-31T00:00:00+03:00
draft: false
menu:
  docs:
    parent: "using-mirrord"
toc: true
tags: ["open source", "team", "enterprise"]
---


The `db_branches` feature in mirrord lets developers spin up isolated DB branches that mirror the production DB, while running safely in isolation.  
This allows schema changes, migrations, and experiments without impacting teammates or shared environments.
* This is an experimental feature, currently it only supports MySQL DB and does not support schema or data replication. 

When is this useful?
1. **Running schema migrations safely**  
   Developers can test migrations and schema changes without risking corruption of the production or staging databases.

2. **Experimenting locally**  
   Developers get a branch of the production DB connected to their local app automatically - no admin setup required.

3. **Collaborating with teammates**  
   If a branch already exists (with the same ID), mirrord reuses it. Developers can share branches as needed.



## Prerequisites

Before you start, make sure you have:  
1. A MySQL database configured in your cluster (production or staging).  
2. Your local application is using **environment variables** to store DB connection strings.  
3. mirrord installed and working.  

---
## Configuring `mirrord db branches`
Developers define branches in their `mirrord.json`:
```json
{
  "db_branches": [
    {
      "id": "users-mysql-db", // optional
      "type": "mysql",
      "name": "users-database-name",
      "ttl_secs": 60,                 // Optional: override default TTL
      "version": "8.0",
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
id: Optional identifier. If reused, mirrord reattaches to the same branch.
type: Currently only "mysql" is supported.
name: Remote database to clone.
ttl_secs: Optional override for branch TTL (default is 30 minutes).
connection.url: Required. The environment variable that contains your DB connection string.

## Running With DB Branches

1. Run your app with mirrord.json configured as defined above:
```
mirrord exec mirrord.json
```
2. mirrord will spin up a new MySQL branch (or reuse an existing one if id matches).
    Technical note: mirrord doesn’t use the original DB data. It creates a new, empty DB and overrides the application’s DB connection environment variables with the branch’s connection URL.
    This design is a safety feature - by always pointing your app to a fresh branch, it ensures that no accidental writes can ever reach the production database.

3. Override your DB environment variable so the app connects to the branch, not production.

4. Destroy the branch automatically when TTL expires or after inactivity.

* If an existing branch is reused, mirrord notifies you:
```
A branch with this ID already exists for the target database.
You’re about to use it! Change the ID if you prefer to start with a clean branch.
```