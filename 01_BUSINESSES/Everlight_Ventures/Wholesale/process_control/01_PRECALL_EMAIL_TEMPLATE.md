# Pre-Call Email Template (sent BEFORE the phone outreach)

**Purpose:** warm the cold contact. Owner sees a name + brand BEFORE phone rings, so the call doesn't feel like a stranger. Also creates a written paper trail for compliance.

**Send via:** branded_mailer.send_branded_email() · category=`vip_reply` (engaged-prospect outreach, NOT bulk)
**From:** henry@everlightventures.io OR rich@everlightventures.io
**Reply-to:** rich@everlightventures.io
**Subject (estate):** Regarding {property_address} -- courtesy notice before our follow-up
**Subject (non-estate):** Regarding your property at {property_address}

**HARD GATE -- NO SEND WITHOUT REAL FIRST NAME.** Per Marquise 2026-04-29: every pre-call email MUST use the recipient's real first name. If we don't have a confirmed first name from the intel deepdive + skip-trace cascade, the email is BLOCKED -- the lead goes back into the queue for Cipher / Rex to enrich, not into the send queue with a generic greeting. branded_mailer should refuse to send any body containing `{first_name}` or `[` characters as a backstop.

For estate leads where we have decedent name but not heir's first name yet:
  - Pull executor name from Shelby Probate Court (browser MHTML)
  - Pull heir candidates from obituary "survived by" section
  - Cross-reference with mailing address on assessor record
  - If still no heir first name after this cascade: use the executor's first name (probate filings list it) -- NOT a generic greeting

---

## Body (estate version)

```
Hi {first_name},

My name is Rich, with Everlight Ventures -- we're a small Memphis-based
real estate group that purchases properties direct from owners and estates.
No agents, no fees.

We noticed the lot at {property_address} is tied to the estate of
{decedent_name}, and I wanted to reach out before calling so this didn't
feel like a cold call out of nowhere.

If the estate has interest in selling, here's what we offer:

  -  Cash close on a quick timeline
  -  No inspection required, lot purchased as-is
  -  Standard back-tax and closing costs handled at the title firm
     (the closing settlement statement will show the breakdown)
  -  All paperwork by email and e-signature -- no travel required
  -  Title firm: Mid-South Title (Memphis, RESPA-compliant)

I'll plan to call in the next 1-2 business days at the number on file.
If a different number or time works better, just reply with what's
convenient -- or if you'd prefer email-only, that's fine too.

If the estate isn't interested, just reply STOP and I won't follow up.

Thanks for the time,

Rich
Everlight Ventures
rich@everlightventures.io  ·  (phone TBD)
```

---

## Body (non-estate, out-of-state owner)

```
Hi {first_name},

My name is Rich, with Everlight Ventures -- a small Memphis real estate
group that purchases properties direct from owners. No agents, no fees.

I noticed your property at {property_address} and wanted to reach out
before calling, so this didn't feel like a cold call.

If you have any interest in selling, here's what we offer:

  -  Cash close on a quick timeline
  -  No inspection required (lot/house purchased as-is)
  -  Back tax + standard closing costs handled at the title firm
     (you'll get an itemized closing statement 24 hrs before close)
  -  All paperwork by email and e-signature -- no travel required
  -  Title firm: Mid-South Title (Memphis, RESPA-compliant)

I'll plan to call in the next 1-2 business days at the number on file.
If a different number or time works better, reply with what's convenient.
Or reply STOP and I won't follow up.

Thanks,

Rich
Everlight Ventures
rich@everlightventures.io
```

---

## Body (local Memphis owner)

```
Hi {first_name},

Rich here with Everlight Ventures -- we buy Memphis properties direct
from owners. No agents, no fees.

I noticed your property at {property_address} and wanted to reach out
before calling.

If there's any interest in selling, here's what we offer:

  -  Cash close on a quick timeline
  -  No inspection
  -  Back tax + standard closing costs handled at the title firm
  -  RESPA-compliant Memphis title firm (Mid-South Title)

I'll plan to call in the next 1-2 business days. Different number or
time work better? Reply with what's convenient. Or reply STOP and I
won't follow up.

Rich
Everlight Ventures
```

---

## Compliance notes

- **CAN-SPAM:** body identifies sender, includes opt-out ("reply STOP"), accurate subject line, real reply-to.
- **TN SB 909:** wholesaler disclosure not yet triggered at email stage (it's a PSA-stage requirement). At PSA we attach the standalone disclosure exhibit.
- **CFPB letter:** does NOT trigger -- we are not a debt collector. No "this is an attempt to collect a debt" language.
- **No false promises:** "back tax handled at the title firm" is true (it's deducted from seller's proceeds at the closing settlement statement, NOT a payment we make from our pocket).
- **No discrimination:** template references SITUATIONAL signals (estate, out-of-state, vacant) NOT identity.

---

## Send sequence

| Day | Action |
|---|---|
| Day 0 (intel done) | Send pre-call email |
| Day 1 morning | Phone call attempt 1 (8-10 AM owner-local time) |
| Day 1 noon | Phone call attempt 2 if no answer |
| Day 1 4pm | Phone call attempt 3 + Slybroadcast voicemail drop if still no answer |
| Day 2 morning | Follow-up email if no reply |
| Day 4 morning | Final email: "offer holds 7 more days, then we move to next" |
| Day 11 | Lead drops to dead-cold queue, comes back in 90 days |
