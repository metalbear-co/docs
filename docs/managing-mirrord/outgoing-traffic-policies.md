---
title: Outgoing Traffic Policies
date: 2025-08-31T00:00:00+03:00
lastmod: 2025-08-31T00:00:00+03:00
draft: false
menu:
  docs:
    parent: "Policies"
toc: true
tags: ["team", "enterprise"]
description: Restricting which resources and endpoints can be accessed when using mirrord
---

# Outgoing Traffic Policies

Cluster administrators can restrict which resources and endpoints can be accessed when using mirrord.
Outgoing traffic restrictions are defined using a `MirrordPolicy` or `MirrordClusterPolicy` resource and enforced by the mirrord operator.

_Supported in mirrord Operator version 3.103.0_
{% hint style="info" %}
This feature is available to users on the Team and Enterprise pricing plans.
{% endhint %}


#### Example Policy 
```yaml
apiVersion: policies.mirrord.metalbear.co/v1alpha
kind: MirrordPolicy
metadata:
  name: block-mirroring-from-boats-deployment
  namespace: default
spec:
  outgoingTraffic:
    default: block  # either "allow" or "block"; defaults to "block" if omitted
    allow:
      - ipBlock:
          cidr: 10.0.0.0/16
          except:
            - 10.0.5.0/24
        ports:
          - protocol: TCP
            port: 80
          - protocol: TCP
            port: 443
          - protocol: UDP
            port: 53
      - hostname:
          exact:
            - metalbear.com
            - metalbear.co
          expression: "^metalbear\\..*"  # regex pattern for hostname matching
        ports:
          - protocol: TCP
            port: 443
    block:
      - ipBlock:
          cidr: 0.0.0.0/0
        ports:
          - protocol: TCP
            port: 22
```

### Rule fields
Rules under allow or block are arrays of objects. Each object matches when all its fields align with the connection details.
​
#### Available fields:
`ipBlock`: Specifies CIDR ranges (cidr) with optional exclusions (except array of CIDRs).

`hostname`:

1. `exact`: Array of exact hostnames.

2. `expression`: Regex pattern (e.g., ^metalbear\\..*) for flexible matching.

`ports`: Array of objects with protocol (TCP/UDP) and port (number or range).
​

### Evaluation Logic
Policies evaluate runtime outgoing connections as follows:

1. No rules: If no allow or block rules exist, the connection is permitted.

2. Allow rules check: If allow rules exist but none match, the connection is forbidden.

3. Block rules precedence: If block rules exist and any match, the connection is forbidden (even if an allow rule would permit it).

4. Otherwise permitted: All other cases allow the connection.

Note: This differs from a strict "block by default" when no rules are present - empty policies remain permissive until rules are added.
