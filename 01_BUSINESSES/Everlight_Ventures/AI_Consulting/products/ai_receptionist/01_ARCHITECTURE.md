# AI Receptionist: Architecture Decision

**Owner**: Forge (Engineering Foreman)
**Date**: 2026-04-21
**Status**: Proposed. Awaiting greenlight.

---

## TL;DR

Use **Vapi + n8n + Google Calendar + Oracle Django monitoring**. We swap Make.com (video's choice) for n8n because we already run n8n on Oracle and the per-client fee savings widen our margin from ~50% to ~65%.

## Stack comparison

| Layer | Video uses | Everlight uses | Reason |
|---|---|---|---|
| Voice + ASR + TTS | Vapi | **Vapi** | Proven, well-documented, tool-calling native |
| Orchestration flows | Make.com ($9/mo per client) | **n8n** (we own it, Oracle :5678) | Kill the vendor pass-through, keep margin |
| Calendar backend | Google Calendar | **Google Calendar** | We already integrate via Gmail MCP |
| Client CRM/sheet | Google Sheets | **Google Sheets + Supabase** | Supabase for analytics, Sheets for client comfort |
| Monitoring | None in video | **Django /receptionist/ view on :8504** | Our differentiator: live call log the client can see |
| Alerts | None in video | **Slack bot to client workspace** | Upsell: missed calls / edge cases go to their Slack |

## Why Vapi over Retell

- Video walks through Vapi verbatim; Retell would require us to re-derive the tool-calling pattern.
- Vapi has a "Voice Library" where clients can pick their AI's voice in 5 minutes (self-service, saves us support time).
- Retell is newer and pricing is similar but docs are thinner.
- **Decision**: start with Vapi. Re-evaluate at 5 clients if Retell has meaningful cost/feature win.

## Why n8n over Make.com

- **We already run n8n**. Oracle service `n8n.service` on :5678 is paid-for (self-hosted, $0 marginal).
- Make.com is $9/mo minimum per workspace. At 10 clients = $90/mo recurring cost.
- n8n supports the same webhook + tool-calling pattern Vapi needs.
- Multi-tenancy: each client gets a subfolder `/n8n/workflows/clients/<client_slug>/` with their flows versioned in git.
- **Decision**: n8n. Set up client-isolated credentials per workflow.

## Call flow (Vapi perspective)

```
[Inbound call]
    |
    v
[Vapi: greeting] "Hi, you've reached <Client Business Name>..."
    |
    v
[Vapi: classify intent]
    |
    +---> [book] ---> get_availability (webhook) ---> book_time (webhook) ---> confirmation TTS
    |
    +---> [cancel] ---> search_cancel_booking (webhook) ---> cancel_booking (webhook) ---> confirmation
    |
    +---> [reschedule] ---> search_cancel_booking ---> cancel_booking ---> get_availability ---> book_time
    |
    +---> [FAQ] ---> vapi knowledge base (client-uploaded) ---> TTS answer
    |
    +---> [edge case: multiple matches, agent request] ---> transfer to human OR voicemail-to-Slack
```

## Webhook endpoints (n8n routes)

All run on Oracle `n8n.service` at `https://n8n.everlightventures.io/webhook/<path>`.

| Path | Verb | Purpose |
|---|---|---|
| `/receptionist/<client>/search_cancel_booking` | POST | Search calendar for event by caller name, 60-day window |
| `/receptionist/<client>/cancel_booking` | POST | Delete specific calendar event by ID |
| `/receptionist/<client>/get_availability` | POST | Parse time preference, return 3 available slots |
| `/receptionist/<client>/book_time` | POST | Create calendar event with caller details |
| `/receptionist/<client>/faq_fallback` | POST | Log unanswered FAQ to Supabase for manual review |
| `/receptionist/<client>/transfer` | POST | Trigger Twilio warm-transfer OR voicemail-to-Slack |

Each webhook is versioned per client (`<client>` is the URL-safe slug). Multi-tenant isolation.

## Credentials isolation

Each client has:
- Their own Google Calendar service account (client installs our app via OAuth during onboarding)
- Their own n8n workflow copies (not shared templates)
- Their own Supabase row-level record for call logs
- Their own Slack webhook (optional, for alert fan-out)

Stored in Oracle `/home/opc/receptionist_clients/<client>/.env`, mode 600, backed up nightly to `08_BACKUPS/`.

## Scaling economics

At N clients:
- Fixed cost: n8n (included), Oracle VM (included), Django dashboard (included)
- Variable cost: Vapi voice + LLM tokens (pass-through + 30% markup) + ~$3/mo per Supabase row impact
- Break-even for $199 recurring: 3 clients (covers our Ops + monitoring time at ~4 hours/mo per client)
- Target steady-state: 10 clients = $1990 MRR after 4 months, $990 margin

## What Forge needs to build (Phase 1 MVP)

1. `pipeline/ai_receptionist.n8n.json` (importable workflow template) **[this session]**
2. Vapi assistant template with prompt + tool definitions `pipeline/vapi_template.json` **[this session]**
3. Per-client onboarding checklist `onboarding/receptionist_checklist.md` **[this session]**
4. Django `/receptionist/` view showing call log per client **[next session, after 1st sale]**
5. Billing SKU in Stripe: `receptionist_setup_4500` + `receptionist_monthly_199` **[at close]**

## Open decisions for Lucrex

- Should Everlight provide each client with a dedicated phone number (Twilio ~$2/mo pass-through), or require the client to bring their own?
  - Default: **Everlight provides.** Cleaner UX for non-technical clients. Add $2/mo to the $199.
- Voicemail fallback: SMS text to Slack, or email to a shared inbox?
  - Default: **Slack with email fallback.** Clients can choose at onboarding.
- Should we offer a white-label tier (client's logo, hidden Everlight branding) at higher price?
  - Default: **Not at MVP.** Introduce "White-Label Plus" at $7500 + $399/mo once 5 clients ship.
