# Documenso E-Sign Setup -- Everlight Ventures PSA

5-minute checklist to wire the new TN SB 909 PSA into the live Documenso
instance at https://sign.everlightventures.io.

---

## 1. Generate an API token

1. Open https://sign.everlightventures.io/settings/tokens in a browser.
2. Click "Create token", name it `wholesale-psa-bot`, copy the value.
3. Add it to the shared secrets file on the phone AND on Oracle:

```bash
# Phone (proot)
grep -q DOCUMENSO_API_KEY /root/.config/everlight/secrets.env \
  || echo 'DOCUMENSO_API_KEY=PASTE_TOKEN_HERE' >> /root/.config/everlight/secrets.env

# Oracle (opc)
ssh opc@163.192.19.196 \
  "grep -q DOCUMENSO_API_KEY /home/opc/.config/everlight/secrets.env \
   || echo 'DOCUMENSO_API_KEY=PASTE_TOKEN_HERE' >> /home/opc/.config/everlight/secrets.env"
```

4. Source it in the current shell:

```bash
export DOCUMENSO_API_KEY=PASTE_TOKEN_HERE
```

---

## 2. Configure the webhook (inbound signed-event)

1. In Documenso: Settings -> Webhooks -> Add Webhook.
   - URL: `https://everlightventures.io/broker/webhook/documenso/`
     (or the Oracle internal: `http://127.0.0.1:8000/broker/webhook/documenso/`
     if Documenso and Django are on the same Oracle node).
   - Events: `document.signed`, `document.completed`.
   - Copy the HMAC signing secret.
2. Add to secrets.env:

```bash
echo 'DOCUMENSO_WEBHOOK=PASTE_HMAC_SECRET_HERE' >> /root/.config/everlight/secrets.env
export DOCUMENSO_WEBHOOK=PASTE_HMAC_SECRET_HERE
```

3. The Django broker_ops webhook view at `/broker/webhook/documenso/` already
   handles `document.completed` -> marks Deal.status = "signed" and fires a
   Slack alert to #broker-pipeline. No code changes needed.

---

## 3. Test a real PSA send

Run this one-liner from the proot (after sourcing secrets.env):

```bash
source /root/.config/everlight/secrets.env

cd /mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/wholesale_agent

python3 - <<'EOF'
from psa_pdf import send_psa_for_signature

lead = {
    "owner_name": "TOWNSEND RITA M",
    "property_address": "836 N BELLEVUE BLVD MEMPHIS TN 38107",
    "parcel_id": "021083 00056",
    "county": "Shelby",
    "state": "TN",
    "owner_email": "YOUR_TEST_EMAIL@example.com",  # use your own email for the test
}
deal_terms = {
    "purchase_price": 33640,
    "emd_amount": 500,
    "assignment_fee": 11500,
    "close_date": "June 15, 2026",
}

url = send_psa_for_signature(None, lead, deal_terms)
print("Signing URL:", url or "NOT SENT (check DOCUMENSO_API_KEY)")
EOF
```

Expected output:
```
[HH:MM:SS] INFO psa_pdf: Rendering PSA PDF for 836 N BELLEVUE BLVD ...
[HH:MM:SS] INFO psa_pdf: PDF written: .../contracts_out/psa_townsend_rita_m_.../psa_contract.pdf (...)
[HH:MM:SS] INFO psa_pdf: PSA sent to Documenso: doc_id=..., signer=YOUR_TEST_EMAIL@example.com
Signing URL: https://sign.everlightventures.io/sign/<doc_id>
```

Open the signing URL in a browser to confirm the PDF renders and the
signature field is available.

---

## 4. Production wiring (pipeline integration)

Once the token is confirmed working, `send_psa_for_signature` is called from
`rex_negotiator.py` when a deal reaches the "offer accepted" stage:

```python
from psa_pdf import send_psa_for_signature

signing_url = send_psa_for_signature(deal_obj, lead_dict, deal_terms_dict)
if signing_url:
    log.info(f"PSA sent: {signing_url}")
else:
    log.warning("PSA not sent -- DOCUMENSO_API_KEY unset or lead has no email")
```

---

## 5. Env var reference

| Variable             | Required | Source                                          |
|----------------------|----------|-------------------------------------------------|
| DOCUMENSO_API_KEY    | YES      | sign.everlightventures.io -> Settings -> Tokens |
| DOCUMENSO_API_URL    | NO       | Default: https://sign.everlightventures.io/api/v1 |
| DOCUMENSO_WEBHOOK    | YES      | sign.everlightventures.io -> Settings -> Webhooks |

Both env vars go in `/root/.config/everlight/secrets.env` (phone proot) and
`/home/opc/.config/everlight/secrets.env` (Oracle). The deploy script syncs
secrets.env to Oracle as part of `deploy_to_oracle.sh`.

---

## 6. Troubleshooting

- **"DOCUMENSO_API_KEY not set"** -- source secrets.env or re-export.
- **HTTP 401** -- token expired; regenerate at /settings/tokens.
- **"No owner_email on lead"** -- the lead must have an `owner_email` key; run
  skip-trace first (`rex_enrichment_engine.py`) to populate it.
- **PDF opens blank in Documenso** -- confirm the file is > 1 KB and starts
  with `%PDF`; run `python3 -c "open('psa_contract.pdf','rb').read(4)"` to verify.
- **Webhook 400** -- DOCUMENSO_WEBHOOK secret mismatch; regenerate the webhook
  secret in Documenso settings and update secrets.env.
