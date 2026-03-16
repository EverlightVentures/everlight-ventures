# User Stories -- Everlight Hive Mind SaaS
# Phase 0 Spec | Version 1.0 | 2026-02-27

Stories are grouped by flow. Each story includes a priority (P0 = MVP critical, P1 = MVP nice-to-have, P2 = Phase 2).

---

## Onboarding Flow

**US-001 (P0)**
As a new user, I want to sign up with my Google account so that I can start using the platform without creating another password.

**US-002 (P0)**
As a new user, I want to see a guided 3-step onboarding checklist so that I know exactly what to do to get my first session running.

**US-003 (P0)**
As a new user, I want to enter my OpenAI API key and immediately test whether it works so that I know my integration is active before building my first session.

**US-004 (P1)**
As a new user, I want to see a short explainer video or animated walkthrough on the onboarding screen so that I understand what a "Hive Session" is before I build one.

**US-005 (P0)**
As a new user, I want to complete onboarding using a pre-built session template so that I can see a real output within 8 minutes of signing up without having to design a workflow from scratch.

---

## Integration Setup Flow

**US-006 (P0)**
As a tenant, I want to add and save multiple API keys (OpenAI, Anthropic, Google AI, Perplexity) in the Integration Vault so that the hive can use my own model access and I am not billed on top of my subscription for model tokens.

**US-007 (P0)**
As a tenant, I want to connect my Slack workspace so that all hive session activity is automatically logged to a channel of my choice.

**US-008 (P0)**
As a tenant, I want to see the connection status (active, expired, error) for every integration on a single screen so that I can diagnose problems without opening each integration individually.

**US-009 (P1)**
As a tenant, I want to revoke an API key from the Integration Vault and confirm it has been deleted so that I can rotate credentials without residual security risk.

**US-010 (P1)**
As a tenant, I want to receive an email alert when one of my connected API keys starts failing so that I do not lose sessions to a silent credential error.

---

## Hive Session Creation Flow

**US-011 (P0)**
As a tenant, I want to create a new Hive Session by choosing a task type from a list so that I do not need to know how to prompt-engineer the AI myself.

**US-012 (P0)**
As a tenant, I want to select a session template (e.g., "Weekly Content Calendar") and fill in my context variables (business name, target audience, topics) so that I get a personalized output with minimal setup.

**US-013 (P0)**
As a tenant, I want to set a recurring schedule for a session (daily at 8 AM, every Monday at 9 AM, etc.) so that the hive runs my workflows automatically without me triggering them manually.

**US-014 (P0)**
As a tenant, I want to run a session manually on demand with a single click so that I can test it or use it when I need a one-off output.

**US-015 (P1)**
As a tenant, I want to see an estimated cost in USD before I run a session so that I can decide whether to proceed without worrying about runaway AI spend.

---

## Hive Session Execution and Output Flow

**US-016 (P0)**
As a tenant, I want to see a live status indicator while a session is running (queued, dispatching, generating, merging, delivering) so that I know the hive is working and not frozen.

**US-017 (P0)**
As a tenant, I want to view the full output of a completed session in the dashboard so that I can review, copy, or download the result.

**US-018 (P0)**
As a tenant, I want to see which AI model contributed to each section of a session output so that I understand how the hive assigned the work and can adjust preferences if needed.

**US-019 (P0)**
As a tenant, I want to receive a Slack notification when a session completes, with a summary of the output and a link to view the full result, so that I can stay informed without checking the dashboard constantly.

**US-020 (P1)**
As a tenant, I want to re-run a previous session with a single click so that I can regenerate an output without rebuilding the session configuration.

---

## Mindmap Flow (Phase 2)

**US-021 (P2)**
As a tenant, I want to view an interactive node graph (mindmap) showing how the hive routed a session -- which model handled which subtask and how results were merged -- so that I can understand and trust the AI's decision-making process.

**US-022 (P2)**
As a tenant, I want to click on any node in the mindmap and see the raw prompt and response for that subtask so that I can diagnose why an output was unsatisfactory.

---

## Billing Flow

**US-023 (P0)**
As a new user on a free trial, I want to see a clear countdown of how many trial days I have remaining and what happens when the trial ends so that I am not surprised by a charge.

**US-024 (P0)**
As a tenant, I want to enter my credit card and subscribe to a plan from within the dashboard so that I can continue using the platform after the trial without contacting support.

**US-025 (P0)**
As a tenant, I want to view my current plan, billing period, usage consumed this month, and next invoice amount on a single billing screen so that I always know where I stand.

**US-026 (P1)**
As a tenant, I want to upgrade from Spark to Hive with one click from within the dashboard so that I can unlock more sessions and integrations without going through a separate sales process.

**US-027 (P1)**
As a tenant, I want to access a self-serve billing portal where I can download past invoices and update my payment method so that I do not need to contact support for routine billing tasks.

---

## Support and Admin Flow

**US-028 (P1)**
As a tenant, I want to submit a support ticket from within the dashboard (with my account context auto-attached) so that I can get help without copy-pasting my account details into a separate form.

**US-029 (P2)**
As a workspace owner, I want to invite a team member by email and assign them an editor or viewer role so that my team can collaborate on hive sessions without sharing my credentials.

**US-030 (P0)**
As a tenant, I want to configure which Slack channel receives audit logs so that different workflows can log to different channels and I can keep my workspace organized.

---

## Summary Table

| Story | Priority | Flow |
|-------|----------|------|
| US-001 | P0 | Onboarding |
| US-002 | P0 | Onboarding |
| US-003 | P0 | Integration Setup |
| US-004 | P1 | Onboarding |
| US-005 | P0 | Onboarding |
| US-006 | P0 | Integration Setup |
| US-007 | P0 | Integration Setup |
| US-008 | P0 | Integration Setup |
| US-009 | P1 | Integration Setup |
| US-010 | P1 | Integration Setup |
| US-011 | P0 | Session Creation |
| US-012 | P0 | Session Creation |
| US-013 | P0 | Session Creation |
| US-014 | P0 | Session Creation |
| US-015 | P1 | Session Creation |
| US-016 | P0 | Session Execution |
| US-017 | P0 | Session Execution |
| US-018 | P0 | Session Execution |
| US-019 | P0 | Session Execution |
| US-020 | P1 | Session Execution |
| US-021 | P2 | Mindmap |
| US-022 | P2 | Mindmap |
| US-023 | P0 | Billing |
| US-024 | P0 | Billing |
| US-025 | P0 | Billing |
| US-026 | P1 | Billing |
| US-027 | P1 | Billing |
| US-028 | P1 | Support |
| US-029 | P2 | Admin |
| US-030 | P0 | Support |
