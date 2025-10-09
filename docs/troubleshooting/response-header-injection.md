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
When debugging, it’s often useful to know whether a response went through mirrord and how it was handled.
This option helps to verify mirrord’s routing decisions and confirm whether traffic went through an agent or bypassed it during debugging.

# Header behavior 
When enabled, the mirrord agent automatically adds a `airrord-agent` header to HTTP responses handled by mirrord.

### Possible values for the header:
- `forwarded-to-client`: The request was intercepted and forwarded to the local process (mirrord handled it).
- `passed-through`: The request was not sent to the local process (for example, it didn’t match active filters, so it was passed through).

Header injection is disabled by default until further notice
You can enable header injection with the following configuration:

```json
{
  "agent": {
    "inject_headers": true
  }
}
```

You can see all the agent configuration options [here](https://metalbear.com/mirrord/docs/config/options#agent).