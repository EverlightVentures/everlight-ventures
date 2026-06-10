# Channel Fusion -- the faces + the deal pipeline, one brain
*Extends `00_MASTER_TREE.md` (the channel doctrine) and the Broker_OS wholesale pipeline.*
*Built 2026-05-24. Legal spec by Priya Bhattacharya. No duplication: one message, routed to the one place that fits its purpose.*

## The core idea: THREE lanes, ONE brain
The platforms are not copies of each other. Each serves one of three lanes, and all of them
read/write the SAME conversation brain (`conversation_memory`) and the SAME contacted registry.

| Lane | Platforms | Job | Engine |
|---|---|---|---|
| **THE FACE** (inbound / top-of-funnel) | Instagram (storefront/discovery), **Facebook Marketplace** (closest to Deal-1), Discord (community), Telegram broadcast, X/LinkedIn | Make people find + trust Everlight, capture the lead | feeds -> contacted registry / leads |
| **THE CONVERSATION** (1:1 deal) | email - SMS - Henry voice call - **Telegram DM - WhatsApp - Instagram DM** | Negotiate + close the deal, on the channel THEY chose | `channel_router` + `conversation_memory` + `negotiation` engine + `llm_compose` |
| **THE CONTROL ROOM** (internal) | **Slack** (war-room) | Where Rich + the Hive watch deals, alerts, the conductor | not a counterparty channel |

A seller who DMs us on Instagram becomes a contact in the SAME memory; the SAME Henry negotiates
them in the SAME brand voice whether it lands as an IG DM, a WhatsApp message, or an email. The
platform is just the pipe. Slack never talks to a seller. Facebook Marketplace is a lead SOURCE,
never an outbound bot.

## THE CONVERSATION lane -- consent + window rules (channel_router)
Consent is the legal key: the seller CHOOSING the channel (and giving the handle) is the opt-in.
Logged to `_logs/channel_consent.jsonl` (email/channel/handle/consent_text/last_inbound_ts).

- **Email** -- default, always lawful for an engaged prospect. Full gold template (branded_mailer).
- **SMS** -- consent = they gave a number / texted us. branded_sms (EV: prefix + STOP). Twilio env to go live.
- **Voice** -- automated Henry call (ElevenLabs script). Consent = they chose it. Telephony to go live.
- **Telegram** -- consent is platform-enforced: a bot cannot message a user until they `/start`.
  Capture `chat_id` on /start. No window. Free bot token. EASIEST + SAFEST -> build #1.
- **WhatsApp** -- STRICTEST. Needs auditable explicit opt-in text (a bare phone is NOT enough),
  Meta business verification, and respects the **24-hour window**: free-form only within 24h of
  their last inbound; outside it requires an approved template. We enforce the window + require
  consent_text; degrade to email otherwise. Build #3.
- **Instagram DM** -- user-initiated only (no cold DM API). 24h window; outside it needs the
  human-agent tag (7d, human-authored). Capture IGSID. Build #2.

Hard rules in code: never cold on any non-email channel (consent gate); free-form only inside the
platform window (window gate); always degrade to email when a credential/approval/handle is
missing. One channel per send (quota-aware). One message generated once, adapted per channel.

## THE FACE lane -- Facebook Marketplace as a lead source (compliant)
Scraping Marketplace is a Meta ToS violation + litigation risk; there is no sanctioned read API.
So FB Marketplace intake is **human-in-the-loop**, never a scraper, and the `hermes_browser_outreach`
harness is FENCED AWAY from Facebook. A person reads Marketplace for distressed-seller signals
(`fb_marketplace_intake.py --keywords`) and manually logs leads (`source=fb_marketplace_manual`,
`consented=false`). First contact is human-initiated + opt-in-seeking; consent is captured later
when the seller picks a real channel. For automated FB lead intake later: Meta Lead Ads + the
Graph leadgen webhook (form = opt-in), never a scraper.

## Brand consistency (never breaks across channels)
Every face + every channel uses the one brand spine: gold `#D4AF37`, dark `#0A0A0A`, light text
`#E8E8E8`, Playfair/Inter -- from `content_tools/report_template.py`. Persona voice is identical
across channels because it is the SAME words reshaped (email full, chat-platforms = concise gist
+ link, voice = spoken script), all from `llm_compose` with the persona dossier. A follower feels
the same Everlight on IG, in a Telegram DM, or in an email.

## Build order (ease + safety, per Priya)
1. Telegram (platform-enforced consent, no window, free) -- adapter built, needs bot token + /start listener.
2. Instagram DM (window logic reused for WhatsApp) -- adapter built, needs Page + token + App Review.
3. WhatsApp (verification + approved templates) -- adapter built + window-gated, needs Meta provisioning.
4. Facebook Marketplace -- manual-intake SOP live now (`fb_marketplace_intake.py`); no code to ship.

All adapters are built + gated TODAY (`channel_router.py`); each goes LIVE when its credential/
approval lands. Until then they degrade to email cleanly -- nothing lost. See memory
[[feedback_multichannel_consent_routing]].
