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

If your application consumes messages from a queue service, you should choose a configuration that matches your intention:

1. Running your application with mirrord without any special configuration will result in your local application competing with the remote target (and potentially other mirrord runs by teammates) for queue messages.
2. Running your application with [`copy_target` + `scale_down`](copy-target.md#replacing-a-whole-deployment-using-scale_down) will result in the deployed application not consuming any messages, and your local application being the exclusive consumer of queue messages.
3. If you want to control which messages will be consumed by the deployed application, and which ones will reach your local application, set up queue splitting for the relevant target, and define a messages filter in the mirrord configuration. Messages that match the filter will reach your local application, and messages that do not, will reach either the deployed application, or another teammate's local application, if they match their filter.

{% hint style="info" %}
This feature is only relevant for users on the Team and Enterprise pricing plans.
{% endhint %}

**NOTE:** So far queue splitting is available for [Amazon SQS](https://aws.amazon.com/sqs/) and [Kafka](https://kafka.apache.org/). Pretty soon we'll support RabbitMQ as well.

### How It Works

#### SQS Splitting

When an SQS splitting session starts, the operator changes the target workload to consume messages from a different, temporary queue created by the operator. The operator also creates a temporary queue that the local application reads from.

So if we have a consumer app reading messages from a queue:

![A K8s application that consumes messages from an SQS queue](queue-splitting/before-splitting-sqs.svg)

After a mirrord SQS splitting session starts, the setup will change to this:

![One SQS splitting session](queue-splitting/1-user-sqs.svg)

The operator will consume messages from the original queue, and try to match their attributes with filter defined by the user in the mirrord configuration file (read more in the [last section](queue-splitting.md#setting-a-filter-for-a-mirrord-run)). A message that matches the filter will be sent to the queue consumed by the local application. Other messages will be sent to the queue consumed by the remote application.

And as soon as a second mirrord SQS splitting session starts, the operator will create another temporary queue for the new local app:

![Two SQS splitting sessions](queue-splitting/2-users-sqs.svg)

The users' filters will be matched in the order of the start of their sessions. If filters defined by two users both match a message, the message will go to whichever user started their session first.

After a mirrord session ends, the operator will delete the temporary queue that was created for that session. When all sessions that split a certain queue end, the mirrord Operator will wait for the deployed application to consume the remaining messages in its temporary queue, and then delete that temporary queue as well, and change the deployed application to consume messages back from the original queue.

#### Kafka Splitting

When a Kafka splitting session starts, the operator changes the target workload to consume messages from a different, temporary topic created by the operator in the same Kafka cluster. The operator also creates a temporary topic that the local application reads from.

So if we have a consumer app reading messages from a topic:

![A K8s application that consumes messages from a Kafka topic](queue-splitting/before-splitting-kafka.svg)

After a mirrord Kafka splitting session starts, the setup will change to this:

![One Kafka splitting session](queue-splitting/1-user-kafka.svg)

The operator will consume messages from the original topic (using the same consumer group id as the target workload), and try to match their headers with filter defined by the user in the mirrord configuration file (read more in the [last section](queue-splitting.md#setting-a-filter-for-a-mirrord-run)). A message that matches the filter will be sent to the topic consumed by the local application. Other messages will be sent to the topic consumed by the remote application.

And as soon as a second mirrord Kafka splitting session starts, the operator will create another temporary queue for the new local app:

![Two Kafka splitting sessions](queue-splitting/2-users-kafka.svg)

The users' filters will be matched in the order of the start of their sessions. If filters defined by two users both match a message, the message will go to whichever user started their session first.

After a mirrord session ends, the operator will delete the temporary topic that was created for that session. When all sessions that split a certain topic end, the mirrord Operator will change the deployed application to consume messages back from the original topic and delete the temporary topic as well.

### Getting Started with SQS Splitting

#### Enabling SQS Splitting in Your Cluster

In order to use the SQS splitting feature, some extra values need be provided during the installation of the mirrord Operator.

First of all, the SQS splitting feature needs to be enabled by setting the [`operator.sqsSplitting`](https://github.com/metalbear-co/charts/blob/06efc8666bd26ff7f3a0863333ea4a109aaa6b62/mirrord-operator/values.yaml#L22) [value](https://helm.sh/docs/chart_template_guide/values_files/) to `true` in the [mirrord-operator Helm chart](https://github.com/metalbear-co/charts/tree/main/mirrord-operator).

When SQS splitting is enabled during installation, some additional resources are created, and the SQS component of the mirrord Operator is started.

Additionally, the operator needs to be able to do some operations on SQS queues in your account. For that, an IAM role with an appropriate policy has to be assigned to the operator's service account. Please follow [AWS's documentation on how to do that](https://docs.aws.amazon.com/eks/latest/userguide/associate-service-account-role.html).

Some of the permissions are needed for your actual queues that you would like to split, and some permissions are only needed for the temporary queues the mirrord Operator creates and later deletes. Here is an overview:

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

Here we provide a short explanation for each required permission.

* `sqs:GetQueueUrl`: the operator finds queue names to split in the provided source, and then it fetches the URL from SQS in order to make all other API calls.
* `sqs:GetQueueAttributes`: the operator gives all temporary queues the same attributes as their corresponding original queue, so it needs permission to get the original queue's attributes. It also reads the attributes of temporary queues it created, in order to check how many messages they have approximately.
* `sqs:ListQueueTags`: the operator queries your queue's tags, in order to give all temporary queues that are created for that queue the same tags.
* `sqs:ReceiveMessage`: the mirrord Operator will read messages from queues you want to split.
* `sqs:DeleteMessage`: after reading a message and forwarding it to a temporary queue, the operator deletes it.
* `sqs:CreateQueue`: the mirrord Operator will create temporary queues in your SQS account.
* `sqs:TagQueue`: all the queues mirrord creates will be tagged with all the tags of their respective original queues, plus any tags that are configured for them in the `MirrordWorkloadQueueRegistry` in which they are declared.
* `sqs:SendMessage`: mirrord will send the messages it reads from an original queue to the temporary queue of the client whose filter matches it, or to the temporary queue the deployed application reads from.
* `sqs:DeleteQueue`: when a user session is done, mirrord will delete the temporary queue it created for that session. After all sessions that split a certain queue end, also the temporary queue that is for the deployed application is deleted.

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

    If you would like to limit the second statement with conditions instead of (only) with the resource name, you can [set a condition that requires a tag](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-abac-tagging-resource-control.html), and in the `MirrordWorkloadQueueRegistry` resource you can specify for each queue tags that mirrord will set for temporary queues that it creates for that original queue.

If the queue messages are encrypted, the operator's IAM role should also have the following permissions:

* `kms:Encrypt`
* `kms:Decrypt`
* `kms:GenerateDataKey`

The ARN of the IAM role has to be passed when installing the operator. The ARN is passed via the `sa.roleArn` value in the Helm chart.

#### Permissions for Target Workloads

In order to be targeted with SQS queue splitting, a workload has to be able to read from queues that are created by mirrord.

Any temporary queues created by mirrord are created with the same policy as the original queues they are splitting (with the single change of the queue name in the policy), so if a queue has a policy that allows the target workload to call `ReceiveMessage` on it, that is enough.

However, if the workload gets its access to the queue by an IAM policy (and not an SQS policy, see [SQS docs](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-using-identity-based-policies.html#sqs-using-sqs-and-iam-policies)) that grants access to that specific queue by its exact name, you would have to add a policy that would allow that workload to also read from new temporary queues created by mirrord on the run.

#### Creating a Queue Registry

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

### Getting Started with Kafka Splitting

#### Enabling Kafka Splitting in Your Cluster

In order to use the Kafka splitting feature, some extra values need be provided during the installation of the mirrord Operator.

First of all, the Kafka splitting feature needs to be enabled by setting the [`operator.kafkaSplitting`](https://github.com/metalbear-co/charts/blob/06efc8666bd26ff7f3a0863333ea4a109aaa6b62/mirrord-operator/values.yaml#L24) [value](https://helm.sh/docs/chart_template_guide/values_files/) to `true` in the [mirrord-operator Helm chart](https://github.com/metalbear-co/charts/tree/main/mirrord-operator).

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

### Setting a Filter for a mirrord Run

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

### Troubleshooting SQS splitting

If you're trying to use SQS-splitting and are facing difficulties, here are some steps you can go through to identify
and hopefully solve the problem.

First, some generally applicable steps:

1. Make sure a [`MirrordWorkloadQueueRegistry`](#creating-a-queue-registry) exists for the workload you're targeting:
   ```shell
   kubectl describe mirrordworkloadqueueregistries.queues.mirrord.metalbear.co -n <target-namespace>
   ```
2. Note [the queue-ids in the mirrord configuration](#setting-a-filter-for-a-mirrord-run) have to match the queue-ids in
   the [`MirrordWorkloadQueueRegistry`](#creating-a-queue-registry) of the used target.
3. Get the logs from the mirrord-operator, in case it becomes necessary for the mirrord team
   to look into your issue, e.g. like this:
   ```shell
   kubectl logs -n mirrord -l app==mirrord-operator --tail -1 > /tmp/mirrord-operator-$(date +"%Y-%m-%d_%H-%M-%S").log
   ```
   If that fails, you might not have permissions to the operator's logs.

   To get especially helpful logs, you can change the log level for SQS-splitting, then
   reproduce the issue to get the relevant logs. This can be achieved by reinstalling the helm chart and setting the
   `operator.logLevel` helm value to `mirrord=info,operator=info,operator_sqs_splitting::forwarder=trace`:
   ```shell
   helm upgrade mirrord-operator --reuse-values --set operator.logLevel "mirrord=info,operator=info,operator_sqs_splitting::forwarder=trace" metalbear/mirrord-operator
   ```
   or by setting
   the `RUST_LOG` environment variable in the operator’s deployment to `mirrord=info,operator=info,operator_sqs_splitting::forwarder=trace`,
   e.g. by using `kubectl edit deploy mirrord-operator -n mirrord`.
4. Some operations, like changing a `MirrordWorkloadQueueRegistry` of a workload while there are active sessions to
   that target, are not yet supported, and can lead to a bad state for mirrord. 
   If you've reached such a state:
   1. Delete all the mirrord SQS session resources of the affected target. Those
      resources, `MirrordSqsSession`, are not the same as `MirrordWorkloadQueueRegistry`. You can delete them with:
      ```shell
      kubectl get mirrordsqssessions.queues.mirrord.metalbear.co -n <TARGET-NAMESPACE> -o json \
      | jq -r '.items[] | select(.spec.queueConsumer.name=="<TARGET-WORKLOAD-NAME>" and .spec.queueConsumer.workloadType=="<TARGET-WORKLOAD-TYPE>") | .metadata.name' \     
      | xargs -r -I {} kubectl delete mirrordsqssessions.queues.mirrord.metalbear.co -n <TARGET-NAMESPACE> {}
      ```
   2. Restart the mirrord operator, e.g.:
      ```shell
      kubectl rollout restart deployment mirrord-operator -n mirrord
      ```
   
#### If some (but not all) of the messages that should arrive at the local service arrive at the remote service

It's possible the target workload's restart is not complete yet, and there are still pods reading directly from the
original queue (those will be pods that DO NOT have a `operator.metalbear.co/patched` label). You can wait a bit for
them to be replaced with new pods, patched by mirrord, that read from a temporary queue created by mirrord, or you can
delete them.

#### If all SQS sessions are over but the remote service still didn't change back to read from the original queue

When there are no more queue splitting sessions to a target, the target workload will not immediately be changed to read
directly from the original queue. Instead, it will keep reading from the temporary queue until its empty, so that no
messages intended for the remote service are lost.

If the target workload doesn't change back within the expected time, check its logs and make sure it is consuming queue
messages.

If you don't want to wait for the remote service to drain the temporary queue, and you don't care about losing those
messages, you can set the
[`operator.sqsSplittingLingerTimeout`](https://github.com/metalbear-co/charts/blob/752892998a1145b826e29c6d812b7a08a312c4f5/mirrord-operator/values.yaml#L102-L108)
value in the operator's helm chart, to set a timeout for the draining of the temporary queue.

If that service is trying to consume messages correctly, and the temporary queue is already empty, but the target
application still doesn't get restored to its original state, please try restarting the application, deleting any
lingering `MirrordSqsSession` objects, and if possible, restart the mirrord operator.
