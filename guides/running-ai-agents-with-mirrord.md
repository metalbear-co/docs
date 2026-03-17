# Running AI Agents with mirrord

Most codebases already have E2E tests that protect critical happy paths. When an AI agent makes changes, those existing tests are the best guardrails you have, but only if they run against real infrastructure. mirrord lets agents run your existing E2E suite against your staging cluster after every change, so new code is held to the same standard as code written by your team. The agent writes code, your tests catch regressions, and the PR arrives with proof that nothing broke.

---

**Tip:** This guide builds on [Testing AI-Generated Code Against Real Services](testing-ai-generated-code.md), which covers why mocks fail for AI-generated code and how mirrord connects your local process to staging. Start there if you haven't read it yet.

---

## The test-after-every-change loop

The key insight: your existing E2E tests already encode the happy paths that must keep working. Run them after every significant change, not just at the end. The agent doesn't need to write new tests, it just needs to not break the ones you already have.

```console
Agent makes change #1 → runs E2E tests via mirrord → GREEN → continue
Agent makes change #2 → runs E2E tests via mirrord → RED → fix immediately
Agent makes change #3 → runs E2E tests via mirrord → GREEN → continue
...
All changes pass → agent opens PR with test results attached
```

Each test run is a checkpoint. When something breaks, the agent knows exactly which change caused it and fixes it immediately, instead of spiraling through cascading errors and delivering a broken PR.

Without this autonomous dev feedback loop, most coding agents stop at code generation. They write changes, maybe run unit tests, and open a PR. But unit tests only verify isolated logic. The engineer then has to deploy to staging, run integration tests, discover the AI broke something, send the agent back to fix it, and repeat. With mirrord, the agent runs integration testing itself before a human ever sees the PR.

![The Agent Testing Loop](running-ai-agents-with-mirrord/agent-testing-loop.png)

## Prerequisites

- A Kubernetes cluster with your services running (staging or dev)
- [mirrord CLI installed](https://metalbear.com/mirrord/docs/installing-mirrord/cli)
- An existing E2E test suite that covers your critical happy paths (Playwright, Cypress, Jest, pytest, bash scripts, or any test runner)
- An AI coding agent that can execute shell commands (Claude Code, Cursor, Codex)

## Step 1: Set up mirrord configs per service

Create a mirrord config for each service an agent might work on. If you already have a config from the [Testing AI-Generated Code](testing-ai-generated-code.md#1-create-a-mirrord-config) guide, you can reuse it. For multi-service repos, create one config per service in `.mirrord/`:

`.mirrord/mirrord-order-service.json`:

```json
{
  "target": {
    "namespace": "shop",
    "path": {
      "deployment": "order-service"
    }
  },
  "feature": {
    "network": {
      "incoming": {
        "mode": "steal",
        "http_filter": {
          "header_filter": "X-Agent-Session: autonomous"
        }
      },
      "outgoing": true
    },
    "fs": {
      "mode": "read"
    },
    "env": true
  }
}
```

**Tip:** You can auto-generate configs and helper scripts for every service using the meta-prompt in [Using mirrord with AI Agents](https://metalbear.com/mirrord/docs/using-mirrord-with-ai).

## Step 2: Create helper scripts

Wrapper scripts add pre-flight checks so the agent doesn't waste time debugging environment issues:

```bash
#!/usr/bin/env bash
# scripts/mirrord-order-service.sh
set -euo pipefail

# Pre-flight checks
command -v mirrord >/dev/null || { echo "FAIL: mirrord not installed"; exit 1; }
kubectl get deployment order-service -n shop >/dev/null 2>&1 || {
  echo "FAIL: deployment/order-service not found in namespace shop"; exit 1
}

echo "Starting order-service with mirrord (targeting deployment/order-service in shop)"
mirrord exec --config-file .mirrord/mirrord-order-service.json -- "$@"
```

The agent calls `./scripts/mirrord-order-service.sh npm start` instead of dealing with raw mirrord commands.

## Step 3: Write AGENTS.md for autonomous operation

The `AGENTS.md` file is what turns a code-generation agent into an autonomous one. Use strong imperative language, agents respond more reliably to direct instructions.

```markdown
# Agent Instructions

## ATTENTION: Testing is REQUIRED

You MUST test all code changes against the staging cluster using mirrord
before opening a PR. Do NOT rely on mocks or unit tests alone.

## Services

| Service | Config | Helper Script | Test Command |
|---------|--------|---------------|--------------|
| order-service | `.mirrord/mirrord-order-service.json` | `scripts/mirrord-order-service.sh` | `./ci/demo_e2e.sh` |

## Workflow

1. Read this file and understand the service you're modifying
2. Make code changes
3. Start the service with mirrord in the background:

   ./scripts/mirrord-order-service.sh <start command> &

4. Wait for the service to be ready, then run E2E tests:

   ./ci/demo_e2e.sh

5. If tests FAIL: read the failure output, fix your code, re-run
6. If tests PASS: continue to the next change
7. Stop the background service before starting the next test cycle
8. After ALL changes pass, open a PR with test output in the description
9. NEVER open a PR without passing E2E tests against staging

## Verification

After starting the service with mirrord, verify it works:
curl http://localhost:<port>/health

## Safety

- NEVER target production clusters
- ALWAYS use the provided mirrord configs (they include traffic filters)
- If mirrord fails to start, check kubectl access and deployment status
```

**Tip:** For per-tool setup (Claude Code, Cursor, Copilot, Windsurf), see [Setting Up mirrord for Your AI Coding Tool](setting-up-mirrord-for-ai-tools.md).

## Example: AI agent testing an order service

This example uses the [MetalBear playground](https://github.com/metalbear-co/playground), a sample microservices app with an order service, inventory, and payment processing.

### The E2E test script

```bash
#!/usr/bin/env bash
set -euo pipefail

SHOP_URL="${SHOP_URL:-http://localhost:3000}"
HEADER_ARGS=(-H "baggage: mirrord=e2e-test")

# Health check
curl -sS --fail "${HEADER_ARGS[@]}" "${SHOP_URL}/banner" >/dev/null || {
  echo "FAIL: Service not reachable"; exit 1
}

# Create an order
order_resp="$(curl -sS -X POST "${HEADER_ARGS[@]}" "${SHOP_URL}/orders" \
  -H "Content-Type: application/json" \
  -d '{"items": [{"productId": 1, "quantity": 1}], "total_cents": 1999}')"

order_id="$(echo "$order_resp" | jq -e '.orderId')" || {
  echo "FAIL: orderId missing"; exit 1
}

# Verify order status
echo "$order_resp" | jq -e '.status == "confirmed"' >/dev/null || {
  echo "FAIL: Expected status 'confirmed'"; exit 1
}

echo "OK: E2E tests passed"
```

This script tests the happy path: create an order, verify it's confirmed. It runs against real Postgres, real payment service, real inventory service. Any regression in the order flow fails the script. Adjust the port and base URL to match your service.

### The agent in action

**Task:** "Add a `discount_cents` field to the order response based on order total."

```console
Agent: Reading AGENTS.md and codebase...
Agent: I see order-service returns orders from POST /orders.
       I'll add discount_cents calculation to the order handler.

Agent: Making changes to order-service/src/handlers/orders.ts...
       Added calculateDiscount() function and discount_cents to response.

Agent: Starting service with mirrord in the background...
       $ ./scripts/mirrord-order-service.sh npm start &
       OK: Service started with mirrord

Agent: Running E2E tests...
       $ ./ci/demo_e2e.sh
       FAIL: ERROR: expected status 'confirmed', got 'pending'

Agent: Stopping service. The discount calculation is triggering an async
       payment re-check. Fixing: add discount after payment confirmation,
       not before.

Agent: Restarting service and re-running tests...
       $ ./scripts/mirrord-order-service.sh npm start &
       $ ./ci/demo_e2e.sh
       OK: E2E tests passed

Agent: All tests pass. Opening PR with test results attached.
```

The agent caught and fixed the bug without human intervention. Nobody wrote new tests for this change. The existing E2E tests acted as **guardrails**, the agent could change the code freely, but the happy paths that the team already validated were protected. The engineer reviews a PR that already includes proof nothing broke.

## Why test after every change, not just at the end

Without guardrails, an agent makes change after change on top of a bad assumption. By the time it runs tests, errors have compounded and it's impossible to tell which change caused the break.

With E2E tests after every change:

- The agent catches breaks immediately
- Each fix is small and targeted
- The agent stays on track instead of spiraling
- Less time spent unwinding cascading errors

Running against real services also catches performance regressions that mocks hide. When every mock call returns in 0ms, you'd never notice a response time jump from 200ms to 2 seconds. With mirrord, your E2E test timeouts catch that immediately.

For a detailed comparison of what real infrastructure catches that mocks miss, see the [Testing AI-Generated Code](testing-ai-generated-code.md#what-you-catch-that-mocks-miss) guide.

## Architecture patterns for safe autonomous agents

### Scoped permissions

Give agents the minimum Kubernetes access they need. Create a dedicated service account with access scoped to their target namespace. If you're using the mirrord Operator, you can use [Policies](https://metalbear.com/mirrord/docs/sharing-the-cluster/policies) to control which targets agents can access and what traffic modes they can use.

### Isolated namespaces

For teams running multiple agents concurrently, use separate namespaces or mirrord for Teams' session management to prevent agents from interfering with each other. See [Sharing the Cluster](https://metalbear.com/mirrord/docs/sharing-the-cluster/overview).

### Traffic filtering

The `http_filter` in mirrord configs controls which traffic is stolen from the remote pod. Only requests matching the header are redirected to the local process, everything else flows to the remote pod normally. Your E2E tests hit `localhost` directly, so they reach the local process regardless of the header, but including the header in test requests is good practice for consistency.

```json
"http_filter": {
  "header_filter": "X-Agent-Session: agent-task-1234"
}
```

Use unique session identifiers per agent run to prevent collisions.

### Read-only database access

For agents that shouldn't modify data, configure your staging environment with read-only database credentials. The agent can still test query logic against real schema and data without risk of corruption.

**Warning:** Keep your AI agent in approval mode until you're comfortable with the workflow. Start with one service at a time. Never target production clusters.

## CI/CD comparison: agent with mirrord vs traditional pipeline

The [MetalBear playground](https://github.com/metalbear-co/playground) runs the same E2E tests two ways in CI/CD to demonstrate the difference:

| | Traditional (kind cluster) | mirrord (existing staging) |
|--|---------------------------|---------------------------|
| Timeout | 45 minutes | 15 minutes |
| Setup | Create cluster, build images, deploy Redis, Kafka, all services | Install mirrord, configure kubeconfig |
| Test execution | Tests hit locally-deployed services | Tests hit real staging services |
| Teardown | Delete kind cluster | Stop mirrord session |
| Infrastructure cost | Ephemeral compute for full cluster | Zero, uses existing staging |

An autonomous agent using mirrord gets the same validation as the full CI/CD pipeline without provisioning any AI agent infrastructure.

## Conclusion

The difference between an AI agent that generates code and one that ships working code is a real feedback signal. mirrord provides that signal by connecting the agent to your staging cluster, so every test run hits real services, real databases, and real APIs. By running integration tests after every change (not just at the end), your existing test suite becomes guardrails that keep the agent on track. Combined with an `AGENTS.md` that enforces the test-before-ship workflow, you get an autonomous dev feedback loop where the agent catches and fixes its own mistakes before a human ever reviews the PR.

## Next steps

- [Testing AI-Generated Code Against Real Services](testing-ai-generated-code.md): the foundational "why" behind testing with real services
- [Setting Up mirrord for Your AI Coding Tool](setting-up-mirrord-for-ai-tools.md): per-tool setup for Cursor, Claude Code, Copilot, and Codex
- [Using mirrord with AI Agents](https://metalbear.com/mirrord/docs/using-mirrord-with-ai): auto-generate mirrord configs and AGENTS.md for your repo
- [Sharing the Cluster](https://metalbear.com/mirrord/docs/sharing-the-cluster/overview): manage concurrent agent sessions with mirrord for Teams
