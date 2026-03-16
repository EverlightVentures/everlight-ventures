# Data Model -- Everlight Hive Mind SaaS
# Phase 0 Spec | Version 1.0 | 2026-02-27
# Format: Business-level entity descriptions and relationships (not SQL)

---

## Overview

The data model is organized around three core concepts:
1. Tenants own everything. Every record belongs to exactly one tenant.
2. Sessions are the unit of work. A session is one AI hive job from creation to output.
3. Integrations are the connective tissue. Sessions use integrations; integrations are managed in the vault.

---

## Entities

---

### TENANT
The top-level organizational unit. One tenant = one workspace = one billing account.

Fields:
- id: unique identifier (UUID)
- name: workspace display name
- owner_email: primary contact email
- plan: current subscription tier (trial, spark, hive, enterprise)
- trial_ends_at: timestamp -- null if not on trial
- onboarding_complete: boolean
- created_at: timestamp
- timezone: IANA timezone string (e.g., "America/Los_Angeles")
- slack_workspace_id: foreign key to SLACK_CONNECTION (nullable)
- default_audit_channel: Slack channel name for session logs

Relationships:
- Has many USERS (MVP: just the owner; Phase 2: team members)
- Has many INTEGRATIONS
- Has many SESSIONS
- Has one SUBSCRIPTION
- Has many WEBHOOK_ENDPOINTS

---

### USER
A person who can log into the dashboard. In MVP, every tenant has exactly one user (the owner). Phase 2 introduces team members.

Fields:
- id: UUID
- tenant_id: foreign key to TENANT
- email: unique login identifier
- name: display name
- role: enum (owner, editor, viewer) -- MVP only "owner" is used
- auth_provider: enum (email, google)
- auth_provider_id: Google sub or null
- password_hash: bcrypt hash or null (null for OAuth users)
- email_verified: boolean
- last_login_at: timestamp
- created_at: timestamp

Relationships:
- Belongs to one TENANT
- Creates SESSIONS (session has a created_by user_id)
- Has NOTIFICATION_PREFERENCES (subdocument or related table)

---

### INTEGRATION
A connected third-party service. Each integration holds encrypted credentials for one external API or service.

Fields:
- id: UUID
- tenant_id: foreign key to TENANT
- provider: enum (openai, anthropic, google_ai, perplexity, slack, google_drive, notion, gmail, shopify)
- display_name: tenant-editable label (e.g., "My OpenAI Key")
- encrypted_credential: AES-256-GCM encrypted blob
- credential_hint: last 4 chars of the key for display only
- status: enum (active, error, revoked, untested)
- last_tested_at: timestamp
- last_used_at: timestamp
- last_error_message: string or null
- created_at: timestamp

Relationships:
- Belongs to one TENANT
- Referenced by SESSIONS (a session may require one or more integrations)

Security note: encrypted_credential is never returned by any API endpoint. Only credential_hint and status are exposed.

---

### SESSION
The core unit of work. One session represents one AI hive job from creation through output delivery.

Fields:
- id: UUID
- tenant_id: foreign key to TENANT
- created_by: foreign key to USER
- name: human-readable session name
- task_type: enum (content, research, support, outreach, ops, code, summary, custom)
- template_id: foreign key to SESSION_TEMPLATE or null (custom sessions)
- status: enum (draft, queued, running, completed, failed, timed_out, cancelled)
- schedule_type: enum (manual, recurring, webhook)
- cron_expression: string or null (for recurring sessions)
- webhook_endpoint_id: foreign key to WEBHOOK_ENDPOINT or null
- context_variables: JSON object (tenant-provided fill-in variables)
- estimated_cost_usd: decimal computed before dispatch
- actual_cost_usd: decimal populated after completion
- model_routing: JSON object recording which model handled which subtask
- output_id: foreign key to SESSION_OUTPUT or null
- started_at: timestamp or null
- completed_at: timestamp or null
- error_message: string or null
- created_at: timestamp
- version: integer (increments on re-run)

Relationships:
- Belongs to one TENANT
- Created by one USER
- Optionally derived from one SESSION_TEMPLATE
- Has one SESSION_OUTPUT (when complete)
- Has many SESSION_EVENTS (the audit trail)
- Optionally triggered by one WEBHOOK_ENDPOINT

---

### SESSION_OUTPUT
The result of a completed session. Stored separately from the session to keep the session record lightweight.

Fields:
- id: UUID
- session_id: foreign key to SESSION
- tenant_id: foreign key to TENANT (denormalized for query efficiency)
- content_markdown: full output text in Markdown
- content_json: structured output if the task type produces structured data
- model_attribution: JSON array -- each element records { subtask_name, model, token_count, cost_usd }
- word_count: integer
- total_tokens_used: integer
- delivery_status: enum (pending, delivered, delivery_failed)
- delivered_to: string (e.g., "Slack: #content-drafts", "Email: owner@example.com")
- created_at: timestamp

Relationships:
- Belongs to one SESSION
- Belongs to one TENANT

---

### SESSION_EVENT
The immutable internal audit log. One record per meaningful thing that happened during a session. This is separate from the Slack log and cannot be modified or deleted by tenants.

Fields:
- id: UUID
- session_id: foreign key to SESSION
- tenant_id: foreign key to TENANT
- event_type: enum (session_started, subtask_dispatched, model_response_received, output_merged, output_delivered, error_occurred, retry_attempted, fallback_used, session_completed, session_failed)
- model: which AI model was involved (or null for non-model events)
- detail: JSON blob with event-specific metadata
- occurred_at: timestamp (UTC)

Relationships:
- Belongs to one SESSION
- Belongs to one TENANT
- Immutable after creation

---

### SESSION_TEMPLATE
A pre-built session recipe. Tenants can use platform templates or create their own.

Fields:
- id: UUID
- tenant_id: UUID or null (null = platform-provided global template)
- name: display name (e.g., "Weekly Content Calendar")
- description: short explanation of what this template does
- task_type: maps to SESSION.task_type
- required_integrations: JSON array of provider enums
- context_variable_schema: JSON Schema definition of the variables the tenant must fill in
- default_model_routing: JSON object of subtask-to-model assignments
- is_public: boolean (Phase 2: community sharing)
- created_at: timestamp
- updated_at: timestamp

Relationships:
- Optionally belongs to one TENANT (null = global)
- Used by many SESSIONS

---

### WEBHOOK_ENDPOINT
An inbound URL that, when POSTed to, triggers a linked session.

Fields:
- id: UUID
- tenant_id: foreign key to TENANT
- session_template_id: foreign key to SESSION_TEMPLATE
- secret: a shared secret used to validate incoming requests (HMAC-SHA256)
- label: human-readable name
- last_triggered_at: timestamp or null
- trigger_count: integer
- is_active: boolean
- created_at: timestamp

Relationships:
- Belongs to one TENANT
- Linked to one SESSION_TEMPLATE
- Each trigger creates one SESSION

---

### SUBSCRIPTION
Billing state for a tenant. Mirrors Stripe subscription data but is cached locally for fast entitlement checks without a Stripe API call on every request.

Fields:
- id: UUID
- tenant_id: foreign key to TENANT (unique -- one subscription per tenant)
- stripe_customer_id: Stripe customer object ID
- stripe_subscription_id: Stripe subscription object ID or null (null = trial)
- plan: enum (trial, spark, hive, enterprise)
- status: enum (trialing, active, past_due, cancelled, paused)
- current_period_start: timestamp
- current_period_end: timestamp
- sessions_used_this_period: integer
- sessions_limit: integer or null (null = unlimited)
- integrations_limit: integer or null
- cancel_at_period_end: boolean
- updated_at: timestamp (updated on every Stripe webhook)

Relationships:
- Belongs to one TENANT
- Referenced when checking entitlements before running a session

---

### SLACK_CONNECTION
OAuth connection details for a tenant's Slack workspace.

Fields:
- id: UUID
- tenant_id: foreign key to TENANT
- slack_team_id: Slack workspace ID
- slack_team_name: display name of the Slack workspace
- bot_access_token: encrypted Slack bot token
- authed_user_id: Slack user ID of the person who authorized
- default_channel_id: Slack channel ID for audit logs
- default_channel_name: human-readable channel name (cached)
- is_active: boolean
- created_at: timestamp

Relationships:
- Belongs to one TENANT
- Used by SESSION_EVENTS to post audit log messages

---

## Key Relationships Summary

```
TENANT
  |-- has many --> USER
  |-- has many --> INTEGRATION
  |-- has many --> SESSION
  |                  |-- has one  --> SESSION_OUTPUT
  |                  |-- has many --> SESSION_EVENT
  |                  |-- may use  --> SESSION_TEMPLATE
  |                  |-- may use  --> WEBHOOK_ENDPOINT
  |-- has many --> SESSION_TEMPLATE (custom)
  |-- has many --> WEBHOOK_ENDPOINT
  |-- has one  --> SUBSCRIPTION
  |-- has one  --> SLACK_CONNECTION
```

---

## Multi-Tenancy Enforcement

Every table except SESSION_TEMPLATE (for global templates) has a tenant_id column. The data access layer (DAL) must enforce tenant_id in every query. This is not optional -- it is the primary security boundary. Cross-tenant data leakage via missing tenant_id filters is treated as a critical security bug with a P0 fix priority.

---

## Phase 2 Additions (Not in MVP)

- TEAM_INVITATION: pending invites with email + role before USER record exists
- AGENT_MEMORY: persistent cross-session context store per tenant
- MINDMAP_SNAPSHOT: serialized graph data for the ReactFlow mindmap view
- APPROVAL_STEP: approval chain records linked to SESSION_OUTPUT
- AUDIT_LOG_EXPORT: tenant-initiated data export job records
