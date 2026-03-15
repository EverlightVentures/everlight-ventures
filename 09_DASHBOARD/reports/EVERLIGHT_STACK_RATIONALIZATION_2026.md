# Everlight Stack Rationalization 2026

## Bottom line

The system does not need more random software. It needs a sharper split between:

1. Core paid rails you keep because they directly run revenue or identity.
2. Self-hosted utilities you add because they reduce time and monitoring blind spots.
3. Duplicate subscriptions you cut because they do not create enough operating leverage.

The repo already shows the right long-term shape: Hive as command plane, Supabase as source of truth, n8n as event bus, Business OS as executive board, and the XLM watchtower as the public proof layer.

## Keep paying for

### Supabase

Keep it as the canonical system for product state, telemetry, leads, auth, storage, cron, and public data mirrors. Do not split this across extra databases or random server scripts.

### Stripe

Keep it as the single monetization rail for software, digital products, services, and future marketplace or broker-style fees.

### GitHub

Keep it as the code truth, deployment trigger, issue log, and audit trail. Do not move source-of-truth code into low-control builders.

### Namecheap and Google

Keep them for domain control, DNS, email, and the small pieces of business identity that should stay boring and reliable.

### One primary LLM vendor plus one fallback

You do not need three premium chat subscriptions plus scattered API usage. Keep one primary model family for most work and one fallback for second opinions or failure handling. Everything else should justify itself with measured ROI, not vibes.

Inference:
Given the repo and current workflow, the most defensible shape is one coding-first default, one reasoning/review fallback, and routing by workflow rather than by habit.

## Add now if you want more leverage per dollar

### Langfuse

Use it as the LLM observability layer across Hive, MCP tools, and bot-assisted flows. This gives you traces, prompt management, evals, and failure visibility without inventing your own tracing stack first.

Use cases:
- Trace which prompts or tools actually create revenue-producing work.
- Score agent sessions instead of trusting subjective impressions.
- Log why a workflow failed before it hits the business board.

### Netdata

Use it for machine-level observability on Oracle and any future app host. Uptime Kuma tells you if a service is reachable. Netdata tells you why the host is degrading.

Use cases:
- CPU, RAM, disk, container, and network monitoring.
- Early warning before the bot or n8n fails.
- One host-level view for the systems that are supposed to run 24/7.

### Postiz

Use it only if you are serious about turning the content side into a repeatable acquisition channel. It fits the repo because it supports self-hosting, automation, and an agent-oriented CLI.

Use cases:
- Schedule content across X, LinkedIn, Threads, and more from one queue.
- Let n8n or Hive prepare drafts and schedule them with human approval.
- Turn build logs, public watchtower notes, and product updates into content automatically.

### Cal.com

Use the hosted free tier or embed if you want services revenue without adding manual back-and-forth. This is the simplest path to turning implementation work into booked calls and paid setup sessions.

Use cases:
- AI setup audit calls.
- Broker intake and qualification calls.
- Onyx or Hive implementation discovery sessions.

### Coolify

Only add this if raw Docker deployment is slowing you down. If you keep shipping manually, Coolify can become the lightweight control plane for app deploys on your own infrastructure.

Use cases:
- One interface for deploying Django, static sites, sidecar services, and databases.
- Push-to-deploy from GitHub.
- Easier app lifecycle management without renting another PaaS.

## Do not add right now

### Another automation platform

You already have n8n. Do not add Zapier, Make, or another orchestration layer unless a specific integration gap forces it.

### Another database or vector service

Supabase is already enough for the current phase. Add specialized storage only after there is a measured bottleneck.

### Another dashboard builder

You already have Django, Business OS, and public pages. Focus on making the existing board trustworthy before adding more UI surfaces.

## Cost cuts to make immediately

### Collapse duplicate scheduling and notifications

Use Supabase Cron for lightweight scheduled jobs close to the data. Use n8n queue mode for heavier multi-step workflows. Do not scatter scheduling across cron, random shell scripts, and multiple third-party schedulers unless there is a clear reason.

### Reduce overlapping premium AI seats

If a seat is not tied to a measurable workflow, cancel it. Keep API access and route calls programmatically where possible. The system should spend money on successful executions, not on idle tabs.

### Make the public site part of the operating system

The public site should not be a separate marketing toy. It should read the same telemetry, forms, and product state as Business OS. That lowers maintenance cost and increases trust.

## Highest ROI operating pattern

### Use the stack like this

- Supabase: source of truth for telemetry, leads, product state, memory indexes, and public data mirrors.
- n8n: event bus for alerts, sales automation, Stripe webhooks, and routine orchestration.
- Hive: command plane and operator interface.
- Business OS: executive board for streams, incidents, approvals, and watchtower state.
- Langfuse: trace and evaluate the AI layer.
- Uptime Kuma plus Netdata: external reachability plus host internals.
- Postiz: content distribution if and only if you commit to a real posting engine.

## Monetization tie-in

The stack should make money in this order:

1. Services and implementation.
2. Broker and operator offers.
3. SaaS trials and waitlists.
4. Digital products and publishing.
5. Affiliate distribution.
6. Trading intelligence as reporting and telemetry, not miracle promises.

## Next 30 days

1. Instrument Hive and at least one core workflow with Langfuse.
2. Put Netdata on the Oracle host and any app host that matters.
3. Decide whether Postiz is a real acquisition channel. If yes, integrate it with n8n and the content queue. If no, skip it.
4. Add a Cal.com embed to the public site for implementation or broker intake.
5. Audit every paid AI seat and cut anything that is not tied to a workflow or metric.

## Sources

- n8n queue mode: https://docs.n8n.io/hosting/scaling/queue-mode/
- Supabase Cron: https://supabase.com/docs/guides/cron
- Langfuse n8n and self-hosting references: https://langfuse.com/docs/prompt-management/features/n8n-node and https://langfuse.com/self-hosting/deployment/kubernetes-helm
- Uptime Kuma: https://github.com/louislam/uptime-kuma and https://uptimekuma.org/
- Netdata: https://learn.netdata.cloud/docs/netdata-agent and https://learn.netdata.cloud/docs/netdata-agent/installation/docker
- Coolify: https://coolify.io/docs and https://coolify.io/docs/installation
- Cal.com: https://cal.com/help/quick-start and https://cal.com/embed and https://cal.com/docs/self-hosting/installation
- Postiz: https://docs.postiz.com/quickstart and https://postiz.com/agent
