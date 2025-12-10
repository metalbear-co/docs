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
            "any_of":    [ /* ... */ ],      //request matches if at least one filter in this array matches.
            "all_of": [ /* ... */ ]       //request matches only if all filters in this array match.
        }
      }
    }
  }
}
```
Note: If one of the arrays is omitted or empty, it is simply ignored.

### JSON body filter configuration

Each JSON body filter entry looks like this:
```json

{
  "body": {
    "type": "json",
    "query": "$.data[*].legacyEntityIds.legacyUserIdentityId",
    "matches": "^identity123$",
  }
}
```
`type`: must be "json" for JSON body filtering.
`query`: JSONPath [(RFC 9535)](https://www.rfc-editor.org/rfc/rfc9535.html#name-jsonpath-examples) used to extract values from the parsed JSON.
`matches`: regex applied to each extracted value (after converting to string).

### Overview
When enabled, mirrord:
1. Check that the request is JSON
mirrord inspects the Content-Type header. if it contains  `(application/json)`, mirrord continues. Otherwise, the filter does not match.
2. Read and parse the request body
mirrord reads the full request body into memory and attempts to parse it as JSON.
- mirrord waits up to the configured timeout (default ~10s).
- If the body cannot be fully read or is not valid JSON, the filter does not match.
- This ensures mirrord only applies JSONPath to a complete and valid JSON document
3. Extract values with the JSONPath query
mirrord applies the user’s JSONPath expression in `query` field to the parsed JSON.
- The query may return zero, one, or multiple values.
- All extracted values are converted to strings before matching.
- If the query returns zero values, the filter does not match.
4. Apply the regex from `matches` field
mirrord tests each extracted value against the regex.
*The filter matches if at least one value matches.*
5. Final decision
If the JSONPath extraction and regex match conditions succeed, the filter matches and mirrord steals the request.
If any step fails, the filter simply does not match.


### Configuration Example
Configuartion below applies to only steal requests for tenant `tenant-a` that either have a specific `legacyUserIdentityId` equals to "identity123" or a numeric price ending with "99".

```json
{
  "feature": {
    "network": {
      "incoming": {
        "http_filter": {
          "any_of": [
            {
              "body": {
                "type": "json",
                "query": "$.data[*].legacyEntityIds.legacyUserIdentityId",
                "matches": "^identity123$",
              }
            },
            {
              "body": {
                "type": "json",
                "query": "$..[?typeof(@.price) == 'number'].price",
                "matches": "99$",
              }
            }
          ],
          "all_of": [
            {
              "body": {
                "type": "json",
                "query": "$.tenant.id",
                "matches": "^tenant-a$",
              }
            }
          ]
        }
      }
    }
  }
}

```


### Request Example and Results
Assume all requests have Content-Type: `application/json`.


#### Request A matches and stolen
```json
{
  "tenant": { "id": "tenant-a" },
  "data": [
    {
      "legacyEntityIds": {
        "legacyUserIdentityId": "identity123"
      }
    }
  ],
  "order": {
    "price": 42
  }
}
```

#### Request B matches and stolen
```json
{
  "tenant": { "id": "tenant-a" },
  "data": [
    {
      "legacyEntityIds": {
        "legacyUserIdentityId": "other-user"
      }
    }
  ],
  "order": {
    "price": 199
  }
}
```


#### Request C does not match and not stolen
```json
{
  "tenant": { "id": "tenant-b" },
  "data": [
    {
      "legacyEntityIds": {
        "legacyUserIdentityId": "identity123"
      }
    }
  ],
  "order": {
    "price": 199
  }
}
```



