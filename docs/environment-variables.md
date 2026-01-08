---
title: Environment Variables
date: 2024-12-19T00:00:00.000Z
lastmod: 2024-12-19T00:00:00.000Z
draft: false
weight: 130
toc: true
tags:
  - open source
  - team
  - enterprise
description: Load environment variables from your target pod into your local process
---

# Environment variables

mirrord loads environment variables from your target pod into your local process. This means your app gets the same configuration it would have in the cluster such as database URLs, feature flags, service discovery values, and secrets.

## How it works

Before your local process starts, mirrord fetches environment variables from the target pod and injects them into your process. Your code reads them normally (e.g., `process.env.DATABASE_URL` or `os.environ["DATABASE_URL"]`), and gets the remote values.

By default, all environment variables from the target are loaded.

## Basic configuration

Enable environment variables (this is the default):

```json
{
  "feature": {
    "env": true
  }
}
```

Disable environment variables:

```json
{
  "feature": {
    "env": false
  }
}
```

## Include specific variables

Load only the variables you need:

```json
{
  "feature": {
    "env": {
      "include": "DATABASE_URL;REDIS_HOST;FEATURE_*"
    }
  }
}
```

Variables are separated by semicolons. Wildcards are supported:
- `*` matches any number of characters
- `?` matches a single character

## Exclude specific variables

Load all variables except certain ones:

```json
{
  "feature": {
    "env": {
      "exclude": "AWS_SECRET_ACCESS_KEY;DATABASE_PASSWORD;*_TOKEN"
    }
  }
}
```

`include` and `exclude` are mutually exclusive—use one or the other.

## Override variables

Replace specific remote values with local ones. This is useful when you want the remote configuration but need to redirect certain outputs (like email or payment providers) to safe sandbox endpoints.

```json
{
  "feature": {
    "env": {
      "override": {
        "SMTP_HOST": "localhost",
        "PAYMENT_API_URL": "https://sandbox.payment-provider.com",
        "LOG_LEVEL": "debug"
      }
    }
  }
}
```

Overrides are applied after loading remote variables, so the override values win.

## Combining options

You can combine `include` or `exclude` with `override`:

```json
{
  "feature": {
    "env": {
      "include": "DATABASE_*;REDIS_*;FEATURE_*",
      "override": {
        "DATABASE_HOST": "localhost:5432"
      }
    }
  }
}
```

This loads only database, Redis, and feature flag variables from the remote, then overrides the database host to point to a local database.

### Safe staging testing

Load remote config but redirect external services to sandboxes:

```json
{
  "feature": {
    "env": {
      "override": {
        "SMTP_HOST": "smtp.mailtrap.io",
        "STRIPE_API_KEY": "sk_test_...",
        "SMS_GATEWAY_URL": "https://sandbox.twilio.com"
      }
    }
  }
}
```

## Security considerations

- **Treat remote env vars like secrets**: they may contain API keys, database passwords, and other sensitive data. Avoid logging them or writing them to files.
- **Use `exclude` for sensitive variables**: if you don't need secrets locally, exclude them.

## Reference

- For more information on how this works checkout [this page](../reference/env.md)
- The [Configuration Options](https://metalbear.com/mirrord/docs/config/options) page contains a full list of configuration options
