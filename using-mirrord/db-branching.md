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
Currently, the feature is limited to MySQL databases.


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
      },
      "copy": {
		    "mode": "empty" // defaults to "empty" if not specified
	    }
    }
  ]
}
```
### Key Fields
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

## Managing DB Branches

mirrord provides CLI commands to inspect and manage database branches.
1. View Branch Status using: 
  ```
  `mirrord db-branches [(-n|--namespace) namespace] [-A | --all-namespaces] status [name...]`
  ```
    Shows the status of running database branches.
    If specific branch names are provided, mirrord shows their statuses.
    If no names are given, all active branches in the selected namespace (or all namespaces, if --all-namespaces is used) are listed.
    If no branches are active, mirrord returns:`No active DB branch found`
2. Destroy Branches using: `mirrord db-branches [(-n|--namespace) namespace] [-A | --all-namespaces] destroy [--all] [name...]`
    Destroys one or more running database branches.
    Use `--all` to destroy every active branch.
    Use one or more branch names to target specific branches.
    mirrord uses the current namespace by default, or the namespace specified with `--namespace`.
    To destroy branches across all namespaces, use `--all-namespaces`.
    If no active branches are found, mirrord returns:
    `Error: No active DB branch found`


## Advanced Configuration: Copy Modes

The `copy` field in the `db_branches` configuration allows developers to control how the database is cloned when creating a branch. 

### Available Modes

`"mode": "empty"`
Creates an empty database with no schema or data, this is the default value when `copy` attribute is not specified.
Best for workflows where your application initializes the schema or runs migrations as part of startup.

`"mode": "schema"`
Copies only the table structures (schemas) from the source database, without any data.
Useful for testing schema changes or local development where structure is needed but data is not.
```
`"mode": "all"`
```
Copies everything from the source database - both schema and data.
This is helpful when you want a full clone of your environment data for debugging or reproducing production-like scenarios.
Note that this can increase branch creation time and storage usage, especially for large databases.


`Filter Data Clone`
Developers can customize what gets copied per table. This allows copying only specific rows or subsets of data using SQL query filters.

```Json
{
  "copy": {
    "mode": "schema", // or "empty" as explained below
    "tables": {
      "users": {
        "filter": "WHERE name = 'alice' OR name = 'bob'"
      },
      "orders": {
        "filter": "WHERE created_at > 1759948761"
      }
    }
  }
}
```

### In this example:
The schema for all tables is cloned.
The `users` table copy includes only rows for `alice` and `bob`.
The `orders` table copy includes only rows created after a certain timestamp.

Filtering can also be combined with `"mode": "empty"`, in which case only the specified tables (and their filtered data) are copied, while all others are excluded.

# Future enhancements 
Won't take long we are actively working on having these feature available for Postgress 
