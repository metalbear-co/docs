If your application consumes messages from a queue service, you should choose a configuration that matches your intention:

1. Running your application with mirrord without any special configuration will result in your local application competing with the deployed application (and potentially other mirrord runs by teammates) for queue messages.
2. Running your application with [`copy_target` + `scale_down`](../using-mirrord/copy-target.md#replacing-a-whole-deployment-using-scale_down) will result in the deployed application not consuming any messages, and your local application being the exclusive consumer of queue messages.
3. If you want to control which messages will be consumed by the deployed application, and which ones will reach your local application, set up queue splitting for the relevant target, and define a messages filter in the mirrord configuration. Messages that match the filter will reach your local application, and messages that do not, will reach either the deployed application, or another teammate's local application, if they match their filter.

{% hint style="info" %}
This feature is available to users on the Team and Enterprise pricing plans.
{% endhint %}

{% hint style="info" %}
Queue splitting is currently available for [Amazon SQS](https://aws.amazon.com/sqs/), [Kafka](https://kafka.apache.org/), [RabbitMQ](https://www.rabbitmq.com), [Google Cloud Pub/Sub](https://cloud.google.com/pubsub), [Azure Service Bus](https://azure.microsoft.com/en-us/products/service-bus), [Redis Pub/Sub](https://redis.io/docs/latest/develop/interact/pubsub/), and [Temporal](https://temporal.io).
The word "queue" in this doc is used to also refer to "topic" in the context of Kafka and Azure Service Bus, "subscription" in the context of Google Cloud Pub/Sub, "channel" in the context of Redis Pub/Sub, and "task queue" in the context of Temporal.
{% endhint %}

### Choose your queue service

Setup and configuration differ per queue service. Pick the one you use to see the full guide:

* [Amazon SQS](queue-splitting/sqs.md)
* [Kafka](queue-splitting/kafka.md)
* [RabbitMQ](queue-splitting/rabbitmq.md)
* [Google Cloud Pub/Sub](queue-splitting/gcp-pubsub.md)
* [Azure Service Bus](queue-splitting/azure-service-bus.md)
* [Redis Pub/Sub](queue-splitting/redis-pubsub.md)
* [Temporal](queue-splitting/temporal.md)

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

### Setting a Filter for a mirrord Run

Once cluster setup is done, mirrord users can start running sessions with queue message filters in their mirrord configuration files.
[`feature.split_queues`](https://metalbear.com/mirrord/docs/config/options#feature-split_queues) is the configuration field they need to specify in order to filter queue messages.
Directly under it, mirrord expects a mapping from a queue or queue ID to a queue filter definition.

Filter definition contains the following fields:
* `queue_type` - `SQS`, `Kafka`, `RMQ`, `GCPPubSub`, `AzureServiceBus`, `RedisPubSub`, or `Temporal`
* `message_filter` - mapping from message attribute (SQS, GCP Pub/Sub), header (Kafka, RabbitMQ), application property (Azure Service Bus), JSON field (Redis Pub/Sub), or task metadata (Temporal) name to a regex for its value.
  The local application will only see queue messages that have **all** of the specified entries matching.
* `jq_filter` - supported for `SQS`, `GCPPubSub`, `AzureServiceBus`, `RedisPubSub`, and `Temporal` queue types.
  * For **SQS**, it runs a jq program on the JSON representation of the SQS [`Message`](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/APIReference/API_Message.html) object.
    For queues configured with `s3_event: "true"`, jq filters can also inspect `S3Metadata`.
    It is populated with user-defined S3 object metadata when the message is parsed as an S3 event
    and metadata is fetched successfully. `S3Metadata` follows the [AWS S3 user-defined metadata format](https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingMetadata.html#UserMetadata):
    a flat key-value map where keys are lowercase strings (without the `x-amz-meta-` prefix) and values are strings.
  * For **GCP Pub/Sub**, it runs a jq program on the JSON representation of the [`PubsubMessage`](https://cloud.google.com/pubsub/docs/reference/rest/v1/PubsubMessage) object.
  * For **Azure Service Bus**, the JSON object has `body`, `application_properties`, `message_id`, `content_type`, and `subject` fields.
  * For **Redis Pub/Sub**, it runs a jq program on the parsed JSON message payload.
  * For **Temporal**, it runs a jq program on a JSON document the operator builds for each task. See the [Temporal page](queue-splitting/temporal.md#setting-a-filter) for the document shape.
  * A message matches if the jq program outputs `true`.

If both `message_filter` and `jq_filter` are specified for the same queue, both must match for a message to be matched.

{% hint style="info" %}
When choosing which SQS attributes, Kafka headers or Pub/Sub attributes to filter on, first check whether your framework, messaging client, or observability library already propagates message metadata for you. Many modern stacks can forward tracing-related context out of the box, especially for Kafka headers. Prefer enabling that before adding manual propagation code.
{% endhint %}

{% hint style="info" %}
An empty `message_filter` without a `jq_filter` is treated as a match-none directive.
{% endhint %}

For complete, copy-pasteable filter examples, see the "Setting a filter" section on each queue service page.
