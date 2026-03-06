# UI Map -- Everlight Hive Mind SaaS
# Phase 0 Spec | Version 1.0 | 2026-02-27

---

## Structure Overview

```
PUBLIC (unauthenticated)
  /                          Landing Page
  /pricing                   Pricing Page
  /login                     Sign-In Page
  /register                  Sign-Up Page
  /verify-email              Email Verification Gate

ONBOARDING (authenticated, onboarding_complete = false)
  /onboarding                Onboarding Checklist (blocks main nav)

MAIN APP (authenticated, onboarding_complete = true)
  /dashboard                 Home / Overview
  /sessions                  Sessions List
  /sessions/new              Session Builder
  /sessions/:id              Session Detail
  /sessions/:id/output       Session Output Viewer
  /sessions/:id/mindmap      Session Mindmap (Phase 2)
  /templates                 Template Library
  /integrations              Integration Vault
  /webhooks                  Webhook Endpoints
  /settings                  Workspace Settings
  /billing                   Billing and Plan Management

ADMIN (platform staff only, separate subdomain)
  /admin/tenants             Tenant List
  /admin/tenants/:id         Tenant Detail
  /admin/sessions            All-Tenant Session Monitor
  /admin/metrics             Platform Metrics Dashboard
```

---

## Screen Specifications

---

### / -- Landing Page
Purpose: Convert visitors to sign-ups. Establish the "AI Chief of Staff as a Service" positioning.

Sections:
1. Hero: Headline, sub-headline, primary CTA ("Start Free Trial -- No Credit Card"), secondary CTA ("See How It Works" -- scrolls to demo section).
2. Pain Agitation: 3-column grid showing the 3 broken alternatives (manual AI prompting, Zapier complexity, developer frameworks). Each with an icon and 2-sentence problem description.
3. Solution Demo: Animated walkthrough or short screen-recording loop showing a session running and a Slack audit log appearing. No voiceover needed -- on-screen labels tell the story.
4. Feature Highlights: 6 feature cards in a 2x3 grid (F01-F06 from PRD). Icon + title + 1 sentence.
5. Pricing Preview: 3-column pricing summary with plan names and prices. CTA to /pricing for full detail.
6. Social Proof (placeholder for MVP): 3 quote cards. Can use beta tester quotes from initial 10 customers.
7. FAQ: 6 questions covering: What is a Hive Session, Do I need to provide my own API keys, Is my data safe, What happens after the trial, Can I cancel anytime, What if an AI provider is down.
8. Footer: Nav links, Everlight Ventures brand, privacy policy, terms of service.

Tech notes: Next.js static page. No auth state needed. Optimized for Core Web Vitals. Meta tags and OG image configured.

---

### /pricing -- Pricing Page
Purpose: Full pricing breakdown to support purchase decision.

Sections:
1. Plan comparison table: 3 columns (Spark, Hive, Enterprise). Rows cover all key features with check/dash indicators.
2. Billing toggle: Monthly / Annual with annual savings callout ("Save 20% annually").
3. FAQ: 4 billing-specific questions.
4. "Talk to Sales" CTA for Enterprise inquiries (opens Calendly or email link).

---

### /login -- Sign-In Page
Purpose: Authenticate returning users.

Elements:
- "Continue with Google" button (primary).
- Or divider.
- Email input + password input.
- "Forgot password?" link.
- "Sign In" button.
- "Don't have an account? Start free trial" link to /register.
- Error state: inline error below the relevant field.

---

### /register -- Sign-Up Page
Purpose: Create new account.

Elements:
- "Continue with Google" button (primary -- skips the form entirely).
- Or divider.
- Workspace name input (pre-fills from email domain if Google).
- Email input.
- Password input with strength indicator.
- "Create Account" button.
- "Already have an account? Sign in" link.
- Fine print: "By creating an account you agree to our Terms of Service and Privacy Policy."
- No credit card prompt on this page.

---

### /verify-email -- Email Verification Gate
Purpose: Hold state while user verifies email. Shown only for email/password registrations.

Elements:
- "Check your inbox" heading with the email address shown.
- Illustration (inbox icon or envelope animation).
- "Resend verification email" link (rate-limited to 1 per 60 seconds).
- "Wrong email? Go back" link.
- Auto-redirect to /onboarding once the verification link is clicked.

---

### /onboarding -- Onboarding Checklist
Purpose: Get the new tenant to their first working session in under 8 minutes.

Layout: Centered single-column layout. No sidebar. No main nav shown (reduces distraction).

Elements:
- Progress indicator: "Step X of 3" with horizontal progress bar.
- Step 1 -- Connect an Integration: Shows a list of supported providers. User clicks one, enters their API key, sees the connection test result (green checkmark or red error). Can skip to step 2 if they want to explore first.
- Step 2 -- Create Your First Session: Shows the 3 most popular templates (content calendar, support triage, sales outreach) as large clickable cards. Selecting one opens a minimal inline form for the context variables. "Run It Now" button fires the session and advances to step 3.
- Step 3 -- Verify Slack Logging: "Connect Slack" button triggers Slack OAuth. After success, shows the channel selector dropdown. "Send Test Message" button posts a test message. If they skip Slack, a note explains they can set it up later in Settings.
- Completion screen: Confetti animation (subtle). "Your hive is ready" heading. "Go to Dashboard" button.

---

### /dashboard -- Home / Overview
Purpose: The daily-driver screen. Answers "what's happening and what do I need to do?"

Layout: 2-column grid (main content left, sidebar right on desktop; stacked on mobile).

Main content:
- "Quick Launch" card: Dropdown to pick a template, then "Run Session" button. One click to start.
- Recent Sessions list: Last 5 sessions with status badge (running/completed/failed), session name, timestamp, cost. Click any row to go to /sessions/:id.
- Usage meter: Progress bar showing sessions used / session limit for current billing period. "Upgrade" link if near limit.

Sidebar:
- Stats cards: Sessions this week, total sessions, total AI spend this month, integrations active.
- Hive status: Shows connection status of each integrated provider (green/red dots with provider name). Alerts if any integration is in error state.
- Trial banner (if on trial): Days remaining + "Upgrade Now" CTA. Hidden after subscribing.

---

### /sessions -- Sessions List
Purpose: Browse, search, and filter all past sessions.

Elements:
- Search bar: Searches by session name.
- Filter bar: Status dropdown, task type dropdown, date range picker.
- Sessions table: Columns: Name, Task Type, Status badge, Models Used, Cost, Date. Sortable by date and cost. Click row to go to detail.
- "New Session" button (top right) -- links to /sessions/new.
- Pagination (20 per page, cursor-based).
- Empty state: If no sessions yet, shows a "Create your first session" card with a template picker.

---

### /sessions/new -- Session Builder
Purpose: Configure and launch a new hive session.

Layout: Multi-step form wizard with 4 steps.

Step 1 -- Pick a Template or Start Custom:
- Grid of template cards (icon + name + description).
- "Custom Session" card at the end.
- Search/filter bar for templates.
- Clicking a card selects it and advances to Step 2.

Step 2 -- Fill In Context:
- Session name input (pre-filled from template name + today's date).
- Context variable inputs (generated from the template's schema -- different for each template).
- Each input has a label and a placeholder hint.

Step 3 -- Schedule:
- 3 options as segmented control: "Run Now", "Schedule", "On Webhook".
- "Run Now" -- no additional config.
- "Schedule" -- shows cron-builder UI (day picker + time picker -- no raw cron required).
- "On Webhook" -- shows existing webhook endpoints or option to create new one.

Step 4 -- Review and Launch:
- Summary of: session name, template used, context variables (abbreviated), schedule, estimated cost in USD.
- "Edit" links next to each section to go back.
- "Launch Session" button (or "Save as Draft" if not running immediately).
- Cost estimate prominently displayed.

---

### /sessions/:id -- Session Detail
Purpose: Monitor a running session or review a completed one.

Elements:
- Session name and status badge (with live status update via polling or websocket).
- Live activity feed: Streaming list of SESSION_EVENTS in human-readable form ("Dispatching research task to Perplexity...", "Draft received from Claude (1,842 tokens)...", "Delivering output to Slack #content-drafts...").
- Model attribution panel: Shows which model handled which subtask with token counts and cost breakdown.
- Cost tracker: Estimated cost on left, running actual cost on right (fills in as steps complete).
- "View Output" button: Appears when status = completed. Links to /sessions/:id/output.
- "Re-run Session" button: Always visible on completed sessions.
- "Cancel Session" button: Visible only on queued or running sessions.
- Error panel: Shown if status = failed. Displays error type, which step failed, and "Retry" button.

---

### /sessions/:id/output -- Session Output Viewer
Purpose: Read, copy, and download the full session output.

Elements:
- Session name and completion timestamp.
- Output rendered as formatted Markdown (code blocks, headers, bullet points preserved).
- "Copy All" button.
- "Download" dropdown: options for Markdown (.md), plain text (.txt), JSON (.json).
- Model attribution accordion: Collapsed by default. Expands to show which model contributed what section.
- Total cost and token breakdown.
- "Re-run" button.
- Link back to session detail.

---

### /sessions/:id/mindmap -- Session Mindmap (Phase 2)
Purpose: Visual exploration of how the hive processed a session.

Elements:
- ReactFlow canvas with pan/zoom. Full-screen toggle.
- Node types: session start (left anchor), model task nodes (color-coded by model), merge node (if multi-model), output delivery node (right anchor).
- Clicking any model task node opens a right-side drawer with: raw prompt, raw model response, tokens, cost, latency.
- Toolbar: Zoom in/out, fit-to-screen, export as PNG.

---

### /templates -- Template Library
Purpose: Browse and select session templates.

Elements:
- Filter tabs: All, Content, Research, Support, Outreach, Ops, Code, Summary.
- Template cards grid (2 or 3 column). Each card: icon, name, description, required integrations (provider logos), "Use Template" button.
- "Create Custom Template" button (P1 -- coming soon tag in MVP).

---

### /integrations -- Integration Vault
Purpose: Manage all connected API keys and third-party services.

Elements:
- Integration cards grid: One card per supported provider. Shows: provider logo, provider name, status badge (Active / Error / Not Connected / Revoked), last used, credential hint (last 4 chars).
- Each card has a "Manage" button opening a right-side drawer:
  - Drawer content: Edit display name, update credential (masked input), "Test Connection" button, "Revoke" button (with confirmation dialog).
- "Add Integration" button: Opens a provider selection modal, then the credential input drawer.
- Alert banner at top if any integration is in error state.

---

### /webhooks -- Webhook Endpoints
Purpose: Create and manage inbound webhook trigger URLs.

Elements:
- Webhooks list: Each row shows label, linked template, trigger URL (truncated with copy button), last triggered, trigger count, active toggle.
- "New Webhook" button: Opens modal to name it and select a template.
- Secret reveal: "View Secret" button -- requires re-authentication (password confirm or 2FA in Phase 2). Secret is shown once; user copies it to their external tool.
- Delete button with confirmation.

---

### /settings -- Workspace Settings
Purpose: Configure workspace, notifications, and connected services.

Tabs:
1. General: Workspace name, timezone, owner email (read-only).
2. Notifications: Digest frequency dropdown, toggle for email-on-complete, email-on-error. Slack channel configuration.
3. Security: Change password (email auth users only), active sessions list with revoke option, API key for programmatic access (Phase 2).
4. Danger Zone: "Delete Workspace" button -- opens a confirmation dialog requiring the user to type their workspace name.

---

### /billing -- Billing and Plan Management
Purpose: View plan, manage subscription, see usage.

Elements:
- Current plan card: Plan name, status badge, next renewal date, next invoice amount. "Change Plan" and "Cancel Plan" buttons.
- Usage this period: Sessions used / limit (progress bar), AI cost to date, cost alert threshold setting.
- Payment method: Card brand + last 4 + expiry. "Update" button opens Stripe Customer Portal.
- Invoice history: Last 6 invoices with date, amount, status, download PDF link.
- "Manage Billing" button: Opens Stripe Customer Portal for all self-serve billing actions.
- Plan comparison table (same as /pricing but embedded, for upsell reference).

---

## Navigation Structure

Top nav (desktop sidebar, mobile bottom bar):
- Dashboard (home icon)
- Sessions (lightning bolt icon)
- Templates (grid icon)
- Integrations (plug icon)
- Settings (gear icon)

Secondary nav items in sidebar footer:
- Billing (credit card icon)
- Help / Support (question mark icon -- opens Intercom or support form)
- User avatar dropdown: Profile, Sign Out

Trial banner: Persistent at top of all app screens until user subscribes. Shows days remaining and an "Upgrade" CTA.
