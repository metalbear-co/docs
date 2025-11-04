---
title: "DB Branching"
description: "How to use mirrord DB branching advanced configuration"
date: 2025-08-31T00:00:00+03:00
lastmod: 2025-08-31T00:00:00+03:00
draft: false
menu:
  docs:
    parent: "using-mirrord"
toc: true
tags: ["team", "enterprise"]
---


The following options provide control over how mirrord creates and manages database branches.

```json
{
  "db_branches": [
    {
      "id": "users-mysql-db",            // Optional
      "type": "mysql",
      "version": "8.0",
      "name": "users-database-name",      // Optional
      "ttl_secs": 60,                     // Optional
      "creation_timeout_secs": 20,        // Optional, Defaults to 60 if not specified
      "connection": {
        "url": {
          "type": "env",
          "variable": "DB_CONNECTION_URL" // Required
        }
      },
      "copy": {
        "mode": "empty"                   // Optional, Defaults to "empty" if not specified
      }
    }
  ]
}
```

## Branch Creation Timeout
`creation_timeout_secs`
Defines how long (in seconds) mirrord waits for a database branch to become ready after creation.
If the branch isn’t ready within this time, mirrord session fails, exists and returns a timeout error.
Use this field to avoid hanging operations when branch creation takes too long or fails.
Default value is 60 seconds.

## Copy Modes 
The `copy` field controls what data gets cloned when creating a database branch.

### Available Modes

1. ### Empty Databae
`"mode": "empty"` Creates an empty database with no schema or data, this is the default value when the `copy` attribute is not specified.
Best for workflows where your application initializes the schema or runs migrations as part of startup.

2. ### Database Schemas
`"mode": "schema"` Copies only the table structures (schemas) from the source database, without any data.
Useful for testing schema changes or local development where structure is needed but data is not.

3. ### Complete Database
`"mode": "all"` Copies everything from the source database - both schema and data.
This is helpful when you want a full clone of your environment data for debugging or reproducing production-like scenarios.
{% hint style="warning" %}
Use this option with caution.
It’s only recommended for very small or empty databases.
Copying large datasets can significantly increase branch creation time and storage usage.
{% endhint %}```

4. ### Filtered Data Clone
Developers can customize what gets copied per table. This allows copying only specific rows or subsets of data using SQL query filters.

```Json
{
  "copy": {
    "mode": "schema",                   // Or "empty" as explained below
    "tables": {
      "users": {
        "filter": "name = 'alice' OR name = 'bob'"
      },
      "orders": {
        "filter": "created_at > 1759948761"
      }
    }
  }
}
```

#### In this example:
The schema for all tables is cloned.
The `users` table copy includes only rows for `alice` and `bob`.
The `orders` table copy includes only rows created after a certain timestamp.

Filtering can also be combined with `"mode": "empty"`, in which case only the specified tables (and their filtered data) are copied, while all others are excluded.

Note: Filtering is not compatible with `"mode": "all"`.
If both are specified, mirrord ignores the `tables` configuration.
