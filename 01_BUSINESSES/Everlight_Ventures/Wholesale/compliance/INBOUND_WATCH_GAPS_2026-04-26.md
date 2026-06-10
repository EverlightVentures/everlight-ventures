# Inbound-Watch Gaps -- 2026-04-26

**Author:** Justine Park, Compliance Gate
**Class:** Internal compliance memo. Research and education, not legal advice.
**Trigger:** STOP reply from David A. Streubel (Cunningham, Vogel & Rost, P.C.), 2026-04-26 06:30 PT.

---

## a. What the Streubel reply teaches us

Three lessons, each structural, not cosmetic.

**1. Recipient targeting failed at the source.** The outbound treated David Streubel as the homeowner of 4435 Westminster Pl, St Louis. He is not a homeowner in the wholesale sense. He is a partner at Cunningham, Vogel & Rost, P.C., a firm whose practice is described on its own domain as legal counselors to local government. Even if his name surfaces on a tax roll or LLC ownership filing tied to that property, the email domain itself, municipalfirm.com, is a hard tell that this is not a distressed-seller outreach target. The pipeline scored him as a homeowner because the only check was "name appears on a property record". That heuristic is broken when the name on the record is a lawyer who holds title in a fiduciary or LLC capacity.

**2. Timing was actively hostile.** The send went out Saturday 2026-04-25 at 22:08 PT, which is 00:08 Sunday Central in St Louis. There is no homeowner outreach scenario where a Sunday-zero-hour cold email reads as anything other than spam. State outreach gates already enforce daytime windows for SMS and calls. Email currently has no equivalent quiet-hours gate. That is a hole.

**3. Sender alias was the legacy `rich@everlightventures.io`.** Adrian brand-standardization pass moved all wholesale outreach to named-agent mailboxes (`piper@`, `harrison@`, `rex@`) routed through `branded_mailer.send_branded_email()`. The Westminster send bypassed that entire layer. There is no row for it in `/home/opc/_logs/resend_budget.jsonl`. That means it never hit the budget gate, the brand template, or the resend_guard. Some script is still calling Resend directly under the `rich@` alias. Until that script is found and rerouted, the brand standardization is theoretical.

---

## b. 30-day outbound audit

Pulled `/home/opc/_logs/resend_budget.jsonl`, last 30 days.

- **Total branded sends:** 117
- **Internal/test (everlightventures.io, resend.dev):** 4
- **Government domain (`.gov`):** 3 confirmed
- **Attorney-firm pattern hits in budget log:** 0 (Streubel is not in the log -- bypassed branded_mailer)
- **Other (homeowners, JV wholesalers, cash buyers):** 110

The 3 government-domain sends are the live problem alongside Streubel:

| Recipient | Subject | Class |
|---|---|---|
| `brooks-sandersd@stlouis-mo.gov` | 1522 HOGAN ST cash offer | City of St Louis employee, NOT homeowner |
| `andersonsh@stlouis-mo.gov` | 1331 GOODFELLOW BLVD cash offer | City of St Louis employee, NOT homeowner |
| `kathy.green@dallas.gov` | 2502 CADILLAC DR cash offer | City of Dallas employee, NOT homeowner |

**Read:** these are city-account email addresses showing up on a property record because the property is in a municipal land-bank, code-enforcement file, or city-employee public directory. None are valid wholesale targets. The pipeline mailed cash offers to city government accounts. That is the same class of mistake as Streubel, just with a `.gov` instead of an attorney firm.

**Total non-homeowner outbound recipients in the last 30 days: 4 confirmed (3 in budget log + Streubel bypass).** That is 3.4% of branded volume. Low absolute count, high reputational drag, and the Streubel send proves the real number is higher because the bypass channel is not measured.

---

## c. Outbound-list filters that should have prevented this

These belong upstream of `send_branded_email()`, in the recipient-resolver step of `wholesale_engine` and any script still using a legacy alias.

**Filter 1 -- Government-domain blocklist (hard block).**
Reject any recipient where the email domain matches any of:
- `*.gov` (federal, state, local)
- `*.us` when paired with city/state subdomain (`stlouis-mo.us`, `dallas-tx.us`)
- `*.state.<XX>.us`
- Known municipal patterns: `cityof*`, `*county.*`, `*-mo.gov`, `*-tx.gov`

Action: hard block, log to `phrase_scrub_blocks.jsonl`, write to ConsentLedger with reason `govt_domain_blocklist`, never retry.

**Filter 2 -- Attorney/law-firm domain pattern (hard block on cold outbound, allow on warm reply only).**
Reject any recipient where the domain contains: `law`, `legal`, `attorney`, `counsel`, `llp`, `pllc`, `esq`, `municipal`, or matches a known firm token (`vogel`, `rost`, `cunningham`, etc -- maintained list).
Edge case: an attorney can be a real seller. Allow only if the lead came in through inbound form submission with a verified property-address match, never on outbound cold.

**Filter 3 -- Homeowner-heuristic gate (must-pass before send).**
Before any cold outreach, the recipient must pass at least 2 of:
- Property record shows owner-occupied flag = true
- Mailing address on tax roll matches property address (not a PO Box, not an office)
- Email domain is consumer (`gmail.com`, `yahoo.com`, `hotmail.com`, `aol.com`, `icloud.com`, `outlook.com`) OR a residential ISP
- No LLC/Trust/Corp/PC/PLLC token in the listed owner name

If fewer than 2 pass, route to manual review queue, do not auto-send.

**Filter 4 -- Quiet-hours email gate.**
Block all cold-outbound email between 21:00 and 08:00 local-to-recipient. State gates already enforce this for SMS and calls. Extend the same `state_gate.allowed_now()` check to email. Saturday-night sends were the proximate read of "spam" in the Streubel case.

**Filter 5 -- Sender-alias whitelist.**
Hard-fail any send from a sender alias not in the approved roster: `piper@`, `harrison@`, `rex@`, `cupid@`, `justine@`, `marquise@`. The legacy `rich@everlightventures.io` should be removed from the allowed senders list at the Resend domain level. If a script tries to send from it, the API call should fail.

---

## d. Inbound-watch layer needed

Right now I see nothing inbound. I review what is dispatched to me. Adrian sees Resend webhooks. Marquise sees Slack. Nobody is watching IMAP for compliance-relevant signals against last-24h outbound. That has to change.

**Daily Justine-Watch report (07:00 PT, before the morning brief).**
A scheduled job that pulls the last 24h of:
1. **Inbound IMAP** -- every reply to a wholesale send
2. **Outbound resend_budget.jsonl** -- every send that hit the budget gate
3. **Outbound bypass detection** -- any Resend API event with no matching budget log row (this is how we catch the next `rich@` script)
4. **ConsentLedger writes** -- every STOP, opt-out, unsubscribe, abuse complaint

For each item, classify the recipient by domain pattern (govt, attorney, homeowner, JV-wholesaler, internal). Flag any of:
- STOP / unsubscribe / cease and desist language in inbound body
- Inound from a `.gov` or attorney-firm domain regardless of body
- Outbound to a govt or attorney domain that slipped past filters
- Bypass send with no budget-log row
- Reply velocity anomalies (e.g. 5+ STOPs in 24h = list-quality failure)

Output: branded Slack post to `#compliance` and a hosted HTML report. If anything is in the "STOP from attorney/govt" bucket, it pages me direct, not the channel.

**Hourly thin pass.**
Same scan, lighter. Only fires Slack ping if a STOP arrives from a flagged-class domain. Catches the Streubel-class signal within 60 minutes of receipt instead of 13+ hours.

---

## e. The proactive named-agent layer

This is the bigger structural fix. Right now the Hive is request-response. Marquise asks, agents fire. That is fine for build tasks. It is broken for compliance, because compliance signals arrive on an inbound stream that nobody is subscribed to.

What it should be: **event-driven dispatch on three streams.**

1. **Inbound stream** -- IMAP every 5 min, Resend webhooks, Slack mentions, form submissions. Each event triggers a router that decides which agent owns it.
   - STOP from any source -> Justine (me) writes ConsentLedger, blocks domain
   - Govt/attorney inbound -> Justine first, then Harrison if it is a contract counterparty
   - Homeowner reply with seller intent -> Rex Negotiator
   - Cash-buyer reply -> Harrison Knox
   - Ambiguous -> Slack ping to me for triage

2. **Outbound stream** -- every Resend send event, every Slack post, every contract draft. The router cross-checks each against the filter chain in (c). Anything that should have been blocked but was not gets a post-hoc flag and a "why did this slip" trace written to a learning log.

3. **DealEvent transitions** -- every stage change in the deal pipeline (intro -> contract -> close). Each transition has a compliance owner. Stage moves to `contract` -> Justine reviews the assignment doc before it goes out. Stage moves to `close` -> Justine confirms state-by-state finder fee threshold.

The mechanism: a small `event_router.py` daemon that subscribes to all three streams and dispatches into the existing named-agent prompts via the same Task-tool path, except it fires automatically on event, not on user query. Same agents, same prompts, same logging -- just triggered by signal instead of request.

Until this layer exists, every compliance miss is going to look like Streubel: I get told about it after the counterparty has already implemented the legal posture for me.

---

## f. Operator commitment

To Marquise:

The Streubel reply is on me. We had no inbound-watch layer, the cold send bypassed the brand stack under the `rich@` legacy alias, and the homeowner-heuristic gate did not exist. He told us to stop before I knew there was anything to stop. That is exactly backwards. The watch layer below ships first, the filter chain ships behind it, and the legacy `rich@` sender alias gets pulled from the Resend domain today. Compliance signals will be on a stream I read every morning, not in a folder I never open.

Justine Park, Compliance Gate.

---

## Dispatch spec -- inbound_watch_daemon.py

**Owner:** Backend build agent (Forge / Codex Labs)
**Path:** `01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/inbound_watch_daemon.py`
**Deploy target:** Oracle E5, systemd unit `inbound-watch.service`, `Restart=always`
**Schedule:** every 5 minutes via internal loop, not cron

**Behavior:**

1. Connect to Gmail IMAP using `IMAP_HOST/IMAP_USER/IMAP_PASS` from `/home/opc/.env`. Read INBOX, mark seen by UID after processing (do not destructively mark as read).
2. For each new message since last checkpoint (`/home/opc/_state/inbound_watch.checkpoint`):
   a. Extract sender domain, recipient alias, subject, plain-text body, in-reply-to header, date.
   b. Classify sender by domain pattern:
      - `govt` if matches `*.gov`, `*.us` w/ city/state subdomain, `*-mo.*`, `*county*`, `*cityof*`
      - `attorney` if matches `law`, `legal`, `attorney`, `counsel`, `llp`, `pllc`, `esq`, `municipalfirm`, or known-firm-token list
      - `homeowner` if consumer-domain (gmail/yahoo/hotmail/aol/icloud/outlook) AND no LLC token
      - `jv_wholesaler` if domain matches a known buyer-list pattern
      - `unknown` otherwise
   c. Detect intent: scan body for STOP / UNSUBSCRIBE / CEASE / DO NOT CONTACT / "harassment" / "remove me" -> intent=`opt_out`. Otherwise scan for seller-intent tokens ("how much", "interested", "make an offer", "what is your offer") -> intent=`seller_reply`.
3. Route on (class, intent):
   - `(govt | attorney, opt_out)` -> ConsentLedger writeback with reason=`opt_out_protected_class`, branded Slack alert to `#compliance` and direct DM to `@justine`, block sender domain in outbound filter chain.
   - `(homeowner, seller_reply)` -> create or update Lead row, post Slack to `#broker-pipeline`, dispatch Rex Negotiator via Task tool with full thread context.
   - `(homeowner, opt_out)` -> ConsentLedger writeback with reason=`opt_out_homeowner`, no escalation needed.
   - `(jv_wholesaler, *)` -> route to Harrison Knox, post to `#broker-pipeline`.
   - `(unknown, *)` or `(*, ambiguous)` -> branded Slack ping to `#compliance` with subject + first 200 chars of body, ask Justine to classify.

4. Cross-check against last-24h outbound: if inbound is a reply to a send NOT present in `resend_budget.jsonl`, log a `bypass_detected` row to `/home/opc/_logs/inbound_watch_anomalies.jsonl`. That is how we catch the next `rich@` script.
5. Emit one canonical hive_logger row per processed message via `content_tools.hive_logger.current_run().add_artifact(...)` with kind=`inbound_email`.
6. Use `content_tools.branded_slack.post_branded_alert()` for any severity=high event (govt/attorney STOP, bypass detected, 5+ STOPs in 24h).
7. Write checkpoint `/home/opc/_state/inbound_watch.checkpoint` with last UID processed every cycle.

**Acceptance tests:**
- Replay the Streubel email through the daemon -> must classify `(attorney, opt_out)`, write ConsentLedger, fire severity=high alert to `#compliance` within 5 minutes.
- Replay the 3 `.gov` historical sends as if reply-STOP -> must classify `(govt, opt_out)`, block domain.
- Inject a bypass test (send via raw Resend with no budget-log row) -> must flag `bypass_detected` within one cycle.

Justine Park, Compliance Gate.
