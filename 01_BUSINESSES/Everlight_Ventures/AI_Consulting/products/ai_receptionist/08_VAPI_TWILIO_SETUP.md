# Vapi + Twilio Setup Walkthrough (For Lucrex)

**Time required**: 15 minutes total
**Upfront cost**: $0 (both accounts are usage-billed)
**Outputs**: 3 API keys to paste into the credentials file

---

## Step 1: Vapi signup (5 minutes)

1. Open https://vapi.ai in your browser
2. Click **Sign Up** (top right). Use `hammer@everlightventures.io` or your personal Gmail.
3. Verify the email (inbox check).
4. Skip the onboarding wizard for now. Click through to the **Dashboard**.
5. Left sidebar -> **API Keys** -> **Create Key** -> name it `everlight-prod` -> **Copy**
6. Set monthly spend cap: Settings -> **Billing** -> Spend Alerts -> set to `$100/mo warning` + `$300/mo hard cap` (prevents runaway cost on a bug).

**Output**: One API key like `vapi_sk_abc123...`

Paste it back to me in chat, or save it yourself at:
`/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env`
as:
```
VAPI_API_KEY=vapi_sk_abc123...
```

## Step 2: Twilio signup (8 minutes)

1. Open https://twilio.com/try-twilio
2. **Sign Up** with `hammer@everlightventures.io` or personal email.
3. Verify email + phone (they will SMS you a code).
4. Walk through the wizard:
   - Role: Developer
   - Product: Voice
   - Language: Python (or whatever, doesn't matter)
   - Skip coding question.
5. You land on the Console. Free trial starts with $15 credit.
6. Top right, you'll see:
   - **Account SID** (looks like `ACabc123...`)
   - **Auth Token** (click the eye to reveal)
7. Copy both.

Then (optional, for first client):
8. Left sidebar -> **Phone Numbers** -> **Buy a Number**
9. Pick a local area code in the first client's city (e.g., 916 Sacramento)
10. Voice capability required. Buy for $1/mo. Don't buy yet if you have no client signed.

**Output**: Two credentials.

Paste them into `.env`:
```
TWILIO_ACCOUNT_SID=ACabc123...
TWILIO_AUTH_TOKEN=your_auth_token_here
```

## Step 3: Verify the keys work

After you paste keys into `.env`, say in chat:
```
check vapi and twilio keys
```

I'll run this test and confirm:
```bash
python3 - <<'PY'
import os, urllib.request
vapi = os.environ.get("VAPI_API_KEY", "")
twilio_sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
# Test Vapi
try:
    req = urllib.request.Request("https://api.vapi.ai/assistant", headers={"Authorization": f"Bearer {vapi}"})
    urllib.request.urlopen(req, timeout=10)
    print("Vapi: OK")
except Exception as e:
    print(f"Vapi: FAIL - {e}")
# Test Twilio
import base64
b64 = base64.b64encode(f"{twilio_sid}:{os.environ.get('TWILIO_AUTH_TOKEN','')}".encode()).decode()
try:
    req = urllib.request.Request(f"https://api.twilio.com/2010-04-01/Accounts/{twilio_sid}.json", headers={"Authorization": f"Basic {b64}"})
    urllib.request.urlopen(req, timeout=10)
    print("Twilio: OK")
except Exception as e:
    print(f"Twilio: FAIL - {e}")
PY
```

## What happens once keys are set

Forge will:
1. Deploy the n8n workflow template to production n8n instance (Oracle :5678)
2. Test the 6 webhooks with curl (dry-run, no real calls)
3. Create a "demo client" Vapi assistant named `everlight_demo` using the Vapi template
4. Place 1 test call to the demo assistant (Forge calls in from his phone)
5. Confirm end-to-end: call -> Vapi -> webhook -> n8n -> Google Calendar -> Slack

This demo assistant becomes the **live audio demo** for the sales one-pager and landing page.

## Budgets + caps (safety nets)

| Service | Free tier | Soft cap | Hard cap |
|---|---|---|---|
| Vapi | $5 trial credit | Warn at $50/mo | Kill at $300/mo |
| Twilio | $15 trial credit | 200 calls/mo per client | Block purchases above 10 numbers |

These caps are dashboard-configurable. Forge will set them up once keys are pasted.

## What NOT to do

- Do not use the same Vapi API key across clients. Each client gets their own assistant; the key is only for Everlight's admin API calls.
- Do not expose Twilio credentials in any client-shared document. They charge back to us.
- Do not buy phone numbers speculatively. Buy only after a deposit clears for that client.
- Do not skip the spend cap configuration. One prompt-injected Vapi assistant could burn $1K in 4 hours if unbounded.

## Rollback

If you decide mid-Phase-2 to not proceed:
- Cancel Vapi at Dashboard -> Settings -> Cancel Account. Pro-rated if any usage.
- Cancel Twilio at Console -> Account -> Close Account. Any unused trial credit forfeits.
- Delete the keys from `.env`.
- Archive this folder: move `products/ai_receptionist/` to `08_BACKUPS/archived_prototypes/`.

No long-term commitment until a real client pays.
