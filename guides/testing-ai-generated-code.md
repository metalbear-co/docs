# How to Test AI Code with mirrord

In this guide, we'll cover how to test AI-generated code against real Kubernetes services using mirrord. You'll learn how to run your local process with staging context so you can validate changes in seconds instead of waiting for CI/CD pipelines.

---

**Tip:** You can use [mirrord](https://metalbear.com/mirrord/) to test AI-generated code locally with Kubernetes context, without needing to build or deploy each time. If you're new to mirrord, start with the [Quick Start](https://metalbear.com/mirrord/docs/getting-started/quick-start).

---

## Prerequisites

- A Kubernetes cluster with your services running (staging or dev)
- [mirrord CLI installed](https://metalbear.com/mirrord/docs/installing-mirrord/cli)
- An AI coding tool (Claude Code, Cursor, Copilot, Codex)

## Step 1: Create a mirrord config

Create `.mirrord/mirrord.json` targeting the service you're working on:

```json
{
  "target": {
    "namespace": "your-namespace",
    "path": {
      "deployment": "your-service"
    }
  },
  "feature": {
    "network": {
      "incoming": {
        "mode": "steal",
        "http_filter": {
          "header_filter": "X-Test-Agent: dev"
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

The `http_filter` ensures you only intercept traffic with your header, other developers and services using the same deployment are unaffected.

## Step 2: Let AI generate code, then validate immediately

Instead of the build, deploy, test cycle, the workflow becomes:

1. AI generates code changes
2. Run locally with mirrord (substitute your framework's start command and port):
   ```bash
   mirrord exec --config-file .mirrord/mirrord.json -- <start command>
   ```
3. Send a test request:
   ```bash
   curl http://localhost:<port>/your-endpoint
   ```
4. See real responses from real services, no mocks, no deploy

If something is wrong, fix it and re-run. Each iteration takes seconds, not minutes.

## Step 3: Run your test suite through mirrord

For automated validation, you have two options depending on your test setup:

**Option A: Run the test runner through mirrord.** This works when your tests start the service themselves (common with frameworks like FastAPI's TestClient or supertest):

```bash
mirrord exec --config-file .mirrord/mirrord.json -- pytest tests/integration/
```

**Option B: Start the service via mirrord, then run tests against localhost.** This works when your tests hit an already-running service (curl-based scripts, Playwright, Cypress):

```bash
# Terminal 1: start the service
mirrord exec --config-file .mirrord/mirrord.json -- <start command>

# Terminal 2: run tests against localhost
./ci/e2e_test.sh
```

Either way, your tests hit real infrastructure. No mock setup, no Docker Compose, no fake data.

## Example: validating a new endpoint

An AI agent adds a `/discount` endpoint to an order service. Without mirrord, you'd need to build, deploy, and test against staging. With mirrord:

```bash
# AI generates the code
# Run locally with staging context
mirrord exec -t deployment/order-service -- <start command>
```

```bash
# Test the new endpoint against real data
curl http://localhost:<port>/discount \
  -H "Content-Type: application/json" \
  -d '{"orderId": 42}'
```

The request reaches your local code, but when your code queries the database or calls other services, those calls go to the real staging cluster. You immediately know:

- Does the database query work with real schema and data?
- Do downstream service calls return what the AI expected?
- Do auth tokens and permissions work correctly?
- Is the response format compatible with the frontend?

## Integrating with AI coding tools

Add mirrord to your agent's instructions so it validates automatically. In your `AGENTS.md`, `CLAUDE.md`, or `.cursor/rules/`:

```markdown
## Validating code changes

ALWAYS validate code changes against the staging cluster before opening a PR.

1. Start the service with mirrord:
   
   mirrord exec --config-file .mirrord/mirrord.json -- <start command>
   
2. Send test requests to verify the change works
3. If the service fails to start or requests fail, fix the issue and retry
4. NEVER assume code works without testing against real infrastructure
```

**Tip:** For a complete auto-generated setup including helper scripts and per-service configs, see [Using mirrord with AI Agents](https://metalbear.com/mirrord/docs/using-mirrord-with-ai).

## Next steps

- [How to Validate AI Agent Changes with mirrord](running-ai-agents-with-mirrord.md): the full agent loop with E2E guardrails and AGENTS.md setup
- [How to Set Up AI Tools with mirrord](setting-up-mirrord-for-ai-tools.md): per-tool config for Cursor, Claude Code, Copilot, and Codex
- [Using mirrord with AI Agents](https://metalbear.com/mirrord/docs/using-mirrord-with-ai): auto-generate mirrord configs and AGENTS.md for your repo
