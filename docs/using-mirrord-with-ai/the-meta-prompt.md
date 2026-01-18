---
title: The Meta-Prompt
description: Configure AI Agents to Use mirrord
---

- [Environment Setup](using-mirrord-with-ai/the-meta-prompt#environment-Setup)
- [The Meta-Prompt](using-mirrord-with-ai/the-meta-prompt#the-meta-prompt)
Exploring the Generated Files

Testing the Workflow

Try It Yourself

Benefits for the Team

[Wrapping Up]()

## Environment Setup
For this demo, we’ll use the [the MetalBear playground repository](https://github.com/metalbear-co/playground). - It's a simple IP visit counter application written in Go, with a Redis dependency, which makes it ideal for demonstrating how this works.

The architecture looks like this:
![High Aevel Architecture](./high-level-architecture.png)
### Here’s what you’ll need to get started:
- Access to a Kubernetes cluster, such as a staging environment
- kubectl configured and ready
- mirrord installed locally
- For this guide, we use Claude Code v2.0.76 as the AI assistant. In the Try it yourself section, we’ll cover other assistants that can be used with the same workflow.

You can follow along using any cluster you already have access to, whether it’s staging or development. The important part is that you’re testing against a real environment.

## The Meta-Prompt
Here’s where it gets interesting. Instead of manually creating all the configuration files, we gave an AI agent a comprehensive prompt that told it exactly what to generate.

We navigated to the repository root, opened Claude Code, and pasted in the following prompt:

```
Generate AGENTS.md with mirrord integration for this repository.

Discovery Phase:
1. Scan repository structure to identify services (main.go, app.py, server.js, etc.)
2. Detect programming languages and frameworks
3. Look for Kubernetes manifests or conventions to understand deployment structure
4. Identify potential Kubernetes targets for each service (do NOT assume correctness)
5. Present discovered services and suspected targets in a table, including:
   - Any existing mirrord configuration files (show path and target)
   - Confidence level for each suspected target

STOP — Ask ONE question at a time. WAIT for my answer before continuing.

Question 1:
"Which services should be configured for AI-driven testing?"
Show the discovered services and WAIT FOR MY ANSWER.
If a service has existing config, note: "(has config - will ask to keep/replace)"

For each selected service, ask the following questions ONE AT A TIME.
WAIT for my answer before proceeding to the next question.

Question 2:
"For service <name>: What Kubernetes target should be used?"

Based on discovery, here are possible targets for this service:
- <candidate target 1> (target type, namespace, confidence)
- <candidate target 2> (target type, namespace, confidence)

Please select one of the above OR provide a different target.

Provide:
- Target type: deployment or pod
- Target name
- Namespace

DO NOT assume a default.
WAIT FOR MY ANSWER.

Question 3:
"For service <name>: How should testing success be verified when running with mirrord?"

Choose one:
- HTTP behavior (I will provide details such as domains/paths..)
- Logs (I will provide success message)
- Side effects (I will describe what to check)
- No automated verification

WAIT FOR MY ANSWER.

Question 4 (if needed, based on verification method):
Ask for verification coordinates only if required.
- Domains, paths, and headers may be supplied by me
- OR explicitly marked as environment variables
- Do NOT guess or hard-code remote URLs
WAIT FOR MY ANSWER.

Question 5:
"For service <name>: Which mirrord network mode should be used?"
- steal (intercept traffic)
- mirror (observe traffic)
WAIT FOR MY ANSWER.

Question 6:
"For service <name>: Any special requirements?"
- Filesystem access
- Environment variables
- Traffic filtering
WAIT FOR MY ANSWER.

IMPORTANT:
- Ask ONE question at a time
- WAIT for my answer before continuing
- DO NOT assume defaults
- DO NOT generate files yet

Generation Phase (ONLY after all required answers are provided):
For each configured service, generate:

1. `.mirrord/mirrord-<service>.json`
   - Use the confirmed target type, target name, and namespace
   - Configure the selected network mode
   - Apply traffic filtering ONLY if I explicitly provided it
   - Use only fields supported by the installed mirrord version
   - Avoid embedding secrets or sensitive values
   
2. `scripts/mirrord-<service>.sh` helper script
   - Perform pre-flight checks (mirrord installed, kubectl access, target exists)
   - Execute mirrord safely
   - Do NOT echo sensitive values to output
   - Include a --stop flag to kill running mirrord session

3. `AGENTS.md`
   - Start with a prominent ATTENTION block
   - Use strong imperative language (MUST / NEVER / ALWAYS)
   - Define mirrord as the required testing runtime
   - Describe verification behavior, not guessed URLs or credentials
   - Reference helper scripts instead of inline commands where possible
   - Include a service overview table
   - Add a troubleshooting section

Validation:
- Verify mirrord is installed (`mirrord --version`)
- Check kubectl access (`kubectl config current-context`)
- Validate each configured target exists in the specified namespace
- Ensure helper scripts are executable

Report Back:
- Services discovered
- Services selected for configuration
- Confirmed target and namespace per service
- Verification method per service
- Files created (paths only)
- Any remaining manual inputs or values requiring review
```

When we ran the prompt, Claude:
1. Discovered the services by scanning for entry points like `main.go` and `app.py`
2. Matched them to Kubernetes deployments using `kubectl get deployments`
3. Generated mirrord configurations, helper scripts, and `AGENTS.md`
4. Validated that everything worked before presenting the results

Let’s see it in action.

![Prompt Executed](./screen-recording.mov)


What Claude Generated

You saw Claude scan the repository and identify all the services. From there, we selected the ip-visit-counter service to configure.

Claude generated three files:
1. `AGENTS.md`
Instructions that tell AI agents how to use mirrord when testing the service.
2. `mirrord/mirrord-ip-visit-counter.json`
The mirrord configuration, including which Kubernetes deployment to connect to and how traffic should be handled.
3. `scripts/mirrord-ip-visit-counter.sh`
A helper script that wraps the mirrord command with pre-flight checks, such as verifying that mirrord is installed, kubectl is working, and the deployment exists.
This is the command Claude runs when you say “test the service.” `AGENTS.md` references this script directly, so the agent knows to use it automatically.


