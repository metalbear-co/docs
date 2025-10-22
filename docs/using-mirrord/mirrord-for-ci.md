---
title: "mirrord for CI"
description: "How to use mirrord in a CI environment with `mirrord ci` commands."
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

mirrord can be used to greatly speed up CI runs by enabling testing against a shared staging environment
without interrupting it. With mirrord for CI, you're able to keep your staging environment working, while
also running your batch of end-to-end and other automated tests. The local app runs in the context of the
targeted app that's deployed in your staging cluster, so it gets access to traffic, files, and more, as if
it's running in the cluster. This means there's no need to spin up a whole test environment for a CI run,
then spin it down when it's done.

While running regular `mirrord exec` can be made to work for this purpose, it requires some
finagling to get right, such as wrapping `mirrord exec` in some other command that would start
it as a background process.
The `mirrord ci start` command is more appropriate for this use case, since it starts your app and mirrord as
background processes, allowing you to then run tests while your app is running in the background and connected to the cluster.

{% hint style="info" %}
You can only have **one** mirrord CI session per service during a CI run. You must do one
`mirrord ci start`, run your tests, then run `mirrord ci stop` when they're done, before you're
able to run `mirrord ci start` again in the same CI run.
{% endhint %}

## Prerequisites

1. Minimum mirrord CLI version `3.166.0`.
2. The CI runner must be able to access the Kubernetes cluster in which you want to test.

## Kubernetes requirements

The CI runner must be able to access the Kubernetes cluster where the service you want to target is deployed,
otherwise mirrord won't work. You'll need a
[kubeconfig](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/) in the
CI runner that points to the target's cluster, and has the appropriate
[authentication](https://kubernetes.io/docs/reference/access-authn-authz/authentication/).

It's recommended that you create a Kubernetes
[service account](https://kubernetes.io/docs/concepts/security/service-accounts/) for the CI runner.

## For mirrord for Teams users

To use mirrord ci with mirrord Operator, you'll need to generate a CI API key and store it
as a **secret** environment variable. This will prevent your usage of mirrord in CI from expending your seats, which are counted using a machine-based ID.

You can get this key by running the command:

```sh
mirrord ci api-key
```

Copy it and save it as the **secret** environment variable `MIRRORD_CI_API_KEY` in your CI.

## Starting a mirrord CI session

The `mirrord ci start` command functions very much like the `mirrord exec` command, meaning that it can take
the same arguments, such as using a configuration file with `--config-file`, setting a target with `--target`, etc.

- An example of starting a mirrord for CI session with `npm run` (you can run anything, it's **not** limited to `npm`):

```sh
mirrord ci start --target deployment/ip-visit-counter npm run
```

The mirrord for CI session should now be running in the background, and you can run the tests.
These tests should target the deployed service (the app running in your staging cluster, for example),
and mirrord will intercept the traffic and redirect it to the local app (the one running in the background in the CI runner
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
