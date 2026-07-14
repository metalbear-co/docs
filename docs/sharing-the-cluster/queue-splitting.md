---
title: "Queue Splitting"
tags:
  - team
  - enterprise
---
If your application consumes messages from a queue service, you should choose a configuration that matches your intention:

1. Running your application with mirrord without any special configuration will result in your local application competing with the deployed application (and potentially other mirrord runs by teammates) for queue messages.
2. Running your application with [`copy_target` + `scale_down`](../using-mirrord/copy-target.md#replacing-a-whole-deployment-using-scale_down) will result in the deployed application not consuming any messages, and your local application being the exclusive consumer of queue messages.
3. If you want to control which messages will be consumed by the deployed application, and which ones will reach your local application, set up queue splitting for the relevant target, and define a messages filter in the mirrord configuration. Messages that match the filter will reach your local application, and messages that do not, will reach either the deployed application, or another teammate's local application, if they match their filter.

{% hint style="info" %}
Queue splitting is currently available for [Amazon SQS](https://aws.amazon.com/sqs/), [Kafka](https://kafka.apache.org/), [RabbitMQ](https://www.rabbitmq.com), [Google Cloud Pub/Sub](https://cloud.google.com/pubsub), [Azure Service Bus](https://azure.microsoft.com/en-us/products/service-bus), [Redis Pub/Sub](https://redis.io/docs/latest/develop/interact/pubsub/), [Temporal](https://temporal.io), and [BullMQ](https://bullmq.io/).
The word "queue" in this doc is used to also refer to "topic" in the context of Kafka and Azure Service Bus, "subscription" in the context of Google Cloud Pub/Sub, "channel" in the context of Redis Pub/Sub, and "task queue" in the context of Temporal.
{% endhint %}

## Choose your queue service

Setup and configuration differ per queue service. Pick the one you use to see the full guide:

* [Amazon SQS](queue-splitting/sqs.md)
* [Kafka](queue-splitting/kafka.md)
* [RabbitMQ](queue-splitting/rabbitmq.md)
* [Google Cloud Pub/Sub](queue-splitting/gcp-pubsub.md)
* [Azure Service Bus](queue-splitting/azure-service-bus.md)
* [Redis Pub/Sub](queue-splitting/redis-pubsub.md)
* [Temporal](queue-splitting/temporal.md)
* [BullMQ](queue-splitting/bullmq.md)

### How It Works

When a queue splitting session starts, the mirrord operator patches the target workload (e.g. deployment or rollout) to consume messages from a different, temporary queue.
That temporary queue is *exclusive* to the target workload.
Similarly, the local application is reconfigured to consume messages from its own *exclusive* temporary queue.

{% hint style="warning" %}
Queue splitting requires that the application read the queue name from an environment variable.
This lets the operator override the environment variable to change the queue that the application reads from.
{% endhint %}

Once all temporary queues are prepared, the mirrord operator starts consuming messages from the original queue, and publishing them to one of the temporary queues, based on message filters provided by the users in their mirrord configs.

Each queue service has its own way of creating temporary queues and routing messages. The per-service pages above walk through the exact behavior, including the diagrams for the first and second concurrent sessions.

Temporary queues are managed by the mirrord operator and garbage collected in the background. After all queue splitting sessions end, the operator promptly deletes the allocated resources.

Please note that:
1. Temporary queues created for the deployed targets will not be deleted as long as there are any targets' pods that use them.
2. In case of SQS splitting, deployed targets will keep reading from the temporary queues as long as their temporary queues have unconsumed messages.
3. For Google Cloud Pub/Sub, the operator creates temporary topics and subscriptions. The target workload's subscription environment variable is patched to read from a temporary subscription, while the operator drains the original subscription and forwards messages through temporary topics.

## Session Key Header

When your operator has session key header injection enabled, every message the operator routes to your session is stamped with a `mirrord-key` carrying your session key, so your local application can tell which mirrord session a message belongs to. Only the copy delivered to your session is stamped; the message the deployed application receives is never modified.

Where the key is placed depends on the queue service. Services with a metadata channel carry the key there; the rest carry it inside the JSON payload.

| Queue service | Carrier | Location of `mirrord-key` |
| --- | --- | --- |
| Amazon SQS | Metadata | Message attribute |
| Google Cloud Pub/Sub | Metadata | Message attribute |
| RabbitMQ | Metadata | Message header |
| Apache Kafka | Metadata | Message header |
| Azure Service Bus | Metadata | Application property |
| Temporal | Metadata | Activity task header |
| BullMQ | JSON payload | Job `data` object |
| Redis Pub/Sub | JSON payload | Message payload |

For BullMQ and Redis Pub/Sub, where the key lives in the JSON payload itself: a payload that is not a JSON object is forwarded unchanged, and an existing `mirrord-key` in the message is never overwritten.

For Temporal, only the activity task is stamped. Workflow tasks are not, because their header lives in workflow history that the worker replays and validates against the server.

{% hint style="info" %}
Injection is enabled through the `operator.injectSessionKeyHeader` setting in the [mirrord-operator Helm chart](https://github.com/metalbear-co/charts/blob/main/mirrord-operator/values.yaml).
{% endhint %}

{% hint style="info" %}
The key is not injected in copy-target mode. A copy-target session runs against its own dedicated copy of the workload, so no shared consumer needs to tell sessions apart, and messages routed to the copy are delivered unchanged.
{% endhint %}

### Setting a Filter for a mirrord Run

Once cluster setup is done, mirrord users can start running sessions with queue message filters in their mirrord configuration files.
[`feature.split_queues`](https://metalbear.com/mirrord/docs/config/options#feature-split_queues) is the configuration field they need to specify in order to filter queue messages.
It pairs each queue ID with a queue filter definition, and accepts either an object keyed by queue ID or an array of entries (see [One queue or many](#one-queue-or-many)).

Filter definition contains the following fields:
* `queue_type` - `SQS`, `Kafka`, `RMQ`, `GCPPubSub`, `AzureServiceBus`, `RedisPubSub`, `Temporal`, or `BullMQ`
* `queue_mode` - optional, `steal` (default) or `mirror`. In `steal` mode, a matched message goes only to your local application. In `mirror` mode, a matched message goes to your local application **and** is still delivered to the deployed application, so both process a copy. Not supported for `Temporal`.
* `message_filter` - mapping from message attribute (SQS, GCP Pub/Sub), header (Kafka, RabbitMQ), application property (Azure Service Bus), JSON field (Redis Pub/Sub, BullMQ), or task metadata (Temporal) name to a regex for its value.
  The local application will only see queue messages that have **all** of the specified entries matching.
* `jq_filter` - supported for `SQS`, `Kafka`, `GCPPubSub`, `AzureServiceBus`, `RedisPubSub`, `Temporal`, and `BullMQ` queue types.
  * For **SQS**, it runs a jq program on the JSON representation of the SQS [`Message`](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/APIReference/API_Message.html) object.
    For queues configured with `s3_event: "true"`, jq filters can also inspect `S3Metadata`.
    It is populated with user-defined S3 object metadata when the message is parsed as an S3 event
    and metadata is fetched successfully. `S3Metadata` follows the [AWS S3 user-defined metadata format](https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingMetadata.html#UserMetadata):
    a flat key-value map where keys are lowercase strings (without the `x-amz-meta-` prefix) and values are strings.
  * For **Kafka**, it runs a jq program on a JSON representation of the record. See the [Kafka page](queue-splitting/kafka.md#setting-a-filter) for the document shape.
  * For **GCP Pub/Sub**, it runs a jq program on the JSON representation of the [`PubsubMessage`](https://cloud.google.com/pubsub/docs/reference/rest/v1/PubsubMessage) object.
  * For **Azure Service Bus**, the JSON object has `body`, `application_properties`, `message_id`, `content_type`, and `subject` fields.
  * For **Redis Pub/Sub**, it runs a jq program on the parsed JSON message payload.
  * For **Temporal**, it runs a jq program on a JSON document the operator builds for each task. See the [Temporal page](queue-splitting/temporal.md#setting-a-filter) for the document shape.
  * For **BullMQ**, it runs a jq program on the parsed JSON value of the job's `data` field.
  * A message matches if the jq program outputs `true`.

If both `message_filter` and `jq_filter` are specified for the same queue, both must match for a message to be matched.

#### One queue or many

`feature.split_queues` accepts two shapes.

For a single queue, use the **object** form, which maps the queue ID to its queue split config:

```json
{
  "feature": {
    "split_queues": {
      "orders": {
        "queue_type": "SQS",
        "message_filter": { "region": "^eu" }
      }
    }
  }
}
```

For multiple queues, use the **array** form, which moves the ID into each entry as `queue_id`:

```json
{
  "feature": {
    "split_queues": [
      {
        "queue_id": "orders",
        "queue_type": "SQS",
        "message_filter": { "region": "^eu" }
      },
      {
        "queue_id": "notifications",
        "queue_type": "RedisPubSub",
        "message_filter": { "tenant": "^test$" }
      }
    ]
  }
}
```

Both forms take the same filter fields (`queue_type`, `message_filter`, `jq_filter`). Unlike the object form, the array form also lets the **same** queue ID be split on more than one broker, since the ID is not a unique key.

{% hint style="info" %}
When choosing which SQS attributes, Kafka headers or Pub/Sub attributes to filter on, first check whether your framework, messaging client, or observability library already propagates message metadata for you. Many modern stacks can forward tracing-related context out of the box, especially for Kafka headers. Prefer enabling that before adding manual propagation code.
{% endhint %}

{% hint style="info" %}
An empty `message_filter` without a `jq_filter` is treated as a match-none directive.
{% endhint %}

For complete, copy-pasteable filter examples, see the "Setting a filter" section on each queue service page.
