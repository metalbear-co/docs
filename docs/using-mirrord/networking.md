# Networking

When you run with mirrord, your local process gets network access as if it were running inside the cluster. This means your code can call internal services, resolve cluster DNS names, and optionally receive incoming traffic—all without deploying.

## Outgoing traffic

Your local process can reach services that are only accessible from inside the cluster.

When your app makes an outgoing connection (e.g., to `http://payment-service:8080`), mirrord intercepts it and routes the request through the target pod. From the cluster's perspective, the request originates from that pod—so network policies, service discovery, and internal DNS all work as expected.

This is enabled by default. You don't need any special configuration to call cluster services.

**When you need more control:** If you want some connections to stay local (e.g., a local database) while others go through the cluster, see [Outgoing Filter](outgoing-filter.md).

## DNS resolution

Cluster service names resolve correctly because mirrord forwards DNS queries to the cluster.

When your app looks up `payment-service.payments.svc.cluster.local` (or just `payment-service` with the right search domains), mirrord resolves it using the cluster's DNS, returning the in-cluster IP.

This is also enabled by default and works together with outgoing traffic.

## Incoming traffic

Your local process can receive traffic that was destined for the target pod.

This is useful when you want to:
- Test how your local code handles real requests
- Debug a specific request flow with your local debugger
- Develop against live traffic patterns

mirrord supports two modes:

**Mirror mode** (default): Traffic is duplicated. The target pod receives and handles the request normally; your local process gets a copy for observation. Your local responses are discarded.

**Steal mode**: Traffic is redirected. Your local process receives the request instead of the target pod, and your response is sent back to the caller.

```json
{
  "feature": {
    "network": {
      "incoming": "steal"
    }
  }
}
```

**When you need more control:** To steal only specific requests (by header, path, or method) while letting other traffic flow to the target normally, see [Traffic Filtering](traffic-filtering.md).

## Putting it together

With these three capabilities, your local process behaves like it's running in the cluster:

| What your code does | What happens with mirrord |
|---------------------|---------------------------|
| Calls `http://other-service:8080` | Request goes through cluster network |
| Resolves `database.prod.svc` | Returns the in-cluster IP |
| Listens on port 8080 | Can receive traffic from the cluster |

You get the network context of your target pod while keeping your code, debugger, and tools local.
