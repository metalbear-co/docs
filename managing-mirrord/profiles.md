---
title: Profiles
date: 2024-03-25T00:00:00.000Z
lastmod: 2024-03-25T00:00:00.000Z
draft: false
images: []
linktitle: Profiles
menu: null
docs: null
teams: null
weight: 530
toc: true
tags:
  - team
  - enterprise
description: Reusable mirrord config templates
---

# Profiles

The installation of the mirrord operator defines a new clusterwide [custom resource](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/) in your cluster, called `MirrordProfile`.

This feature is only relevant for users on the Team and Enterprise pricing plans.

This resource can be used to provide mirrord users with a unified base for their mirrord configs. Users can reference an available profile in their configs, and they will be modified accordingly.

```yaml
apiVersion: profiles.mirrord.metalbear.co/v1alpha
kind: MirrordProfile
metadata:
  # This name can be referenced by the user in their mirrord configs.
  name: example-profile
spec:
  # A list of adjustments to be made in the user's feature config.
  #
  # The adjustments are applied in order.
  featureAdjustments:
  # Incoming traffic will be stolen.
  - change: incoming-steal
  # All outgoing traffic will be remote.
  - change: outgoing-remote
  # All DNS resolution will be remote.
  - change: dns-remote
```

The complete list of allowed values for the `featureAdjustments.[].change` field is as follows:

1. `incoming-mirror` - incoming traffic will be mirrored
2. `incoming-steal` - incoming traffic will be stolen
3. `incoming-off` - incoming traffic will not be intercepted
4. `dns-remote` - all DNS resolution will be remote
5. `dns-off` - all DNS resolution will be local
6. `outgoing-remote` - all outgoing traffic will be remote
7. `outgoing-off` - all outgoing traffic will be local

#### Selecting a profile

Starting from mirrord version 3.136.0, the user can select a mirrord profile in their mirrord config. The profile is referenced by its name.

```json
{
    "profile": "example-profile"
}
```

#### Enforcing profiles

Use of mirrord profiles can be enforced with [mirrord policies](../managing-mirrord/policies.md#profile-policy).

**Important:** mirrord profiles are applied to the session on the user machine, and should not be used as security features.
