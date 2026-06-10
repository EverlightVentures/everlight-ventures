# Stripe SKUs + Per-Client Env Template

**Owner**: Cash (pricing) + Forge (env wiring)
**Date**: 2026-04-21

---

## Stripe setup

Everlight already has Stripe live keys in `.env`. Adding 2 products + 2 prices.

### Product 1: AI Receptionist Build (one-time)

Run this from a shell with `STRIPE_SECRET_KEY` in env:

```bash
stripe products create \
  --name "AI Receptionist Build" \
  --description "Custom AI phone receptionist for your business. Includes Vapi voice setup, n8n workflow, Google Calendar integration, FAQ knowledge base, 2 weeks of tuning." \
  --metadata[product_slug]=receptionist_build \
  --metadata[owner]=ai_consulting

stripe prices create \
  --product <PRODUCT_ID_FROM_ABOVE> \
  --unit_amount 450000 \
  --currency usd \
  --nickname "Build Fee (one-time)" \
  --metadata[sku]=receptionist_setup_4500
```

Output: a price ID like `price_1RecbuildXYZ...`. Store it in `.env` as `STRIPE_PRICE_RECEPTIONIST_BUILD`.

### Product 2: AI Receptionist Hosting (recurring monthly)

```bash
stripe products create \
  --name "AI Receptionist Hosting" \
  --description "Monthly hosting, monitoring, and up to 200 calls for your AI receptionist." \
  --metadata[product_slug]=receptionist_hosting \
  --metadata[owner]=ai_consulting

stripe prices create \
  --product <PRODUCT_ID_FROM_ABOVE> \
  --unit_amount 19900 \
  --currency usd \
  --nickname "Monthly Hosting" \
  --recurring[interval]=month \
  --metadata[sku]=receptionist_monthly_199
```

Store price ID as `STRIPE_PRICE_RECEPTIONIST_HOSTING`.

### Product 3 (optional): Call overage

```bash
stripe products create \
  --name "AI Receptionist Call Pack" \
  --description "Additional 100 calls per month." \
  --metadata[product_slug]=receptionist_overage \
  --metadata[owner]=ai_consulting

stripe prices create \
  --product <PRODUCT_ID_FROM_ABOVE> \
  --unit_amount 5000 \
  --currency usd \
  --nickname "100-call pack" \
  --metadata[sku]=receptionist_pack_100
```

## Stripe Checkout session (for sales page)

For the `/ai-receptionist` landing page's "Book Discovery Call + Reserve Build" CTA, create a Checkout Session combining both prices:

```javascript
// Edge function: 01_BUSINESSES/Everlight_Ventures/Everlight_Foundations/edge_functions/create-receptionist-checkout/index.ts
const session = await stripe.checkout.sessions.create({
  mode: "subscription",
  line_items: [
    { price: env.STRIPE_PRICE_RECEPTIONIST_BUILD, quantity: 1, tax_rates: [] },
    { price: env.STRIPE_PRICE_RECEPTIONIST_HOSTING, quantity: 1 }
  ],
  success_url: "https://everlightventures.io/ai-receptionist/welcome?session={CHECKOUT_SESSION_ID}",
  cancel_url: "https://everlightventures.io/ai-receptionist",
  client_reference_id: formData.business_email,
  metadata: {
    product: "ai_receptionist",
    business_name: formData.business_name,
    contact_name: formData.contact_name
  },
  subscription_data: {
    // hosting only recurs; the build is one-time via invoice after deposit
    trial_period_days: 0
  },
  // Collect 50% deposit up front; the second 50% is invoiced on go-live
  payment_intent_data: { capture_method: "automatic" }
});
```

**Deposit flow**: Since Stripe Checkout handles recurring + one-time line items atomically, we set the build at $4,500 but actually charge in two installments ($2,250 now via invoice split; $2,250 on Day 14 via scheduled invoice).

Simpler alternative: charge $2,250 deposit as a separate one-time price, invoice the second $2,250 manually on go-live. Less automation, less error risk. Recommended for first 5 clients.

```bash
stripe prices create \
  --product <RECEPTIONIST_BUILD_PRODUCT_ID> \
  --unit_amount 225000 \
  --currency usd \
  --nickname "Build Deposit (50%)" \
  --metadata[sku]=receptionist_deposit_2250
```

Store as `STRIPE_PRICE_RECEPTIONIST_DEPOSIT`.

## Per-client env template

Every signed client gets a folder on Oracle:
```
/home/opc/receptionist_clients/<client_slug>/
  .env
  faq.md
  intake_form.json
  vapi_assistant_id.txt
  n8n_workflow_id.txt
```

### `.env` template

```bash
# Everlight AI Receptionist - Client Environment
# Client: <CLIENT_BUSINESS_NAME>
# Slug: <CLIENT_SLUG>
# Onboarded: <YYYY-MM-DD>
# Owner: Forge

# ----- Vapi (voice layer) -----
VAPI_ASSISTANT_ID=                      # populated by Forge after assistant creation
VAPI_PHONE_NUMBER_ID=                   # populated after Twilio number purchase + Vapi wire-up

# ----- Twilio (phone number) -----
TWILIO_PHONE_NUMBER=                    # e.g., +19165551234
TWILIO_FORWARD_NUMBER=                  # client's original line, for offboarding rollback

# ----- Google Calendar (backend) -----
GOOGLE_CALENDAR_ID=                     # primary client calendar ID
GOOGLE_CALENDAR_AUTH_JSON_PATH=/home/opc/receptionist_clients/<slug>/gcal_oauth.json

# ----- n8n (workflow orchestration) -----
N8N_WORKFLOW_ID=                        # populated after template import
N8N_WEBHOOK_BASE=https://n8n.everlightventures.io/webhook/receptionist/<slug>

# ----- Supabase (call log + analytics) -----
SUPABASE_URL=https://jdqqmsmwmbsnlnstyavl.supabase.co
SUPABASE_ANON_KEY=<shared from workspace .env>

# ----- Slack notifications (optional - client's workspace) -----
CLIENT_SLACK_WEBHOOK=                   # client provides; leave blank for email-only mode
CLIENT_NOTIFY_EMAIL=                    # fallback if no Slack

# ----- Business config -----
BUSINESS_NAME=
BUSINESS_HOURS_JSON={"mon":"9-17","tue":"9-17","wed":"9-17","thu":"9-17","fri":"9-17","sat":"closed","sun":"closed"}
BUSINESS_TIMEZONE=America/Los_Angeles
SERVICE_LIST=
AGENT_VOICE_ID=                         # ElevenLabs voice id, picked at onboarding
AGENT_VOICE_NAME=                       # human-readable, e.g., "Julie"

# ----- Billing -----
STRIPE_CUSTOMER_ID=
STRIPE_SUBSCRIPTION_ID=
MONTHLY_CALL_CAP=200
OVERAGE_PACK_PRICE=50
```

### Setup script

```bash
# 03_AUTOMATION_CORE/01_Scripts/receptionist/provision_client.sh
#!/usr/bin/env bash
set -euo pipefail

SLUG="$1"
BUSINESS_NAME="$2"

if [ -z "$SLUG" ] || [ -z "$BUSINESS_NAME" ]; then
  echo "usage: $0 <slug> <business_name>"
  exit 1
fi

CLIENT_DIR="/home/opc/receptionist_clients/$SLUG"
mkdir -p "$CLIENT_DIR"
cp /home/opc/receptionist_clients/_template/.env "$CLIENT_DIR/.env"
chmod 600 "$CLIENT_DIR/.env"
sed -i "s|<CLIENT_BUSINESS_NAME>|$BUSINESS_NAME|g" "$CLIENT_DIR/.env"
sed -i "s|<CLIENT_SLUG>|$SLUG|g" "$CLIENT_DIR/.env"
sed -i "s|<YYYY-MM-DD>|$(date -I)|g" "$CLIENT_DIR/.env"

echo "Client $SLUG provisioned at $CLIENT_DIR"
echo "Next: ./install_vapi_assistant.sh $SLUG && ./install_n8n_workflow.sh $SLUG"
```

## Webhook from Stripe to Django

Wire up: when a client pays the deposit, Django triggers client provisioning.

```python
# 09_DASHBOARD/hive_dashboard/payments/views.py (extension)
@csrf_exempt
def stripe_webhook_receptionist(request):
    # ...existing stripe webhook parsing...
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        if session.get("metadata", {}).get("product") == "ai_receptionist":
            slug = slugify(session["metadata"]["business_name"])
            subprocess.run([
                "/home/opc/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/receptionist/provision_client.sh",
                slug,
                session["metadata"]["business_name"]
            ], check=True)
            notify_slack_ft_consult(f"New receptionist client: {session['metadata']['business_name']}")
    return HttpResponse("ok")
```

## Final checklist before Phase 3 (first sale)

- [ ] Stripe products 1-3 created (use script above)
- [ ] Stripe price IDs saved to `.env`
- [ ] Edge function `create-receptionist-checkout` deployed to Cloudflare
- [ ] Django webhook handler for `ai_receptionist` product wired up
- [ ] `/home/opc/receptionist_clients/_template/.env` exists on Oracle
- [ ] `provision_client.sh` lives in the deploy path
- [ ] Test run: create a fake client with Stripe test keys, confirm provisioning flow fires end-to-end

This is Phase 2.5 work. Forge can do it in parallel while Piper runs outbound.
