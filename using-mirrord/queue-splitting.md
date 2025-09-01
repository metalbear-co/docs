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

1. Running your application with mirrord without any special configuration will result in your local application competing with the deployed application (and potentially other mirrord runs by teammates) for queue messages.
2. Running your application with [`copy_target` + `scale_down`](copy-target.md#replacing-a-whole-deployment-using-scale_down) will result in the deployed application not consuming any messages, and your local application being the exclusive consumer of queue messages.
3. If you want to control which messages will be consumed by the deployed application, and which ones will reach your local application, set up queue splitting for the relevant target, and define a messages filter in the mirrord configuration. Messages that match the filter will reach your local application, and messages that do not, will reach either the deployed application, or another teammate's local application, if they match their filter.

{% hint style="info" %}
This feature is only available for users on the Team and Enterprise pricing plans.
{% endhint %}

{% hint style="info" %}
Queue splitting is currently available for [Amazon SQS](https://aws.amazon.com/sqs/) and [Kafka](https://kafka.apache.org/). Pretty soon we'll support RabbitMQ as well.
{% endhint %}

## How It Works

When a queue splitting session starts, the mirrord operator patches the target workload (e.g. deployment or rollout) to consume messages from a different, temporary queue or topic.
That temporary queue/topic is *exclusive* to the target workload.
Similarly, the local application is reconfigured to consume messages from its own *exclusive* temporary queue or topic.

{% hint style="warning" %}
In both cases, the redirections are done by manipulating environment variables.
For this reason, queue splitting always requires that the application reads the queue or topic name from environment variables.
{% endhint %}

Once all temporary topics or queues are prepared, the mirrord operator starts consuming messages from the original queue or topic, and publishing them to one of the temporary queues, based on message filters provided by the users in their mirrord configs.
This routing is based on message filters provided by the users in their mirrord configs.

{% tabs %}

{% tab title="Amazon SQS" %}

First, we have a consumer app reading messages from an SQS queue:

![A K8s application that consumes messages from an SQS queue](queue-splitting/before-splitting-sqs.svg)

When the first mirrord SQS splitting session starts, two temporary queues are created (one for the target deployed in the cluster, one for the user's local application),
and the mirrord operator routes messages according to the user's filter (read more in the [last section](queue-splitting.md#setting-a-filter-for-a-mirrord-run)):

![One SQS splitting session](queue-splitting/1-user-sqs.svg)

If a second user then starts a mirrord SQS splitting session on the same queue, a the third temporary queue is created (for the second user's local application).
The mirrord operator includes the new queue and the second user's filter in the routing logic.

![Two SQS splitting sessions](queue-splitting/2-users-sqs.svg)

If the filters defined by the two users both match some message, one of the users will receive the message at random.

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

### Authenticate and authorize the mirrord operator

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

### Provide application context

On operator installation with `operator.sqsSplitting` enabled, a new [`CustomResource`](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/)
type is defined in your cluster — `MirrordWorkloadQueueRegistry`. Users with permissions to get CRDs can verify its existence
with `kubectl get crd mirrordworkloadqueueregistries.queues.mirrord.metalbear.co`.
Before you can run sessions with SQS splitting, you must create a queue registry for the desired target.
This is because the queue registry contains additional application context required by the mirrord operator.
For example, the operator needs to know which environment variables contain the names of the SQS queues to split.

See an example queue registry defined for a deployment `meme-app` living in namespace `meme`:

```yaml
apiVersion: queues.mirrord.metalbear.co/v1alpha
kind: MirrordWorkloadQueueRegistry
metadata:
  name: meme-app-q-registry
  namespace: meme
spec:
  consumer:
    name: meme-app
    workloadType: Deployment
    container: main
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
```

The registry above says that:
1. It provides context for container `main` running in deployment `meme-app` in namespace `meme`.
2. The container consumes two SQS queues. Their names are read from environment variables `INCOMING_MEME_QUEUE_NAME` and `AD_QUEUE_NAME`.
3. The SQS queues can be referenced in a mirrord config under IDs `meme-queue` and `ad-queue`, respectively.
4. When creating a temporary queue derived from either of the two queues, mirrord operator should add the tag `tool=mirrord`.

#### Link the registry to the deployed consumer

The queue registry is a namespaced resource, so it can only reference a consumer deployed in the same namespace.
The reference is specified with `spec.consumer`:
* `name` — name of the Kubernetes workload of the deployed consumer.
* `workloadType` — type of the Kubernetes workload of the deployed consumer. Right now only consumers deployed in deployments and rollouts are supported.
* `container` — name of the exact container running in the workload. This field is optional. If you omit it, the registry will reference all of the workload's containers.

#### Desribe consumed queues in the registry

The queue registry describes SQS queues consumed by the referenced consumer.
The queues are described in entries of the `spec.queues` object.

The entry's key can be arbitrary, as it will only be referenced from the user's mirrord config
(compare with the [last section](queue-splitting.md#setting-a-filter-for-a-mirrord-run)).

The entry's value is an object describing single or multiple SQS queues consumed by the workload:

* `nameSource` describes which environment variables contain names/URLs of the consumed queues. Either `envVar` or `regexPattern` field is required.
  * `envVar` stores a name of a single environment variables.
  * `regexPattern` selects multiple environment variables based on a regular expression.
* `fallbackName` stores an optional fallback name/URL, in case `nameSource` is not found in the workload spec.
  `nameSource` will still be used to inject the name/URL of the temporary queue.
* `namesFromJsonMap` specifies how to process the values of environment variables that contain queue names/URLs.
  If set to `true`, values of all variables of will be parsed as JSON objects with string values. All values in these objects will be treated as queue names/URLs.
  If set to `false`, values of all variables will be treated directly as queue names/URLs.
  Defaults to `false`.
* `tags` specifies additional tags to be set on all created temporary queues.
* `sns` specifies whether the queues contains SQS messages created from SNS notifications.
  If set to `true`, message bodies will be parsed and matched against users' filters,
  as SNS notification attributes are found in the SQS message body.
  If set to `false`, message attributes will be used matched against users' filters.
  Defaults to `false`.

{% hint style="warning" %}
The mirrord operator can only read consumer's environment variables if they are either:
1. defined directly in the workload's pod template, with the value defined in `value` or in `valueFrom` via config map reference; or
2. loaded from config maps using `envFrom`.
{% endhint %}

{% endstep %}
{% endstepper %}

## Enabling Kafka Splitting in Your Cluster

{% stepper %}
{% step %}

### Enable Kafka splitting in the Helm chart

Enable the `operator.kafkaSplitting` setting in the [mirrord-operator Helm chart](https://github.com/metalbear-co/charts/blob/main/mirrord-operator/values.yaml).

{% endstep %}
{% step %}

### Configure the operator's Kafka client

The mirrord operator will need to be able to do some operations on the Kafka cluster on your behalf.
To allow for properly configuring the operator's Kafka client, on operator installation with `operator.kafkaSplitting` enabled,
a new [`CustomResource`](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/) type is defined in your cluster
— `MirrordKafkaClientConfig`. Users with permissions to get CRDs can verify its existence with `kubectl get crd mirrordkafkaclientconfigs.queues.mirrord.metalbear.co`.

The resource allows for specifying a list of properties for the Kafka client, like this:

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
  - name: client.id
    value: mirrord-operator
```

When used by the mirrord Operator for Kafka splitting, the example below will be resolved to following `.properties` file:

```properties
bootstrap.servers=kafka.default.svc.cluster.local:9092
client.id=mirrord-operator
```

This file will be used when creating a Kafka client for managing temporary topics, consuming messages from the original topic and producing messages to the temporary topics. Full list of available properties can be found [here](https://github.com/confluentinc/librdkafka/blob/master/CONFIGURATION.md).

{% hint style="info" %}
`group.id` property will always be overwritten by mirrord Operator when resolving the `.properties` file.
{% endhint %}

{% hint style="warning" %}
`MirrordKafkaClientConfig` resources must always be created in the operator's namespace.
{% endhint %}

See [additional options](queue-splitting.md#additional-options) section for more Kafka configuration info.

{% endstep %}
{% step %}

### Authorize deployed consumers

In order to be targeted with Kafka splitting, a deployed consumer must be able to use the temporary topics created by mirrord.
E.g. if the consumer application describes the topic or reads messages from it — it must be able to do the same on a temporary topic.
This might require extra actions on your side to adjust the authorization, for example based on topic name prefix. See [topic names](queue-splitting.md#customizing-temporary-kafka-topic-names) section for more info.

{% endstep %}
{% step %}

### Provide application context

On operator installation with `operator.kafkaSplitting` enabled,
a new [`CustomResource`](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/) type is defined in your cluster
— `MirrordKafkaTopicsConsumer`. Users with permissions to get CRDs can verify its existence with `kubectl get crd mirrordkafkatopicsconsumers.queues.mirrord.metalbear.co`.
Before you can run sessions with Kafka splitting, you must create a topics consumer resource for the desired target.
This is because the topics consumer resource contains additional application context required by the mirrord operator.
For example, the operator needs to know which environment variables contain the names of the Kafka topics to split.

See an example topics consumer resource, for a meme app that consumes messages from a Kafka topic:

```yaml
apiVersion: queues.mirrord.metalbear.co/v1alpha
kind: MirrordKafkaTopicsConsumer
metadata:
  name: meme-app-topics-consumer
  namespace: meme
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

The topics consumer resource above says that:
1. It provides context for deployment `meme-app` in namespace `meme`.
2. The deployment consumes one topic. Its name is read from environment variable `KAFKA_TOPIC_NAME` in container `consumer`.
The Kafka consumer group id is read from environment variable `KAFKA_GROUP_ID` in container `consumer`.
3. The Kafka topic can be referenced in a mirrord config under ID `views-topic`.

#### Link the topics consumer resource to the deployed consumer

The topics consumer resource is namespaced, so it can only reference a Kafka consumer deployed in the same namespace.
The reference is specified with `spec.consumer*` fields, which cover api version, kind, and name of the Kubernetes workload.
For instance to configure Kafka splitting of a consumer deployed in a stateful set `kafka-notifications-worker`, you would set:

```yaml
consumerApiVersion: apps/v1
consumerKind: StatefulSet
consumerName: kafka-notifications-worker
```

The operator supports Kafka splitting on deployments, stateful sets, and Argo rollouts.

#### Desribe consumed topics in the topics consumer resource

The topics consumer resource describes Kafka topics consumed by the referenced consumer.
The topics are described in entries of the `spec.topics` list:
* `id` can be arbitrary, as it will only be referenced from the user's mirrord config
(compare with the [last section](queue-splitting.md#setting-a-filter-for-a-mirrord-run)).
* `clientConfig` stores the name of the `MirrordKafkaClientConfig` to use when making connections to the Kafka cluster.
* `nameSources` stores a list of all occurences of the topic name in the consumer workload's pod template.
* `groupIdSources` stores a list of all occurences of the consumer Kafka group ID in the consumer workload's pod template.
The operator will use the same group ID when consuming messages from the topic.

{% hint style="warning" %}
The mirrord operator can only read consumer's environment variables if they are either:
1. defined directly in the workload's pod template, with the value defined in `value` or in `valueFrom` via config map reference; or
2. loaded from config maps using `envFrom`.
{% endhint %}

{% endstep %}
{% endstepper %}

### Additional Options

#### Customizing Temporary Kafka Topic Names

{% hint style="info" %}
Available since chart version `1.27` and operator version `3.114.0`.
{% endhint %}

To serve Kafka splitting sessions, mirrord operator creates temporary topics in the Kafka cluster. The default format for their names is as follows:

* `mirrord-tmp-1234567890-fallback-topic-original-topic` - for the fallback topic (unfiltered messages, consumed by the deployed workload).
* `mirrord-tmp-0987654321-original-topic` - for the user topics (filtered messages, consumed by local applications running with mirrord).

Note that the random digits will be unique for each temporary topic created by the operator.

You can adjust the format of the created topic names to suit your needs (RBAC, Security, Policies, etc.),
using the `OPERATOR_KAFKA_SPLITTING_TOPIC_FORMAT` environment variable of the mirrord operator,
or `operator.kafkaSplittingTopicFormat` helm chart value. The default value is:

`mirrord-tmp-{{RANDOM}}{{FALLBACK}}{{ORIGINAL_TOPIC}}`

The provided format must contain the three variables: `{{RANDOM}}`, `{{FALLBACK}}` and `{{ORIGINAL_TOPIC}}`.

* `{{RANDOM}}` will resolve to random digits.
* `{{FALLBACK}}` will resolve either to `-fallback-` or `-` literal.
* `{{ORIGINAL_TOPIC}}` will resolve to the name of the original topic that is being split.

#### Reusing Kafka Client Configs

`MirrordKafkaClientConfig` resource supports property inheritance via `spec.parent` field. When resolving a resource `config-A` that has a parent `config-B`:

1. `config-B` is resolved into a `.properties` file.
2. For each property defined in `config-A`:
   * If `value` is provided, it overrides any previous value of that property
   * If `value` is not provided (`null`), that property is removed

Below we have an example of two `MirrordKafkaClientConfig`s with an inheritance relation:

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

When used by the mirrord operator for Kafka splitting, the `with-client-id` below will be resolved to following `.properties` file:

```properties
bootstrap.servers=kafka.default.svc.cluster.local:9092
client.id=mirrord-operator
```

#### Configuring Kafka Clients with Secrets

`MirrordKafkaClientConfig` also supports loading properties from a Kubernetes [`Secret`](https://kubernetes.io/docs/concepts/configuration/secret/), with the `spec.loadFromSecret` field.
The value for `spec.loadFromSecret` is given in the form: `<secret-namespace>/<secret-name>`.

Each key-value entry defined in the secret's data will be included in the resulting `.properties` file.
Property inheritance from the parent still occurs, and within each `MirrordKafkaClientConfig` properties loaded from the secret are overwritten by those in `properties`.

This means the priority of setting properties (from highest to lowest) is like so:

* child `spec.properties`
* child `spec.loadFromSecret`
* parent `spec.properties`
* parent `spec.loadFromSecret`

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

{% hint style="info" %}
Note that by default, mirrord operator has read access only to the secrets in the operator's namespace.
{% endhint %}

#### Configuring Custom Kafka Authentication

For authentication methods that cannot be handled just by setting [client properties](https://github.com/confluentinc/librdkafka/blob/master/CONFIGURATION.md),
we provide a separate field `spec.authenticationExtra`. The field allows for specifying custom authentication methods:

{% tabs %}
{% tab title="MSK IAM/OAUTHBEARER" %}

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

The example above configures IAM/OAUTHBEARER authentication with Amazon Managed Streaming for Apache Kafka.
When the `MSK_IAM` kind is used, two additional properties are automatically merged into the configuration:
1. `sasl.mechanism=OAUTHBEARER`
2. `security.protocol=SASL_SSL`

To produce the authentication tokens, the operator will use the default credentials provider chain.
The easiest way to provide the crendentials for the operator is with IAM role assumption.
For that, an IAM role with an appropriate policy has to be assigned to the operator's service account.
Please follow [AWS's documentation on how to do that](https://docs.aws.amazon.com/eks/latest/userguide/associate-service-account-role.html).
Note that operator's service account can be annotated with the IAM role's ARN with the `sa.roleArn` setting in the [mirrord-operator Helm chart](https://github.com/metalbear-co/charts/blob/main/mirrord-operator/values.yaml).

{% endtab %}
{% endtabs %}

#### Configuring Workload Restart

To inject the names of the temporary topics into the consumer workload, 
the operator always requires the workload to be restarted.
Depending on cluster conditions, and the workload itself, this might take some time.

`MirrordKafkaTopicsConsumer` allows for specifying two more options for this:
1. `spec.consumerRestartTimeout` — specifies how long the operator should wait,
before a new pod becomes ready, and after the workload restart is triggered.
This allows for silencing timeout errors when the workload pods take a long time to start.
Specified in seconds, defaults to 60s.
2. `spec.splitTtl` — specifies how long the consumer workload should remain patched,
after the last Kafka splitting session against it have finished.
This allows for skipping the subsequent restart in case the next Kafka splitting session
is started before the TTL elapses. Specified in seconds.

## Setting a Filter for a mirrord Run

Once cluster setup is done, mirrord users can start running sessions with queue message filters in their mirrord configuration files.
[`feature.split_queues`](https://app.gitbook.com/s/Z7vBpFMZTH8vUGJBGRZ4/options#feature.split_queues) is the configuration field they need to specify in order to filter queue messages.
Directly under it, mirrord expects a mapping from a queue or topic ID to a queue filter definition.

Filter definition contains two fields:
* `queue_type` — `SQS` or `Kafka`
* `message_filter` — mapping from message attribute (SQS) or header (Kafka) name to a regex for its value.
  The local application will only see queue messages that have **all** of the specified message attributes/headers.

{% hint style="info" %}
An empty `message_filter` is treated as a match-none directive.
{% endhint %}

See example configurations below:

{% tabs %}

{% tab title="SQS and Kafka" %}

```json
{
  "operator": true,
  "target": "deployment/meme-app/container/main",
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

In the example above, the local application:

* Will receive a subset of messages from SQS queues desribed in the registry under ID `meme-queue`.
  All received messages will have an attribute `author` with the value `me`, AND an attribute `level` with value either `beginner` or `intermediate`.
* Will receive no messages from SQS queues described in the registry under ID `ad-queue`.
* Will receive a subset of messages from Kafka topic with ID `views-topic`.
  All received messages will have an attribute `author` with the value `me`, AND an attribute `source` with value starting with `my-session-` (e.g `my-session-844cb78789-2fmsw`).


{% endtab %}
{% tab title="SQS with wildcard" %}

```json
{
  "operator": true,
  "target": "deployment/meme-app/container/main",
  "feature": {
    "split_queues": {
      "*": {
        "queue_type": "SQS",
        "message_filter": {
          "author": "^me$",
        }
      },
    }
  }
}
```

In the example above, the local application will receive a subset of message from **all** SQS queues described in the registry.
All received messages will have an attribute `author` with the value `me`.
`*` is a special queue ID for SQS queues, and resolves to all queues described in the registry.

{% endtab %}
{% endtabs %}

## FAQ

#### How do I authenticate operator's Kafka client with an SSL certificate?

An example `MirrordKafkaClientConfig` would look as follows:

```yaml
apiVersion: queues.mirrord.metalbear.co/v1alpha
kind: MirrordKafkaClientConfig
metadata:
  name: ssl-auth
  namespace: mirrord
spec:
  properties:
  # Contents of the PEM file with client certificate.
  - name: ssl.certificate.pem
    value: "..."
  # Contents of the PEM file with client private key.
  - name: ssl.key.pem
    value: "..."
  # Contents of the PEM file with CA.
  - name: ssl.ca.pem
    value: "..."
  # Password for the client private key (if password protected).
  - name: ssl.key.password
    value: "..."
```

Alternatively, you can store the credentials in a secret, and have them loaded to the config automatically:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: mirrord-kafka-ssl
  namespace: mirrord
type: Opaque
data:
  ssl.certificate.pem: "..."
  ssl.key.pem: "..."
  ssl.ca.pem: "..."
  ssl.key.password: "..."

---
apiVersion: queues.mirrord.metalbear.co/v1alpha
kind: MirrordKafkaClientConfig
metadata:
  name: ssl-auth
  namespace: mirrord
spec:
  loadFromSecret: mirrord/mirrord-kafka-ssl
  properties: []
```

#### How do I authenticate operator's Kafka client with a Java KeyStore?

The mirrord operator does not support direct use of JKS files.
In order to use JKS files with Kafka splitting, first extract all necessary certificates and key to PEM files.
You can do it like this:

```sh
# Convert keystore.jks to PKCS12 format.
keytool -importkeystore \
  -srckeystore keystore.jks \
  -srcstoretype JKS \
  -destkeystore keystore.p12 \
  -deststoretype PKCS12

# Extract client certificate PEM from the converted keystore
openssl pkcs12 -in keystore.p12 -clcerts -nokeys -out client-cert.pem

# Extract client private key PEM from the converted keystore.
openssl pkcs12 -in keystore.p12 -nocerts -nodes -out client-key.pem

# Convert truststore.jks to PKCS12 format.
keytool -importkeystore \
  -srckeystore truststore.jks \
  -srcstoretype JKS \
  -destkeystore truststore.p12 \
  -deststoretype PKCS12

# Extract CA PEM from the converted truststore.
openssl pkcs12 -in truststore.p12 -nokeys -out ca-cert.pem
```

Then, follow the guide for [authenticating with an SSL certificate](queue-splitting.md#how-do-i-authenticate-operators-kafka-client-with-an-ssl-certificate).
