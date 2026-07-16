---
title: chaos testing with mirrord
date: 2026-07-15T21:00:00.000Z
lastmod: 2026-07-15T21:00:00.000Z
draft: false
menu:
  docs:
    parent: using-mirrord
toc: true
description: Introduce unexpected failures or disruptions to chaos test your app with mirrord.
tags:
  - alpha
  - oss
  - team
  - enterprise
---

# Chaos Testing

mirrord can be used to introduce artificial failures or disruptions to select network traffic and file operations, allowing you to
test how your app responds under unexpected conditions. Create selectors that turn connections to specific hosts into errors, or just
add latency. Turn an instant file read into an operation that takes seconds to complete and see how your app reacts to that.
Increase the latency of some HTTP requests that have a matching header, or match some other HTTP filter (link to HTTP filter config docs file).

{% hint style="info" %}
Currently, the only supported chaos operations are interactions with outgoing TCP connections, while file operations, HTTP traffic and more are planned.
{% endhint %}

#### Prerequisites

1. Minimum mirrord CLI version `3.232.0`.

#### Starting the chaos backend for a mirrord session

To interact with the chaos feature, the mirrord ui must be running, so start by running:

```sh
mirrord ui
```

{% hint style="info" %}
For more information on mirrord ui, see (link to mirrord ui docs file).
{% endhint %}

Grab the `API token` and the ui server address, it should look something like this:

```sh
* Web UI:
 -> http://127.0.0.1:59281/auth?token=60733e94f1799442e2f5af9048fac1a0efd6051715a2131992784f9c11876349&redirect=/
* API token:
 -> x-auth-token: 60733e94f1799442e2f5af9048fac1a0efd6051715a2131992784f9c11876349
```

Now let's start a mirrord session that will be impacted by the chaos rules. In this example we run it from the terminal, but you
can start the mirrord session from the IDE plugins too:

```sh
mirrord exec -f .mirrord/mirrord.json -- node app.js
```

You should see something like this in your terminal (logs shortened for clarity):

```sh
* session ID: c425f391-e9cc-4199-8de9-7bdbb3e7dfcc
* Running command: node app.js
```

With the `API token` and the `session ID`, we can now start interacting with the chaos server, creating, modifying and deleting
chaos rules that will impact this particular session only.

#### Creating our first chaos rule

To create a chaos rule you just need to send an HTTP POST request to the ui server address with the header `x-auth-token` and the
json body of the rule you want to create, for example:

```sh
http post --content-type application/json --headers { "x-auth-token": "60733e94f1799442e2f5af9048fac1a0efd6051715a2131992784f9c11876349" } "http://127.0.0.1:59281/api/chaos/rules/c425f391-e9cc-4199-8de9-7bdbb3e7dfcc" {
  name: "latency for database interactions"
  priority: 10
  effect: {
    latency: {
      read_ms: 750
    }
  }
  selector: {
    upstream: "sonic.database.svc.cluster.local"
    percentage: 35
  }
}
```

The outgoing traffic (roughly 35% of it) from the service we are debugging with mirrord will now be affected by latency on read operations, when this traffic is
destined to a host that matches the `selector`. In this example, outgoing traffic on this database connection would be impacted by this latency rule,
so we can test how the `app.js` service behaves when there's latency requesting data from this database.

#### Modifying or deleting a chaos rule

To either modify or delete an active chaos rule, we first need to get its ID. The ID for a rule is displayed when it's first created, and you can also retrieve it by sending an HTTP GET request
to the chaos backend, like so:

```sh
http get --content-type application/json --headers { "x-auth-token": "{mirrord ui token}" } "http://127.0.0.1:59281/api/chaos/rules/{session id}"
```

Change the `x-auth-token` to the `API token` from your mirrord ui, and the session ID to the ID of your session. Sending this request will show all the chaos rules that are active for this session,
and the chaos rule ID you want in hand, now we can modify it with an HTTP PUT request:

```sh
http put --content-type application/json --headers { "x-auth-token": "60733e94f1799442e2f5af9048fac1a0efd6051715a2131992784f9c11876349" } "http://127.0.0.1:59281/api/chaos/rules/c425f391-e9cc-4199-8de9-7bdbb3e7dfcc/6b8f1c4e-2a73-4d9b-8e56-c3f0a7d1b924" {
  name: "latency for database interactions more often"
  priority: 10
  effect: {
    latency: {
      read_ms: 750
    }
  }
  selector: {
    upstream: "sonic.database.svc.cluster.local"
    percentage: 75
  }
}
```

Here we changed both the `name` of the chaos rule and its `percentage` (roughly how often this chaos rule will trigger its effect on a matched selector). We also added the rule ID at the end of
the url.

To delete a chaos rule, you just need to send an HTTP DELETE request with the ID of the rule you want:

```sh
http delete --content-type application/json --headers { "x-auth-token": "60733e94f1799442e2f5af9048fac1a0efd6051715a2131992784f9c11876349" } "http://127.0.0.1:59281/api/chaos/rules/c425f391-e9cc-4199-8de9-7bdbb3e7dfcc/6b8f1c4e-2a73-4d9b-8e56-c3f0a7d1b924"
```

The chaos rule (in this example `6b8f1c4e-2a73-4d9b-8e56-c3f0a7d1b924`) will be deleted, and will stop affecting the session immediately.

#### Supported chaos rules

- Outgoing traffic latency

```json
{
  "name": "latency for api.example.com",
  "priority": 0,
  "selector": {
    "upstream": "api.example.com:443",
    "percentage": 100
  },
  "effect": {
    "latency": {
      "read_ms": 100,
      "write_ms": 200,
      "jitter_ms": 25
    }
  }
}
```

- Outgoing traffic connection errors

```json
{
  "name": "error for api.example.com",
  "priority": 0,
  "selector": {
    "upstream": "api.example.com:443",
    "percentage": 100
  },
  "effect": {
    "connection_error": {
      "type": "reset",
      "after_ms": 0
    }
  }
}
```

`type` can be one of: `reset` (can be applied for ongoing connections), `timed_out`, `refused`.
