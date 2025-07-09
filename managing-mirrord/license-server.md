---
title: License Server
date: 2025-04-07T00:00:00.000Z
lastmod: 2025-04-07T00:00:00.000Z
draft: false
images: []
linktitle: License Server
menu:
  docs:
    teams: null
weight: 540
toc: true
tags:
  - enterprise
description: License Server
---

# License Server

The license server enables you to manage your organization’s seats without sending any data to mirrord’s servers. It can aggregate license metrics from multiple operators (useful if you’re running mirrord across multiple clusters) and provides visibility into seat usage across your organization. This feature is only relevant for users on the Team and Enterprise pricing plans.

### Basic Setup

The license server is installable via Helm. First, add the MetalBear Helm repository:

```bash
helm repo add metalbear-co https://metalbear-co.github.io/charts
```

Next, save the following yaml as `values.yaml` on your machine.

```yaml
# ./values.yaml
createNamespace: true

service:
  type: ClusterIP

license:
  key: secret
  file:
    data:
      license.pem: |
        ----- ... 
        MIRRORD-LICENSE 
        ... -----
```

Fill in the license.key and license.pem fields according to the following guidelines:

* License key - Can be any string of your choosing. We recommend using random characters or a UUID.
* License file - Must be a valid operator license. This can also be a secret under the `license.pem` key.

You can customize the license server deployment further - all values.yaml configuration options can found [here](https://raw.githubusercontent.com/metalbear-co/charts/main/mirrord-license-server/values.yaml)

_NOTE: The license server needs to be accessible to any mirrord operators you want to track. To that end, the default value for `service.type` is `ClusterIP`, but can be changed to `NodePort` or `LoadBalancer`, according to your requirements._

Next, install the license server on your cluster:

```bash
helm install metalbear-co/mirrord-operator-license-server -f ./values.yaml --generate-name --wait
```

To make sure it's been installed successfully and is running:

```bash
kubectl get deployment -n mirrord mirrord-license-server
```

If your operator(s) are running at on a different cluster, make sure the `mirrord-operator-license-server` service is exposed to them via ingress.

#### Connecting Operators to the License Server

First update your operator [`values.yaml`](https://github.com/RinkiyaKeDad/gitbook-mirrord-docs/blob/main/overview/quick-start/README.md#helm) for quickstart helm setup for operator) file:

```yaml
# ./values.yaml
license:
  key: secret
  licenseServer: http://<license-server-addr>
```

_NOTE: The server value must contain the protocol and the prefix for any ingress that the the license server can be behind._

Then run:

```bash
helm install metalbear-co/mirrord-operator -f ./values.yaml --generate-name --wait
```
