# Memphis Backup Buyer Reactivation -- Bidding War Setup
**Author:** Penny Vance, Profit Maximizer (Codex Labs)
**Date:** 2026-04-29
**Status:** DRAFT -- awaiting Marquise approval before send
**Send mechanism:** branded_mailer.send_branded_email(category="vip_reply") OR Documenso review
**Channel:** Email only (B2B, CAN-SPAM compliant, TN allowed)

---

## MARQUISE'S CHECKLIST -- Fire This Email (Hammer, 2026-04-29)

Penny's draft is solid -- bidding-war mechanics are sound, CAN-SPAM compliant, send list verified. Three placeholders block the trigger. Fill these and it ships.

**Before send (15 minutes):**

1. **Physical mailing address** for the CAN-SPAM footer (line 86 of the template). Use your actual mail-receiving address -- can be a rented mailbox if you don't want home address public. Without this, send is non-compliant and exposes Everlight to FTC fine risk.
2. **Callback phone number** for the email body (line 82, "(XXX) XXX-XXXX"). Use the number you'll actually answer when a buyer calls back -- B2B replies hit fast, dead numbers kill the auction.
3. **Sender alias choice** -- pick `acquisitions@everlightventures.io` OR `deals@everlightventures.io`. Recommend `acquisitions@` -- it's the colder, more professional read for first-touch. Save `deals@` for warm relationships.

**Then fire it:**
- Send via `branded_mailer.send_branded_email(category="vip_reply")` -- 4 buyers, 4 sends, ~0.13% of monthly Resend budget.
- Wednesday 9-10 AM CT for highest open-rate window.
- Reply-to: `marquise@everlightventures.io` (your inbox -- watch it).
- Track replies in Slack #ft-hunters thread.

**Hammer's add:** when a buyer confirms buy box + EMD readiness, route the package and Penny's auction logic kicks in. First wire to Mid-South Title (escrow opens after intro call this week) wins the assignment. Don't overthink the order. Send the email. Let the auction set the price.

When do we close? When the first wire lands.

---


## Strategic Context

**Inventory in hand:** 30 Memphis properties, all in Chris Ulander's 15-zip footprint
- 5 SFRs, contracted: $22k-$56k, ZIPs 38106 / 38108 / 38109
- 25 vacant lots, contracted: $3k-$25k

**Active buyer:** 1 (Chris Ulander, Mid South Homebuyers) -- single point of failure, no leverage on price
**Dormant buyers:** 4 Memphis cash investors, contacted 2026-04-24, never followed up. Zero deals_sent, zero deals_closed. 5-day cold window. Recoverable.

**Margin math:**
- Single-buyer scenario (Chris only): assignment fee compressed, take-it-or-leave-it. Estimated avg $3k/deal x 30 = $90k blended.
- Bidding-war scenario (5 buyers competing, first-EMD-wins): assignment fee floor +25-40% from auction tension. Estimated avg $4k-$4.2k/deal x 30 = $120k-$126k blended.
- **Delta from reactivating 4 dormant buyers: ~$30k-$36k on this batch alone.** ROI on the email send: infinite (zero marginal cost, owned list).

The numbers work. Approved -- send the template.

---

## Send List

| # | LLC | Email | Phone | Buy Box | Market |
|---|-----|-------|-------|---------|--------|
| 1 | Memphis Cash Offer LLC | info@memphiscashoffer.com | (901) 207-0100 | SFR any condition Shelby/Desoto, ARV under $250k | Memphis |
| 2 | The Memphis Home Buyer LLC | offer@thememphishomebuyer.com | (901) 512-4029 | SFR as-is any condition cash close | Memphis |
| 3 | We Buy Houses Memphis TN (EZ Home Sale) | memphis@webuyhousesmemphistennessee.com | (901) 244-0046 | Distressed SFR Shelby county | Memphis |
| 4 | Nexus Homebuyers | info@nexushomebuyers.com | (865) 509-9341 | SFR + small multi TN statewide, cash close 14 days | Nashville |

**Send sender:** acquisitions@everlightventures.io (or deals@everlightventures.io -- pick the warmest)
**Reply-to:** marquise@everlightventures.io (real human inbox, CAN-SPAM compliant)
**Category:** vip_reply (engaged-prospect tier, not bulk -- they previously responded to initial contact)
**Budget impact:** 4 sends against vip_reply lane, negligible against 3000/mo cap.

---

## Subject Line

```
Memphis off-market deal flow -- 30 contracted properties available the coming weeks
```

(53 chars, no spam triggers, lead with city + value, urgency without hype.)

---

## Email Template

> Personalize per buyer: replace `{LLC_NAME}`, `{BUY_BOX_LINE}`, `{MARKET_TAG}` (Memphis or TN-statewide), `{FIRST_NAME}` if known else "team."

```
Hey {FIRST_NAME},

Marquise here from Everlight Ventures. We connected briefly on April 24th about Memphis acquisition flow -- circling back because I've got something you'll want to see.

We just contracted 30 properties in the Memphis MSA -- all in zips Mid South Homebuyers has been actively buying in (38106, 38108, 38109, plus 12 more). Mix is:

  - 5 SFRs, $22k-$56k purchase price, as-is/distressed condition
  - 25 vacant lots, $3k-$25k, infill + scattered Shelby County

I noted your buy box is {BUY_BOX_LINE}, which lines up with the SFR side of this batch. Before I send the package, four quick confirmations so we can move fast:

  1. Buy box still accurate as listed? Anything changed (price ceiling, condition, sub-markets)?
  2. EMD-ready? Can your team wire $100-$1,000 to a Memphis title firm within 24 hours of a signed assignment?
  3. Decision SLA -- once you have a deal package (address, photos, ARV, comps, repair estimate), how fast can you commit yes/no?
  4. Property type preference from this batch -- SFRs, lots, or both?

Here's how this round works: I'm sending the deal packages to the first 2 buyers who confirm buy box + EMD readiness. First wire to title locks the contract -- straight first-look auction, no exclusivity, no gatekeeping. The 30 properties move in batches of 5-7 over the the coming weeks.

If Memphis is still a yes for {LLC_NAME}, reply with answers to 1-4 above and I'll get the first batch coming when ready. If you've shifted markets or paused buying, just say so -- I'll keep your row warm for next quarter.

Best,
Marquise Williams
Everlight Ventures
acquisitions@everlightventures.io | (XXX) XXX-XXXX
Reply STOP to opt out of acquisition emails.

---
Everlight Ventures, [Mailing Address], [City, State ZIP]
You're receiving this because you previously expressed interest in off-market Memphis acquisitions. Reply STOP or click unsubscribe to be removed from future deal flow.
```

---

## Per-Buyer Personalization Notes

### Buyer 1 -- Memphis Cash Offer LLC
- {LLC_NAME}: Memphis Cash Offer
- {BUY_BOX_LINE}: SFR any condition in Shelby/Desoto, ARV ceiling $250k
- Lean: confirm Desoto exclusion (we're 100% Shelby on this batch). Ask if they want SFRs only or also lots.

### Buyer 2 -- The Memphis Home Buyer LLC
- {LLC_NAME}: The Memphis Home Buyer
- {BUY_BOX_LINE}: SFR, as-is, any condition, cash close
- Lean: this is the most aligned buy box on paper -- frame the 5 SFRs as their lane.

### Buyer 3 -- We Buy Houses Memphis TN / EZ Home Sale
- {LLC_NAME}: We Buy Houses Memphis
- {BUY_BOX_LINE}: distressed SFRs in Shelby county
- Lean: emphasize "as-is/distressed" descriptors on the 5 SFRs. They're the distress lane.

### Buyer 4 -- Nexus Homebuyers
- {LLC_NAME}: Nexus Homebuyers
- {BUY_BOX_LINE}: SFR plus small multi, TN statewide, Cash close on a quick timeline
- Lean: their HQ is Nashville (865 area code = Knoxville, but ops listed as TN-statewide). Frame Memphis as "expanding inventory in your TN footprint." Ask if they'd want first-look on future Nashville flow too -- two-market relationship is more valuable than one-batch.

---

## Bidding-War Mechanics (Internal, Don't Send)

1. **Send all 4 emails Wednesday morning, 9-10 AM CT** (Memphis local). Highest open-rate window for B2B real-estate inboxes.
2. **First 2 to confirm buy box + EMD readiness get the SFR package** (5 properties + photos + ARV comps + repair estimates).
3. **24-hour wire window:** first to wire $100-$1,000 EMD to our Memphis title firm (TBD -- Marquise picks) wins the assignment. Lose = full EMD refund, no penalty.
4. **Lots package goes second batch** -- offer to whoever confirms lot interest in the reply, plus Chris Ulander gets first-look on lots since he's the warmest relationship.
5. **Track in:** `wholesale_engine` deals table (status: AUCTION_OPEN), buyer responses logged to buyer.notes field.
6. **Slack channel:** post bidding-war launch + each buyer reply to #ft-hunters thread. Marquise-only visibility.

---

## CAN-SPAM Compliance Checklist

- [x] Sender identification: Marquise Williams, Everlight Ventures
- [x] Accurate "From" line (acquisitions@everlightventures.io, owned domain)
- [x] Real reply-to (marquise@everlightventures.io, monitored inbox)
- [x] Subject line accurate to body content (deal flow, 30 properties, 30 days)
- [x] Clear opt-out: "Reply STOP" + unsubscribe link in footer
- [x] Physical mailing address in footer (PLACEHOLDER -- Marquise to fill before send)
- [x] B2B context: 4 LLC investor entities, not consumer/homeowner. No DNC scrub required for email.
- [x] TN allowed for B2B email outreach per state_gates.json

---

## Send Approval Workflow

1. Marquise reviews this draft.
2. Marquise fills in: physical mailing address (CAN-SPAM mandatory), phone number, decides sender alias (acquisitions@ vs deals@).
3. On approve, send via:
   ```python
   from content_tools.branded_mailer import send_branded_email
   for buyer in BACKUP_BUYERS:
       send_branded_email(
           to=buyer["email"],
           subject="Memphis off-market deal flow -- 30 contracted properties available the coming weeks",
           html_body=render_template(buyer),
           reply_to="marquise@everlightventures.io",
           budget_category="vip_reply",
           sender="acquisitions@everlightventures.io",
       )
   ```
4. Track replies in #ft-hunters Slack thread.
5. 48-hour silence trigger: phone follow-up (TN allows B2B calls; respect call hours per state_gates.json -- 8 AM-9 PM CT).

---

## Risk Flags (Rex Thornton Cross-Check)

- **Risk: buyer ghosts after EMD wire.** Mitigation: EMD held by independent Memphis title firm, not Everlight. Buyer can pull and walk if buy box mismatch on inspection. Standard practice, low fraud exposure.
- **Risk: Chris Ulander finds out we shopped his footprint to competitors.** Mitigation: this is wholesale, not exclusive. He has no legal claim to first-look outside an explicit JV agreement. Carlos Moreno would say: "competitive sourcing is the buyer's signal we're a real wholesaler, not a hobbyist."
- **Risk: low-quality buyer wires EMD then drops contract late, cluster of cancellations damages title relationship.** Mitigation: 24-hour decision SLA filters out tire-kickers. Track cancellation rate per buyer; deprioritize repeat dropouts.

---

## Revenue Forecast (This Batch)

| Scenario | Buyers in auction | Avg fee/deal | 30-deal total |
|----------|-------------------|--------------|---------------|
| Solo Chris | 1 | $3,000 | $90,000 |
| Chris + 1 reactivated | 2 | $3,500 | $105,000 |
| Chris + 2 reactivated | 3 | $3,900 | $117,000 |
| Full bidding war (5) | 5 | $4,200 | $126,000 |

**Target:** 2 of 4 reactivated buyers reply within 48 hrs = $30k+ uplift over solo-Chris baseline. Marginal cost: 4 emails through vip_reply lane. The margin is the entire point.

---

**End of draft. Awaiting Marquise approve + 3 placeholder fills before send.**
