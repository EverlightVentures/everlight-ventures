# AI Receptionist - Client Onboarding Checklist

**Owner**: Forge (build) + Piper (client-facing)
**SLA**: 7 business days from signed deposit to soft launch.

---

## Pre-kickoff

- [ ] Stripe deposit ($2,250) received
- [ ] Contract signed via Stripe checkout auto-DocuSign add-on
- [ ] Client added to Supabase `receptionist_clients` table
- [ ] Client Slack channel created: `#client-<slug>` (internal, not shared)
- [ ] `/home/opc/receptionist_clients/<slug>/.env` file provisioned on Oracle

## Day 1-2: Intake

- [ ] Intake form sent (Tally.so): services, pricing, hours, FAQ doc link, Google account email
- [ ] Client completes intake
- [ ] Piper reviews intake, flags anything unclear
- [ ] Client grants Google Calendar OAuth to Everlight service account
- [ ] Client picks AI voice from ElevenLabs library (send them 5 preselected options)

## Day 3-4: Build

- [ ] Forge copies `02_n8n_workflow_template.json` to client folder
- [ ] Forge replaces placeholders: `{{CLIENT_SLUG}}`, `{{GOOGLE_CAL_ID}}`, `{{SLACK_WEBHOOK}}`
- [ ] Import to n8n (production instance)
- [ ] Forge copies `03_vapi_template.json`, replaces `{{CLIENT_BUSINESS_NAME}}`, `{{AGENT_VOICE_NAME}}`, etc.
- [ ] Deploy Vapi assistant via API
- [ ] Upload client FAQ doc as Vapi knowledge base
- [ ] Provision Twilio phone number (local area code matching client's city)
- [ ] Wire Twilio number to Vapi inbound

## Day 5: Internal test

- [ ] Forge places 5 test calls, scripts:
  - [ ] Book appointment with specific time
  - [ ] Book appointment with generic time
  - [ ] Cancel existing appointment
  - [ ] Reschedule existing appointment
  - [ ] FAQ with a question the KB doesn't cover (should transfer)
- [ ] Verify all 5 flow through n8n webhooks correctly
- [ ] Verify Supabase logs each call
- [ ] Verify Slack alerts fire

## Day 6: Client review

- [ ] Piper sends client the temporary test number
- [ ] Client places 3 test calls from their own cell phone
- [ ] Client reviews the call recordings in the Django dashboard
- [ ] Client submits tuning feedback (voice tone, word choice, FAQ additions)
- [ ] Forge applies tuning (typically 1-2 hour turnaround)

## Day 7: Soft launch

- [ ] Forward half of client's main line to the AI number (Twilio forwarding rule)
- [ ] AI handles 50% inbound for first 3 days
- [ ] Daily review: Piper + Forge listen to 5 random recordings each morning, tune
- [ ] Client checks in end-of-Day-2 to confirm no disasters

## Day 10-14: Full cutover

- [ ] Forward 100% of inbound to AI number
- [ ] Continue daily review for 3 days, then weekly
- [ ] Auto-charge second payment ($2,250) on Day 14
- [ ] Mark client "live" in Supabase `receptionist_clients.status = live`
- [ ] Monthly billing automatic via Stripe subscription

## Day 30: 30-day report

- [ ] Cash runs booking-rate comparison: pre-receptionist vs post-receptionist
- [ ] Piper writes client-facing report (template in `onboarding/30_day_report_template.md`, to be created at first client)
- [ ] If booking rate improved <20%: apply refund guarantee (refund month 1 hosting, continue service, debug)
- [ ] If booking rate improved >=20%: ask for testimonial + referral

## Ongoing SLA

- 24/7 uptime monitoring (Django dashboard + PagerDuty for outages >5 min)
- Client support response: 4 business hours
- Monthly usage report auto-sent on 1st of each month
- Quarterly tune-up call (30 min) included

## Offboarding (if client cancels)

- [ ] Forward Twilio number back to client's original line within 24 hours
- [ ] Export call log as CSV, send to client
- [ ] Delete client credentials from Oracle
- [ ] Archive Supabase record to `receptionist_clients_archived`
- [ ] Send offboarding survey
- [ ] Mark Stripe subscription cancelled

## Files that matter

- Client config: `/home/opc/receptionist_clients/<slug>/.env`
- Vapi assistant ID: stored in `<slug>/.env` as `VAPI_ASSISTANT_ID`
- n8n workflow ID: stored in `<slug>/.env` as `N8N_WORKFLOW_ID`
- Twilio number: stored in `<slug>/.env` as `TWILIO_PHONE_NUMBER`
- FAQ doc (original): stored in Supabase blob and mirrored to `<slug>/faq.md`
