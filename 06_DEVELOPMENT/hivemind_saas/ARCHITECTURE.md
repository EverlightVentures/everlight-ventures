# Everlight AI Hive Mind -- Multi-Tenant SaaS Architecture

**Version**: 1.0
**Date**: 2026-02-27
**Author**: Everlight Architect (Claude)
**Status**: Approved for Phase 0

---

## 1. Executive Summary

Everlight AI Hive Mind is a multi-tenant SaaS platform that gives businesses their own AI executive team. Each tenant gets a dedicated "war room" where Claude (strategy), Gemini (SEO/structure), Codex (automation), and Perplexity (research) deliberate in parallel on business problems -- producing synthesized, action-ready outputs across content, trading analytics, book publishing, and SaaS product design.

**Target price point**: $49/month (Starter) -- $199/month (Pro) -- $499/month (Agency)
**Core value prop**: Replace 4 different AI subscriptions plus manual stitching with one orchestrated system that thinks like a team, not a chatbot.

---

## 2. Architecture Philosophy

This is a **modular monolith** -- not microservices. All business logic lives in one deployable Python application. Modules have strict internal boundaries (no cross-module direct imports) but share one database and one process. This makes it operationally simple enough to run on Railway/Render's free tier while remaining splittable into services later if scale demands it.

The three governing principles:

1. **Tenant isolation by default** -- PostgreSQL Row-Level Security (RLS) enforces it at the database layer. App code cannot accidentally leak data between tenants even if there is a bug.
2. **Event-driven for live feel** -- Redis pub/sub broadcasts real-time events (step completions, AI responses streaming in) to WebSocket subscribers so the dashboard feels alive, not like a polling loading bar.
3. **API-first** -- Every UI action goes through a FastAPI endpoint. The frontend (React or plain HTMX) is a thin client. This means the same API powers a mobile app, CLI, or Slack bot without rework.

---

## 3. Module Inventory

| Module | Responsibility | Key Tables |
|--------|---------------|------------|
| **Identity** | Auth, session tokens, user profiles | `users` |
| **Tenant** | Tenant lifecycle, plan enforcement, slug routing | `tenants`, `subscriptions` |
| **Integrations** | Store/retrieve encrypted API keys per tenant | `integrations` |
| **Workflow Engine** | Parse requests, build step plans, track runs | `workflow_runs`, `sessions` |
| **AI Orchestrator** | Fan-out to Claude/Gemini/Codex/Perplexity, collect results, synthesize | `messages` |
| **Billing** | Stripe webhooks, subscription sync, usage metering | `subscriptions` |
| **Support** | Ticket ingestion, Slack escalation, internal notes | (Slack + email, no primary table needed at MVP) |
| **Audit/Telemetry** | All events, all Slack notifications sent, structured logs | `slack_audit_log`, `workflow_runs` |

---

## 4. System Architecture Diagram

```mermaid
flowchart TD
    subgraph Client ["Client Layer"]
        WEB["Web Dashboard\n(React / HTMX)"]
        CLI["CLI\n(everlight-cli)"]
        SLACK_BOT["Slack Bot\n(/hive command)"]
    end

    subgraph Gateway ["API Gateway (FastAPI)"]
        AUTH_MW["Auth Middleware\n(Clerk JWT Verify)"]
        ROUTER_API["REST Router\n/api/v1/*"]
        WS["WebSocket Hub\n/ws/session/{id}"]
    end

    subgraph Core ["Modular Monolith (Python)"]
        IDENTITY["Identity Module\nClerk/Supabase Auth"]
        TENANT["Tenant Module\nPlan + Slug"]
        WORKFLOW["Workflow Engine\nRouter + Step Planner"]
        ORCHESTRATOR["AI Orchestrator\nFan-out + Convergence"]
        BILLING["Billing Module\nStripe Webhooks"]
        INTEGRATIONS["Integrations Module\nVault Secret Fetch"]
        AUDIT["Audit Module\nTelemetry + Slack"]
    end

    subgraph AIWorkers ["AI Workers (Async Tasks)"]
        CLAUDE_W["Claude Worker\nStrategy / Architecture"]
        GEMINI_W["Gemini Worker\nSEO / Structure"]
        CODEX_W["Codex Worker\nAutomation / Code"]
        PERP_W["Perplexity Worker\nResearch / Intel Scout"]
    end

    subgraph Data ["Data Layer"]
        PG["PostgreSQL\n+ Row-Level Security"]
        REDIS["Redis\nPub/Sub + Job Queue"]
        VAULT["HashiCorp Vault\nor Encrypted PG Column"]
        S3["Object Storage\nR2 / S3\nArtifact Files"]
    end

    subgraph External ["External Services"]
        STRIPE["Stripe\nBilling"]
        CLERK["Clerk\nSSO + OAuth"]
        SLACK_EXT["Slack Webhooks\nObservability"]
        AI_APIS["AI APIs\nAnthropic / Google /\nOpenAI / Perplexity"]
    end

    WEB -->|HTTPS + JWT| AUTH_MW
    CLI -->|HTTPS + API Key| AUTH_MW
    SLACK_BOT -->|HTTPS + JWT| AUTH_MW
    AUTH_MW --> ROUTER_API
    ROUTER_API --> IDENTITY
    ROUTER_API --> TENANT
    ROUTER_API --> WORKFLOW
    ROUTER_API --> BILLING
    ROUTER_API --> INTEGRATIONS
    WEB <-->|WebSocket| WS

    WORKFLOW -->|enqueue job| REDIS
    REDIS -->|dequeue| ORCHESTRATOR
    ORCHESTRATOR -->|parallel tasks| CLAUDE_W
    ORCHESTRATOR -->|parallel tasks| GEMINI_W
    ORCHESTRATOR -->|parallel tasks| CODEX_W
    ORCHESTRATOR -->|parallel tasks| PERP_W

    CLAUDE_W -->|result event| REDIS
    GEMINI_W -->|result event| REDIS
    CODEX_W -->|result event| REDIS
    PERP_W -->|result event| REDIS

    REDIS -->|publish event| WS
    WS -->|push update| WEB

    ORCHESTRATOR -->|write messages| PG
    WORKFLOW -->|write runs| PG
    BILLING -->|write subscriptions| PG
    INTEGRATIONS -->|read secrets| VAULT

    ORCHESTRATOR -->|store artifacts| S3
    AUDIT -->|send blocks| SLACK_EXT
    BILLING <-->|webhooks| STRIPE
    IDENTITY <-->|JWT verify| CLERK
    CLAUDE_W <-->|API calls| AI_APIS
    GEMINI_W <-->|API calls| AI_APIS
    CODEX_W <-->|API calls| AI_APIS
    PERP_W <-->|API calls| AI_APIS
```

---

## 5. Multi-Tenant Data Isolation

### Strategy: PostgreSQL Row-Level Security (RLS)

Every tenant-scoped table has a `tenant_id UUID NOT NULL` column and a corresponding RLS policy. The application sets a session-local variable before any query:

```sql
SET LOCAL app.current_tenant_id = '<uuid>';
```

PostgreSQL evaluates this against the policy on every row read or write. No tenant can read another tenant's rows even if the application accidentally omits a WHERE clause.

**Three isolation tiers:**

| Tier | Mechanism | Tables |
|------|-----------|--------|
| **Hard** | RLS on every SELECT/INSERT/UPDATE/DELETE | All tenant-scoped tables |
| **Soft** | App-layer tenant_id filter as defense-in-depth | Same tables, redundant filter |
| **Audit** | Every cross-tenant query attempt logged and alerted | `audit_log` + Slack |

### RLS Implementation Pattern

```python
# In database session factory (core/db.py)
async def get_tenant_db(tenant_id: str):
    async with pool.acquire() as conn:
        await conn.execute(
            "SET LOCAL app.current_tenant_id = $1", tenant_id
        )
        yield conn
```

The policy (full detail in `database/rls_policies.sql`):
```sql
CREATE POLICY tenant_isolation ON messages
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

### What RLS Does NOT Protect Against

- A compromised `postgres` superuser (mitigated by: app uses a least-privilege role, not superuser)
- Schema-level objects (functions, sequences) -- those are audited separately
- Storage (S3 keys are prefixed per tenant: `s3://bucket/{tenant_id}/...`)

---

## 6. API Design (FastAPI)

### Base URL Structure

```
/api/v1/
  auth/                  # handled by Clerk SDK
  tenants/               # tenant CRUD (admin only)
  sessions/              # hive mind sessions
    POST   /             # start a new session
    GET    /{id}         # get session status + messages
    DELETE /{id}         # cancel running session
  messages/              # session messages (conversation history)
    GET    /?session_id= # paginated message history
  integrations/          # API key management
    GET    /             # list connected integrations
    POST   /             # add new integration (key stored to Vault)
    DELETE /{id}         # revoke integration
  workflows/             # workflow run history
    GET    /             # list runs
    GET    /{id}         # get run detail + step log
  billing/               # billing management
    GET    /portal       # redirect to Stripe customer portal
    POST   /webhook      # Stripe webhook (unauthenticated, signature verified)
  admin/                 # internal admin (requires admin role)
    GET    /tenants      # all tenants
    GET    /health       # system health
```

### Request Context Object

Every authenticated request gets a context object injected via FastAPI dependency:

```python
@dataclass
class RequestContext:
    user_id: str
    tenant_id: str
    plan_tier: str        # "starter" | "pro" | "agency"
    role: str             # "owner" | "member" | "viewer"
    raw_token: str
```

This context is passed to every service layer call. It never comes from user input -- always derived from the verified JWT.

### Rate Limiting

Per-tenant rate limits enforced via Redis sliding window:

| Plan | Sessions/day | AI calls/month | Concurrent sessions |
|------|-------------|----------------|---------------------|
| Starter | 10 | 500 | 1 |
| Pro | 100 | 5,000 | 3 |
| Agency | Unlimited | 50,000 | 10 |

---

## 7. Real-Time Event System (Redis Pub/Sub + WebSocket)

The "live, aware" feel comes from this pipeline:

```
AI Worker completes a step
        |
        v
Worker publishes to Redis channel:  session:{session_id}:events
        |
        v
WebSocket Hub subscribes to that channel
        |
        v
Hub pushes JSON event to all WebSocket clients subscribed to that session
        |
        v
Dashboard updates in real-time (message streams in, progress bar advances)
```

### Event Schema

```json
{
  "event_type": "manager_result",
  "session_id": "abc123",
  "tenant_id": "...",
  "payload": {
    "manager": "claude",
    "role": "Strategy Advisor",
    "status": "done",
    "response_preview": "Based on the competitive landscape...",
    "duration_s": 4.2
  },
  "ts": "2026-02-27T10:00:00Z"
}
```

### Event Types

| Event | When fired |
|-------|-----------|
| `session_started` | Workflow Engine accepts the job |
| `intel_ready` | Perplexity intel scout completes |
| `manager_started` | Individual AI worker begins |
| `manager_result` | Individual AI worker finishes |
| `synthesis_ready` | All managers done, convergence complete |
| `session_complete` | All artifacts written to S3 |
| `session_error` | Any unrecoverable failure |

### WebSocket Authentication

Clients authenticate the WebSocket connection with the same JWT used for REST calls. The Hub verifies the token and only subscribes the client to channels belonging to their tenant_id. Cross-tenant channel access returns a 4403 close code.

---

## 8. RAG Memory Layer

Each tenant has a persistent memory layer that feeds context into every AI call. This is the key differentiator over a stateless chatbot.

### Components

**Per-tenant conversation history** (PostgreSQL `messages` table):
- Every message stored with vector embedding (pgvector extension)
- At session start, top-K similar past messages retrieved and injected into system prompt
- Enables the hive to "remember" that a tenant is a B2B SaaS company targeting SMBs, without re-explaining every time

**Mindmap data** (PostgreSQL `mindmap_nodes` table):
- Each session's key decisions/conclusions become nodes
- Edges represent causal relationships ("conclusion A informed decision B")
- Frontend renders as an interactive graph (D3.js or React Flow)
- Nodes searchable, selectable as context for future sessions

### RAG Retrieval Flow

```
New session prompt arrives
        |
        v
Embed prompt with text-embedding-3-small (OpenAI)
        |
        v
pgvector similarity search on messages WHERE tenant_id = current
        |
        v
Top 5 most relevant past messages retrieved
        |
        v
Injected into system prompt: "Context from your history: ..."
        |
        v
AI workers have tenant-specific context without being explicitly told
```

### Privacy Guarantee

The vector similarity search is scoped to `tenant_id` before distance calculation. PostgreSQL RLS enforces this. There is no cross-tenant embedding leakage.

---

## 9. Authentication and Secret Storage

### Auth: Clerk

Clerk handles the full auth surface:
- Email/password sign-up and login
- Google OAuth, GitHub OAuth (one-click)
- Magic links
- MFA (Pro and Agency plans)
- Org-level accounts (multiple users per tenant)

The FastAPI backend uses the Clerk Python SDK to verify JWTs on every request. Clerk stores no business data -- it only issues tokens.

```python
# Auth middleware
from clerk_backend_api import Clerk

async def verify_token(authorization: str = Header(...)) -> RequestContext:
    token = authorization.removeprefix("Bearer ")
    claims = clerk.verify_token(token)
    tenant = await tenants.get_by_clerk_org(claims["org_id"])
    return RequestContext(
        user_id=claims["sub"],
        tenant_id=str(tenant.id),
        plan_tier=tenant.plan_tier,
        role=claims["org_role"],
        raw_token=token,
    )
```

### Secret Storage: Encrypted Columns (MVP) then HashiCorp Vault (Scale)

**MVP approach** (Railway/Render deployment):
- User API keys (Anthropic, Google, OpenAI, Perplexity) stored in `integrations.encrypted_credentials`
- Encrypted at rest with AES-256-GCM using a `MASTER_ENCRYPTION_KEY` env var
- Key rotation supported via re-encryption endpoint (admin only)
- Column is `bytea` type, never returned in API responses -- only decrypted server-side when making AI calls

**Scale approach** (when revenue justifies it):
- Migrate to HashiCorp Vault Cloud (free tier handles ~25 secrets fine)
- Each tenant gets a Vault path: `secret/tenants/{tenant_id}/integrations/{provider}`
- App holds a Vault token with read access to all `secret/tenants/*` paths
- Zero-knowledge from the app's perspective: decryption happens inside Vault

---

## 10. Slack Observability Pipeline

Slack is not used for raw logs. It is used for structured business events that a human wants to read.

### Observability Channels (per deployment)

| Channel | Events |
|---------|--------|
| `#hive-sessions` | Session start/complete/error for each tenant |
| `#billing` | New subscriptions, upgrades, cancellations, failed payments |
| `#ai-workers` | Worker failures, timeout warnings, API quota alerts |
| `#infra` | Deploy completions, DB migrations, health check failures |
| `#support` | Any user-facing error with traceback (no PII in the message) |

### Structured Block Format

All Slack messages use the Block Kit format -- never raw text. Example session completion block:

```json
{
  "blocks": [
    {
      "type": "header",
      "text": { "type": "plain_text", "text": "Hive Session Complete" }
    },
    {
      "type": "section",
      "fields": [
        { "type": "mrkdwn", "text": "*Tenant:* acme-corp" },
        { "type": "mrkdwn", "text": "*Plan:* Pro" },
        { "type": "mrkdwn", "text": "*Duration:* 18.4s" },
        { "type": "mrkdwn", "text": "*Workers:* Claude, Gemini, Perplexity" }
      ]
    },
    {
      "type": "section",
      "text": { "type": "mrkdwn", "text": "*Prompt:* Analyze our Q1 content strategy..." }
    },
    {
      "type": "actions",
      "elements": [
        {
          "type": "button",
          "text": { "type": "plain_text", "text": "View Session" },
          "url": "https://app.everlight.ai/sessions/abc123"
        }
      ]
    }
  ]
}
```

Every notification sent is logged to `slack_audit_log` with the full payload, channel, and HTTP response code. This enables replay and debugging.

---

## 11. Billing (Stripe)

### Subscription Tiers

| Tier | Price | Sessions/day | Workers | RAG Memory | Support |
|------|-------|-------------|---------|------------|---------|
| Starter | $49/mo | 10 | Perplexity + 1 | 30-day window | Community |
| Pro | $99/mo | 100 | All 4 | 1-year window | Email (48h) |
| Agency | $199/mo | Unlimited | All 4 + priority | Unlimited | Priority (4h) |

### Stripe Integration Flow

```
User clicks "Upgrade"
        |
        v
POST /api/v1/billing/checkout
Backend creates Stripe Checkout Session
        |
        v
User completes payment on Stripe-hosted page
        |
        v
Stripe sends webhook: checkout.session.completed
        |
        v
POST /api/v1/billing/webhook (verified with Stripe signature)
Billing Module updates tenants.plan_tier + inserts subscriptions row
        |
        v
Slack #billing notification sent
        |
        v
Rate limits update in Redis (plan cache TTL: 5 minutes)
```

Cancellations, upgrades, and failed payments follow the same webhook-first pattern. The `subscriptions` table is the source of truth -- not in-memory plan state.

---

## 12. Deployment Architecture

### Phase 1: Simple (Launch Day)

```
Railway or Render
  Web Service: FastAPI app (Gunicorn + Uvicorn workers)
  Worker Service: ARQ async workers (consumes Redis queue)
  PostgreSQL: Railway managed Postgres (or Supabase)
  Redis: Railway managed Redis (or Upstash)
  Object Storage: Cloudflare R2 (free egress)

DNS: app.everlight.ai -> Railway load balancer
Secrets: Railway environment variables (MASTER_ENCRYPTION_KEY, Stripe keys, etc.)
```

**Cost estimate at launch**: ~$20-40/month total infrastructure for 0-100 tenants.

### Phase 2: Scale (>500 tenants or >$5k MRR)

```
Google Cloud Run (autoscaling, pay-per-request)
  API service: Cloud Run (FastAPI)
  Worker service: Cloud Run Jobs (ARQ workers)
  Database: Cloud SQL (PostgreSQL 15)
  Cache: Memorystore (Redis)
  Storage: GCS buckets (per-tenant prefix)
  Secrets: Secret Manager (replaces env var approach)
  CDN: Cloudflare (static assets + edge caching)
```

### Dockerfile (API Service)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Non-root user
RUN adduser --disabled-password --gecos '' appuser
USER appuser

CMD ["gunicorn", "saas.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "2", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120"]
```

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host/db

# Redis
REDIS_URL=redis://host:6379/0

# Auth
CLERK_SECRET_KEY=sk_live_...
CLERK_PUBLISHABLE_KEY=pk_live_...

# Encryption
MASTER_ENCRYPTION_KEY=<32-byte hex>

# Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Storage
R2_ACCOUNT_ID=...
R2_ACCESS_KEY_ID=...
R2_SECRET_ACCESS_KEY=...
R2_BUCKET_NAME=everlight-artifacts

# Slack
SLACK_WEBHOOK_SESSIONS=https://hooks.slack.com/...
SLACK_WEBHOOK_BILLING=https://hooks.slack.com/...
SLACK_WEBHOOK_INFRA=https://hooks.slack.com/...
```

---

## 13. Module Interface Contracts

### Workflow Engine -> AI Orchestrator

The Workflow Engine produces a `HiveJobRequest` and enqueues it to Redis. The Orchestrator picks it up and executes.

```python
@dataclass
class HiveJobRequest:
    job_id: str           # UUID, used as Redis channel suffix
    tenant_id: str
    session_id: str
    user_id: str
    prompt: str
    mode: str             # "full" | "lite" | "all"
    context_messages: List[Dict]   # from RAG retrieval
    integration_keys: Dict[str, str]  # decrypted at enqueue time, not stored in Redis plain
    plan_tier: str
    created_at: str
```

### AI Orchestrator -> Session Storage

When a session completes, the Orchestrator writes a `HiveSessionResult`:

```python
@dataclass
class HiveSessionResult:
    session_id: str
    tenant_id: str
    manager_results: List[ManagerResult]   # from existing hive_mind/contracts.py
    synthesis: str         # combined summary
    artifact_urls: List[str]  # S3/R2 URLs for downloaded files
    total_duration_s: float
    tokens_used: int
    estimated_cost_usd: float
```

---

## 14. Folder Structure

```
hivemind_saas/
  ARCHITECTURE.md          # This file
  database/
    schema.sql             # Full schema with indexes + RLS
    rls_policies.sql       # All RLS policies isolated
  saas/
    main.py                # FastAPI app factory
    config.py              # Settings (pydantic-settings)
    deps.py                # FastAPI dependencies (auth, db, redis)
    modules/
      identity/            # Auth + user management
      tenant/              # Tenant lifecycle
      integrations/        # API key management
      workflow/            # Step planning + session management
      orchestrator/        # AI fan-out + convergence
      billing/             # Stripe webhooks
      support/             # Slack escalation
      audit/               # Telemetry + audit log
    workers/
      base.py              # ARQ worker setup
      claude_worker.py
      gemini_worker.py
      codex_worker.py
      perplexity_worker.py
    core/
      db.py                # Async PostgreSQL pool (asyncpg)
      redis.py             # Redis client + pub/sub helpers
      storage.py           # S3/R2 artifact storage
      encryption.py        # AES-256-GCM for credentials
      slack.py             # Block Kit notification builder
      rag.py               # pgvector retrieval + embedding
    api/
      v1/
        sessions.py
        integrations.py
        workflows.py
        billing.py
      ws.py                # WebSocket hub
  docker/
    Dockerfile
    Dockerfile.worker
    docker-compose.yml
```

---

## 15. Migration Path from Single-User OS

The existing `everlight_os/` code does not need to be rewritten. The SaaS layer wraps it:

1. `HiveJobRequest` maps directly to the existing `HiveSession` contract in `hive_mind/contracts.py`
2. The existing `hive_mind/dispatcher.py` becomes the inner execution layer -- called by `orchestrator/`
3. The existing `core/slack_client.py` is replaced by `saas/core/slack.py` (Block Kit structured)
4. The existing `_logs/everlight_runs.jsonl` pattern is preserved but writes to PostgreSQL `workflow_runs` instead of a flat file
5. The existing `path_map.json` paths become tenant-scoped S3 paths: `{tenant_id}/{engine}/{project_id}/`

No existing engine code (content, books, trading, saas_factory) changes. It all runs inside the worker processes as before.

---

## 16. Security Checklist

- [ ] RLS enabled on all tenant-scoped tables
- [ ] App DB role does not have BYPASSRLS privilege
- [ ] All API keys encrypted at rest (AES-256-GCM)
- [ ] JWT verified on every request (not just on login)
- [ ] Stripe webhook signature verified before processing
- [ ] WebSocket channels scoped to tenant_id
- [ ] S3 keys never returned in API responses
- [ ] SQL queries use parameterized statements only (no string interpolation)
- [ ] Rate limiting per tenant in Redis
- [ ] Audit log writes cannot be disabled by app code (Postgres trigger)
- [ ] CORS restricted to known origins
- [ ] HTTPS enforced (Railway/Render handle TLS termination)
