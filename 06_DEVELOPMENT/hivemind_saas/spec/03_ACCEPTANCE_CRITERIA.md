# Acceptance Criteria -- Everlight Hive Mind SaaS
# Phase 0 Spec | Version 1.0 | 2026-02-27
# Format: BDD (Given / When / Then)

The 5 features covered here are the most critical for MVP viability. If any of these fail, the product does not work.

---

## Feature 1: Multi-Tenant Auth and Onboarding (F01)

### AC-F01-01: Google OAuth Sign-Up
Given a visitor is on the sign-up page
When they click "Continue with Google" and authorize the OAuth consent screen
Then a new tenant account is created with their Google profile name and email
And they are redirected to the onboarding checklist
And no password is required

### AC-F01-02: Email/Password Sign-Up
Given a visitor submits a valid email and password (8+ characters, 1 uppercase, 1 number)
When the form is submitted
Then a new tenant account is created
And a verification email is sent to the provided address
And the user sees a "Check your inbox" screen
And the account is in "unverified" state until the link is clicked

### AC-F01-03: Duplicate Email Blocked
Given an email address already exists in the system
When a new sign-up is submitted with the same email
Then the form returns an error: "An account with this email already exists. Sign in instead."
And no duplicate account is created

### AC-F01-04: Onboarding Completion Tracking
Given a new tenant has signed up
When they complete all 3 onboarding steps (connect integration, create session, verify Slack log)
Then their account record shows onboarding_complete = true
And the onboarding checklist is replaced with the main dashboard home
And a "Welcome to Hive Mind" Slack message is posted to their configured channel

### AC-F01-05: Session Persistence
Given a tenant is logged in
When they close the browser tab and reopen the app URL within 7 days
Then they are automatically returned to their dashboard without being prompted to sign in again
And their session token is refreshed silently

---

## Feature 2: Integration Vault -- API Key Manager (F02)

### AC-F02-01: API Key Save and Encrypt
Given a tenant navigates to the Integration Vault and selects "Add OpenAI Key"
When they paste a valid-format OpenAI API key and click Save
Then the key is encrypted with AES-256 before writing to the database
And the dashboard displays "OpenAI: Connected" with a green status badge
And only the last 4 characters of the key are ever shown in the UI (e.g., "...k9Qz")

### AC-F02-02: Connection Test on Save
Given a tenant saves an API key
When the save action completes
Then the system immediately makes a lightweight test call to the provider's API (e.g., list models)
And if the call succeeds, the status badge shows "Active"
And if the call fails (invalid key, quota exceeded), the status badge shows "Error: [reason]"
And the key is still saved even on a failed test (tenant may need to update quota)

### AC-F02-03: Key Revocation
Given a tenant clicks "Revoke" on a connected integration
When they confirm the action in the confirmation dialog
Then the encrypted key is permanently deleted from the database
And the integration status changes to "Not Connected"
And any scheduled sessions that require that integration are paused and the tenant is notified

### AC-F02-04: Key Never Exposed in Plaintext
Given any tenant API key has been saved
When the tenant views the Integration Vault, calls the API, or inspects server logs
Then the full key value is never returned in any UI, API response, or application log
And any attempt to GET the raw key via the API returns a 403 Forbidden

---

## Feature 3: Hive Session Dispatcher (F04)

### AC-F04-01: Task Routing by Type
Given a tenant creates a session with task_type = "research"
When the session is dispatched
Then the primary model used is Perplexity
And the Slack audit log shows: "Subtask dispatched to Perplexity: [task description]"
And if Perplexity fails, the fallback model is Claude with a "fallback" tag in the log

### AC-F04-02: Multi-Model Synthesis Session
Given a tenant creates a session with task_type = "content" requiring research + writing
When the session is dispatched
Then Perplexity is called first for research
And its output is passed as context to the Claude writing call
And the final output in the dashboard shows a model attribution breakdown: "Research: Perplexity, Draft: Claude"

### AC-F04-03: Session Completion Within SLA
Given a tenant runs a standard single-model session (task length under 2,000 tokens)
When the session is dispatched
Then the output is delivered within 45 seconds
And if the session exceeds 120 seconds total, the tenant receives an in-app and Slack timeout warning
And the session is marked "Timed Out" rather than hanging indefinitely

### AC-F04-04: Model Fallback on API Failure
Given a tenant's primary model API returns a 429 (rate limit) or 500 (server error)
When the dispatcher receives the error
Then it retries the same model after 3 seconds, then 9 seconds
And if both retries fail, it routes the subtask to the fallback model for that task type
And the Slack log notes: "Primary model unavailable -- routed to fallback [model name]"
And the final output is still delivered to the tenant

### AC-F04-05: Session Blocked When Integration Missing
Given a tenant creates a session that requires an OpenAI key
And their OpenAI key is not connected or is in error state
When they attempt to run the session
Then the run is blocked before dispatch
And the tenant sees: "This session requires an OpenAI connection. Go to Integration Vault to fix this."
And no API calls are made

---

## Feature 4: Slack Audit Logger (F05)

### AC-F05-01: Session Start Log
Given a tenant has a Slack workspace connected and a channel configured
When any session begins execution
Then within 5 seconds a Slack message is posted to the configured channel
And the message contains: tenant name, session name, session ID, task type, start timestamp (PT), and estimated cost

### AC-F05-02: Session Complete Log
Given a session completes successfully
When the output is finalized
Then a Slack message is posted containing: completion timestamp, models used, actual cost, output word count, and a link to view the full output in the dashboard

### AC-F05-03: Session Error Log
Given a session fails at any step
When the error is captured
Then a Slack message is posted with: error type, which model failed, step in the pipeline that failed, and a "Retry" deep link back to the dashboard

### AC-F05-04: Slack Not Connected -- Graceful Degradation
Given a tenant has not connected a Slack workspace
When a session runs
Then the session executes normally
And the output is available in the dashboard
And no Slack messages are attempted
And the tenant sees a persistent banner: "Slack audit logging is inactive. Connect Slack to enable it."

### AC-F05-05: Slack Channel Selection
Given a tenant clicks "Configure Slack Logging" in Settings
When they authorize the Slack OAuth and are shown their workspace's channel list
Then they can select any public channel or private channel they have access to
And the selection is saved
And a test message "Hive Mind connected to this channel" is immediately posted to confirm

---

## Feature 5: Billing and Subscription Management (F08)

### AC-F08-01: Free Trial Start
Given a new tenant completes sign-up
When their account is created
Then a 7-day free trial is automatically started with Hive tier entitlements
And the dashboard shows a trial badge: "7 days remaining in your free trial"
And no credit card is required to start the trial

### AC-F08-02: Trial Expiry Enforcement
Given a tenant's 7-day trial has ended
And they have not added a payment method
When they attempt to run a new session
Then the session is blocked
And a modal is shown: "Your trial has ended. Add a payment method to continue."
And existing session history remains accessible

### AC-F08-03: Successful Subscription
Given a tenant is on the billing page
When they enter a valid credit card and select a plan
Then the card is tokenized via Stripe.js (card number never touches our servers)
And the subscription is activated in Stripe
And a webhook updates their entitlement in our database within 30 seconds
And they receive a confirmation email with their plan name and renewal date

### AC-F08-04: Tier Limit Enforcement -- Spark Plan
Given a Spark plan tenant has consumed 100 sessions this billing month
When they attempt to run session number 101
Then the session is blocked
And the tenant sees: "You've used all 100 sessions in your Spark plan. Upgrade to Hive for unlimited sessions."
And a one-click upgrade CTA is displayed

### AC-F08-05: Payment Failure Handling
Given a tenant's subscription renewal fails due to a declined card
When Stripe sends the payment_intent.payment_failed webhook
Then the tenant is sent an email with a link to update their payment method
And they have a 7-day grace period before sessions are suspended
And a banner in the dashboard shows: "Payment failed. Update your billing info to avoid interruption."
And after 7 days without resolution, sessions are suspended (not the account -- data is preserved)
