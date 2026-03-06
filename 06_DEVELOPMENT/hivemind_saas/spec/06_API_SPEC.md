# API Specification -- Everlight Hive Mind SaaS
# Phase 0 Spec | Version 1.0 | 2026-02-27
# Base URL: https://api.hivemind.everlightventures.com/v1
# Auth: Bearer token (JWT) in Authorization header on all endpoints except /auth/*

---

## Conventions

- All timestamps are ISO 8601 UTC strings.
- All IDs are UUIDs.
- Errors always return: { "error": { "code": "ERROR_CODE", "message": "Human-readable description" } }
- Pagination uses cursor-based pagination: { "data": [...], "next_cursor": "...", "has_more": true }
- Tenant context is inferred from the JWT -- never passed as a query param.

---

## Auth

---

### POST /auth/login
Email/password login. Returns JWT and refresh token.

Request:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123"
}
```

Response 200:
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "tenant_id": "ten_abc123",
  "user": {
    "id": "usr_xyz789",
    "email": "user@example.com",
    "name": "Jane Doe",
    "role": "owner"
  }
}
```

Response 401:
```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Email or password is incorrect."
  }
}
```

Refresh token is set as an HttpOnly cookie on the response. Not in the JSON body.

---

### POST /auth/logout
Invalidates the refresh token server-side.

Request: No body. JWT in Authorization header.

Response 204: No content.

---

### GET /auth/oauth/google
Initiates Google OAuth flow. Redirects to Google consent screen.

Query params:
- redirect_uri: URL to return to after auth (must be in allowlist)

Response: 302 redirect to Google OAuth URL.

---

### GET /auth/oauth/callback
OAuth callback handler. Exchanges code for token, creates or retrieves user.

Query params:
- code: OAuth authorization code
- state: CSRF state token

Response 302: Redirects to dashboard with access token in URL fragment (then immediately exchanged via POST to /auth/token/exchange -- not stored in URL history).

---

### POST /auth/register
Email/password registration.

Request:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123",
  "workspace_name": "Acme Agency"
}
```

Response 201:
```json
{
  "message": "Account created. Please check your email to verify your address.",
  "tenant_id": "ten_abc123",
  "user_id": "usr_xyz789"
}
```

---

### POST /auth/verify-email
Verifies email using token from email link.

Request:
```json
{
  "token": "verify_tok_abc123"
}
```

Response 200:
```json
{
  "message": "Email verified successfully.",
  "access_token": "eyJhbGci..."
}
```

---

## Tenants

---

### GET /tenants/me
Returns the current tenant's workspace details and onboarding state.

Response 200:
```json
{
  "id": "ten_abc123",
  "name": "Acme Agency",
  "plan": "trial",
  "trial_ends_at": "2026-03-06T00:00:00Z",
  "onboarding_complete": false,
  "onboarding_steps": {
    "integration_connected": true,
    "session_created": false,
    "slack_verified": false
  },
  "created_at": "2026-02-27T10:00:00Z",
  "timezone": "America/Los_Angeles"
}
```

---

### PATCH /tenants/settings
Updates workspace settings.

Request:
```json
{
  "name": "Acme Digital",
  "timezone": "America/New_York",
  "default_audit_channel": "hive-logs",
  "notification_preferences": {
    "digest_frequency": "weekly",
    "email_on_session_complete": false,
    "email_on_error": true
  }
}
```

Response 200: Updated tenant object (same shape as GET /tenants/me).

---

## Integrations

---

### GET /integrations
List all integrations for the current tenant.

Response 200:
```json
{
  "data": [
    {
      "id": "int_aaa111",
      "provider": "openai",
      "display_name": "My OpenAI Key",
      "status": "active",
      "credential_hint": "k9Qz",
      "last_tested_at": "2026-02-27T09:30:00Z",
      "last_used_at": "2026-02-27T10:15:00Z",
      "last_error_message": null,
      "created_at": "2026-02-25T08:00:00Z"
    }
  ]
}
```

---

### POST /integrations
Add a new integration.

Request:
```json
{
  "provider": "openai",
  "display_name": "My OpenAI Key",
  "credential": "sk-proj-abc...xyz"
}
```

Response 201:
```json
{
  "id": "int_bbb222",
  "provider": "openai",
  "display_name": "My OpenAI Key",
  "status": "active",
  "credential_hint": "cxyz",
  "last_tested_at": "2026-02-27T10:20:00Z",
  "test_result": {
    "success": true,
    "message": "Connection verified successfully."
  }
}
```

Note: The raw credential value is never returned in any response.

---

### GET /integrations/:id
Get a single integration by ID.

Response 200: Same shape as a single item from GET /integrations list (no credential field).

---

### PATCH /integrations/:id
Update an integration's display name or credential.

Request:
```json
{
  "display_name": "Primary OpenAI Key",
  "credential": "sk-proj-new...key"
}
```

Response 200: Updated integration object.

---

### DELETE /integrations/:id
Revoke and delete an integration.

Response 204: No content.

Side effects: Any scheduled sessions requiring this integration are paused. Tenant is notified via email and Slack.

---

### POST /integrations/:id/test
Re-test an existing integration's connection.

Response 200:
```json
{
  "status": "active",
  "test_result": {
    "success": true,
    "message": "Connection verified successfully.",
    "tested_at": "2026-02-27T10:25:00Z"
  }
}
```

---

## Sessions

---

### POST /sessions
Create and optionally start a new hive session.

Request:
```json
{
  "name": "Weekly Content Calendar -- Week of Mar 3",
  "task_type": "content",
  "template_id": "tmpl_content_calendar",
  "context_variables": {
    "business_name": "Acme Agency",
    "target_audience": "Small business owners aged 30-50",
    "topics": ["AI tools", "productivity", "client acquisition"],
    "tone": "professional but approachable",
    "output_format": "5 post ideas with hooks and CTAs"
  },
  "schedule_type": "manual",
  "run_immediately": true
}
```

Response 202 (accepted and queued):
```json
{
  "id": "sess_xyz111",
  "name": "Weekly Content Calendar -- Week of Mar 3",
  "status": "queued",
  "task_type": "content",
  "estimated_cost_usd": 0.04,
  "created_at": "2026-02-27T10:30:00Z",
  "poll_url": "/v1/sessions/sess_xyz111"
}
```

---

### GET /sessions/:id
Get the current state of a session.

Response 200:
```json
{
  "id": "sess_xyz111",
  "name": "Weekly Content Calendar -- Week of Mar 3",
  "status": "completed",
  "task_type": "content",
  "template_id": "tmpl_content_calendar",
  "schedule_type": "manual",
  "estimated_cost_usd": 0.04,
  "actual_cost_usd": 0.037,
  "model_routing": {
    "research": "perplexity",
    "draft": "claude",
    "seo_formatting": "gemini"
  },
  "output_id": "out_abc999",
  "started_at": "2026-02-27T10:30:05Z",
  "completed_at": "2026-02-27T10:31:22Z",
  "created_at": "2026-02-27T10:30:00Z",
  "created_by": "usr_xyz789"
}
```

---

### GET /sessions
List sessions for the current tenant.

Query params:
- status: filter by status (optional)
- task_type: filter by type (optional)
- limit: integer 1-100, default 20
- cursor: pagination cursor (optional)
- from: ISO date start range (optional)
- to: ISO date end range (optional)

Response 200:
```json
{
  "data": [
    {
      "id": "sess_xyz111",
      "name": "Weekly Content Calendar -- Week of Mar 3",
      "status": "completed",
      "task_type": "content",
      "actual_cost_usd": 0.037,
      "completed_at": "2026-02-27T10:31:22Z",
      "created_at": "2026-02-27T10:30:00Z"
    }
  ],
  "next_cursor": "cur_abc456",
  "has_more": false,
  "total_count": 47
}
```

---

### POST /sessions/:id/rerun
Re-run a previous session using the same configuration and context variables.

Request: No body.

Response 202: Same shape as POST /sessions response, with new session id and status "queued". Links back to parent session via parent_session_id field.

---

### DELETE /sessions/:id
Cancel a queued or running session.

Response 204: No content. If session is already running, it is cancelled at the next safe checkpoint. Partial costs are recorded.

---

## Session Output

---

### GET /sessions/:id/output
Get the full output of a completed session.

Response 200:
```json
{
  "id": "out_abc999",
  "session_id": "sess_xyz111",
  "content_markdown": "## Week of March 3 -- Content Ideas\n\n**Post 1:** ...",
  "model_attribution": [
    {
      "subtask_name": "research",
      "model": "perplexity",
      "token_count": 1200,
      "cost_usd": 0.012
    },
    {
      "subtask_name": "draft",
      "model": "claude",
      "token_count": 2100,
      "cost_usd": 0.021
    }
  ],
  "word_count": 847,
  "total_tokens_used": 3300,
  "delivery_status": "delivered",
  "delivered_to": "Slack: #content-drafts",
  "created_at": "2026-02-27T10:31:22Z"
}
```

Response 404 if session not found or output not yet available (session still running).

---

## Mindmap

---

### GET /sessions/:id/mindmap
Returns the node graph data for a completed session, formatted for ReactFlow rendering.

Response 200:
```json
{
  "session_id": "sess_xyz111",
  "nodes": [
    {
      "id": "node_1",
      "type": "sessionStart",
      "data": { "label": "Session: Weekly Content Calendar", "status": "completed" },
      "position": { "x": 0, "y": 0 }
    },
    {
      "id": "node_2",
      "type": "modelTask",
      "data": {
        "label": "Research",
        "model": "perplexity",
        "status": "completed",
        "token_count": 1200,
        "cost_usd": 0.012,
        "prompt_preview": "Find trending topics in AI tools for small businesses..."
      },
      "position": { "x": 200, "y": -100 }
    },
    {
      "id": "node_3",
      "type": "modelTask",
      "data": {
        "label": "Draft Writing",
        "model": "claude",
        "status": "completed",
        "token_count": 2100,
        "cost_usd": 0.021,
        "prompt_preview": "Using the research below, write 5 social media post ideas..."
      },
      "position": { "x": 200, "y": 100 }
    },
    {
      "id": "node_4",
      "type": "outputDelivery",
      "data": { "label": "Delivered to Slack", "status": "completed" },
      "position": { "x": 400, "y": 0 }
    }
  ],
  "edges": [
    { "id": "e1-2", "source": "node_1", "target": "node_2" },
    { "id": "e1-3", "source": "node_1", "target": "node_3" },
    { "id": "e2-4", "source": "node_2", "target": "node_4" },
    { "id": "e3-4", "source": "node_3", "target": "node_4" }
  ]
}
```

Response 404 if session not found.
Response 425 (Too Early) if session is still running -- client should poll GET /sessions/:id until status = "completed" before fetching mindmap.

---

## Billing

---

### GET /billing/plans
Returns available plan definitions. Public endpoint -- no auth required.

Response 200:
```json
{
  "plans": [
    {
      "id": "spark",
      "name": "Spark",
      "price_monthly_usd": 49,
      "price_annual_usd": 470,
      "sessions_per_month": 100,
      "integrations_limit": 3,
      "users_limit": 1,
      "features": ["Session templates", "Slack audit logging", "Email digest", "Session history"]
    },
    {
      "id": "hive",
      "name": "Hive",
      "price_monthly_usd": 129,
      "price_annual_usd": 1238,
      "sessions_per_month": null,
      "integrations_limit": 20,
      "users_limit": 5,
      "features": ["Everything in Spark", "Unlimited sessions", "Mindmaps", "Webhook triggers", "Priority support"]
    },
    {
      "id": "enterprise",
      "name": "Enterprise",
      "price_monthly_usd": 399,
      "price_annual_usd": 3830,
      "sessions_per_month": null,
      "integrations_limit": null,
      "users_limit": null,
      "features": ["Everything in Hive", "White-label", "Unlimited users", "Dedicated support", "SLA", "Custom integrations"]
    }
  ]
}
```

---

### GET /billing/current
Returns the current tenant's subscription state.

Response 200:
```json
{
  "plan": "hive",
  "status": "active",
  "current_period_end": "2026-03-27T00:00:00Z",
  "sessions_used_this_period": 23,
  "sessions_limit": null,
  "cancel_at_period_end": false,
  "next_invoice_amount_usd": 129.00,
  "payment_method": {
    "brand": "visa",
    "last4": "4242",
    "exp_month": 12,
    "exp_year": 2028
  }
}
```

---

### POST /billing/subscribe
Subscribe to a plan. Creates or updates a Stripe subscription.

Request:
```json
{
  "plan_id": "hive",
  "billing_period": "monthly",
  "payment_method_id": "pm_stripe_tok_abc123"
}
```

Response 200:
```json
{
  "subscription_id": "sub_stripe_xyz",
  "plan": "hive",
  "status": "active",
  "current_period_end": "2026-03-27T00:00:00Z",
  "message": "Subscription activated successfully."
}
```

Response 402:
```json
{
  "error": {
    "code": "PAYMENT_FAILED",
    "message": "Your card was declined. Please try a different payment method."
  }
}
```

---

### POST /billing/portal
Creates a Stripe Customer Portal session for self-serve billing management (invoice download, payment method update, cancellation).

Request: No body.

Response 200:
```json
{
  "portal_url": "https://billing.stripe.com/session/sess_live_abc123",
  "expires_at": "2026-02-27T11:30:00Z"
}
```

Client redirects the user to portal_url. Stripe handles everything from there.

---

### GET /billing/usage
Returns current period usage details.

Response 200:
```json
{
  "billing_period_start": "2026-02-27T00:00:00Z",
  "billing_period_end": "2026-03-27T00:00:00Z",
  "sessions_used": 23,
  "sessions_limit": null,
  "estimated_overage_usd": 0,
  "ai_cost_this_period_usd": 2.14,
  "ai_cost_budget_usd": null,
  "ai_cost_alert_threshold_usd": 50.00
}
```

---

## Webhook Endpoints

---

### GET /webhooks
List all webhook endpoints for the tenant.

Response 200:
```json
{
  "data": [
    {
      "id": "wh_abc123",
      "label": "Trigger from Zapier",
      "session_template_id": "tmpl_support_triage",
      "url": "https://api.hivemind.everlightventures.com/v1/webhooks/wh_abc123/trigger",
      "is_active": true,
      "last_triggered_at": "2026-02-26T14:00:00Z",
      "trigger_count": 12,
      "created_at": "2026-02-20T09:00:00Z"
    }
  ]
}
```

---

### POST /webhooks
Create a new webhook endpoint.

Request:
```json
{
  "label": "Trigger from Contact Form",
  "session_template_id": "tmpl_support_triage"
}
```

Response 201:
```json
{
  "id": "wh_def456",
  "label": "Trigger from Contact Form",
  "session_template_id": "tmpl_support_triage",
  "url": "https://api.hivemind.everlightventures.com/v1/webhooks/wh_def456/trigger",
  "secret": "whsec_abc123xyz789",
  "is_active": true,
  "created_at": "2026-02-27T10:45:00Z"
}
```

Note: The secret is only returned once at creation time. It cannot be retrieved later -- only rotated.

---

### POST /webhooks/:id/trigger
The inbound trigger endpoint. This URL is given to external tools.

Auth: HMAC-SHA256 signature in X-Hive-Signature header (not Bearer JWT).

Request: Any JSON payload. The payload is passed as context_variables to the linked session template.

Response 202:
```json
{
  "session_id": "sess_triggered_ghi789",
  "status": "queued",
  "message": "Session queued successfully."
}
```

---

## Templates

---

### GET /templates
List available session templates (platform + tenant custom).

Query params:
- source: "platform" | "custom" | "all" (default "all")
- task_type: filter by type

Response 200:
```json
{
  "data": [
    {
      "id": "tmpl_content_calendar",
      "name": "Weekly Content Calendar",
      "description": "Generates 5 social media post ideas with hooks and CTAs for the week.",
      "task_type": "content",
      "required_integrations": ["anthropic", "perplexity"],
      "context_variable_schema": {
        "type": "object",
        "properties": {
          "business_name": { "type": "string", "description": "Your business or brand name" },
          "target_audience": { "type": "string", "description": "Who you are writing for" },
          "topics": { "type": "array", "items": { "type": "string" }, "description": "3-5 topics to cover" },
          "tone": { "type": "string", "description": "Tone of voice (e.g., professional, casual)" }
        },
        "required": ["business_name", "target_audience", "topics"]
      },
      "source": "platform",
      "created_at": "2026-01-01T00:00:00Z"
    }
  ]
}
```

---

## Error Codes Reference

| Code | HTTP Status | Meaning |
|------|-------------|---------|
| INVALID_CREDENTIALS | 401 | Wrong email or password |
| TOKEN_EXPIRED | 401 | JWT has expired -- refresh required |
| FORBIDDEN | 403 | Tenant does not own this resource |
| NOT_FOUND | 404 | Resource does not exist |
| INTEGRATION_MISSING | 422 | Required integration not connected |
| PLAN_LIMIT_REACHED | 422 | Session limit for current plan exceeded |
| TRIAL_EXPIRED | 402 | Trial has ended -- payment required |
| PAYMENT_FAILED | 402 | Stripe charge declined |
| RATE_LIMITED | 429 | Too many requests |
| VALIDATION_ERROR | 400 | Request body failed validation |
| INTERNAL_ERROR | 500 | Unexpected server error |
