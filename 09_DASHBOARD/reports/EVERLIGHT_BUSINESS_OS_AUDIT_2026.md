# Everlight Business OS Audit and Upgrade Plan

Scope: workspace audit based on `c927b9f8`, current Hive docs/code, and the self-hosted stack now present in the repo.

## Executive Diagnosis

The system is not small anymore. It is already a business OS in pieces:

- Hive Mind is the decision layer.
- n8n is the workflow layer.
- Supabase is the app/database layer.
- Stripe is the billing layer.
- Blinko is the memory layer.
- GitHub is the build/deploy layer.
- Netdata and Langfuse are the observability layer.
- everlightventures.io is the front door.

What is broken is not capability. What is broken is coordination.

Today the stack behaves like multiple smart islands instead of one company:

- Hive can deliberate, but there is no enforced event contract for downstream systems.
- MCP exists, but this session exposes zero MCP resources/templates, so context is not flowing back into the agent loop.
- The Broker OS MCP server currently exposes tools, not resources, which makes it useful for actions but weak as a shared context plane.
- Blinko can ingest memory, but memory is still optional instead of mandatory before dispatch.
- n8n is present, but the current compose file is single-instance and not configured for queue-mode workers.
- Stripe architecture exists on paper, but revenue instrumentation is still mostly pre-implementation.
- Dashboards exist, but there is no single "CEO screen" that answers: what ran, what failed, what made money, what needs approval.
- Profit tracking exists, but current trading profit is tiny and does not justify treating the bot as the core business.

Conclusion:

You do not need more tools first. You need one operating model.

## What The Repo Already Proves

The audit found strong building blocks already in place:

- Hive protocol and routing: `HIVE_MIND.md`
- Prior session references and telemetry for `c927b9f8`: `everlight_os/hive_mind/telemetry.jsonl`
- Existing multi-tenant Hive SaaS architecture: `06_DEVELOPMENT/hivemind_saas/ARCHITECTURE.md`
- Existing daily monetization engine draft: `03_AUTOMATION_CORE/01_Scripts/daily_drop_orchestrator.py`
- Existing broker revenue workflow: `03_AUTOMATION_CORE/00_N8N/broker/broker_master_workflow.json`
- Existing Blinko bridge: `03_AUTOMATION_CORE/01_Scripts/ai_workers/blinko_bridge.py`
- Existing self-hosted n8n, Blinko, Langfuse, Netdata stacks:
  - `06_DEVELOPMENT/everlight_os/n8n/docker-compose.yml`
  - `06_DEVELOPMENT/everlight_os/blinko/docker-compose.yml`
  - `06_DEVELOPMENT/everlight_os/langfuse/docker-compose.yml`
  - `06_DEVELOPMENT/everlight_os/netdata/docker-compose.yml`
- Existing Stripe architecture doc: `03_AUTOMATION_CORE/STRIPE_PAYMENT_ARCHITECTURE.md`
- Existing pricing plan: `06_DEVELOPMENT/hivemind_saas/launch/pricing.md`
- Existing business warning that the bot alone is not the business: `09_DASHBOARD/reports/EVERLIGHT_FINANCIAL_PLAN_2026.md`

This means the right move is not greenfield. The right move is consolidation.

## Hard Truths

### 1. The bot is not the company

Treat the bot as:

- proof of automation credibility
- a data product source
- a small cash-flow experiment

Do not treat it as the primary path to scale.

### 2. "8 income streams" does not mean 8 random projects

It means 8 standardized loops with:

- a source of demand
- an automated fulfillment path
- a billing method
- a dashboard KPI
- an owner agent

### 3. Autonomy without observability is fake autonomy

If a workflow runs and you are not told:

- what happened
- what changed
- whether revenue was affected
- whether human approval is needed

then the system is not autonomous. It is just background noise.

## The Target Operating Model

Use this stack in six layers.

### Layer 1: Source of Truth

Supabase becomes the operational database for the business OS.

Supabase should hold:

- events
- workflow runs
- customers
- subscriptions
- affiliates
- deals
- content inventory
- gear catalog
- agent tasks
- alerts
- approvals
- revenue ledger

Rule:

Every important action in the company writes one structured event row.

### Layer 2: Decision Layer

Hive remains the "executive brain", but it should stop thinking in a vacuum.

Every Hive run should always receive:

- latest operational KPIs
- latest failures
- latest customer/revenue changes
- relevant Blinko memory
- open approvals
- current campaign priorities

Rule:

No high-value Hive session should launch without preloaded business state.

### Layer 3: Execution Layer

n8n becomes the company event bus and orchestrator for cross-system workflows.

Use n8n for:

- webhooks
- retries
- approvals
- schedules
- Slack notifications
- Google/Gmail/Drive automation
- Stripe event handling
- GitHub deployment triggers
- handoffs between Supabase, Hive, Blinko, and site publishing

Rule:

Business flows go through n8n. Complex product logic stays in code. Do not bury core business logic inside giant no-code flows.

### Layer 4: Memory Layer

Blinko remains long-term memory and operator notes, but must be categorized and fed back into the loop.

Store:

- war room summaries
- failed run postmortems
- customer objections
- winning offers
- outreach templates
- affiliate/product performance notes
- decision rationales

Rule:

Blinko is memory, not the system of record. Supabase is the system of record.

### Layer 5: Observability Layer

Use two observability tracks:

- Langfuse for model traces, prompt cost, agent quality, evaluations
- Netdata for machine/process/container health

Route both into:

- Slack alerts
- Supabase `alerts` table
- the CEO dashboard

### Layer 6: Monetization Layer

Stripe handles:

- subscriptions
- one-time digital sales
- invoices
- usage-based overages
- partner payouts later via Connect where needed

Namecheap should be reduced to:

- registrar
- DNS entry point
- SSL/domain routing decisions only

Do not let Namecheap become an application layer.

## The One Schema You Are Missing

Create a single event contract and make every system write to it.

Suggested event model:

```json
{
  "event_id": "uuid",
  "event_type": "workflow.completed",
  "source": "n8n",
  "entity_type": "gear_drop",
  "entity_id": "drop_2026_03_14",
  "status": "success",
  "priority": "medium",
  "revenue_impact_usd": 0,
  "requires_approval": false,
  "owner_agent": "distribution_ops",
  "summary": "Published 1 gear drop to everlightventures.io",
  "payload": {},
  "created_at": "ISO8601"
}
```

If you do not standardize events, you will never have a real autonomous system.

## The 24/7 Agent Team You Actually Need

Keep the current model managers, but add persistent operational roles.

### 1. CEO Agent

Purpose:

- daily priorities
- resource allocation
- escalate blockers
- produce morning and evening executive summaries

### 2. Revenue Ops Agent

Purpose:

- track MRR, affiliate sales, deal flow, conversion rates
- detect drops in revenue or traffic
- recommend experiments

### 3. Workflow Watchdog Agent

Purpose:

- detect broken jobs
- retry safely
- open incidents
- page you only when thresholds are exceeded

### 4. Memory Curator Agent

Purpose:

- ingest and tag Blinko notes
- summarize repeated failures
- push relevant memory into Hive sessions

### 5. Commerce Agent

Purpose:

- manage gear drops
- product ranking
- affiliate content
- merchandising decisions

### 6. Broker Agent

Purpose:

- scout offers
- match leads
- run follow-up
- produce deal pipeline summaries

### 7. Content and Distribution Agent

Purpose:

- generate pages, newsletters, clips, social posts
- schedule distribution
- monitor content-to-revenue attribution

### 8. Billing and Support Agent

Purpose:

- Stripe lifecycle
- failed payments
- onboarding nudges
- refund flags
- customer health status

## The 8 Revenue Streams Worth Standardizing

These are the eight that fit the current repo and can share infrastructure.

### 1. Hive Mind SaaS

Model:

- recurring subscription
- usage-based overages
- paid onboarding

Primary stack:

- Stripe + Supabase + Hive dashboard

### 2. Broker OS Deal Fees

Model:

- finder fees
- intro fees
- recurring referral revenue

Primary stack:

- Broker OS Django app + MCP + n8n + Stripe invoicing or Connect later

### 3. Onyx POS / Ops SaaS

Model:

- recurring subscriptions
- implementation fee
- premium support

### 4. Daily Gear Drop Affiliate Engine

Model:

- affiliate commissions
- sponsored placements later

Primary stack:

- daily drop orchestrator + site publishing + content distribution

### 5. Direct Digital Products

Model:

- ebooks
- guides
- templates
- prompts
- operator playbooks

Primary stack:

- Stripe + Supabase + content engine

### 6. AI Implementation Services

Model:

- setup fee
- monthly retainer
- paid strategy calls

Primary stack:

- Hive + Broker OS + Stripe invoices + scheduling

### 7. Publishing / Media Catalog

Model:

- books
- audio
- bundles
- upsells

Primary stack:

- content engine + Stripe + email funnels

### 8. Trading Intelligence Product

Model:

- analytics subscription
- paid alerts/reports
- proof-backed dashboard access

Primary stack:

- bot telemetry + dashboard + paid access

Do not make autonomous trading itself one of the main eight.
Make intelligence, reporting, and credibility the product.

## What Should Happen Every Day Without You

### Every 5 minutes

- health check all core services
- record heartbeat event
- alert only on threshold breach

### Every hour

- sync Stripe, Supabase, dashboard metrics
- check failed workflows
- refresh hot KPIs

### Twice daily

- broker pipeline report
- revenue delta report
- content performance report

### Once daily

- publish one revenue action minimum:
  - one gear drop, or
  - one outbound deal action batch, or
  - one paid content/product publish
- send morning CEO summary
- send evening operations summary
- update dashboard scoreboards

### Weekly

- review what made money
- review what failed
- disable low-performing loops
- promote one winning loop

## The Dashboard You Need

One dashboard. One URL. One home screen.

Top row:

- cash today
- MRR
- affiliate revenue
- pending deals value
- failed workflows
- open approvals
- active incidents

Middle row:

- 8 revenue streams with green/yellow/red status
- latest 10 events
- latest 10 alerts
- latest 10 customer or lead changes

Bottom row:

- agent status
- model cost by worker
- top content
- top offers
- today's actions completed vs missed

If it cannot be seen there, it is not part of the business OS.

## Current Gaps To Fix First

### Gap 1: MCP is not acting as shared context

Evidence:

- this session saw no MCP resources or templates
- Broker OS MCP server appears tool-first rather than resource-first

Fix:

- expose resources for revenue, alerts, open tasks, pipeline, top offers, and recent runs
- add remote MCP endpoints, not just local stdio use
- make the Hive and coding agents consume those resources by default

### Gap 2: n8n is not yet scaled for always-on operations

Evidence:

- current compose file is a single-instance setup

Fix:

- move n8n to queue mode
- add Redis
- separate main/webhook/worker roles
- add standard error workflows and alerting

### Gap 3: Memory is disconnected from dispatch

Evidence:

- Blinko bridge exists, but usage is optional

Fix:

- require pre-dispatch retrieval for selected workflows
- write back postmortems and decisions automatically

### Gap 4: Billing exists mostly as design

Evidence:

- Stripe architecture is documented, but the repo signals pre-implementation

Fix:

- ship one paid product fully first
- wire webhooks to event table
- show payment status in the main dashboard

### Gap 5: No unified CEO reporting loop

Evidence:

- multiple dashboards and reports exist
- no single operational truth surface

Fix:

- create one nerve-center dashboard backed by Supabase event and alert tables

## Recommended Tool Ownership

Use each platform for one thing on purpose.

### Hive

- strategic reasoning
- prioritization
- synthesis

### MCP

- shared context and tool access for agents

### n8n

- event automation
- approvals
- retries
- notifications

### Supabase

- auth
- Postgres
- storage
- edge functions
- cron
- realtime dashboards

### GitHub

- source control
- CI/CD
- deploy gates
- issue/backlog hygiene

### Stripe

- subscriptions
- one-time checkout
- invoicing
- overages
- partner payouts later

### Blinko

- memory and RAG

### Langfuse

- model observability

### Netdata

- infra/process monitoring

### Google

- Gmail outreach
- Drive asset flow
- Docs/report distribution
- Calendar approvals or calls

### Seedance

- video/ad creative production

## 30 / 60 / 90 Day Upgrade Path

### Days 1-30

- pick one system of record: Supabase
- define event schema
- wire n8n, Stripe, Hive, and site publishing to write events
- create CEO dashboard
- add Slack incident and summary channels
- expose MCP resources for core business state
- instrument Hive and key automations with Langfuse

### Days 31-60

- move n8n to queue mode
- add approval workflows
- productionize one monetization loop end-to-end:
  - Hive Mind SaaS, or
  - Daily Gear Drop, or
  - Broker OS
- add customer onboarding and failed-payment automations
- add weekly business review packet generated automatically

### Days 61-90

- launch second and third monetization loops on same event model
- add usage-based billing where appropriate
- add partner payouts or referral tracking
- add A/B testing for offers and landing pages
- prune low-performing flows aggressively

## What A Real Operator Would Do

A serious operator would simplify the company into:

- one front door
- one data layer
- one billing system
- one event log
- one dashboard
- one alert policy
- a small number of repeatable revenue loops

They would not try to manage ten half-connected systems by memory.

They would make the company answer these questions at any time:

- What made money today?
- What broke today?
- What should the agents do next?
- What requires human approval?
- What can be safely automated tomorrow?

## Final Recommendation

Your best move is to build "Everlight Business OS", not "more bots".

That means:

1. Supabase as source of truth.
2. n8n as event bus.
3. Hive as executive reasoning.
4. MCP as shared context surface.
5. Blinko as memory.
6. Langfuse plus Netdata as observability.
7. Stripe as monetization backbone.
8. One CEO dashboard over all of it.

If you do that, the system stops feeling like "salesforce, openai, anthropic, google, crypto and cloud had a baby" and starts behaving like an actual company with machine operators.
