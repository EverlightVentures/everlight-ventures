# PRD -- Everlight Hive Mind SaaS
# Phase 0 Spec | Version 1.0 | 2026-02-27

---

## Executive Summary

Everlight Hive Mind is a multi-tenant SaaS platform that gives solopreneurs, small businesses, and agencies an AI-powered Chief of Staff. Clients connect their API keys and project folders through a premium web dashboard, then assign autonomous AI agents -- drawn from a quad-AI hive (Claude, Gemini, Codex, Perplexity) -- to handle workflows, sales outreach, customer support, subscription management, and operations. Every agent action is logged to Slack for full human audit control.

The core insight: the technology already exists and works (proven in the Everlight OS). The gap in the market is a clean, managed, multi-tenant delivery layer that eliminates the DIY setup, prompt engineering expertise, and infrastructure overhead for non-technical buyers.

---

## Problem Statement

Small business operators are drowning in repeatable, low-decision-overhead work: drafting replies, routing support tickets, generating weekly reports, scheduling follow-ups, producing content, monitoring integrations. They know AI can do most of this. The barrier is not awareness -- it is the setup cost, the need for a developer, and the fragmentation of AI tools.

Existing solutions fall into three broken categories:

1. Single-AI tools (ChatGPT Plus, Claude.ai) -- require constant prompting, no automation, no integrations, no memory across sessions.
2. Automation platforms (Zapier, Make.com) -- require technical configuration, lack true reasoning, cannot adapt to ambiguous inputs.
3. Developer frameworks (LangChain, AutoGPT) -- require engineering skill, offer no managed hosting, no billing, no SaaS wrapper.

No product currently offers: a fully managed, multi-AI hive that autonomously handles real business workflows, operates behind a clean dashboard, logs all actions to Slack, and is ready to use without any setup beyond connecting API keys.

---

## Solution

Everlight Hive Mind is a managed AI operations platform. The client:

1. Signs up and verifies identity.
2. Connects their existing API keys (OpenAI, Anthropic, Google, Perplexity) and project context (Google Drive folders, Notion workspaces, Slack channels, email accounts).
3. Defines a Hive Session: a named workflow task with a scope, output type, and target (e.g., "Weekly sales outreach draft" or "Respond to all support tickets older than 4 hours").
4. The platform dispatches the right AI agents from the hive, routes subtasks across models by specialty, collects outputs, and delivers them to the defined destination.
5. All steps are logged to the client's Slack workspace with a full audit trail.

The client does not prompt-engineer. They configure once, then the hive works autonomously on a schedule or trigger.

---

## Core MVP Features (Phase 1, Months 0-2)

### F01 -- Multi-Tenant Auth and Onboarding
Google OAuth and email/password sign-up. New tenant gets an isolated workspace with a unique tenant_id. Guided 3-step onboarding: (1) connect first integration, (2) create first session, (3) verify Slack logging. Onboarding completion rate is a primary activation metric.

### F02 -- Integration Vault (API Key Manager)
Secure, encrypted storage for third-party API keys (OpenAI, Anthropic, Google AI, Perplexity, Slack). AES-256 encryption at rest. Keys are never exposed in plaintext after initial entry. Per-integration connection test on save. Tenant can view connection status, last-used timestamp, and revoke at any time.

### F03 -- Hive Session Builder
Create a named session by selecting: task type (content, support, research, outreach, ops), target integration, output format, and schedule (manual, recurring cron, or webhook trigger). Session config is stored and versioned. MVP supports 8 task types with templates.

### F04 -- AI Hive Dispatcher
Core engine. Routes session tasks to the appropriate model based on task type:
- Research tasks: Perplexity
- Code/automation tasks: Codex (OpenAI)
- Long-form writing/analysis: Claude
- SEO/structured content: Gemini

Tasks requiring multi-model synthesis are broken into subtasks, each model completes its step, and results are merged by a designated lead model (default: Claude). All routing logic is tenant-configurable.

### F05 -- Slack Audit Logger
Every agent action (session start, subtask dispatch, model response received, output delivered, error) is posted to a tenant-configured Slack channel. Structured log format with timestamps, model used, cost estimate, and output preview. Client can reply in Slack to approve, reject, or re-run any session output.

### F06 -- Session Output Viewer
Web dashboard view of every completed session: full output text, model breakdown (which AI contributed what), cost summary, and delivery status. Outputs can be downloaded as Markdown, JSON, or plain text.

### F07 -- Basic Dashboard Home
Metrics overview: sessions run today/this week, estimated cost, active integrations count, last session status. Recent activity feed. Quick-launch button to start a new session.

### F08 -- Billing and Subscription Management
Stripe-powered subscription tiers. Tenant selects plan at end of free trial. Usage meter tracks sessions consumed. Hard limits enforced at tier ceiling. Upgrade flow from dashboard. Billing portal for invoice history, plan changes, and cancellation. Webhook-driven entitlement updates.

### F09 -- Session Templates Library
Pre-built session templates for the 12 most common small business AI workflows: weekly content calendar, support ticket triage, sales follow-up drafts, invoice reminder emails, SEO keyword research, competitor monitoring, weekly P&L summary, meeting notes cleanup, product description generation, social media posting queue, customer onboarding email sequence, and ad copy variations. Templates are fill-in-the-blank; the tenant provides their context variables.

### F10 -- User Profile and Workspace Settings
Tenant name, billing contact, timezone, notification preferences, Slack workspace connection, default AI model preferences. Supports one owner account per workspace in MVP (multi-user is Phase 2).

### F11 -- Cost Estimation and Usage Tracking
Before running a session, display an estimated token cost in USD. After completion, record actual cost. Per-session cost log. Monthly cost summary. Alerts when projected monthly AI cost exceeds a tenant-configured threshold. This directly addresses the "runaway AI spend" anxiety that is a top adoption barrier.

### F12 -- Webhook Trigger Endpoints
Each tenant gets unique inbound webhook URLs. Posting to a webhook URL triggers a linked Hive Session. Used to trigger AI workflows from Zapier, Make.com, form submissions, or external events without requiring a full integration setup.

### F13 -- Session History and Replay
Full searchable history of every session. Filter by date range, task type, model, integration, and status. Re-run any historical session with one click. Diff view between two runs of the same session.

### F14 -- Error Handling and Retry Logic
If a model call fails (rate limit, API outage, timeout), the hive automatically retries with exponential backoff on the same model, then falls back to an alternate model in the same category. Tenant sees a clear error state in the dashboard, not a silent failure.

### F15 -- Email Notification Digest
Daily or weekly email digest summarizing: sessions completed, total cost, any errors, and a link to this week's output highlights. Tenant can configure digest frequency or disable.

---

## Non-MVP Features (Phase 2 and Beyond)

- Interactive Mindmap: Visual graph showing agent-to-agent task routing for each session (using ReactFlow -- already in dashboard dependencies).
- Multi-User Workspaces: Invite team members with role-based access (owner, editor, viewer).
- Integrations Marketplace: 50+ pre-built integration connectors (Gmail, HubSpot, Shopify, Notion, Airtable, Stripe, Twilio, etc.).
- White-Label Mode: Custom domain, logo, and brand colors for agency resale.
- Agent Memory Store: Cross-session persistent memory so the hive "knows" the client's business context without re-prompting.
- Voice Input Sessions: Record a voice note; hive transcribes and dispatches a session.
- Client Portal Mode: Agency clients can view outputs in a read-only portal without accessing the full dashboard.
- Custom Model Fine-Tuning: Connect a fine-tuned model hosted externally.
- Approval Workflows: Route session outputs through an approval chain before delivery.
- Enterprise SSO (SAML/OKTA).
- SOC 2 Type II Certification.
- Dedicated Compute Tier: On-demand isolated worker for burst workloads.

---

## Success Metrics

### Activation
- Onboarding completion rate (steps 1-3 completed): target 60% by Month 2.
- Time-to-first-session: target under 8 minutes from sign-up to first session run.

### Engagement
- Weekly active sessions per tenant: target 5+ for paying tenants.
- Session template adoption rate: target 70% of new tenants use a template for their first session.

### Revenue
- MRR target Month 3: $10,000 (approx. 78 paying tenants blended at ~$128 ARPU).
- Net Revenue Retention at Month 6: 105%+ (expansion via plan upgrades).
- Trial-to-paid conversion: target 25%.

### Retention
- Month 1 churn: below 8%.
- Month 3 churn: below 5%.
- NPS at Month 3: 40+.

### Support
- Median first response time: under 2 hours.
- Support ticket volume per 100 active tenants: below 15 per week.

---

## Competitive Landscape

### Zapier AI (Zapier Agents)
Strength: Massive integration library (6,000+ apps), established brand trust.
Weakness: Not truly autonomous -- still requires manual trigger/action mapping. AI layer is thin. No multi-model routing. No audit trail. $69-$799/mo (Tables + Interfaces + Agents bundled chaotically).
Our edge: True multi-model hive reasoning. Clean AI-first UX. Slack audit log. Transparent per-session cost.

### Make.com
Strength: Visual automation builder, strong power-user base, lower pricing than Zapier.
Weakness: Zero AI reasoning -- pure if/then logic. Steep learning curve. No language model integration native to the product.
Our edge: No-config required. The hive reasons; the client does not need to build logic.

### Notion AI
Strength: Embedded in a popular workspace product. Context-aware to Notion documents.
Weakness: Locked to Notion ecosystem. Not an autonomous agent. No cross-platform workflow execution.
Our edge: Platform-agnostic. Works across the client's existing tools.

### AutoGPT / AgentGPT (Open Source)
Strength: Free. Fully flexible. Active community.
Weakness: Requires self-hosting, developer skill, no support, frequent breakage, no billing, no security boundaries, no multi-tenancy. Not suitable for non-technical buyers.
Our edge: Fully managed. Zero setup. Enterprise-grade security. Works out of the box.

### Relevance AI
Strength: No-code AI agent builder. Growing integration set.
Weakness: Complex builder UI. Workflow-oriented, not hive-oriented. No audit trail. Positioned toward enterprise only.
Our edge: SMB-accessible pricing. AI Chief of Staff positioning. Slack-native audit trail.

### ChatGPT Team ($30/user/mo)
Strength: Brand recognition. Quality model. Shared workspace.
Weakness: Still requires human prompting. No autonomous scheduling. No integrations. No audit trail.
Our edge: Fully autonomous. Zero prompting. Runs while the client sleeps.

---

## Ideal Customer Profile (ICP) -- First 100 Customers

### Primary ICP: The Overextended Solopreneur

Demographics: Solo business owner, 1-5 years in business, annual revenue $80,000-$400,000, no full-time employees or 1-2 part-time contractors. Industries: digital agency, content creator with a product/course, online coach, freelance consultant, e-commerce operator with their own brand.

Tech stack: Google Workspace or Notion, Stripe or Shopify, Slack for personal comms. Has at least one paid AI subscription already (ChatGPT Plus, Claude Pro, or Jasper). Comfortable with SaaS tools but not a developer.

Pain: Spends 2-4 hours per day on repeatable tasks that feel like they "should be automated." Has tried to set up Zapier or ChatGPT workflows but abandoned them due to complexity or unreliability. Feels like AI tools require too much babysitting.

Budget: $100-$200/mo for tools that demonstrably save time. Makes purchasing decisions quickly if the ROI is obvious.

Decision trigger: A friend or peer recommends it and shows them a working example. Or they find it via a YouTube tutorial or Twitter/X thread.

Success looks like: "I set it up on Sunday and it ran my weekly content calendar, responded to 12 support emails, and drafted my sales follow-up sequence while I was at the gym Monday morning."

### Secondary ICP: The 2-5 Person Agency

A small digital marketing, content, or development agency doing $300,000-$1,500,000 ARR. Owner is technical enough to set up API keys. Has 2-5 staff who do execution work that is largely templated. Already spending $500-$2,000/mo on tools.

Pain: Client deliverable volume has outpaced team capacity. Wants AI to handle first-draft production and reporting while the team handles client relationships and quality review.

Value driver: The white-label and multi-user features (Phase 2) are the long-term unlock. In MVP they pay for Hive tier ($129/mo) and use it for their own ops.

### What the First 100 Are NOT

Not enterprise (Fortune 500) -- too slow of a sales cycle and too high a compliance bar for MVP. Not developers -- they have their own tools. Not pure e-commerce with no services component -- limited workflow surface area for AI.
