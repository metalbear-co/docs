---
title: "ECS Quickstart"
description: "Deploy a sample service to Amazon ECS with Terraform, then run it on your laptop with mirrord through MetalBear Cloud: steal requests by header and reach a private RDS database."
tags:
  - experimental
  - enterprise
---

{% hint style="warning" %}
mirrord for Amazon ECS is **experimental**, and may change without notice.
{% endhint %}

This quickstart deploys a small orders API to Amazon ECS on Fargate, next to a private Postgres database on Amazon RDS. Then you run the same service on your laptop with mirrord, and see two things:

* **Real requests reach your laptop:** requests to the public load balancer that carry your session header reach the process on your laptop. All other requests still go to the ECS task.
* **Your laptop reads the real database:** your local process reads and writes the orders in the RDS database, which has no public endpoint. mirrord sends the database connection through the ECS task, inside the VPC. It also gives the local process the task's environment variables, so the process gets the database settings from the task.

The ECS task connects to mirrord through MetalBear Cloud. The code and the Terraform configuration are in the [mirrord-ecs-quickstart](https://github.com/metalbear-co/mirrord-ecs-quickstart) repository.

## How it works

![The client sends requests to the load balancer and the ECS task. The mirrord remote bootstrap in the task sends requests with your header through the MetalBear sessions-manager to the app on your machine. The task connects to the private RDS database for both apps.](../../.gitbook/assets/ecs-quickstart.svg)

The ECS task and your laptop both make only outbound HTTPS connections to the MetalBear sessions-manager, which pairs them. mirrord needs no inbound access to your VPC. The public load balancer is part of the sample app, so that you can send requests to it.

## Prerequisites

1. An AWS account, and the AWS CLI signed in to it.
2. Terraform 1.6 or later.
3. Python 3.12 or another Python 3 version that FastAPI supports.
4. The mirrord CLI.
5. A MetalBear account. To generate the API key, you must be an admin of your MetalBear organization.

{% hint style="info" %}
This quickstart creates billable AWS resources: a NAT gateway, an Application Load Balancer, a `db.t4g.micro` RDS instance and one Fargate task. Run `terraform destroy` when you finish; see [Clean up](#clean-up).
{% endhint %}

---

## Get an API key

The ECS task signs in to MetalBear Cloud with the serverless agent API key of your organization. Your organization has one active key at a time. If it already has a key, ask the admin who generated it for the key, and go to the next step.

1. Open the [MetalBear dashboard](https://app.metalbear.com), and go to **Settings → Serverless agents**.
2. Generate the key.
3. Copy the key, and keep it. It begins with `metalbear_key_`. The dashboard shows the key only once.

This guide calls the key `<API_KEY>`.

## Deploy the service to ECS

Clone the repository and put your API key in the Terraform variables file:

```bash
git clone https://github.com/metalbear-co/mirrord-ecs-quickstart.git
cd mirrord-ecs-quickstart/terraform
cp terraform.tfvars.example terraform.tfvars
```

In `terraform.tfvars`, set:

```hcl
mirrord_api_key = "<API_KEY>"
```

The resources go to `us-east-1`. To use a different region, also set `region`.

Deploy:

```bash
terraform init
terraform apply
```

The apply takes about 10 minutes, mostly for RDS. Terraform stores the API key in AWS Secrets Manager, and ECS gives it to the task as `MIRRORD_SESSIONS_MANAGER_API_KEY`.

When the apply finishes, keep the service URL, and send a request to it:

```bash
export URL=$(terraform output -raw url)
curl $URL/orders
```

The ECS task sends the response, with `"version": "v1"` and three orders from the database.

## Run the service locally

Sign in to your MetalBear account once:

```bash
mirrord login
```

The sign-in must be to the organization that owns the API key. For more, see [Developer setup](metalbear-cloud.md#developer-setup).

Install the app's dependencies:

```bash
cd ../app
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
```

Open `app/main.py` and change the code. For example:

```python
GREETING = "Hello from my laptop"
VERSION = "v2"
```

Run the app with mirrord, from the root of the repository:

```bash
cd ..
mirrord exec -f mirrord.json -- uvicorn main:app --app-dir app --port 8080
```

When the app starts, it creates the `orders` table in RDS if the table does not exist. So the log line `Application startup complete` also shows that your local process reached the private database.

## Send requests

`mirrord exec` keeps its terminal busy. Open a second terminal, go to the `terraform` directory of the repository, and set the service URL again:

```bash
export URL=$(terraform output -raw url)
```

Send a request with your session header:

```bash
curl -H "baggage: mirrord-session=quickstart" $URL/
curl -H "baggage: mirrord-session=quickstart" $URL/orders
```

Both responses show `"version": "v2"`, so your local code served them. The `/orders` response also lists the rows from the RDS database, which your laptop has no route to.

Send the same request without the header:

```bash
curl $URL/orders
```

The response shows `"version": "v1"`. The ECS task still serves all other traffic, so other developers are not affected.

Add an order from your local code, and then read it from the ECS task:

```bash
curl -X POST -H "baggage: mirrord-session=quickstart" \
  -H "content-type: application/json" -d '{"item": "bagel"}' $URL/orders
curl $URL/orders
```

The ECS task returns the new order, because both processes use the same database.

To try more changes, change the code, stop `mirrord exec`, and start it again. You do not build an image or deploy between changes.

---

## The mirrord configuration

The repository's `mirrord.json` is:

```json
{
  "target": {
    "path": "serverless/orders",
    "namespace": "quickstart"
  },
  "operator": false,
  "key": "quickstart",
  "feature": {
    "env": true,
    "network": {
      "outgoing": true,
      "dns": true,
      "incoming": {
        "mode": "steal",
        "http_filter": {
          "header_filter": "^baggage: .*mirrord-session={{ key }}.*$"
        }
      }
    }
  }
}
```

| Setting | Value | What it does |
| --- | --- | --- |
| `target.path` | `serverless/orders` | Selects the service. It matches `MIRRORD_REMOTE_SERVICE` on the task. |
| `target.namespace` | `quickstart` | Selects the environment. It matches `MIRRORD_REMOTE_ENVIRONMENT` on the task. |
| `operator` | `false` | Connects through MetalBear Cloud. Without it, mirrord looks for an Operator in your current kubeconfig context, and uses it if it finds one. |
| `key` | `quickstart` | The session key. The header filter uses it. |
| `feature.network.incoming` | `steal` with `header_filter` | Steals only HTTP requests whose `baggage` header carries the session key. |

To use a different session key, change `key`, or set the `MIRRORD_KEY` environment variable. Then send that key in the header.

## The task definition

The task definition in [`terraform/ecs.tf`](https://github.com/metalbear-co/mirrord-ecs-quickstart/blob/main/terraform/ecs.tf) has the changes from [Amazon ECS](ecs.md) and [Connecting ECS to MetalBear Cloud](ecs-metalbear-cloud.md):

1. A setup container copies the [remote bootstrap](ecs.md) into a shared volume before the app starts.
2. The app container loads the bootstrap with `LD_PRELOAD`. The app image does not change.
3. `MIRRORD_REMOTE_SERVICE` and `MIRRORD_REMOTE_ENVIRONMENT` name the workload.
4. ECS injects the API key from Secrets Manager as `MIRRORD_SESSIONS_MANAGER_API_KEY`.

The service runs one task, because one replica serves a mirrord session. The app image is based on `python:3.12-slim-bookworm`, because the bootstrap needs glibc. For all the requirements, see [Application container requirements](README.md#application-container-requirements).

To use the same setup with the mirrord Operator on EKS, see [Operator-hosted mode](https://github.com/metalbear-co/mirrord-ecs-quickstart#operator-hosted-mode) in the repository.

## Clean up

Delete all the resources:

```bash
cd terraform
terraform destroy
```

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| `mirrord operator does not serve the operator-hosted sessions-manager` | `mirrord.json` has no `"operator": false`, and your current kubeconfig context has an Operator. |
| `mirrord exec` cannot find the target | `target.path` or `target.namespace` does not match the task's `MIRRORD_REMOTE_SERVICE` or `MIRRORD_REMOTE_ENVIRONMENT`, or the task is not running. |
| A request with the header gets `"version": "v1"` | The header does not match the filter. Send `baggage: mirrord-session=<key>`, with the `key` from `mirrord.json`. |
| `mirrord exec` asks you to sign in, or refuses the session | Your sign-in expired, or it is to a different organization from the API key's. Run `mirrord login` again. |

For other problems, see [Connecting ECS to MetalBear Cloud](ecs-metalbear-cloud.md#troubleshooting) and [Amazon ECS](ecs.md#troubleshooting).
