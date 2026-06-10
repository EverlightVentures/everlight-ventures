# API Key Rotation Policy

_Applies to every API credential the Hive uses for outbound or financial actions._

## 90-day rotation cadence

| Key | Provider | Cadence | Last rotated | Next due |
|-----|----------|---------|--------------|----------|
| `TWILIO_AUTH_TOKEN` | Twilio | 90d | 2026-04-25 | 2026-07-24 |
| `ELEVENLABS_API_KEY` | ElevenLabs | 90d | 2026-04-25 | 2026-07-24 |
| `STRIPE_SECRET_KEY` | Stripe | 90d or on incident | TBD | TBD |
| `RESEND_API_KEY` | Resend | 90d | TBD | TBD |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase | 180d | TBD | TBD |
| `GOOGLE_PLACES_API_KEY` | Google | 90d when set | not set | n/a |
| `LOB_API_KEY` | Lob | 90d when set | not set | n/a |
| `SLACK_WARROOM_TOKEN` | Slack bot | 365d | TBD | TBD |
| `OPENAI_API_KEY` | OpenAI | 90d | 2026-03-23 | 2026-06-22 |

## How to rotate (universal flow)

1. Log into the provider dashboard
2. Generate a NEW key, do not delete the old one yet
3. Add new key to `/home/opc/.env` as `<KEY>_NEW=...`
4. Run integration tests
5. Swap: rename old to `<KEY>_OLD`, rename `_NEW` to `<KEY>`
6. After 24 hours stable, delete `_OLD` and revoke the old key upstream
7. Update the table above

## Incident-triggered rotation (within 1 hour)

Rotate immediately if:
- Key committed to a public repo
- Unusual API usage or billing spike
- Departing team member had access
- Provider notification of a leak

## Logging

Every rotation logs to `/home/opc/_logs/key_rotations.jsonl` with timestamp, key name (never the value), reason, and verifier.

## Quarterly reminder cron

```
0 9 1 1,4,7,10 * /usr/bin/python3 /home/opc/wholesale/compliance/key_rotation_reminder.py
```

_Owner: Rich. Reviewer: external CPA annually._
