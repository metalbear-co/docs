---
title: Response Header Injection
date: 2020-11-16T12:59:39.000Z
lastmod: 2020-11-16T12:59:39.000Z
draft: false
images: []
menu:
  docs:
    parent: troubleshooting
weight: 140
toc: true
tags:
  - open source
  - team
  - enterprise
description: Indicate whether the request was handled by mirrord.
---

{% hint style="info" %}
This feature requires at least mirrord-agent version **3.163.0**.
{% endhint %}

# Use Case
When debugging, it’s often useful to know how a response was handled by mirrord after being intercepted.
This option helps verify mirrord’s routing decisions and understand whether the intercepted traffic was forwarded to the local process or passed through to its original destination.

# Header behavior
When enabled, the mirrord agent automatically adds a `mirrord-agent` header to HTTP responses handled by mirrord.

### Possible values for the header:
- `forwarded-to-client`: The mirrord agent intercepted the request, sent it to the local process, and then passed back the response (mirrord handled it).
- `passed-through`: The mirrord agent also intercepted the request, sent it to its original destination, and then passed back the response (the request was not handled by the local process. for example, it didn’t match active filters, so it was passed to the original destination).

Header injection is disabled by default.
You can enable it with the following configuration:

```json
{
  "agent": {
    "inject_headers": true
  }
}
```

You can see all the agent configuration options [here](https://metalbear.com/mirrord/docs/config/options#agent).