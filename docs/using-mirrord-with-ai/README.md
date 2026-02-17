# Configure AI Agents to Use mirrord

On September 2025, we published an article about [self-correcting AI agents](https://metalbear.com/blog/self-correcting-ai/) that showed how to test code changes in seconds using mirrord. The response was incredible. Engineers loved the idea of AI agents that could write code, test it instantly against a real Kubernetes cluster, find bugs, fix them, and iterate in a tight 2-3 second feedback loop.

But then came the questions: "*How do I actually set this up?*" "*What do I put in [AGENTS.md](http://AGENTS.md)?*" "*How do I configure mirrord for my services?*"

So we decided to write this guide. In it you'll find two approaches you can use together or separately:

- **[Agent skills for mirrord](./ai-skills-plugin.md)** — Install skills that give your AI assistant built-in mirrord expertise.
- **[The meta-prompt](./the-meta-prompt.md)** — A prompt that generates project-specific `AGENTS.md` and configs. Writing them manually is time-consuming (for 5–10 services, it can take hours); the meta-prompt automates that.