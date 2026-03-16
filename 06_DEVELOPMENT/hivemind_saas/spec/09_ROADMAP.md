# Product Roadmap -- Everlight Hive Mind SaaS
# Phase 0 Spec | Version 1.0 | 2026-02-27

---

## Guiding Principles

1. Ship the smallest version that demonstrates the core value (AI runs a real workflow end-to-end) as fast as possible.
2. Every phase gate requires: working software, at least 5 paying customers who renew, and NPS above 30 before proceeding.
3. Do not build Phase 2 features until Phase 1 is stable and converting.
4. Revenue funds Phase 2. If Phase 1 does not reach $3,000 MRR by Month 3, pause and re-evaluate ICP or pricing before expanding.

---

## Phase 1 -- MVP (Months 0-2)
### Target: 10 paying customers, $1,000 MRR, first Slack audit log posted

**Theme: Prove the core loop works.**

The core loop is: sign up -> connect API key -> run a session from a template -> see the output in the dashboard -> get a Slack audit log. Everything else is secondary to proving this loop is valuable enough to pay for.

---

### Month 0 -- Foundation (Weeks 1-4)

**Infrastructure and Auth**
- Provision cloud environment (Vercel + Supabase recommended for solo builder speed).
- Set up CI/CD pipeline (GitHub Actions: test on push, deploy on merge to main).
- Implement multi-tenant auth: Google OAuth + email/password + JWT refresh tokens.
- Implement tenant data isolation at the database layer.
- Build onboarding checklist UI (3-step flow).
- Deploy staging environment at staging.hivemind.everlightventures.com.

**Integration Vault**
- Build Integration Vault UI and API.
- Implement AES-256 credential encryption with secrets manager.
- Support 4 initial providers: OpenAI, Anthropic, Google AI, Perplexity.
- Per-integration connection test endpoint.

**Hive Dispatcher (v1)**
- Build session dispatcher service.
- Implement 4 task type routes: research (Perplexity), writing (Claude), structured content (Gemini), code (OpenAI).
- Single-model session support only (multi-model synthesis is Week 5+).
- Session queue backed by Redis + BullMQ.
- Retry logic with exponential backoff and model fallback.

**Deliverable at end of Month 0:** A working session can be created and run from the terminal (not yet the full dashboard UI). A research session using a Perplexity key produces an output stored in the database.

---

### Month 1 -- Core Product (Weeks 5-8)

**Session Builder UI**
- Full session creation wizard (4-step: template, context, schedule, review).
- 12 session templates built and tested.
- Session templates library screen.

**Dashboard and Output Viewer**
- Dashboard home screen (stats, quick launch, recent sessions).
- Session list screen with filters.
- Session detail screen with live status feed.
- Session output viewer with model attribution and download options.

**Slack Audit Logger**
- Slack OAuth integration.
- Channel selector.
- Structured audit log messages for: session start, model dispatch, completion, error.
- Graceful degradation when Slack is not connected.

**Multi-Model Synthesis (v1)**
- Implement research + writing pipeline (Perplexity feeds Claude).
- Model attribution tracking in SESSION_EVENT and SESSION_OUTPUT.

**Billing (Basic)**
- Stripe integration: Spark ($49/mo) and Hive ($129/mo) plans.
- 7-day free trial with Hive-tier entitlements.
- Trial expiry enforcement.
- Subscription activation flow.
- Billing screen with usage meter.

**Deliverable at end of Month 1:** The full product loop works. A real user can sign up, connect keys, run a content calendar session from a template, see the output in the dashboard, and view the Slack audit log.

---

### Month 2 -- Polish and First Customers (Weeks 9-12)

**Onboarding Refinement**
- Instrument every onboarding step with analytics.
- Add in-app tooltip guidance on first use.
- Add "Platform key" option to reduce friction for non-technical users (uses Everlight-managed keys at markup). This is the key conversion unlock.

**Webhook Triggers**
- Webhook endpoint CRUD.
- Inbound trigger handler with HMAC validation.
- Rate limiting and loop detection.

**Email Notification Digest**
- Transactional email via Resend or Postmark.
- Weekly digest email: sessions completed, cost, errors.
- Session completion and error notification emails.

**Error Handling Polish**
- Comprehensive error states in the UI (no silent failures).
- Retry button on failed sessions.
- "Integration in error" alert banner in dashboard.

**Security Review**
- Internal security review of credential vault, auth, and API endpoints.
- Confirm no plaintext credentials in logs, API responses, or error messages.
- Rate limiting verified on all auth and session endpoints.

**Soft Launch**
- Invite 20 beta users from the ICP (solopreneurs, small agency owners).
- Offer 30-day free full access in exchange for a 30-minute feedback call.
- Use feedback to fix the top 3 problems before public launch.

**Deliverable at end of Month 2:** 10 paying customers. Feedback incorporated. Ready for Phase 2.

**Phase 1 Gate Criteria (must all pass before Phase 2 starts):**
- All 15 MVP features (F01-F15) are live and tested.
- At least 10 paying customers have used the product more than once.
- Trial-to-paid conversion rate is above 15%.
- No P0 security bugs open.
- Onboarding completion rate above 40%.
- NPS from beta users above 30.

---

## Phase 2 -- Growth (Months 3-5)
### Target: 100 paying customers, $10,000 MRR, Hive plan as dominant tier

**Theme: Make the product stickier and expand its surface area.**

---

### Month 3 -- Mindmaps and Multi-User

**Interactive Mindmap Viewer**
- Build the ReactFlow-based session mindmap screen (/sessions/:id/mindmap).
- Node types: session start, model task, merge, output delivery.
- Right-side drawer for node detail (prompt + response).
- Export as PNG.
- This is a high-perceived-value feature that differentiates the platform visually.

**Multi-User Workspaces (v1)**
- Invite team members by email.
- Role-based access: owner, editor, viewer.
- Editor: can create and run sessions. Viewer: read-only access to session history and outputs.
- Team member management screen in Settings.

**Session Collaboration**
- Session outputs can be commented on by team members (Phase 2 addition to output viewer).
- Comment notifications via email.

---

### Month 4 -- Integrations Marketplace v1

**Integration Framework**
- Refactor integration system to support a broader set of providers beyond AI model APIs.
- New integration categories: storage (Google Drive, Dropbox), CRM (HubSpot, Pipedrive), communication (Gmail, Outlook), content (Notion, Airtable).
- Each integration type has its own credential handler and connection test.

**First 10 New Integrations**
Priority order based on ICP survey results. Expected top picks: Gmail, Google Drive, Notion, HubSpot, Airtable, Shopify, Mailchimp, Typeform, Calendly, Stripe.

**Delivery Destinations**
- Sessions can now deliver outputs directly to a connected integration (e.g., save output as a Google Doc, add a row to an Airtable base, send a draft email via Gmail).
- Tenant explicitly enables auto-delivery per session. "Review before delivery" remains the default.

---

### Month 5 -- Agent Memory and Billing Expansion

**Agent Memory Store (v1)**
- Cross-session persistent memory: the hive can reference the tenant's business context (company description, tone guide, target audience, product catalog) in every session without re-entering it each time.
- Memory editor in Settings: a form where the tenant fills in key business facts.
- Memory is injected into every session's system prompt automatically.

**Annual Billing**
- Add annual billing option to all plans (20% discount).
- Annual plan upgrade prompts on the billing screen at Month 4 (optimal timing for tenants who have proven value over 3 months).

**Enterprise Tier (v1)**
- Enable Enterprise plan at $399/mo.
- Manual onboarding call for Enterprise sign-ups.
- Dedicated Slack support channel.
- Custom integrations scoping.

**Phase 2 Gate Criteria:**
- 100 paying customers.
- MRR at $10,000 or above.
- Month-3 churn below 5%.
- NPS above 40.
- At least 10 customers on annual plans.

---

## Phase 3 -- Scale (Months 6+)
### Target: $50,000 MRR, white-label revenue, enterprise contracts, team workspaces as a primary use case

**Theme: Turn the platform into a business operating system for small teams.**

---

### Months 6-8 -- White-Label and Agencies

**White-Label Mode**
- Custom domain (client.agencyname.com).
- Custom logo, brand colors, and email templates.
- "Powered by Everlight" removed (or kept as optional co-branding).
- This unlocks the agency resale channel. An agency using Hive Mind can resell it to their clients under their own brand.

**Client Portal Mode**
- Agencies can grant read-only portal access to their clients.
- Client portal shows: sessions run on their behalf, outputs, cost summary.
- Agency retains full control; clients only see what the agency allows.

**Agency Billing**
- Agencies can bill their clients directly through the platform (Stripe Connect or manual invoice generation).
- Usage-based billing: agencies see cost per client per month and can mark up accordingly.

---

### Months 8-10 -- Enterprise Features

**Enterprise SSO**
- SAML 2.0 / OKTA integration.
- Provisioning/deprovisioning via SCIM.

**SOC 2 Type II Preparation**
- Engage a compliance firm (e.g., Vanta for automated evidence collection).
- Estimated 6-month timeline to certification.
- Required to sell to companies with procurement teams.

**Advanced Approval Workflows**
- Session outputs can require approval before delivery.
- Multi-step approval chains (e.g., editor reviews, then owner approves).
- Approval tracked in SESSION_EVENT audit log.

**Custom Model Support**
- Connect a fine-tuned OpenAI model or a custom inference endpoint.
- The hive can route specific task types to the custom model.

---

### Months 10+ -- Platform Expansion

**Everlight Hive Mind API**
- Public API allowing developers to embed Hive Mind session execution in their own products.
- Rate-limited, key-based access.
- SDK libraries for Node.js and Python.
- This opens a B2B2B channel: developers build on top of our hive.

**Voice Input Sessions**
- Record a voice note via the dashboard or mobile web.
- The hive transcribes (Whisper API) and dispatches a session based on the spoken request.
- Targets solopreneurs who have ideas while on the move.

**Community Template Marketplace**
- Tenants can publish custom templates to a community library.
- Rating and usage count system.
- Featured templates highlighted on the /templates screen.
- Top template creators get a revenue share (5% of subscriptions using their template).

---

## Milestone Summary

| Milestone | Target Date | Key Metric |
|-----------|-------------|------------|
| Private beta launch | Month 2, Week 3 | 20 beta users |
| Phase 1 complete | End of Month 2 | 10 paying customers |
| Phase 2 launch | Start of Month 3 | Mindmaps live |
| Phase 2 complete | End of Month 5 | 100 customers, $10k MRR |
| White-label launch | Month 6 | First agency resale |
| SOC 2 initiated | Month 8 | Compliance firm engaged |
| Phase 3 milestones | Month 10+ | $50k MRR target |
