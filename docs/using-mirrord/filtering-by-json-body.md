---
title: Traffic Filtering by JSON body
date: 2020-11-16T12:59:39.000Z
lastmod: 2025-02-24T00:00:00.000Z
draft: false
menu:
  docs:
    parent: using-mirrord
weight: 100
toc: true
tags:
  - open source
  - team
  - enterprise
description: How to filter traffic by JSON body using mirrord
---

# JSON Body Filtering for Incoming HTTP Requests

mirrord can steal incoming HTTP requests based on values inside a JSON request body. This allows matching on deeply nested fields and applying a regular expression to the extracted values.
This filter is available in the following mirrord.json configuration:

```json
{
  "feature": {
    "network": {
      "incoming": {
        "mode": "steal",
        "http_filter": {
          "body_filter": {
            "body": "json",
            "query": "$.data[*].legacyEntityIds.legacyUserIdentityId",
            "matches": "^identity123$",
          }
        }
      }
    }
  }
}
```

`body`: must be "json" for JSON body filtering.

`query`: JSONPath [(RFC 9535)](https://www.rfc-editor.org/rfc/rfc9535.html#name-jsonpath-examples) used to extract values from the parsed JSON.

`matches`: regex applied to each extracted value (after converting to string).

### Overview
When enabled, mirrord:
1. Read and parse the request body
    mirrord reads the full request body into memory and attempts to parse it as JSON.
    - mirrord waits up to the configured timeout (default ~1s).
    - If the body cannot be fully read or is not valid JSON, the filter does not match.
    - This ensures mirrord only applies JSONPath to a complete and valid JSON document
2. Extract values with the JSONPath query
    mirrord applies the user’s JSONPath expression in `query` field to the parsed JSON.
    - The query may return zero, one, or multiple values.
    - All extracted values are converted to strings before matching.
3. Apply the regex from `matches` field
    mirrord tests each extracted value against the regex.
    *The filter matches if at least one value matches.*
4. Final decision
    If the JSONPath extraction and regex match conditions succeed, the filter matches and mirrord may steal the request based on the overall filtering rules.
    If any step fails, the filter simply does not match.


### Configuration Example
Configuartion below applies to only steal requests with path `/orders` and have a JSON body with at least one numeric `price` value ending in "99".

```json
{
  "feature": {
    "network": {
      "incoming": {
        "http_filter": {
          "all_of": [
            {
              "path": "/orders"
            },
            {
              "body_filter": {
                "body": "json",
                "query": "$..[?(typeof(@.price) == 'number')].price",
                "matches": "99$"
              }
            }
          ]
        }
      }
    }
  }
}

```


### Examples and Results

#### Request A matches and stolen
```bash
POST /orders
Content-Type: application/json
```
```json
{
  "orderId": "123",
  "items": [
    { "name": "A", "price": 199 },
    { "name": "B", "price": 42 }
  ]
}
```

#### Request B does not match and not stolen
```bash
POST /orders
Content-Type: application/json
```
```json
{
  "orderId": "124",
  "items": [
    { "name": "A", "price": 150 },
    { "name": "B", "price": 42 }
  ]
}
```


#### Request C does not match and not stolen
```bash
POST /payments
Content-Type: application/json
```
```json
{
  "orderId": "125",
  "items": [
    { "name": "A", "price": 199 }
  ]
}
```



