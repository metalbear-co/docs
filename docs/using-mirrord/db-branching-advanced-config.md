---
title: "DB Branching"
description: "How to use mirrord DB branching to clone data for safe development and testing DB migrations"
date: 2025-08-31T00:00:00+03:00
lastmod: 2025-08-31T00:00:00+03:00
draft: false
menu:
  docs:
    parent: "using-mirrord"
toc: true
tags: ["team", "enterprise"]
---


# Advanced Configuration: Copy Modes

`copy` field in the `db_branches` configuration allows developers to control how the database is cloned when creating a branch. 

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

## Available Modes

1. ### `"mode": "empty"`
Creates an empty database with no schema or data, this is the default value when `copy` attribute is not specified.
Best for workflows where your application initializes the schema or runs migrations as part of startup.

2. ### `"mode": "schema"`
Copies only the table structures (schemas) from the source database, without any data.
Useful for testing schema changes or local development where structure is needed but data is not.

3. ### `"mode": "all"`
Copies everything from the source database - both schema and data.
This is helpful when you want a full clone of your environment data for debugging or reproducing production-like scenarios.
Note that this can increase branch creation time and storage usage, especially for large databases.

3. ### `Filter Data Clone`
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
