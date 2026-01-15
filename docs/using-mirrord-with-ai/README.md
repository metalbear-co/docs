# Configure AI Agents to Use mirrord

On September 2025, we published an article about [self-correcting AI agents](https://metalbear.com/blog/self-correcting-ai/) that showed how to test code changes in seconds using mirrord. The response was incredible. Engineers loved the idea of AI agents that could write code, test it instantly against a real Kubernetes cluster, find bugs, fix them, and iterate in a tight 2-3 second feedback loop.

But then came the questions: "How do I actually set this up?" "What do I put in [AGENTS.md](http://AGENTS.md)?" "How do I configure mirrord for my services?"

So we decided to write this guide. Think of it as a **meta-prompt,** a prompt that generates instructions for AI agents. Writing an `AGENTS.md` file manually is time-consuming. You need to figure out the right mirrord configuration for each service, create helper scripts, write clear instructions and validate everything works. For a typical microservices repository with 5-10 services, this setup can take several hours.

## **What We’re Building**

The goal is to help you create an `AGENTS.md` file that lives in your repository and tells AI agents something like: “*Hey, when testing code changes, use mirrord first, not CI/CD.*” Now the challenge is that writing this file manually is tedious. You need to figure out mirrord configs for each service, create helper scripts, write clear instructions and validate that everything works.