# Reposition: Piper IS Everlight's Receptionist

**Filed**: 2026-04-21
**Directive from Lucrex**: "These 1-10 are things I want to build out for myself."

---

## The rule

Everlight only sells products we have successfully built and used ourselves. The AI receptionist pattern is no different. We build it for Everlight first. We run it live against our own inbound (Hammer's line, hammer@everlightventures.io inquiries, incoming calls from the public site). Once it proves it can book discovery calls without friction, THEN we package it for clients.

## What this means for the artifacts already built

All 11 docs from Phase 1 + Phase 2 remain valid. Their framing shifts from "packaged service for SMBs" to "internal infrastructure we are deploying for Everlight first."

| Original framing | Reposition |
|---|---|
| "Your client's AI receptionist" | "Everlight's inbound-call handler" |
| "Client intake form" | "Everlight discovery-call intake" |
| "Client-isolated env" | "Everlight env first; multi-client isolation ships when we onboard client #1" |
| "$4,500 + $199 price" | "Internal cost to operate < $150/mo; external price holds if we package later" |
| "5-target outreach sequence" | "Applies ONLY to Everlight's own outreach for consulting prospects" |

## The actual Everlight configuration

- **Assistant name**: Piper (not Julie)
- **Business name in prompts**: Everlight Ventures
- **Phone number**: one Twilio local number (Sacramento 916 or Bay Area 510 area code), published at `everlightventures.io/contact`
- **First message**: "Hi, this is Piper from Everlight Ventures. How can I help?"
- **Primary intents she handles**:
  1. **AI Consulting discovery call** - books on Hammer's Google Calendar
  2. **Broker OS inquiry** - takes company + use-case, alerts Marcus in Slack, promises callback within 1 business day
  3. **Wholesale buyer interest** - captures buyer criteria, routes to Hammer for B-side matching
  4. **Content / publishing inquiries** - routes to Piper's email, NOT a book-call flow (low volume)
  5. **General info / FAQ** - reads from Everlight's FAQ knowledge base (to be uploaded from existing docs)
  6. **Edge case** - drops to voicemail, transcript lands in #war-room with audio

## The internal deployment checklist (overrides doc 07)

1. Forge creates ONE Vapi assistant named `everlight_piper` (not per-client)
2. Forge provisions ONE Twilio number, forwards to Vapi
3. Forge configures ONE n8n workflow set under `/n8n/workflows/internal/piper/`
4. Google Calendar target: Hammer's main calendar (not a per-client calendar)
5. FAQ knowledge base: upload existing Everlight docs
   - `CLAUDE.md` context extracts
   - `DISASTER_RECOVERY.md` summary
   - Product sheets for Onyx POS, Hive Mind, Alley Kingz, Publishing
   - Pricing + packages for AI Consulting
6. Slack notifications go to existing `#ai-consulting` and `#ft-consult` channels
7. Live call log appears in Django `/receptionist/piper/` view on :8504

## Success metric for "we built it successfully"

- 30 days of live uptime at Everlight's published phone number
- Zero customer-reported booking errors
- Call log shows real usage (even 5-10 real calls is enough proof)
- Hammer confirms a booked discovery call came through Piper that would otherwise have been missed
- Cost stays under $150/mo total (Vapi + Twilio)

Only then do we open the packaged offering, use the Everlight case study as proof, and offer it to SMBs at $4,500 + $199/mo.

## What to do with the Phase 1 + 2 product docs

Stay put where they are. Add a banner at the top of each:

> **Status: INTERNAL FIRST.** These docs define a product pattern. Everlight runs it for itself before selling. Client-facing versions activate only after we prove the pattern works for us.

Optionally, move client-specific files (sales one-pager, outbound playbook, email templates) to a `_pending_external_launch/` subfolder so they're clearly on ice until Everlight proves the pattern.

## Phase-gating: internal vs external

| Gate | Trigger |
|---|---|
| Internal deploy | Lucrex pastes Vapi + Twilio keys |
| Internal go-live | Forge + Hammer test 5 real calls, 100% pass |
| External packaging unlock | 30 days internal + 1 Hammer-confirmed missed-call-saved |
| First external sale | Only after external packaging is unlocked |

## What's different from Phase 2 work

Change in the receptionist docs:

- Doc 01 (Architecture): Change "client" references to "Everlight"; keep multi-tenant-ready wiring for later
- Doc 02 (n8n JSON): Replace `{{CLIENT_SLUG}}` with `internal/piper` for the Everlight deployment
- Doc 03 (Vapi JSON): Replace `{{CLIENT_BUSINESS_NAME}}` with "Everlight Ventures", `{{AGENT_VOICE_NAME}}` with "Piper"
- Doc 04 (Sales one-pager): STAYS, but moved to `_pending_external_launch/`
- Doc 05 (Financial model): STAYS; add an "Everlight internal cost" block above the revenue tables
- Doc 06 (Outbound playbook): Applies ONLY to Everlight's own outreach, not a client service
- Doc 07 (Onboarding checklist): STAYS for later; doc 00 above supersedes for Everlight deployment
- Doc 10 (Target research): APPLIES AS IS - we are targeting 5 businesses for OUR AI consulting, not for a receptionist product sale
- Doc 11 (Email templates): REMOVE vertical-specific pitches; these were for selling the receptionist. Replace with Everlight's own AI consulting pitch (to be drafted separately)

Forge and Piper will execute these doc updates alongside Phase 3 implementation.
