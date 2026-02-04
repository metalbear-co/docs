---
title: Monitoring
date: 2024-04-01T13:37:00.000Z
lastmod: 2024-04-01T13:37:00.000Z
draft: false
images: []
linktitle: Monitoring
menu: null
docs: null
teams: null
weight: 500
toc: true
tags:
  - team
  - enterprise
description: Monitoring with mirrord for Teams
---

# Monitoring

The mirrord Operator can produce logs in JSON format that can be digested by most popular logging solutions (DataDog, Dynatrace, etc). To enable JSON logging, set `operator.jsonLog` to `true` in the Operator Helm chart values. The log level is `INFO` by default, and can be changed by setting `operator.logLevel` in the Helm chart values, or alternatively by using the `RUST_LOG` environment variable in the Operator container, which takes values in the following format: `mirrord={log_level}` (e.g. `mirrord=debug`).

{% hint style="info" %}
This feature is available to users on the Team and Enterprise pricing plans.
{% endhint %}

## Functional Logs

The following logs are written with log level `INFO`, and can be used for dashboards within monitoring solutions in order to monitor mirrord usage within your organization:

Log messages:

* Copy Target
* Port Steal
* Port Mirror
* Port Release
* Session Start
* Session End

Fields:

| field             | description                                                                                                                                                                  | events                                                                         |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| target            | the session's target                                                                                                                                                         | `All`                                                                          |
| client\_hostname  | `whoami::hostname` of client                                                                                                                                                 | `All`                                                                          |
| client\_name      | `whoami::realname` of client                                                                                                                                                 | `All`                                                                          |
| client\_user      | Kubernetes user of client (via k8s RBAC)                                                                                                                                     | `All`                                                                          |
| client\_id        | unique client id produced from client's certificate                                                                                                                          | `All`                                                                          |
| session\_id       | unique id for individual mirrord sessions                                                                                                                                    | `Port Steal` `Port Mirror` `Port Release` `Session Start` `Session End` |
| session\_duration | the session's duration in seconds                                                                                                                                            | `Session End`                                                                |
| port              | port number                                                                                                                                                                  | `Port Steal` `Port Mirror` `Port Release`                                  |
| http\_filter      | the client's configured [HTTP Filter](https://app.gitbook.com/s/Z7vBpFMZTH8vUGJBGRZ4/options#feature.network) | `Port Steal`                                                                  |
| scale\_down       | whether the session's target was scaled down                                                                                                                                 | `Copy Target`                                                                |

## Prometheus

The mirrord Operator can expose Prometheus metrics if enabled (the default endpoint is `:9000/metrics`).

### Helm

```yaml
# values.yaml for mirrord-operator helm chart
operator:
  ...
  metrics: true
  ...
```

### Manual

| env                        | description              | type              | default        |
| -------------------------- | ------------------------ | ----------------- | -------------- |
| OPERATOR\_METRICS\_ENABLED | enable metrics endpoint  | "true" \| "false" | "false"        |
| OPERATOR\_METRICS\_ADDR    | metrics http server addr | SocketAddr        | "0.0.0.0:9000" |

### Exposed metrics

| metric                           | description                                          | labels                                                  | minimum version                  |
| -------------------------------- | ---------------------------------------------------- | ------------------------------------------------------- | ---------------------------------------------------- | 
| mirrord\_license\_valid\_seconds | Seconds until license expiration            |                                                         | operator 3.101.0 (helm chart 1.15.0)|                            
| mirrord\_sessions\_create\_total | Count of created sessions                            | `client_hostname` `client_name` `client_user` `user_id` | operator 3.101.0 (helm chart 1.15.0) |
| mirrord\_sessions\_duration      | Histogram for finished sessions duration | `client_hostname` `client_name` `client_user` `user_id` | operator 3.101.0 (helm chart 1.15.0) | 
| mirrord\_operator\_ping\_latency | Histogram for round trip latency between the mirrord users and the Operator, helps identify infrastructure issues that may affect mirrord performance | `client_hostname` `client_name` `client_user` `user_id`                        | operator 3.122.0 (helm chart 1.35.0) |
| mirrord\_stolen\_connections\_count     | Count of stolen TCP connections | `port` `namespace` `target` `user_id` | operator 3.122.0 (helm chart 1.35.0) |
| mirrord\_stolen\_requests\_count      | Count of stolen HTTP requests | `port` `namespace` `target` `user_id`| operator 3.122.0 (helm chart 1.35.0) |
| mirrord\_read\_sqs\_messages\_count | Count of SQS messages read from `original_queue`  | `original_queue`                                        | operator 3.125.0 (helm chart 1.38.0) |
| mirrord\_sqs\_messages\_forwarded\_to\_user\_count | Count of SQS messages read from `original_queue`, forwarded to the local service of `k8s_user`, `local_username`.  | `k8s_user`, `local_username`, `original_queue` | operator 3.125.0 (helm chart 1.38.0) |
| mirrord\_unmatched\_sqs\_messages\_count | Count of SQS messages read from `original_queue` that weren't matched by any user's filter and were sent to the main output queue for the deployed application. | `original_queue` | operator 3.125.0 (helm chart 1.38.0) |

## OpenTelemetry

{% hint style="info" %}
The features under the "OpenTelemetry" heading require at least operator chart version 1.46.0.
{% endhint %}

### Exporting Logs

To export logs from the operator to an endpoint, set `operator.otelLogExportUrl` to the URL in the Operator Helm chart values. You _must_ set this value to export logs. This value does not affect the logs which are printed by the operator to `stdout` and are always enabled.

The log level is `INFO` by default, and can be changed by setting `operator.otelLogLevel` in the Helm chart values (or alternatively by using the `OTEL_RUST_LOG` environment variable in the Operator container), which takes values in the following format: `mirrord={log_level}` (e.g. `mirrord=debug`).

Note that this log level is separate to that defined for logs controlled by `operator.logLevel`, which are printed by the operator to `stdout`.

### Exporting Traces

To export traces from the operator to an endpoint, set `operator.otelTraceExportUrl` to the URL in the Operator Helm chart values. You _must_ set this value to export traces.

### Context Propagation

{% hint style="info" %}
This feature requires at least mirrord version 3.184.0.
{% endhint %}

You can use the `mirrord.json` file to propagate `traceparent` and `baggage` values to the Operator when running mirrord:

```json
{
  "traceparent": "<trace ID>",
  "baggage": "my_key=my_value,another_key=a_second_value"
}
```

_Note that it is expected that the trace ID value of `traceparent` is not hardcoded, but rather handled and passed in by some wrapper around mirrord. This is because duplicate trace IDs will lead to strange behaviour._

The Operator will propagate these values into exported spans for some frequently used actions, including creating a new resource. Other actions, especially those that result from Kubernetes resource reconciliation, will propagate these values in future versions.

For more info about using `traceparent` and `baggage`, see [the OpenTelemetry docs about context propagation](https://opentelemetry.io/docs/concepts/context-propagation/).

## Pre-Built Dashboards

### DataDog Dashboard

We offer a DataDog dashboard you can import to track statistics.

Download it [here](https://github.com/metalbear-co/docs/tree/main/docs/managing-mirrord/assets/Mirrord_datadog_Operator_Dashboard.json).

### Grafana Dashboard

Alternatively there is a Grafana dashboard you can import to track statistics.

Download it [here](https://github.com/metalbear-co/docs/tree/main/docs/managing-mirrord/assets/Mirrord_grafana_Operator_Dashboard.json).

## fluentd

If you are using fluentd you can add a filter to unpack some values from the "log" message:

```
<filter kubernetes.var.log.containers.**_mirrord_mirrord-operator-**>
  @type parser
  key_name log
  reserve_data true
  remove_key_name_field true
  <parse>
    @type json
  </parse>
</filter>
```

This will expand all the extra fields stored in the "log" field.

### fluentd + Elasticsearch

Assuming you are using `logstash_format true` and the connected mapping will store the extra fields in a `keyword` type, we have a ready made dashboard you can simply import.

Download it [here](https://github.com/metalbear-co/docs/tree/main/docs/managing-mirrord/assets/operator-fluentd-kibana.ndjson) (use Saved Objects to import).
