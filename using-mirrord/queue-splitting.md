---
title: Queue Splitting
date: 2024-08-31T13:37:00.000Z
lastmod: 2024-08-31T13:37:00.000Z
draft: false
menu:
  docs:
    parent: using-mirrord
weight: 170
toc: true
tags:
  - team
  - enterprise
description: Sharing queues by splitting messages between multiple clients and the cluster
---

# Queue Splitting

If your application consumes messages from a message broker (e.g. Kafka cluster), you should choose a configuration that matches your intention:

1. If you're ok with your local application competing for queue messages with the remote target, and with your teammates' mirrord sessions — run the application with mirrord without any special configuration.
2. If you want your local application to be an exclusive consumer of queue messages — run the application with [`copy_target` + `scale_down`](copy-target.md#replacing-a-whole-deployment-using-scale_down) features.
3. If you want to precisely control which messages will be consumed by your local application — run the application with the queue splitting feature. The allows you define a message filter in your mirrord configuration. All messages matching that filter will be redirected by the mirrord operator to your local application. Other messages will **not** reach your local application. 

{% hint style="info" %}
This feature is only relevant for users on the Team and Enterprise pricing plans.
{% endhint %}

{% hint style="info" %}
So far queue splitting is available for [Amazon SQS](https://aws.amazon.com/sqs/) and [Kafka](https://kafka.apache.org/). Pretty soon we'll support RabbitMQ as well.
{% endhint %}

## How It Works

When a Kafka splitting session starts, the mirrord operator patches the target workload (e.g. deployment or rollout) to consume messages from a different, temporary queue or topic.
That temporary queue/topic is *exclusive* to the target workload, and its name is randomized.
Similarly, the local application is redirected to consume messages from its own *exclusive* temporary queue or topic.

{% hint style="warning" %}
In both cases, the redirections are done by manipulating environment variables.
For this reason, queue splitting always requires that the application reads queue or topic name from environment variables.
This is a prerequisite.
{% endhint %}

Once all temporary topics or queues are prepared, the mirrord operator starts consuming messages from the original queue or topic, and publishing them to the correct temporary one.
This routing is based on message filters provided by the users in their mirrord configs.

{% tabs %}

{% tab title="Amazon SQS" %}

First, we have a consumer app reading messages from an SQS queue:

![A K8s application that consumes messages from an SQS queue](queue-splitting/before-splitting-sqs.svg)

Then, the first mirrord SQS splitting session starts. Two temporary queues are created (one for the target deployed in the cluster, one for the user's local application),
and the mirrord operator routes messages according to the user's filter (read more in the [last section](queue-splitting.md#setting-a-filter-for-a-mirrord-run)):

![One SQS splitting session](queue-splitting/1-user-sqs.svg)

Then, another mirrord SQS splitting session starts. The third temporary queue is created (for the second user's local application).
The mirrord operator includes the new queue and the second user's filter in the routing logic.

![Two SQS splitting sessions](queue-splitting/2-users-sqs.svg)

If the filters defined by the two users both match some message, it is not defined which one of the users will receive that message.

{% endtab %}

{% tab title="Kafka" %}

First, we have a consumer app reading messages from a Kafka topic:

![A K8s application that consumes messages from a Kafka topic](queue-splitting/before-splitting-kafka.svg)

Then, the first mirrord Kafka splitting session starts. Two temporary topics are created (one for the target deployed in the cluster, one for the user's local application),
and the mirrord operator routes messages according to the user's filter (read more in the [last section](queue-splitting.md#setting-a-filter-for-a-mirrord-run)):

![One Kafka splitting session](queue-splitting/1-user-kafka.svg)

Then, another mirrord Kafka splitting session starts. The third temporary topic is created (for the second user's local application).
The mirrord operator includes the new topic and the second user's filter in the routing logic.

![Two Kafka splitting sessions](queue-splitting/2-users-kafka.svg)

If the filters defined by the two users both match some message, it is not defined which one of the users will receive that message.

{% endtab %}

{% endtabs %}

Temporary queues and topics are managed by the mirrord operator and garbage collected in the background. After all queue splitting sessions end, the operator promptly deletes the allocated resources.

Plese note that:
1. Temporary queues and topics created for the deployed targets will not be deleted as long as there are any targets' pods that use them.
2. In case of SQS splitting, deployed targets will remain redirected as long as their temporary queues have unconsumed messages.


## Enabling SQS Splitting in Your Cluster

{% stepper %}
{% step %}

### Enable SQS splitting in the Helm chart

Enable the `operator.sqsSplitting` setting in the [mirrord-operator Helm chart](https://github.com/metalbear-co/charts/blob/main/mirrord-operator/values.yaml).

{% endstep %}
{% step %}

### Authenticate and authorize the mirrord operator with SQS

The mirrord operator will need to be able to do some operations on the SQS queues on your behalf.
To do this, it will build an SQS client, using the default credentials provider chain.

The easiest way to provide the crendentials for the operator is with IAM role assumption.
For that, an IAM role with an appropriate policy has to be assigned to the operator's service account. Please follow [AWS's documentation on how to do that](https://docs.aws.amazon.com/eks/latest/userguide/associate-service-account-role.html). Note that operator's service account can be annotated with the IAM role's ARN with the `sa.roleArn` setting in the [mirrord-operator Helm chart](https://github.com/metalbear-co/charts/blob/main/mirrord-operator/values.yaml).

Some of the SQS permissions are needed for your actual queues that you would like to split, and some permissions are only needed for the temporary queues, managed by the operator.
Here is an overview:

| SQS Permission     | needed for your queues | needed for temporary queues |
| ------------------ | :--------------------: | :-------------------------: |
| GetQueueUrl        |            ✓           |                             |
| ListQueueTags      |            ✓           |                             |
| ReceiveMessage     |            ✓           |                             |
| DeleteMessage      |            ✓           |                             |
| GetQueueAttributes |            ✓           |          ✓ (both!)          |
| CreateQueue        |                        |              ✓              |
| TagQueue           |                        |              ✓              |
| SendMessage        |                        |              ✓              |
| DeleteQueue        |                        |              ✓              |

And here we provide a short explanation for each required permission:

* `sqs:GetQueueUrl`: the operator finds queue names to split in the provided source, and then it fetches the URL from SQS in order to make other API calls.
* `sqs:GetQueueAttributes`: the operator queries your queue's attributes, in order to clone these attributes to all derived temporary queues. It also reads the attributes of the temporary queues, in order to check the number of remaining messages.
* `sqs:ListQueueTags`: the operator queries your queue's tags, in order to clone these tags to all derived temporary queues.
* `sqs:ReceiveMessage`: the operator reads messages from the queues you split.
* `sqs:DeleteMessage`: after reading a message and forwarding it to a temporary queue, the operator deletes the message from the split queue.
* `sqs:CreateQueue`: the operator creates temporary queues in your SQS account.
* `sqs:TagQueue`: the operator sets tags on the temporary queues.
* `sqs:SendMessage`: the operator sends messages to the temporary queues.
* `sqs:DeleteQueue`: the operator deletes stale temporary queues in the background.

This is an example for a policy that gives the operator's roles the minimal permissions it needs to split a queue called `ClientUploads`:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "sqs:GetQueueUrl",
                "sqs:GetQueueAttributes",
                "sqs:ListQueueTags",
                "sqs:ReceiveMessage",
                "sqs:DeleteMessage"
            ],
            "Resource": [
                "arn:aws:sqs:eu-north-1:314159265359:ClientUploads"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "sqs:CreateQueue",
                "sqs:TagQueue",
                "sqs:SendMessage",
                "sqs:GetQueueAttributes",
                "sqs:DeleteQueue"
            ],
            "Resource": "arn:aws:sqs:eu-north-1:314159265359:mirrord-*"
        }
    ]
}
```

*   The first statement gives the role the permissions it needs for your original queues.

    Instead of specifying the queues you would like to be able to split in the first statement, you could alternatively make that statement apply for all resources in the account, and limit the queues it applies to using conditions instead of resource names. For example, you could add a condition that makes the statement only apply to queues with the tag `splittable=true` or `env=dev` etc. and set those tags for all queues you would like to allow the operator to split.
*   The second statement in the example gives the role the permissions it needs for the temporary queues. Since all the temporary queues created by mirrord are created with the name prefix `mirrord-`, that statement in the example is limited to resources with that prefix in their name.

    If you would like to limit the second statement with conditions instead of (only) with the resource name, you can [set a condition that requires a tag](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-abac-tagging-resource-control.html), and in the `MirrordWorkloadQueueRegistry` resource you can specify for each queue tags that mirrord will set for temporary queues that it creates for that original queue (see [relevant section](queue-splitting.md#create-the-queue-registry)).

If the queue messages are encrypted, the operator's IAM role should also have the following permissions:

* `kms:Encrypt`
* `kms:Decrypt`
* `kms:GenerateDataKey`

{% endstep %}
{% step %}

### Authorize deployed consumers

In order to be targeted with SQS splitting, a deployed consumer must be able to use the temporary queues created by mirrord.
E.g. if the consumer application retrieves the queue's URL based on its name, lists queue's tags, consumes and deletes messages from the queue — it must be able to do the same on a temporary queue.

Any temporary queues managed by mirrord are created with the same policy as the original queues they are splitting (with the single change of updating the queue name in the policy).
Therefore, access control based on SQS policies should automatically be taken care of.

However, if the consumer's access to the queue is controlled by an IAM policy (and not an SQS policy, see [SQS docs](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-using-identity-based-policies.html#sqs-using-sqs-and-iam-policies)), you will need to adjust it.

{% endstep %}
{% step %}

### Create the queue registry

On operator installation, a new [`CustomResources`](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/) type was created on your cluster: `MirrordWorkloadQueueRegistry`. Users with permissions to get CRDs, can verify its existence with `kubectl get crd mirrordworkloadqueueregistries.queues.mirrord.metalbear.co`. After an SQS-enabled operator is installed, and before you can start splitting queues, a resource of that type must be created for the target you want to run against, in the target's namespace.

Below we have an example for such a resource, for a meme app that consumes messages from two queues:

```yaml
apiVersion: queues.mirrord.metalbear.co/v1alpha
kind: MirrordWorkloadQueueRegistry
metadata:
  name: meme-app-q-registry
spec:
  queues:
    meme-queue:
      queueType: SQS
      nameSource:
        envVar: INCOMING_MEME_QUEUE_NAME
      tags:
        tool: mirrord
    ad-queue:
      queueType: SQS
      nameSource:
        envVar: AD_QUEUE_NAME
      tags:
        tool: mirrord
  consumer:
    name: meme-app
    container: main
    workloadType: Deployment
```

* `spec.queues` holds queues that should be split when running mirrord with this target. It is a mapping from a queue ID to the details of the queue.
  * The queue ID is chosen by you, and will be used by every teammate who wishes to filter messages from this queue. You can choose any string for that, it does not have to be the same as the name of the queue. In the example above the first queue has the queue id `meme-queue` and the second one `ad-queue`.
  * `nameSource` tells mirrord where the app finds the name of this queue.
    * Currently `envVar` is the only supported source for the queue name. The value of `envVar` is the name of the
      environment variable the app reads the queue name from. That environment variable could be one that has a value
      directly in the spec, or it could get its value from a ConfigMap via `valueFrom` or `envFrom`. It is crucial that
      both the local and the deployed app use the queue name they find in that environment variable. mirrord changes the
      value of that environment variable in order to make the application read from a temporary queue it creates.
  * `tags` is an optional field where you can specify queue tags that should be added to all temporary queues mirrord creates for splitting this queue.
* `spec.consumer` is the workload that consumes these queues. The queues specified above will be split whenever that workload is targeted.
  * `container` is optional, when set - this queue registry only applies to runs that target that container.

{% endstep %}
{% endstepper %}

## Enabling Kafka Splitting in Your Cluster

In order to use the Kafka splitting feature, some extra values need be provided during the installation of the mirrord Operator.

First of all, the Kafka splitting feature needs to be enabled:

* When installing with the [mirrord-operator Helm chart](https://github.com/metalbear-co/charts/tree/main/mirrord-operator) it is enabled by setting the [`operator.kafkaSplitting`](https://github.com/metalbear-co/charts/blob/06efc8666bd26ff7f3a0863333ea4a109aaa6b62/mirrord-operator/values.yaml#L24) [value](https://helm.sh/docs/chart_template_guide/values_files/) to `true`.
* When installing via the `mirrord operator setup` command, set the `--kafka-splitting` flag.

When Kafka splitting is enabled during installation, some additional resources are created, and the Kafka component of the mirrord Operator is started.

#### Configuring Kafka Splitting with Custom Resources

On operator installation, new [`CustomResources`](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/) types were created on your cluster: `MirrordKafkaTopicsConsumer` and `MirrordKafkaClientConfig`. Users with permissions to get CRDs, can verify their existence with `kubectl get crd mirrordkafkatopicsconsumers.queues.mirrord.metalbear.co` and `kubectl get crd mirrordkafkaclientconfigs.queues.mirrord.metalbear.co`.

After a Kafka-enabled operator is installed, and before you can start splitting queues, resources of these types must be created.

1. `MirrordKafkaTopicsConsumer` is a resource that must be created in the same namespace as the target workload. It describes Kafka topics that this workload consumes and contains instructions for the mirrord Operator on how to execture splitting. Each `MirrordKafkaTopicsConsumer` is linked to a single workload that can be targeted with a Kafka splitting session.
2. `MirrordKafkaClientConfig` is a resource that must be created in the namespace where mirrord operator is installed. It contains properties that the operator will use when creating a Kafka client used for all Kafka operations during the split. This resource is referenced by `MirrordKafkaTopicsConsumer`.

**`MirrordKafkaTopicsConsumer`**

Below we have an example for `MirrordKafkaTopicsConsumer` resource, for a meme app that consumes messages from a Kafka topic:

```yaml
apiVersion: queues.mirrord.metalbear.co/v1alpha
kind: MirrordKafkaTopicsConsumer
metadata:
  name: meme-app-topics-consumer
spec:
  consumerApiVersion: apps/v1
  consumerKind: Deployment
  consumerName: meme-app
  topics:
  - id: views-topic
    clientConfig: base-config
    groupIdSources:
    - directEnvVar:
        container: consumer
        variable: KAFKA_GROUP_ID
    nameSources:
    - directEnvVar:
        container: consumer
        variable: KAFKA_TOPIC_NAME
```

* `spec.topics` is a list of topics that can be split when running mirrord with this target.
  * The topic ID is chosen by you, and will be used by every teammate who wishes to filter messages from this topic. You can choose any string for that, it does not have to be the same as the name of the queue. In the example above the topic has id `views-topic`.
  * `clientConfig` is the name of the `MirrordKafkaClientConfig` resource living in the mirrord Operator's namespace that will be used when interacting with the Kafka cluster.
  *   `groupIdSources` holds a list of all occurences of Kafka consumer group id in the workload's pod spec. mirrord Operator will use this group id when consuming messages from the topic.

      Currently the only supported source type is an environment variable with value defined directly in the pod spec.
  *   `nameSources` holds a list of all occurences of topic name in the workload's pod spec. mirrord Operator will use this name when consuming messages. It is crucial that both the local and deployed app take topic name from these sources, as mirrord Operator will use them to inject the names of temporary topics.

      Currently the only supported source type is an environment variable with value defined directly in the pod spec.

**`MirrordKafkaClientConfig`**

Below we have an example for `MirrordKafkaClientConfig` resource:

```yaml
apiVersion: queues.mirrord.metalbear.co/v1alpha
kind: MirrordKafkaClientConfig
metadata:
  name: base-config
  namespace: mirrord
spec:
  properties:
  - name: bootstrap.servers
    value: kafka.default.svc.cluster.local:9092
```

When used by the mirrord Operator for Kafka splitting, the example below will be resolved to following `.properties` file:

```properties
bootstrap.servers=kafka.default.svc.cluster.local:9092
```

This file will be used when creating a Kafka client for managing temporary topics, consuming messages from the original topic and producing messages to the temporary topics. Full list of available properties can be found [here](https://github.com/confluentinc/librdkafka/blob/master/CONFIGURATION.md).

> _**NOTE:**_ `group.id` property will always be overwritten by mirrord Operator when resolving the `.properties` file.

`MirrordKafkaClientConfig` resource supports property inheritance via `spec.parent` field. When resolving a resource `X` that has parent `Y`:

1. `Y` is resolved into a `.properties` file.
2. For each property defined in `X`:
   * If `value` is provided, it overrides any previous value of that property
   * If `value` is not provided (`null`), that property is removed

Below we have an example of two `MirrordKafkaClientConfig`s with inheritance relation:

```yaml
apiVersion: queues.mirrord.metalbear.co/v1alpha
kind: MirrordKafkaClientConfig
metadata:
  name: base-config
  namespace: mirrord
spec:
  properties:
  - name: bootstrap.servers
    value: kafka.default.svc.cluster.local:9092
  - name: message.send.max.retries
    value: 4
```

```yaml
apiVersion: queues.mirrord.metalbear.co/v1alpha
kind: MirrordKafkaClientConfig
metadata:
  name: with-client-id
  namespace: mirrord
spec:
  parent: base-config
  properties:
  - name: client.id
    value: mirrord-operator
  - name: message.send.max.retries
    value: null
```

When used by the mirrord Operator for Kafka splitting, the `with-client-id` below will be resolved to following `.properties` file:

```properties
bootstrap.servers=kafka.default.svc.cluster.local:9092
client.id=mirrord-operator
```

`MirrordKafkaClientConfig` also supports setting properties from a Kubernetes [`Secret`](https://kubernetes.io/docs/concepts/configuration/secret/) with the `spec.loadFromSecret` field. The value for `loadFromSecret` is given in the form: `<secret-namespace>/<secret-name>`.

Each key-value entry defined in secret's data will be included in the resulting `.properties` file. Property inheritance from the parent still occurs, and within each `MirrordKafkaClientConfig` properties loaded from the secret are overwritten by those in `properties`.

This means the priority of setting properties (from highest to lowest) is like so:

* `childProperty`
* `childSecret`
* `parentProperty`
* `parentSecret`

Below is an example for a `MirrordKafkaClientConfig` resource that references a secret:

```yaml
apiVersion: queues.mirrord.metalbear.co/v1alpha
kind: MirrordKafkaClientConfig
metadata:
  name: base-config
  namespace: mirrord
spec:
  loadFromSecret: mirrord/my-secret
  properties: []
```

For additional authentication configuration, here is an example of a `MirrordKafkaClientConfig` resource that supports IAM/OAUTHBEARER authentication with Amazon Managed Streaming for Apache Kafka:

```yaml
apiVersion: queues.mirrord.metalbear.co/v1alpha
kind: MirrordKafkaClientConfig
metadata:
  name: base-config
  namespace: mirrord
spec:
  authenticationExtra:
    awsRegion: eu-south-1
    kind: MSK_IAM
  properties: []
```

Currently, `MSK_IAM` is the only supported value for `spec.authenticationExtra.kind`.
When this kind is specified, additional properties are automatically merged into the configuration:
1. `sasl.mechanism=OAUTHBEARER`
2. `security.protocol=SASL_SSL`

> _**NOTE:**_ By default, the operator will only have access to secrets in its own namespace (`mirrord` by default).

#### Customizing mirrord created Kafka Topic Names

> _**NOTE:**_ Available since chart version `1.27` and operator version 3.114.0

To serve Kafka splitting sessions, mirrord Operator creates temporary topics in the Kafka cluster. The default format for their names is as follows:

* `mirrord-tmp-1234567890-fallback-topic-original-topic` - for the fallback topic (unfiltered messages, consumed by the deployed workload).
* `mirrord-tmp-9183298231-original-topic` - for the user topics (filtered messages, consumed by local applications running with mirrord).

Note that the random digits will be unique for each temporary topic created by the mirrord Operator.

You can adjust the format of the created topic names to suit your needs (RBAC, Security, Policies, etc.), using the `OPERATOR_KAFKA_SPLITTING_TOPIC_FORMAT` environment variable of the mirrord Operator, or `operator.kafkaSplittingTopicFormat` helm chart value. The default value is:

`mirrord-tmp-{{RANDOM}}{{FALLBACK}}{{ORIGINAL_TOPIC}}`

The provided format must contain the three variables: `{{RANDOM}}`, `{{FALLBACK}}` and `{{ORIGINAL_TOPIC}}`.

* `{{RANDOM}}` will resolve to random digits.
* `{{FALLBACK}}` will resolve either to `-fallback-` or `-` literal.
* `{{ORIGINAL_TOPIC}}` will resolve to the name of the original topic that is being split.

## Setting a Filter for a mirrord Run

Once everything else is set, you can start using message filters in your mirrord configuration file. Below is an example for what such a configuration might look like:

```json
{
    "operator": true,
    "target": "deployment/meme-app/main",
    "feature": {
        "split_queues": {
            "meme-queue": {
                "queue_type": "SQS",
                "message_filter": {
                    "author": "^me$",
                    "level": "^(beginner|intermediate)$"
                }
            },
            "ad-queue": {
                "queue_type": "SQS",
                "message_filter": {}
            },
            "views-topic": {
                "queue_type": "Kafka",
                "message_filter": {
                    "author": "^me$",
                    "source": "^my-session-"
                }
            }
        }
    }
}
```

* [`feature.split_queues`](https://app.gitbook.com/s/Z7vBpFMZTH8vUGJBGRZ4/options#feature.split_queues) is the configuration field you need to specify in order to filter queue messages. Directly under it, we have a mapping from a queue or topic ID to a queue filter definition.
  * Queue or topic ID is the ID that was set in the [SQS queue registry resource](queue-splitting.md#creating-a-queue-registry) or [Kafka topics consumer resource](queue-splitting.md#creating-a-topics-registry).
  *   `message_filter` is a mapping from message attribute (SQS) or header (Kafka) names to message attribute or header value regexes. Your local application will only see queue messages that have **all** of the specified message attributes or headers.

      Empty `message_filter` is treated as a match-none directive.

In the example above, the local application:

* Will receive a subset of messages from SQS queue with ID `meme-queue`. All received messages will have an attribute `author` with the value `me`, AND an attribute `level` with value either `beginner` or `intermediate`.
* Will receive a subset of messages from Kafka topic with ID `views-topic`. All received messages will have an attribute `author` with the value `me`, AND an attribute `source` with value starting with `my-session-` (e.g `my-session-844cb78789-2fmsw`).
* Will receive no messages from SQS queue with id `ad-queue`.

Once all users stop filtering a queue (i.e. end their mirrord sessions), the temporary queues (SQS) and topics (Kafka) that mirrord operator created will be deleted.
