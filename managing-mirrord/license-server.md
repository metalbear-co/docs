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

The license server enables you to manage your organization’s seats without sending any data to mirrord’s servers. It can aggregate license metrics from multiple operators (useful if you’re running mirrord across multiple clusters) and provides visibility into seat usage across your organization. 

{% hint style="info" %}
This feature is only relevant for users on the Team and Enterprise pricing plans.
{% endhint %}

### Basic Setup

The license server is installable via Helm. First, add the MetalBear Helm repository:

```bash
helm repo add metalbear https://metalbear-co.github.io/charts
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
helm install metalbear-co/mirrord-operator-license-server -f ./values.yaml --wait
```

To make sure it's been installed successfully and is running:

```bash
kubectl get deployment -n mirrord mirrord-license-server
```

If your operator(s) are running at on a different cluster, make sure the `mirrord-operator-license-server` service is exposed to them via ingress.

#### Connecting Operators to the License Server

First update your operator `values.yaml` file ([see this page](../overview/quick-start.md#helm) for quickstart helm setup for operator):

```yaml
# ./values.yaml
license:
  key: secret
  licenseServer: http://<license-server-addr>
```

_NOTE: The server value must contain the protocol and the prefix for any ingress that the the license server can be behind._

Then run:

```bash
helm install metalbear-co/mirrord-operator -f ./values.yaml --wait
```

## Getting a Utilisation Report from the License Server

The license server has an endpoint that can be used to get a spreadsheet report with stats about mirrord usage. It has general metrics as well as specific per-user metrics. The reports include:

* **General stats** for the timeframe specified in query parameters
  * Number of licenses acquired
  * Number of unique machines used OR unique kubernetes users, depending on the type of license being used
* **Per-user stats**
  * Oldest and most recent activity date
  * Total mirrord session time and number
  * Average (mean) session duration and average (mean) number of daily sessions over the timeframe specified in query parameters

**Query params**

* `format` (required): 
  * `"xlsx"`: produces an Excel spreadsheet with two tabs: general stats and per-user stats (_As curl will warn you, this produces binary data, and should be directed into a file rather that printed out raw_).
* `from` (optional): A date time, e.g. `"2025-08-20T00:00:00Z"`, to bound the beginning of the period for relevant stats.
* `to` (optional): A date time, e.g. `"2025-08-20T00:00:00Z"`, to bound the end of the period for relevant stats.

{% hint style="info" %}
If the query parameters `to` and `from` are not specified, the data will be for all time.
{% endhint %}

To get a report:

* Ensure that the license server is accessible - by default it is installed as a `ClusterIP` so either expose it outside the cluster or access it from inside the cluster (for example, you can use `mirrord exec -- curl`).
* Get the IP of the license server - e.g. if it is a `ClusterIP`, you can run this:

```bash
MIRRORD_LIC_SERV_IP=$(kubectl get svc mirrord-operator-license-server -n mirrord -o jsonpath='{.spec.clusterIP}')
```

* Run `curl`, ensuring that you use the correct API license key, for example:

```bash
mirrord exec -- curl --get --location "${MIRRORD_LIC_SERV_IP}/api/v1/reports/usage?format=xlsx" --header 'x-license-key: <operator API license key>' --output report.xlsx
```
