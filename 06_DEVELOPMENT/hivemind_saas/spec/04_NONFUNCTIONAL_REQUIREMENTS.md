# Non-Functional Requirements -- Everlight Hive Mind SaaS
# Phase 0 Spec | Version 1.0 | 2026-02-27

---

## 1. Performance

### NFR-PERF-01: Dashboard Load Time
The main dashboard page (home screen) must achieve a Largest Contentful Paint (LCP) under 2.5 seconds on a 4G mobile connection. Measured with Lighthouse in CI on every deploy.

### NFR-PERF-02: Session Dispatch Latency
Time from "Run Session" button click to first Slack audit log message must be under 5 seconds for sessions that do not require queuing. This covers the "is it working?" anxiety window.

### NFR-PERF-03: Session Completion SLA
- Single-model sessions (under 2,000 input tokens): complete within 45 seconds.
- Multi-model synthesis sessions (up to 4 models, up to 8,000 tokens total): complete within 3 minutes.
- Sessions exceeding 5 minutes are auto-cancelled and marked "Timed Out." Tenant is notified.

### NFR-PERF-04: API Endpoint Response Times
All REST API endpoints must return a response (or a 202 Accepted with a session_id) within 800ms at the 95th percentile under normal load (up to 500 concurrent tenants).

### NFR-PERF-05: Concurrent Session Capacity (MVP)
The system must handle 200 concurrent hive sessions without degradation. Sessions beyond capacity enter a queue with a position indicator. Target queue wait time: under 60 seconds.

### NFR-PERF-06: Database Query Performance
All database reads used in dashboard rendering must complete in under 100ms at the 95th percentile. Slow query alerts fire at 250ms. No N+1 query patterns in session list views.

---

## 2. Security

### NFR-SEC-01: API Key Encryption
All third-party API keys stored in the Integration Vault must be encrypted at rest using AES-256-GCM. Encryption keys must be stored in a separate secrets manager (AWS Secrets Manager or equivalent), not in the application database or environment variables.

### NFR-SEC-02: Tenant Isolation
Every database query touching tenant data must include a tenant_id filter enforced at the data access layer -- not only in application logic. Cross-tenant data access via crafted API requests must be impossible. Tested with a dedicated security regression suite.

### NFR-SEC-03: Authentication Tokens
- JWTs used for session auth must have a 1-hour expiry with silent refresh.
- Refresh tokens must be stored in HttpOnly, Secure, SameSite=Strict cookies.
- No JWTs stored in localStorage or sessionStorage.
- Tokens must be invalidated server-side on logout.

### NFR-SEC-04: HTTPS Everywhere
All traffic must be served over TLS 1.2+. HTTP must redirect to HTTPS (301). HSTS header must be set with a minimum max-age of 31536000 seconds. No mixed content.

### NFR-SEC-05: Input Sanitization
All user-supplied input (session names, context variables, integration names) must be sanitized before storage and before being passed to AI model APIs. Prompt injection attempts (e.g., "Ignore all previous instructions") must be detected and flagged in the audit log, not silently passed to the model.

### NFR-SEC-06: Payment Data
Card numbers must never touch application servers. Stripe.js tokenizes card data client-side. PCI DSS SAQ A compliance is the target for MVP.

### NFR-SEC-07: Rate Limiting
API endpoints must enforce per-tenant rate limits:
- Auth endpoints: 10 requests per minute per IP.
- Session run endpoint: 60 sessions per hour per tenant (enforced separately from plan limits).
- Integration Vault endpoints: 30 requests per minute per tenant.
Exceeding limits returns HTTP 429 with a Retry-After header.

### NFR-SEC-08: Audit Log Integrity
Slack audit logs must not be the only record of session activity. All session events must also be written to an internal immutable event log in the database. This log must not be editable or deletable by tenants.

---

## 3. Availability and Reliability

### NFR-AVAIL-01: Uptime SLA
Target: 99.5% monthly uptime for the web application and API (excludes planned maintenance windows). This allows approximately 3.6 hours of downtime per month. Measured by an external uptime monitor (UptimeRobot or Better Uptime).

### NFR-AVAIL-02: Planned Maintenance
Planned maintenance windows must be announced 48 hours in advance via status page and email. Windows must be scheduled between 2:00 AM and 5:00 AM PT on weekdays or anytime on Sundays.

### NFR-AVAIL-03: AI Provider Outage Handling
The platform must remain fully available (dashboard, session history, billing, settings) even when all upstream AI providers are unavailable. Sessions during an outage are queued or fail gracefully with clear error messaging. The platform must not crash because Anthropic or OpenAI is down.

### NFR-AVAIL-04: Database Backups
Database must be backed up daily with a 30-day retention window. Backup restoration must be tested quarterly. Recovery Time Objective (RTO): 4 hours. Recovery Point Objective (RPO): 24 hours for MVP, targeting 1 hour by Phase 2.

### NFR-AVAIL-05: Health Checks
Every service (API, worker, scheduler) must expose a /health endpoint returning HTTP 200 with a JSON payload: { "status": "ok", "timestamp": "...", "version": "..." }. Orchestration layer (Docker/Kubernetes) must use this for liveness and readiness probes.

---

## 4. Scalability

### NFR-SCALE-01: Horizontal Scaling
The API and worker services must be stateless so they can be horizontally scaled by adding instances behind a load balancer. No in-process state. All shared state lives in the database or Redis.

### NFR-SCALE-02: Session Queue
Session dispatch must use a durable message queue (e.g., BullMQ backed by Redis) so that a worker crash does not lose in-flight sessions. Sessions must be retried automatically on worker restart.

### NFR-SCALE-03: Database Scaling Path
The data model must be designed to support read replicas for high-volume reads (session history, dashboard metrics) without schema changes. Tenant data must not be sharded in MVP, but the design must not prevent future sharding.

---

## 5. Compliance and Privacy

### NFR-COMP-01: GDPR -- Data Deletion
Tenants must be able to request deletion of all their data (account, sessions, outputs, API keys, audit logs) via a self-serve flow in account settings. Deletion must complete within 30 days. A confirmation email is sent when deletion is complete.

### NFR-COMP-02: CCPA -- Data Export
Tenants must be able to export all their data as a ZIP file containing: account info, session history, session outputs, and billing history. Export must be available within 24 hours of request.

### NFR-COMP-03: Data Residency (MVP)
MVP defaults to US-based data residency (AWS us-east-1 or equivalent). EU data residency is a Phase 2 requirement but the architecture must not make it impossible.

### NFR-COMP-04: Third-Party Data Passthrough
When tenant-provided API keys are used to call model providers, the data passes through the tenant's own API account. Hive Mind does not train on tenant session content. This must be stated explicitly in the Terms of Service and Privacy Policy.

### NFR-COMP-05: Secrets Handling
Environment variables containing secrets (database credentials, Stripe keys, internal API keys) must never be logged, included in error responses, or committed to version control. The .env.example file must contain only placeholder values.

---

## 6. Observability

### NFR-OBS-01: Structured Logging
All application logs must be structured JSON with fields: timestamp, level, service, tenant_id (if applicable), request_id, message, and error (if applicable). Logs must be shipped to a centralized log aggregator (e.g., Logtail, Datadog, or Grafana Loki).

### NFR-OBS-02: Error Tracking
Unhandled exceptions must be captured and reported to an error tracking service (Sentry or equivalent) with full stack trace, request context, and tenant_id (hashed for privacy). Alert thresholds: any new error type triggers a Slack alert within 5 minutes.

### NFR-OBS-03: Key Metrics Tracked
At minimum, the following metrics must be instrumented and dashboardable:
- Sessions dispatched per minute
- Session success rate (%)
- Session p50/p95 completion time
- API error rate by endpoint
- AI provider error rate by provider
- Active tenants (last 24h, last 7d)
- New sign-ups per day
- Trial-to-paid conversion rate

### NFR-OBS-04: Alerting
Critical alerts (service down, error rate > 5%, payment webhook failures, database connection failures) must page the on-call engineer via PagerDuty or equivalent within 2 minutes. Non-critical alerts (slow queries, high queue depth) go to a Slack ops channel.

---

## 7. Accessibility

### NFR-A11Y-01: WCAG 2.1 AA Compliance
The web dashboard must meet WCAG 2.1 Level AA for all core flows: sign-up, onboarding, session creation, output viewing, and billing. This includes keyboard navigation, sufficient color contrast (4.5:1 for normal text), and ARIA labels on all interactive elements.

### NFR-A11Y-02: Responsive Design
The dashboard must be fully usable on screens from 375px (iPhone SE) to 2560px (27-inch desktop). All interactive elements must be reachable and functional on mobile without horizontal scrolling.
