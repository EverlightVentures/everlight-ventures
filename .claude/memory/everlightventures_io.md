# everlightventures.io -- Infrastructure State

## Supabase Project (CORRECT)
- Project ref: jdqqmsmwmbsnlnstyavl
- URL: https://jdqqmsmwmbsnlnstyavl.supabase.co
- Anon key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpkcXFtc213bWJzbmxuc3R5YXZsIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI4MTk5ODMsImV4cCI6MjA4ODM5NTk4M30.9BDviI2WR46sphcS3uzKapcKbslYpMO4PdSEPFrv3Ww
- Storage bucket: "Ebooks" (capital E)
- WRONG project (do NOT use): axamanzvzsyuljpxifdl

## Edge Functions (deployed 2026-03-09)
- create-checkout (ACTIVE)
- verify-ebook-purchase (ACTIVE) -- auto-sends purchase email via send-purchase-email
- verify-arcade-purchase (ACTIVE)
- verify-gem-purchase (ACTIVE)
- stripe-webhook (ACTIVE)
- send-purchase-email (ACTIVE) -- Resend API, branded HTML, purchase + recovery types
- recovery-sweep (ACTIVE) -- finds orphaned Stripe purchases, auto-sends recovery emails + free bonus book
- Source: 01_BUSINESSES/Everlight_Ventures/Everlight_Foundations/edge_functions/
- Secrets set: STRIPE_SECRET_KEY, SLACK_WEBHOOK_URL, STRIPE_WEBHOOK_SECRET, RESEND_API_KEY

## Stripe
- Account: Gd8n4Fz3nA (visible in price IDs)
- 17 LIVE products created (see STRIPE_PRODUCT_CATALOG.md)
- Test key provided in session (sk_test_51T83BE2fe...)
- Live key: sk_live_51T83B3Gd8n4Fz3nA... (set as Edge Function secret)
- Webhook ID: we_1T9AfEGd8n4Fz3nA90HnUd51 (LIVE, created 2026-03-09)
- Webhook secret: whsec_CLDxvF71v30aRYxsSWB5pHPSrn9417gt (set as Edge Function secret)
- Webhook URL: https://jdqqmsmwmbsnlnstyavl.supabase.co/functions/v1/stripe-webhook
- Events: checkout.session.completed, customer.subscription.created/deleted, invoice.payment_succeeded/failed

## DNS (Namecheap)
- Root (@): A Record -> 185.158.133.1 (Namecheap parking IP, redirects via URL Redirect)
- Root (@): URL Redirect Record -> https://everlightventures.io (301)
- www: CNAME -> Everlightventures.io. (WRONG -- should point to Lovable project URL)
- _lovable: TXT verification record (present)
- SPF TXT record present

## Architecture Decision
- Hybrid: Lovable for frontend ONLY, own Supabase/Slack/hive for backend
- User does NOT want extra cloud costs from Lovable
- Edge Functions bypass Lovable's broken deployment pipeline

## Database Tables (created 2026-03-09)
- ebook_purchases, download_tokens, arcade_purchases, gem_purchases
- player_accounts, arcade_sessions, arcade_scores, stripe_events

## Resend Email (added 2026-03-09)
- API key: re_6S6DgX94_BDzaAU3r3Y5Syca6F58m2aEt (set as RESEND_API_KEY secret)
- Domain: everlightventures.io -- PENDING VERIFICATION
- DNS records needed in Namecheap: DKIM TXT, MX send, SPF TXT send, DMARC TXT
- Currently sends from: onboarding@resend.dev (switch to noreply@everlightventures.io after verification)
- Slack webhook: https://hooks.slack.com/services/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

## Customers Recovered
- 1m.rich.gee@gmail.com -- recovery email SENT (sam-book-1 + free sam-book-2)
- tapizme@gmail.com -- PENDING (blocked by Resend domain verification, product_type was "no-type")

## Pending
- Resend domain verification (user adding DNS records)
- tapizme@gmail.com recovery email after domain verified
- Beyond the Veil EPUB still needs creating
- www CNAME needs fixing (point to Lovable project URL)
- Phase 2-6 from plan: polished-gliding-church.md

## Session Protocol
- Full session transcripts auto-saved at /root/.claude/projects/-mnt-sdcard-AA-MY-DRIVE/*.jsonl
- On compaction: persist credentials/config to this memory file BEFORE data is lost
- NEVER lose user-provided keys during compaction
