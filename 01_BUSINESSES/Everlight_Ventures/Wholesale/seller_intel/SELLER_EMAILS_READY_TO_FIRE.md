# Pre-Call Seller Emails -- Ready to Fire (2 verified, 3 blocked)

Generated 2026-04-29 ~3:30 AM PT after MX verification on Phil's pattern-guess emails.

**Send via:** `branded_mailer.send_branded_email(category="vip_reply")`
**From:** rich@everlightventures.io (or henry@everlightventures.io)
**Sequence:** these go out FIRST, before the phone follow-up window.

---

## ✓ READY TO FIRE: Mikal Hakeem -- 1536 S Third St

**Email:** mhakeem@timemphis.org (MX verified, Google Workspace)
**Subject:** Regarding 1536 S Third Street, Memphis -- courtesy notice before our follow-up
**Owner profile:** Mikal Hakeem L, owned 7 years, lot tax-delinquent 4+ years, multiple sales in history (active investor pattern)
**Pitch hook:** Investor-to-investor, no pitch needed (`is_llc_owner` adjacent signal)

```
Hi Mikal,

My name is Rich, with Everlight Ventures -- a small Memphis real estate
group that purchases properties direct from owners. No agents, no
commissions.

I noticed your property at 1536 S Third Street and wanted to reach out
before calling, so this didn't feel like a cold call.

Looking at your portfolio, you appear to be an active investor in the
area. We work investor-to-investor when that's the cleaner path -- no
agent commission, fast assignment-friendly close, RESPA-clean Memphis
title firm (Mid-South Title), and we're happy to package multiple
properties at once if you're looking to thin inventory.

For 1536 S Third specifically, here's our standard offer:

  - Cash close on a quick timeline
  - No inspection required, property purchased as-is
  - Standard back property tax handled at the title firm
    (you don't write a check or owe out of pocket)
  - All paperwork by email and e-signature -- no driving anywhere

If there's any interest, reply with what time works for a quick call.
Or if you'd prefer email-only, that's fine too. If you're not selling,
just reply STOP and I won't follow up.

Thanks for the time,

Rich
Everlight Ventures
rich@everlightventures.io
```

---

## ✓ READY TO FIRE: Trezden Matthews -- 1393 Valse (vacant lot)

**Email:** tmatthews@qclfocus.com (MX verified, Titan Email)
**Subject:** Regarding your lot at 1393 Valse, Memphis -- courtesy notice
**Owner profile:** Out-of-state (Kennesaw GA), apartment mailing, owned 6 years, vacant lot, 4+ years tax-delinquent
**Pitch hook:** Out-of-state convenience + back-tax relief

```
Hi Trezden,

My name is Rich, with Everlight Ventures -- a small Memphis-based real
estate group that purchases properties direct from owners. No agents,
no commissions.

I noticed your lot at 1393 Valse and wanted to reach out before
calling.

Managing a Memphis lot from Kennesaw, Georgia is its own kind of work
-- tax notices, code letters, occasional weed-cutting bills. We handle
the entire close-out by mail and wire. You don't fly in.

If there's any interest in selling, here's what we offer:

  - Cash close on a quick timeline
  - No inspection required, lot purchased as-is
  - Standard back property tax handled at the title firm
    (you don't write a check or owe out of pocket)
  - All paperwork by email and e-signature
  - Title firm: Mid-South Title (Memphis, RESPA-compliant)

Reply with what time works for a quick call, or email-only if you
prefer. If not interested, reply STOP and I won't follow up.

Thanks,

Rich
Everlight Ventures
rich@everlightventures.io
```

---

## ✗ BLOCKED: Bennie Leggett -- 108 E Olive (LA absentee)

**Email guess:** bennie@bennieboystowing.com  -- **MX FAILED, domain has no mail server**
**Why:** Bennie Boys Towing in LA per Voyage LA bio, but the business website doesn't run email
**Next step:** LinkedIn message (manually) OR Google for the towing business direct phone (TX cold-call permitted) OR skip to next priority lead

---

## ⏳ NEEDS_MORE_INTEL (4 leads, 20 min total to unblock tomorrow)

These are the same 4 Phil flagged. Email cannot fire until first name + verified address captured.

1. **Howard Eddie estate** (117 Farrow) -- Shelby Probate Court browser MHTML, 5 min
2. **Carnegie Church** (1577 McMillan) -- call (901) 942-2500 for pastor first name, 5 min
3. **Greater Love Ministries** (1537 Wilson) -- NM SOS officer search, 5 min
4. **Toby Jones** (1596 Gabay) -- re-pull assessor MHTML for missing zip, 5 min

---

## How to fire (when Marquise approves)

```bash
# Single send (Mikal):
python3 -c "
from content_tools.branded_mailer import send_branded_email
send_branded_email(
    to='mhakeem@timemphis.org',
    from_email='rich@everlightventures.io',
    subject='Regarding 1536 S Third Street, Memphis -- courtesy notice before our follow-up',
    body=open('/path/to/mikal_body.md').read(),
    budget_category='vip_reply',
)
"
```

Marquise: do NOT fire yet -- approve each one first, fire one at a time, watch for replies before sending the next batch. Lead-by-lead, not blast.

---

## Status snapshot

```
14 priority leads
├─ 2 ready to fire (verified MX) ........... Mikal, Trezden
├─ 1 mail-only (tier-2) ..................... Marco Williams (door-knock dropped per Marquise; re-route to email pattern + mail; door-knock deferred to post-Deal-1)
├─ 1 blocked on bad email pattern ........... Bennie Leggett (need LinkedIn / phone)
├─ 4 blocked on intel gaps .................. Howard Eddie, Carnegie, Greater Love, Toby Jones
└─ 6 ready but no email/phone surfaced ..... need verified contact still
```

Action: Marquise approves and fires the 2 verified emails (Mikal + Trezden). Marco re-routed to email-find (Cipher) then Lob mail. Phone follow-up gates after Oracle skip-trace fix lands. See dispatch_orders/2026-04-29/MARCO_reroute_decision.md.
