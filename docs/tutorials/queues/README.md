---
title: Queue and Workflow Tutorials
description: Tutorials that test queue consumers and workflow workers in Kubernetes against a shared staging queue, with mirrord queue splitting and no code changes.
tags:
  - team
  - enterprise
---

# Queue and Workflow Tutorials

These tutorials show how to test a changed consumer against the real queue in a shared staging cluster. Each tutorial deploys a small sample app, starts a mirrord session with a message filter, and shows which messages go to your local process and which go to the deployed consumer.

## The problem that these tutorials solve

A queue does not route a message to a person. When you run a second consumer on a shared queue, the two consumers compete for the messages. Your local consumer gets some of the messages, and your colleagues lose them. When you make a private copy of the queue, you also need a copy of each producer that writes to it.

mirrord queue splitting solves this in the operator. You give a filter, for example a header `x-user: alice`. The operator sends the messages that match the filter to your local consumer, and it sends all other messages to the deployed consumer. Many developers and coding agents can use the same queue at the same time.

Your consumer code does not change. You do not add an SDK, an interceptor, or a routing check to the consumer. The operator makes all the changes, and it removes them when the session ends.

## Tutorials

| System | Tutorial | What the filter matches |
|---|---|---|
| Temporal | [How to Test Temporal Workers](how-to-test-temporal-workers.md) | Workflow ID, workflow type, activity type, Temporal headers, search attributes |
| RabbitMQ | [How to Test RabbitMQ Consumers](how-to-test-rabbitmq-consumers.md) | Message headers, message body (jq) |
| Google Cloud Pub/Sub | [How to Test GCP Pub/Sub Consumers](how-to-test-gcp-pubsub-consumers.md) | Message attributes, message (jq) |
| Redis Pub/Sub | [How to Test Redis Pub/Sub Consumers](how-to-test-redis-pubsub-consumers.md) | Top-level fields of a JSON payload, payload (jq) |
| NATS | [How to Test NATS Consumers](how-to-test-nats-consumers.md) | Message headers, subject and payload (jq) |
| Azure Service Bus | [How to Test Azure Service Bus Consumers](how-to-test-azure-service-bus-consumers.md) | Application properties, message body (jq) |
| BullMQ | [How to Test BullMQ Workers](how-to-test-bullmq-workers.md) | Top-level fields of the job data, job data (jq) |
| Apache Kafka | [How to Debug Kafka Consumers](https://metalbear.com/mirrord/docs/guides/queue-guides/how-to-debug-kafka-consumers) | Message headers, message content (jq) |
| Amazon SQS | [How to Debug SQS Consumers](https://metalbear.com/mirrord/docs/guides/queue-guides/how-to-debug-sqs-consumers) | Message attributes, message body (jq) |

## Before you start

All tutorials need these items:

- A Kubernetes cluster for development or staging, version `1.30` or later. Do not use a production cluster.
- `kubectl`, configured for that cluster.
- The mirrord CLI.
- The mirrord operator, with queue splitting turned on for your queue system. Queue splitting is a mirrord for Teams feature. Each tutorial gives the Helm value that it needs.

## See also

- [Queue splitting overview](../../sharing-the-cluster/queue-splitting.md)
- [Queue splitting status](../../sharing-the-cluster/queue-splitting/status.md)
- [Sessions](../../sharing-the-cluster/sessions.md)
