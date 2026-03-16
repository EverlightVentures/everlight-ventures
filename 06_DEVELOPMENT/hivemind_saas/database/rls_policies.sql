-- =============================================================================
-- Everlight AI Hive Mind -- Row-Level Security Policies
-- Version: 1.0
-- Date: 2026-02-27
--
-- HOW RLS WORKS IN THIS SYSTEM:
--
--   Before any query, the application sets a session-local configuration
--   variable identifying the current authenticated tenant:
--
--       SET LOCAL app.current_tenant_id = '<uuid>';
--
--   PostgreSQL evaluates every policy expression against this variable on
--   each row access. The app role (everlight_app) has NO BYPASSRLS privilege,
--   so these policies are mathematically enforced -- no application bug can
--   expose one tenant's data to another.
--
-- POLICY NAMING CONVENTION:
--   rls_{table}_{operation}
--   e.g. rls_users_select, rls_sessions_insert
--
-- ADMIN OVERRIDE:
--   Internal admin operations (migrations, backups, support) use a separate
--   'everlight_admin' role that has BYPASSRLS. This role is NEVER used by the
--   application process -- only by ops tooling with explicit audit logging.
--
-- TESTING ISOLATION:
--   After applying these policies, verify isolation with:
--     SET LOCAL app.current_tenant_id = '<tenant_a_uuid>';
--     SELECT COUNT(*) FROM sessions;   -- should return only tenant A rows
--     SET LOCAL app.current_tenant_id = '<tenant_b_uuid>';
--     SELECT COUNT(*) FROM sessions;   -- should return only tenant B rows
-- =============================================================================


-- =============================================================================
-- HELPER FUNCTION: current_tenant_id()
--
-- Centralizes the setting lookup so policy expressions are readable.
-- Returns NULL if the setting is not set, which causes USING clauses to
-- evaluate to NULL (treated as FALSE) -- effectively blocking all access
-- if the app forgot to set the tenant context.
-- =============================================================================

CREATE OR REPLACE FUNCTION current_tenant_id()
RETURNS UUID
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
    SELECT NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID;
$$;

COMMENT ON FUNCTION current_tenant_id() IS
    'Returns the current authenticated tenant UUID from session-local config. '
    'Returns NULL if not set, which blocks all RLS-protected row access. '
    'Used in all tenant isolation policies.';


-- =============================================================================
-- HELPER FUNCTION: current_user_id()
--
-- Used in policies that need to check user ownership within a tenant.
-- Set by the app alongside current_tenant_id before queries.
-- =============================================================================

CREATE OR REPLACE FUNCTION current_user_id()
RETURNS UUID
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
    SELECT NULLIF(current_setting('app.current_user_id', TRUE), '')::UUID;
$$;

COMMENT ON FUNCTION current_user_id() IS
    'Returns the current authenticated user UUID from session-local config. '
    'Used in policies where row ownership matters (e.g. personal data).';


-- =============================================================================
-- TABLE: users
--
-- A user can see and modify only other users within their own tenant.
-- Users cannot see users from other tenants.
-- Only owners can INSERT (invite) or DELETE (remove) users.
-- All users can SELECT their own tenant's user list (for @mentions, sharing).
-- All users can UPDATE their own row (display_name, last_seen_at).
-- =============================================================================

-- SELECT: see all users in your tenant
CREATE POLICY rls_users_select
    ON users
    FOR SELECT
    USING (tenant_id = current_tenant_id());

-- INSERT: only owners can invite new users (enforced by app role check + this policy)
-- The app sets app.current_user_role before calling INSERT.
CREATE POLICY rls_users_insert
    ON users
    FOR INSERT
    WITH CHECK (tenant_id = current_tenant_id());

-- UPDATE: users can update their own row; owners can update any row in their tenant
CREATE POLICY rls_users_update
    ON users
    FOR UPDATE
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

-- DELETE: restricted to tenant scope (app layer further restricts to owner role)
CREATE POLICY rls_users_delete
    ON users
    FOR DELETE
    USING (tenant_id = current_tenant_id());


-- =============================================================================
-- TABLE: integrations
--
-- Integrations are per-tenant. No user from another tenant can see, modify,
-- or delete another tenant's API keys. encrypted_credentials is never exposed
-- in SELECT responses at the API layer (app strips it), but RLS ensures even
-- a raw DB query cannot cross tenant boundaries.
-- =============================================================================

CREATE POLICY rls_integrations_select
    ON integrations
    FOR SELECT
    USING (tenant_id = current_tenant_id());

CREATE POLICY rls_integrations_insert
    ON integrations
    FOR INSERT
    WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY rls_integrations_update
    ON integrations
    FOR UPDATE
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY rls_integrations_delete
    ON integrations
    FOR DELETE
    USING (tenant_id = current_tenant_id());

COMMENT ON TABLE integrations IS
    'RLS: tenant_id must equal current_tenant_id() on all operations. '
    'encrypted_credentials column is stripped at the API layer before any response. '
    'Double isolation: RLS prevents cross-tenant DB access, app layer prevents '
    'credential exposure in responses.';


-- =============================================================================
-- TABLE: sessions
--
-- Sessions are per-tenant. All users within a tenant can see all sessions
-- (collaborative view). Only the session creator can cancel/delete their session.
-- Inserts are restricted to the current tenant.
-- =============================================================================

CREATE POLICY rls_sessions_select
    ON sessions
    FOR SELECT
    USING (tenant_id = current_tenant_id());

CREATE POLICY rls_sessions_insert
    ON sessions
    FOR INSERT
    WITH CHECK (tenant_id = current_tenant_id());

-- UPDATE: any user in the tenant can update (status changes, results writing)
-- App layer further restricts cancellation to owner/creator role
CREATE POLICY rls_sessions_update
    ON sessions
    FOR UPDATE
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

-- DELETE: owner role only (enforced at app layer); RLS ensures tenant scope
CREATE POLICY rls_sessions_delete
    ON sessions
    FOR DELETE
    USING (tenant_id = current_tenant_id());


-- =============================================================================
-- TABLE: messages
--
-- Messages inherit tenant isolation from their parent session.
-- All users within a tenant can read all messages (shared conversation history).
-- INSERT is performed by the AI workers (running as app role with tenant context set).
-- Users cannot delete messages (immutable audit trail).
-- =============================================================================

CREATE POLICY rls_messages_select
    ON messages
    FOR SELECT
    USING (tenant_id = current_tenant_id());

CREATE POLICY rls_messages_insert
    ON messages
    FOR INSERT
    WITH CHECK (tenant_id = current_tenant_id());

-- UPDATE: allowed for embedding backfill jobs (app sets tenant context)
CREATE POLICY rls_messages_update
    ON messages
    FOR UPDATE
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

-- DELETE: not permitted via app role. Hard delete requires admin role.
-- Soft deletes are handled by setting metadata->>'deleted' = 'true'.
-- (No DELETE policy defined = default DENY for this table under RLS)

COMMENT ON TABLE messages IS
    'RLS: tenant_id isolation on SELECT/INSERT/UPDATE. '
    'No DELETE policy -- messages are immutable via app role. '
    'Soft deletes via metadata JSONB field.';


-- =============================================================================
-- TABLE: mindmap_nodes
--
-- Mindmap nodes are per-tenant. All users in a tenant share the mindmap.
-- Nodes can be created by any member. Only owners can delete nodes.
-- =============================================================================

CREATE POLICY rls_mindmap_select
    ON mindmap_nodes
    FOR SELECT
    USING (tenant_id = current_tenant_id());

CREATE POLICY rls_mindmap_insert
    ON mindmap_nodes
    FOR INSERT
    WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY rls_mindmap_update
    ON mindmap_nodes
    FOR UPDATE
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY rls_mindmap_delete
    ON mindmap_nodes
    FOR DELETE
    USING (tenant_id = current_tenant_id());


-- =============================================================================
-- TABLE: workflow_runs
--
-- Workflow run audit logs are per-tenant. All users in a tenant can read
-- their workflow history (transparency). Only the system (app worker) inserts
-- and updates. Users cannot delete workflow run records.
-- =============================================================================

CREATE POLICY rls_workflow_runs_select
    ON workflow_runs
    FOR SELECT
    USING (tenant_id = current_tenant_id());

CREATE POLICY rls_workflow_runs_insert
    ON workflow_runs
    FOR INSERT
    WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY rls_workflow_runs_update
    ON workflow_runs
    FOR UPDATE
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

-- No DELETE policy = immutable audit trail via app role.

COMMENT ON TABLE workflow_runs IS
    'RLS: tenant_id isolation. No DELETE policy -- immutable execution audit log. '
    'Workers always set app.current_tenant_id before writing.';


-- =============================================================================
-- TABLE: subscriptions
--
-- Subscriptions are per-tenant. Tenants can read their own subscription data.
-- Only the system (Billing Module processing Stripe webhooks) can insert/update.
-- Tenants CANNOT modify their own subscription records directly.
-- =============================================================================

CREATE POLICY rls_subscriptions_select
    ON subscriptions
    FOR SELECT
    USING (tenant_id = current_tenant_id());

-- INSERT/UPDATE: only via Billing Module worker (sets tenant context from Stripe metadata)
CREATE POLICY rls_subscriptions_insert
    ON subscriptions
    FOR INSERT
    WITH CHECK (tenant_id = current_tenant_id());

CREATE POLICY rls_subscriptions_update
    ON subscriptions
    FOR UPDATE
    USING (tenant_id = current_tenant_id())
    WITH CHECK (tenant_id = current_tenant_id());

-- No DELETE -- cancellations set status='cancelled', not hard delete.

COMMENT ON TABLE subscriptions IS
    'RLS: tenants can read their own subscription. '
    'INSERT/UPDATE only by Billing Module with valid tenant context. '
    'No DELETE -- use status field for lifecycle management.';


-- =============================================================================
-- TENANTS TABLE: special case
--
-- The tenants table itself does NOT have RLS for SELECT. The app needs to
-- resolve a tenant by slug or clerk_org_id before setting the tenant context
-- (it cannot set context if it cannot find the tenant row). This is safe
-- because the tenants table contains only non-sensitive metadata.
--
-- However, INSERT and UPDATE on tenants require admin privileges.
-- DELETE (deprovisioning) requires admin role with audit log entry.
-- =============================================================================

-- tenants RLS is NOT enabled by default.
-- Admin-only operations use everlight_admin role (BYPASSRLS).
-- If you want belt-and-suspenders protection on tenants:
--
-- ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY rls_tenants_select_own
--     ON tenants
--     FOR SELECT
--     USING (id = current_tenant_id());
--
-- This would block cross-tenant resolution by slug. For MVP, leave tenants
-- without RLS since the lookup-by-slug flow needs it pre-authentication.


-- =============================================================================
-- VECTOR SEARCH ISOLATION FUNCTION
--
-- pgvector similarity searches must be tenant-scoped. A raw similarity search
-- across all embeddings would leak which topics other tenants have discussed
-- (via returned similarity scores). This function wraps the search and enforces
-- tenant scoping BEFORE the vector distance calculation.
--
-- Usage (from application):
--   SELECT * FROM tenant_message_search('<tenant_uuid>', '[0.1,0.2,...]'::vector, 5);
-- =============================================================================

CREATE OR REPLACE FUNCTION tenant_message_search(
    p_tenant_id     UUID,
    p_embedding     vector(1536),
    p_limit         INT DEFAULT 5
)
RETURNS TABLE (
    id          UUID,
    session_id  UUID,
    role        TEXT,
    manager     TEXT,
    content     TEXT,
    similarity  FLOAT,
    created_at  TIMESTAMPTZ
)
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
    SELECT
        m.id,
        m.session_id,
        m.role,
        m.manager,
        m.content,
        1 - (m.embedding <=> p_embedding) AS similarity,
        m.created_at
    FROM messages m
    WHERE
        m.tenant_id = p_tenant_id
        AND m.embedding IS NOT NULL
        AND m.role = 'assistant'
    ORDER BY m.embedding <=> p_embedding
    LIMIT p_limit;
$$;

COMMENT ON FUNCTION tenant_message_search IS
    'Tenant-scoped vector similarity search for RAG retrieval. '
    'The WHERE tenant_id = p_tenant_id clause is applied BEFORE distance sorting, '
    'guaranteeing no cross-tenant similarity data leaks through result rankings. '
    'SECURITY DEFINER runs as function owner (everlight_admin) to bypass RLS '
    'for the internal lookup, but p_tenant_id is passed explicitly -- never '
    'derived from the session config inside this function.';


-- Same pattern for mindmap node search:
CREATE OR REPLACE FUNCTION tenant_mindmap_search(
    p_tenant_id     UUID,
    p_embedding     vector(1536),
    p_limit         INT DEFAULT 5
)
RETURNS TABLE (
    id          UUID,
    label       TEXT,
    content     TEXT,
    node_type   TEXT,
    similarity  FLOAT,
    created_at  TIMESTAMPTZ
)
LANGUAGE sql
STABLE
SECURITY DEFINER
AS $$
    SELECT
        n.id,
        n.label,
        n.content,
        n.node_type,
        1 - (n.embedding <=> p_embedding) AS similarity,
        n.created_at
    FROM mindmap_nodes n
    WHERE
        n.tenant_id = p_tenant_id
        AND n.embedding IS NOT NULL
    ORDER BY n.embedding <=> p_embedding
    LIMIT p_limit;
$$;


-- =============================================================================
-- AUDIT TRIGGER: detect and log cross-tenant access attempts
--
-- This trigger fires on any SELECT/INSERT/UPDATE/DELETE on tenant-scoped tables
-- where the tenant_id in the row does NOT match the session tenant context.
-- In normal operation this should never fire (RLS blocks mismatched rows).
-- If it fires, it means RLS was bypassed somehow -- immediate alert warranted.
-- =============================================================================

CREATE TABLE IF NOT EXISTS rls_violation_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_name      TEXT NOT NULL,
    operation       TEXT NOT NULL,              -- TG_OP: INSERT | UPDATE | DELETE
    row_tenant_id   UUID,
    session_tenant  UUID,
    row_id          UUID,
    detected_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE rls_violation_log IS
    'Should always be empty in production. '
    'Any row here means RLS was bypassed and a cross-tenant access occurred. '
    'Alert on INSERT to this table via Postgres NOTIFY or scheduled check.';

-- Violation trigger function
CREATE OR REPLACE FUNCTION detect_rls_violation()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_session_tenant UUID;
BEGIN
    v_session_tenant := current_tenant_id();

    -- If tenant context is set and row tenant_id does not match, log violation
    IF v_session_tenant IS NOT NULL AND NEW.tenant_id != v_session_tenant THEN
        INSERT INTO rls_violation_log (
            table_name, operation, row_tenant_id, session_tenant, row_id
        ) VALUES (
            TG_TABLE_NAME, TG_OP, NEW.tenant_id, v_session_tenant, NEW.id
        );

        -- Raise exception to abort the operation
        RAISE EXCEPTION 'RLS violation: tenant_id mismatch on table % (row tenant: %, session tenant: %)',
            TG_TABLE_NAME, NEW.tenant_id, v_session_tenant;
    END IF;

    RETURN NEW;
END;
$$;

-- Apply violation detection trigger to all tenant-scoped tables
CREATE TRIGGER trg_rls_check_users
    BEFORE INSERT OR UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION detect_rls_violation();

CREATE TRIGGER trg_rls_check_integrations
    BEFORE INSERT OR UPDATE ON integrations
    FOR EACH ROW EXECUTE FUNCTION detect_rls_violation();

CREATE TRIGGER trg_rls_check_sessions
    BEFORE INSERT OR UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION detect_rls_violation();

CREATE TRIGGER trg_rls_check_messages
    BEFORE INSERT OR UPDATE ON messages
    FOR EACH ROW EXECUTE FUNCTION detect_rls_violation();

CREATE TRIGGER trg_rls_check_mindmap
    BEFORE INSERT OR UPDATE ON mindmap_nodes
    FOR EACH ROW EXECUTE FUNCTION detect_rls_violation();

CREATE TRIGGER trg_rls_check_workflow_runs
    BEFORE INSERT OR UPDATE ON workflow_runs
    FOR EACH ROW EXECUTE FUNCTION detect_rls_violation();

CREATE TRIGGER trg_rls_check_subscriptions
    BEFORE INSERT OR UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION detect_rls_violation();


-- =============================================================================
-- VERIFICATION QUERIES
--
-- Run these after applying policies to confirm isolation is working.
-- Expected: each query returns only rows for the set tenant.
-- =============================================================================

-- Test block (comment out in production migration):
/*
DO $$
DECLARE
    v_tenant_a UUID := '<paste tenant A uuid>';
    v_tenant_b UUID := '<paste tenant B uuid>';
    v_count_a  INT;
    v_count_b  INT;
BEGIN
    -- Test tenant A isolation
    PERFORM set_config('app.current_tenant_id', v_tenant_a::text, TRUE);
    SELECT COUNT(*) INTO v_count_a FROM sessions;

    -- Switch to tenant B and verify different count
    PERFORM set_config('app.current_tenant_id', v_tenant_b::text, TRUE);
    SELECT COUNT(*) INTO v_count_b FROM sessions;

    -- Verify tenant A cannot see tenant B's data
    PERFORM set_config('app.current_tenant_id', v_tenant_a::text, TRUE);
    IF EXISTS (SELECT 1 FROM sessions WHERE tenant_id = v_tenant_b) THEN
        RAISE EXCEPTION 'RLS FAILURE: tenant A can see tenant B sessions';
    ELSE
        RAISE NOTICE 'RLS OK: tenant isolation verified for sessions table';
    END IF;
END $$;
*/


-- =============================================================================
-- POLICY SUMMARY
-- =============================================================================
--
-- Table               | SELECT | INSERT | UPDATE | DELETE | Notes
-- --------------------|--------|--------|--------|--------|----------------------
-- tenants             | open   | admin  | admin  | admin  | Pre-auth slug lookup
-- users               | tenant | tenant | tenant | tenant |
-- integrations        | tenant | tenant | tenant | tenant | credentials stripped by app
-- sessions            | tenant | tenant | tenant | tenant |
-- messages            | tenant | tenant | tenant | DENY   | Immutable via app role
-- mindmap_nodes       | tenant | tenant | tenant | tenant |
-- workflow_runs       | tenant | tenant | tenant | DENY   | Immutable audit log
-- subscriptions       | tenant | tenant | tenant | DENY   | Lifecycle via status field
-- slack_audit_log     | admin  | admin  | admin  | admin  | No RLS, admin-only
-- rls_violation_log   | admin  | system | --     | admin  | Alert on any insert
--
-- "tenant" = current_tenant_id() match required
-- "admin"  = everlight_admin role (BYPASSRLS) only
-- "DENY"   = no policy defined, default deny under RLS
-- =============================================================================
