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

The mirrord Operator can produce logs in JSON format that can be digested by most popular logging solutions (DataDog, Dynatrace, etc). To enable JSON logging, set `operator.jsonLog` to `true` in the Operator Helm chart values. The log level is `INFO` by default, and can be changed using the `RUST_LOG` environment variable in the Operator container, which takes values in the following format: `mirrord={log_level}` (e.g. `mirrord=debug`).

This feature is only relevant for users on the Team and Enterprise pricing plans.

### Functional Logs

The following logs are written with log level `INFO`, and can be used for dashboards within monitoring solutions in order to monitor mirrord usage within your organization:

Log messages:

* Target Copied
* Port Stolen
* Port Mirrored
* Port Released
* Session Started
* Session Ended

Fields:

| field             | description                                                                                                                                                                  | events                                                                         |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| target            | the session's target                                                                                                                                                         | `All`                                                                          |
| client\_hostname  | `whoami::hostname` of client                                                                                                                                                 | `All`                                                                          |
| client\_name      | `whoami::realname` of client                                                                                                                                                 | `All`                                                                          |
| client\_user      | Kubernetes user of client (via k8s RBAC)                                                                                                                                     | `All`                                                                          |
| client\_id        | unique client id produced from client's certificate                                                                                                                          | `All`                                                                          |
| session\_id       | unique id for individual mirrord sessions                                                                                                                                    | `Port Steal` `Port Mirrored` `Port Released` `Session Started` `Session Ended` |
| session\_duration | the session's duration in seconds                                                                                                                                            | `Session Ended`                                                                |
| port              | port number                                                                                                                                                                  | `Port Stolen` `Port Mirrored` `Port Released`                                  |
| http\_filter      | the client's configured [HTTP Filter](https://github.com/RinkiyaKeDad/gitbook-mirrord-docs/blob/main/reference/configuration/README.md#feature-network-incoming-http-filter) | `Port Stolen`                                                                  |
| scale\_down       | whether the session's target was scaled down                                                                                                                                 | `Target Copied`                                                                |

### Prometheus

mirrord Operator can expose prometheus metrics if enabled. (default endpoint is `:9000/metrics`)

#### Helm

```yaml
# values.yaml for mirrord-operator helm chart
operator:
  ...
  metrics: true
  ...
```

#### Manual

| env                        | description              | type              | default        |
| -------------------------- | ------------------------ | ----------------- | -------------- |
| OPERATOR\_METRICS\_ENABLED | enable metrics endpoint  | "true" \| "false" | "false"        |
| OPERATOR\_METRICS\_ADDR    | metrics http server addr | SocketAddr        | "0.0.0.0:9000" |

#### Exposed metrics

| metric                           | description                                          | labels                                                  |
| -------------------------------- | ---------------------------------------------------- | ------------------------------------------------------- |
| mirrord\_license\_valid\_seconds | Seconds left for current license validity            |                                                         |
| mirrord\_sessions\_create\_total | Count of created sessions                            | `client_hostname` `client_name` `client_user` `user_id` |
| mirrord\_sessions\_duration      | Histogram for session durations after they are ended | `client_hostname` `client_name` `client_user` `user_id` |

### DataDog Dashboard

We offer a DataDog dashboard you can import to track statistics.

Download it [here](https://github.com/RinkiyaKeDad/gitbook-mirrord-docs/blob/main/mirrord/datadog/Mirrord_Operator_Dashboard.json)

### Grafana Dashboard

Alternatively there is a Grafana dashboard you can import to track statistics.

Download it [here](https://github.com/RinkiyaKeDad/gitbook-mirrord-docs/blob/main/mirrord/grafana/Mirrord_Operator_Dashboard.json)

### fluentd

If you are using fluentd you can add a filter to unpack some values from the "log" message

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

This will expand all the extra fields stored in "log" field.

#### fluentd + Elasticsearch

Assuming you are using `logstash_format true` and the connected mapping will store the extra fields in a `keyword` type, we have a ready made dashboard you can simply import.

Download it [here](https://github.com/RinkiyaKeDad/gitbook-mirrord-docs/blob/main/mirrord/operator-fluentd-kibana.ndjson) (use Saved Objects to import).
