# Environment variables

mirrord loads environment variables from your target pod into your local process. This means your app gets the same configuration it would have in the cluster—database URLs, feature flags, service discovery values, and secrets.

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

## Common patterns

### Use remote config but local database

```json
{
  "feature": {
    "env": {
      "exclude": "DATABASE_*",
      "override": {
        "DATABASE_URL": "postgres://localhost:5432/myapp_dev"
      }
    }
  }
}
```

### Load only service discovery variables

Kubernetes injects service discovery variables like `SERVICE_NAME_HOST` and `SERVICE_NAME_PORT`. Load only these:

```json
{
  "feature": {
    "env": {
      "include": "*_SERVICE_HOST;*_SERVICE_PORT;*_PORT"
    }
  }
}
```

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
- **Override outbound services**: when testing against staging, override payment providers, email services, and SMS gateways to point to sandboxes rather than production endpoints.

## Reference

- [Environment Variables](../reference/env.md) — detailed reference
- [Configuration Options](https://metalbear.com/mirrord/docs/config/options) — full list of env configuration options
