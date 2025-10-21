---
title: "mirrord for CI"
description: "How to use the mirrord in a CI environment, with the mirrord ci commands."
date: 2025-10-21T00:00:00+03:00
lastmod: 2025-10-21T00:00:00+03:00
draft: false
menu:
  docs:
    parent: "using-mirrord"
toc: true
tags:
  - open source
  - team
  - enterprise
---

mirrord can be used to greatly speed up CI runs by avoiding the need to deploy the app you're trying to test.
Instead of setting up a whole kubernetes environment for every CI run, you can just use mirrord to redirect
the traffic from the service you want to test, which is already running in some cluster (e.g. a staging environment).

While running regular `mirrord exec` can be made to work for this purpose, it requires some finagling to get right.
The `mirrord ci start` command is more appropriate for this use case, since it starts your app and mirrord as
background processes, allowing you to run tests and whatever else you want while mirrord is running.

Note that you can only have **one** mirrord CI session per service during a CI run, this means that
we (currently) don't support executing multiple `mirrord ci start`, you must do one `mirrord ci start`, run your
tests, then run `mirrord ci stop`, before you're able to run `mirrord ci start` again in the same CI run.

## Prerequisites

1. Minimum mirrord CLI version `3.166.0`.

## For mirrord Operator users

To use the `mirrord ci` with a mirrord Operator, you'll need to generate a CI API key and store it
as a **secret** environment variable.

You can get this key by running the command:

```sh
mirrord ci api-key
```

Copy it and save it as the **secret** environment variable `MIRRORD_CI_API_KEY` in your CI.

## Starting a mirrord CI session

The `mirrord ci start` command functions very much like the `mirrord exec` command, meaning that it can take
the same arguments, such as using a configuration file with `--config-file`, setting a target with `--target`.

- An example of starting a mirrord for CI session with `npm run` (you can run anything, it's **not** limited to `npm`):

```sh
mirrord ci start --target deployment/ip-visit-counter npm run
```

The mirrord for CI session should now be running in the background, and you can run the tests.
These tests should target the deployed service (the app running in your staging cluster, for example),
and mirrord will intercept the traffic and redirect it to the local app (the one running in the background
with mirrord).

## Stopping a mirrord CI session

As previously mentioned, to start another mirrord CI session in the same CI run, you must first stop the one
that's running. You can do this with the `mirrord ci stop` command.

- Stopping a mirrord CI session:

```sh
mirrord ci stop
```

After you're done with the tests, just run this command (no args needed), and mirrord will stop running
itself, and the local app.
