-- =============================================================================
-- Everlight AI Hive Mind -- Production PostgreSQL Schema
-- Version: 1.0
-- Date: 2026-02-27
--
-- CONVENTIONS:
--   - All PKs are UUID (gen_random_uuid())
--   - All timestamps are TIMESTAMPTZ stored in UTC
--   - Every tenant-scoped table has tenant_id UUID NOT NULL
--   - RLS is ENABLED on every tenant-scoped table (policies in rls_policies.sql)
--   - Indexes named: idx_{table}_{column(s)}
--   - FKs named: fk_{table}_{referenced_table}
--
-- SETUP REQUIREMENT:
--   Enable required extensions before running this file:
--     CREATE EXTENSION IF NOT EXISTS "pgcrypto";
--     CREATE EXTENSION IF NOT EXISTS "vector";
-- =============================================================================


-- =============================================================================
-- EXTENSIONS
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";    -- gen_random_uuid(), pgp_sym_encrypt
CREATE EXTENSION IF NOT EXISTS "vector";      -- pgvector for RAG embeddings


-- =============================================================================
-- ENUMS
-- =============================================================================

CREATE TYPE plan_tier AS ENUM ('starter', 'pro', 'agency', 'internal');
CREATE TYPE user_role AS ENUM ('owner', 'member', 'viewer');
CREATE TYPE session_status AS ENUM ('pending', 'running', 'done', 'partial', 'cancelled', 'error');
CREATE TYPE workflow_status AS ENUM ('pending', 'running', 'done', 'failed', 'cancelled');
CREATE TYPE subscription_status AS ENUM ('active', 'trialing', 'past_due', 'cancelled', 'unpaid');
CREATE TYPE integration_provider AS ENUM ('anthropic', 'openai', 'google', 'perplexity', 'slack', 'stripe', 'custom');
CREATE TYPE audit_event_type AS ENUM (
    'session_started', 'session_complete', 'session_error',
    'manager_started', 'manager_result', 'intel_ready', 'synthesis_ready',
    'integration_added', 'integration_removed',
    'subscription_created', 'subscription_updated', 'subscription_cancelled',
    'user_invited', 'user_removed',
    'api_key_rotated',
    'slack_notification_sent'
);


-- =============================================================================
-- TABLE: tenants
--
-- One row per customer organization. This is the root of the multi-tenant tree.
-- All other tables reference tenant_id back to this table.
-- plan_tier drives rate limits, feature flags, and billing.
-- slug is the human-readable identifier used in URLs: app.everlight.ai/t/acme-corp
-- =============================================================================

CREATE TABLE tenants (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                TEXT NOT NULL,                          -- Display name: "Acme Corp"
    slug                TEXT NOT NULL UNIQUE,                   -- URL-safe: "acme-corp"
    plan_tier           plan_tier NOT NULL DEFAULT 'starter',
    stripe_customer_id  TEXT UNIQUE,                            -- Stripe cus_... ID
    clerk_org_id        TEXT UNIQUE,                            -- Clerk org_ ID for JWT lookup
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,          -- FALSE = suspended
    trial_ends_at       TIMESTAMPTZ,                            -- NULL if not in trial
    max_sessions_per_day INT NOT NULL DEFAULT 10,               -- Enforced by app layer
    max_concurrent_sessions INT NOT NULL DEFAULT 1,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tenants_slug        ON tenants (slug);
CREATE INDEX idx_tenants_clerk_org   ON tenants (clerk_org_id);
CREATE INDEX idx_tenants_stripe      ON tenants (stripe_customer_id);

COMMENT ON TABLE tenants IS
    'Root entity. Every other table with tenant_id references this. '
    'Deleting a tenant cascades to all child tables via FK ON DELETE CASCADE.';


-- =============================================================================
-- TABLE: users
--
-- One row per user within a tenant. A user belongs to exactly one tenant.
-- Role determines what the user can do within their tenant:
--   owner  -- full control, billing access
--   member -- can run sessions, view history
--   viewer -- read-only, cannot start sessions
--
-- auth is handled by Clerk. We store the Clerk user ID (clerk_user_id) as the
-- external identity anchor. email is denormalized here for display/search.
-- =============================================================================

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    clerk_user_id   TEXT NOT NULL UNIQUE,                   -- Clerk user_ ID
    email           TEXT NOT NULL,
    display_name    TEXT,
    role            user_role NOT NULL DEFAULT 'member',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_seen_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_users_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);

CREATE INDEX idx_users_tenant_id    ON users (tenant_id);
CREATE INDEX idx_users_clerk_user   ON users (clerk_user_id);
CREATE INDEX idx_users_email        ON users (tenant_id, email);

-- RLS enabled in rls_policies.sql
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE users IS
    'Users within a tenant. One user = one tenant (no cross-tenant users at MVP). '
    'clerk_user_id is the stable external ID from Clerk JWT claims.';


-- =============================================================================
-- TABLE: integrations
--
-- Stores tenant API keys for AI providers and other external services.
-- encrypted_credentials is an AES-256-GCM encrypted JSON blob containing
-- the actual secret(s) for that provider. The app decrypts at runtime using
-- MASTER_ENCRYPTION_KEY from the environment. This column is NEVER returned
-- in API responses -- only decrypted server-side when making AI calls.
--
-- scopes is a JSONB array of permission strings, e.g. ["read", "write"].
-- provider_metadata is a JSONB bag for provider-specific non-secret data
-- (e.g. the Slack workspace name, the Google project ID).
-- =============================================================================

CREATE TABLE integrations (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    provider                integration_provider NOT NULL,
    display_name            TEXT,                               -- Human label: "Production Anthropic Key"
    encrypted_credentials   BYTEA NOT NULL,                    -- AES-256-GCM ciphertext
    scopes                  JSONB NOT NULL DEFAULT '[]',        -- ["read", "write"]
    provider_metadata       JSONB NOT NULL DEFAULT '{}',        -- Non-secret provider info
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    last_used_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_integrations_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
    CONSTRAINT uq_integrations_tenant_provider UNIQUE (tenant_id, provider, display_name)
);

CREATE INDEX idx_integrations_tenant_id ON integrations (tenant_id);
CREATE INDEX idx_integrations_provider  ON integrations (tenant_id, provider);

ALTER TABLE integrations ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE integrations IS
    'Encrypted API keys per tenant per provider. '
    'encrypted_credentials is never sent to clients -- decrypted server-side only. '
    'Rotate keys by updating encrypted_credentials and bumping updated_at.';


-- =============================================================================
-- TABLE: sessions
--
-- One row per hive mind deliberation session. A session is the top-level unit
-- of work: the user submits a prompt, the system fans out to AI workers,
-- converges, and produces artifacts.
--
-- mode controls which workers engage:
--   full  -- Perplexity + Claude + Gemini + Codex
--   lite  -- Perplexity + Claude only
--   all   -- same as full, explicit
--
-- status follows: pending -> running -> done | error | cancelled
-- artifact_urls is a JSONB array of S3/R2 URLs for downloadable output files.
-- =============================================================================

CREATE TABLE sessions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE SET NULL,
    prompt              TEXT NOT NULL,
    mode                TEXT NOT NULL DEFAULT 'full',           -- "full" | "lite" | "all"
    status              session_status NOT NULL DEFAULT 'pending',
    routed_to           JSONB NOT NULL DEFAULT '[]',            -- ["claude","gemini","perplexity"]
    intel_summary       TEXT,                                   -- Perplexity output
    combined_summary    TEXT,                                   -- Convergence synthesis
    artifact_urls       JSONB NOT NULL DEFAULT '[]',            -- S3 file URLs
    total_duration_s    FLOAT,
    tokens_used         INT,
    estimated_cost_usd  NUMERIC(10,6),
    error_message       TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at         TIMESTAMPTZ,

    CONSTRAINT fk_sessions_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id),
    CONSTRAINT fk_sessions_user   FOREIGN KEY (user_id)   REFERENCES users(id)
);

CREATE INDEX idx_sessions_tenant_id   ON sessions (tenant_id);
CREATE INDEX idx_sessions_user_id     ON sessions (user_id);
CREATE INDEX idx_sessions_status      ON sessions (tenant_id, status);
CREATE INDEX idx_sessions_created_at  ON sessions (tenant_id, created_at DESC);

ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE sessions IS
    'Top-level unit of work for the Hive Mind. '
    'One row = one deliberation session from prompt submission to synthesis. '
    'Child messages rows contain the per-manager responses.';


-- =============================================================================
-- TABLE: messages
--
-- Individual messages within a session. Each AI manager writes one row
-- when it completes (role="assistant", manager="claude" etc).
-- User prompts are also stored (role="user") for conversation continuity.
--
-- embedding is a 1536-dim vector (text-embedding-3-small) used for RAG.
-- pgvector ivfflat index enables fast approximate nearest-neighbor search
-- across a tenant's history to surface relevant past context.
-- =============================================================================

CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    session_id      UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role            TEXT NOT NULL,                  -- "user" | "assistant" | "system"
    manager         TEXT,                           -- "claude" | "gemini" | "codex" | "perplexity" | NULL for user
    content         TEXT NOT NULL,
    embedding       vector(1536),                   -- pgvector embedding for RAG retrieval
    token_count     INT,
    duration_s      FLOAT,                          -- How long this manager took
    error           TEXT,                           -- Non-null if this manager failed
    metadata        JSONB NOT NULL DEFAULT '{}',    -- Arbitrary extra data
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_messages_tenant  FOREIGN KEY (tenant_id)  REFERENCES tenants(id),
    CONSTRAINT fk_messages_session FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE INDEX idx_messages_tenant_id   ON messages (tenant_id);
CREATE INDEX idx_messages_session_id  ON messages (session_id);
CREATE INDEX idx_messages_created_at  ON messages (tenant_id, created_at DESC);

-- ivfflat index for vector similarity search (RAG).
-- lists=100 is appropriate for up to ~1M rows per tenant.
-- Rebuild with higher lists value if tenant history grows beyond 1M rows.
CREATE INDEX idx_messages_embedding ON messages
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE messages IS
    'Per-message log for every session. Stores both user prompts and AI responses. '
    'embedding column enables RAG: at session start, top-K similar past messages '
    'are retrieved and injected into the AI workers system prompt. '
    'This is what makes the Hive Mind feel like it knows your business.';


-- =============================================================================
-- TABLE: mindmap_nodes
--
-- Nodes in the per-tenant knowledge graph. Each session can produce nodes
-- representing key conclusions, decisions, or entities. Edges are stored as
-- a JSONB array on each node pointing to parent node IDs.
--
-- This table powers the interactive mindmap visualization on the dashboard.
-- It also serves as a structured knowledge base for future RAG retrieval
-- (nodes are embedded and searchable just like messages).
-- =============================================================================

CREATE TABLE mindmap_nodes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    session_id      UUID REFERENCES sessions(id) ON DELETE SET NULL,   -- Source session (nullable: manual nodes)
    label           TEXT NOT NULL,                      -- Short node label: "Q1 Content Strategy"
    content         TEXT,                               -- Full node body text
    node_type       TEXT NOT NULL DEFAULT 'insight',    -- "insight" | "decision" | "entity" | "action"
    parent_ids      JSONB NOT NULL DEFAULT '[]',        -- Array of UUID strings (parent nodes)
    tags            JSONB NOT NULL DEFAULT '[]',        -- ["content", "strategy", "q1"]
    embedding       vector(1536),                       -- For semantic node search
    is_pinned       BOOLEAN NOT NULL DEFAULT FALSE,     -- Pinned nodes always included in context
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_mindmap_tenant  FOREIGN KEY (tenant_id)  REFERENCES tenants(id),
    CONSTRAINT fk_mindmap_session FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE INDEX idx_mindmap_tenant_id   ON mindmap_nodes (tenant_id);
CREATE INDEX idx_mindmap_session_id  ON mindmap_nodes (session_id);
CREATE INDEX idx_mindmap_node_type   ON mindmap_nodes (tenant_id, node_type);
CREATE INDEX idx_mindmap_pinned      ON mindmap_nodes (tenant_id, is_pinned) WHERE is_pinned = TRUE;
CREATE INDEX idx_mindmap_embedding   ON mindmap_nodes
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 50);

ALTER TABLE mindmap_nodes ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE mindmap_nodes IS
    'Nodes in the per-tenant knowledge graph (mindmap). '
    'Populated automatically from session synthesis, or manually by users. '
    'parent_ids array encodes directed edges for graph rendering. '
    'Pinned nodes are always injected into the AI context window.';


-- =============================================================================
-- TABLE: workflow_runs
--
-- Audit log of every step in every workflow execution. While sessions tracks
-- the high-level result, workflow_runs records each individual step (research,
-- outline, draft, quality_gate, etc.) with timing and outcome.
--
-- This is the primary table for debugging failed workflows, measuring step
-- latency, and computing per-step cost attribution.
-- =============================================================================

CREATE TABLE workflow_runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    session_id      UUID REFERENCES sessions(id) ON DELETE SET NULL,
    step_name       TEXT NOT NULL,                      -- "research" | "outline" | "draft" etc.
    worker          TEXT NOT NULL,                      -- "claude" | "gemini" | "perplexity" | "local"
    status          workflow_status NOT NULL DEFAULT 'pending',
    input_summary   TEXT,                               -- Brief description of inputs (no secrets)
    output_path     TEXT,                               -- S3/R2 path of output artifact
    error_message   TEXT,
    token_count     INT,
    duration_s      FLOAT,
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_workflow_tenant  FOREIGN KEY (tenant_id)  REFERENCES tenants(id),
    CONSTRAINT fk_workflow_session FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE INDEX idx_workflow_tenant_id  ON workflow_runs (tenant_id);
CREATE INDEX idx_workflow_session_id ON workflow_runs (session_id);
CREATE INDEX idx_workflow_status     ON workflow_runs (tenant_id, status);
CREATE INDEX idx_workflow_created_at ON workflow_runs (tenant_id, created_at DESC);
CREATE INDEX idx_workflow_step       ON workflow_runs (tenant_id, step_name);

ALTER TABLE workflow_runs ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE workflow_runs IS
    'Step-level execution log for every workflow. '
    'One session produces N workflow_runs rows (one per step). '
    'Used for debugging, cost attribution, and step-level performance metrics. '
    'Maps directly to the StepDef and RunLogEntry contracts in core/contracts.py.';


-- =============================================================================
-- TABLE: subscriptions
--
-- Stripe subscription data mirrored from webhooks. This table is the source
-- of truth for billing state -- not in-memory or cached values.
--
-- current_period_start/end track the active billing period.
-- cancel_at is set when a subscription is scheduled for cancellation
-- (Stripe "cancel at period end" setting).
-- =============================================================================

CREATE TABLE subscriptions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    stripe_subscription_id  TEXT NOT NULL UNIQUE,           -- sub_... from Stripe
    stripe_price_id         TEXT NOT NULL,                  -- price_... from Stripe
    plan_tier               plan_tier NOT NULL,
    status                  subscription_status NOT NULL,
    current_period_start    TIMESTAMPTZ NOT NULL,
    current_period_end      TIMESTAMPTZ NOT NULL,
    cancel_at               TIMESTAMPTZ,                    -- NULL = not scheduled for cancellation
    cancelled_at            TIMESTAMPTZ,                    -- NULL = not yet cancelled
    trial_start             TIMESTAMPTZ,
    trial_end               TIMESTAMPTZ,
    metadata                JSONB NOT NULL DEFAULT '{}',    -- Stripe metadata passthrough
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_subscriptions_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);

CREATE INDEX idx_subscriptions_tenant_id  ON subscriptions (tenant_id);
CREATE INDEX idx_subscriptions_stripe_id  ON subscriptions (stripe_subscription_id);
CREATE INDEX idx_subscriptions_status     ON subscriptions (status);

ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE subscriptions IS
    'Stripe subscription data, kept in sync via webhooks. '
    'When a Stripe webhook fires, the Billing Module upserts this table '
    'and updates tenants.plan_tier to match. '
    'Never trust in-memory plan state -- always read from this table.';


-- =============================================================================
-- TABLE: slack_audit_log
--
-- Every Slack notification sent by the system. Includes the full Block Kit
-- payload, target channel, HTTP response code, and whether it succeeded.
-- Enables replay of failed notifications and debugging of observability gaps.
--
-- tenant_id is nullable because some notifications are system-level
-- (e.g. deployment complete, DB migration run) and not associated with a tenant.
-- =============================================================================

CREATE TABLE slack_audit_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID REFERENCES tenants(id) ON DELETE SET NULL,   -- NULL = system event
    event_type      audit_event_type NOT NULL,
    channel         TEXT NOT NULL,                      -- "#hive-sessions", "#billing", etc.
    payload         JSONB NOT NULL,                     -- Full Block Kit payload sent
    http_status     INT,                                -- Slack API response code
    success         BOOLEAN NOT NULL DEFAULT FALSE,
    error_message   TEXT,
    session_id      UUID REFERENCES sessions(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_slack_audit_tenant     ON slack_audit_log (tenant_id);
CREATE INDEX idx_slack_audit_event_type ON slack_audit_log (event_type);
CREATE INDEX idx_slack_audit_created_at ON slack_audit_log (created_at DESC);
CREATE INDEX idx_slack_audit_success    ON slack_audit_log (success) WHERE success = FALSE;

-- NOTE: No RLS on slack_audit_log intentionally.
-- This table is admin-only. App-layer guards restrict access to internal admin endpoints.
-- Tenants cannot query this table directly via the API.

COMMENT ON TABLE slack_audit_log IS
    'Immutable log of every Slack notification sent. '
    'tenant_id is nullable for system-level events. '
    'The idx_slack_audit_success partial index makes it fast to find failed '
    'notifications for replay. No RLS -- admin access only.';


-- =============================================================================
-- TRIGGER: update updated_at automatically
-- =============================================================================

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_tenants_updated_at
    BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_integrations_updated_at
    BEFORE UPDATE ON integrations
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_sessions_updated_at
    BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_mindmap_updated_at
    BEFORE UPDATE ON mindmap_nodes
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_subscriptions_updated_at
    BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- =============================================================================
-- APP ROLE (least-privilege)
--
-- The application connects as 'everlight_app', not 'postgres'.
-- This role has no BYPASSRLS privilege, so RLS policies are always enforced.
-- Sequence grants allow INSERT to work on UUID defaults (pgcrypto gen_random_uuid
-- does not need sequence access, but listed for completeness).
-- =============================================================================

-- CREATE ROLE everlight_app WITH LOGIN PASSWORD 'changeme_in_production';
-- GRANT CONNECT ON DATABASE everlight TO everlight_app;
-- GRANT USAGE ON SCHEMA public TO everlight_app;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO everlight_app;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO everlight_app;
-- Critically: do NOT grant BYPASSRLS to everlight_app.

COMMENT ON SCHEMA public IS
    'Everlight Hive Mind schema. App connects as everlight_app role (no BYPASSRLS). '
    'RLS policies in rls_policies.sql enforce tenant isolation on all data-bearing tables.';
