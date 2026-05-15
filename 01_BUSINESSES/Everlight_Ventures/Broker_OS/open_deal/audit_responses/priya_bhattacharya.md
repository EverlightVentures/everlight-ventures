# Priya Bhattacharya's Privacy + Comms Audit -- Open Deal

**Auditor:** Priya "Pri" Bhattacharya, Privacy & Data Counsel
**Date:** 2026-05-15
**Files reviewed:** `EMD_LOCK_POLICY.md`, `BUYER_DISCLOSURE_LOCK_FEE.md`, `OPEN_DEAL_BUILD_SPEC.md`
**Pairs notified:** Mona Castile (FL gate), Lupe Salazar (AZ gate), Theo Briggs (GC escalation), Imani Calder (litigation co-lead), Justine Park (compliance peer)

---

## Verdict: FIX REQUIRED -- five hard gaps, two soft. Do not flip the SMS rail or the drop-email rail until items 1, 2, 3, and 8 are closed. Stripe lane (item 6) is clean. Pulse-feed lane (item 5) needs a one-paragraph consent string.

The architecture is salvageable. The disclosure modal is already 80% of the way there. We are NOT in TCPA-class-action territory yet because nothing has shipped. We will be on day 1 if we ship the spec as written. The SMS-to-Chris path is the single highest-exposure failure mode and it is one checkbox away from clean.

Documented. Gaps remain. Patch language below.

---

## Privacy Gaps (numbered, with statute)

**P1. No privacy policy exists at `/legal/privacy` and the build spec doesn't create one.** -- BLOCKER

We are collecting bank statements, government ID, LLC formation docs, IP address, user agent, and email + phone on a public-facing site. CCPA (Cal. Civ. Code 1798.100(b)) requires a "reasonably accessible" privacy notice at or before collection. CO (CPA), VA (VCDPA), CT (CTDPA), UT (UCPA), TX (TDPSA, eff. 2026), OR (OCPA) all have parallel notice-at-collection requirements. The geofence in the spec allows TN, CA, AZ, FL -- CA alone triggers CCPA. No privacy policy = $2,500-$7,500 per intentional violation under CCPA Sec. 1798.155, per record. 200 buyers = up to $1.5M theoretical exposure. This is the "thousand $1.5k violations" pattern.

**P2. Verified-tier KYC docs (bank statement, ID, LLC docs) have no retention schedule, no encryption-at-rest commitment, no breach-response runbook tied to them.** -- FIX REQUIRED

Bank statements are non-public personal information under GLBA Sec. 6809(4) the second we receive them, even though we are not a "financial institution" in the strict sense -- but Supabase's free-tier database is not GLBA-grade and we have no GLBA Safeguards Rule program documented. ID images push us into state biometric / ID statutes: IL BIPA (740 ILCS 14, $1k-$5k per record statutory) does not apply because we geofence-block IL, but TX CUBI (Tex. Bus. & Com. Code 503.001) applies if we hold a TX buyer's ID and we are not geofence-blocking TX in the spec's listed allowed states. Also CCPA 1798.100(a)(3) requires a retention period at the point of collection -- the disclosure has none.

**P3. The geofence allowlist (TN, CA, AZ, FL) is missing the GDPR exclusion.** -- FIX REQUIRED

The spec says "geofence config: TN, CA, AZ, FL allowed; others blocked at signup until per-state disclosure is drafted." That blocks 46 US states but says nothing about the EU, UK, EEA, Switzerland. A buyer using a VPN, a US-resident EU citizen, or a snowbird with an EU billing address triggers GDPR Art. 3(2) extraterritorial scope the moment we offer them a paid service. GDPR fines are up to 4% of global annual turnover or EUR 20M, whichever is higher -- but the practical exposure is the data-subject-access-request firehose, not the fine. We have no DSAR process and no DPO. The geofence has to explicitly block EU/EEA/UK at the Cloudflare Worker edge, not just at the signup form.

**P4. IP + UA storage in `drop_locks.disclosure_client_ip` has no retention period, no purpose limitation statement, and IP is "personal information" under CCPA 1798.140(v)(1)(A).** -- FIX REQUIRED

The spec's disclosure-acceptance log captures `client_ip` and `user_agent` indefinitely. Under CCPA we must (a) disclose it in the privacy notice as a category we collect, (b) state the business purpose (fraud prevention + dispute defense), (c) state the retention period. Under GDPR Art. 5(1)(c) we must minimize. Recommended retention: 3 years from disclosure acceptance (matches TN's general civil SOL on contract disputes per Tenn. Code Ann. 28-3-109), then auto-purge. Currently the spec retains forever.

**P5. Pulse-feed publication of "@username locked drop X" is a public disclosure of personal information without explicit per-event consent.** -- FIX REQUIRED

CCPA 1798.140(v) defines personal information broadly. A pseudonymous username + a property address + a timestamp + a financial action (locked a deal) is identifiable when combined with the Verified badge KYC we hold. Buyers consenting to "use the platform" is not the same as consenting to be publicly featured in a live feed visible to anyone on the internet. We need a separate, granular consent checkbox at signup: "I consent to my username and lock activity appearing in the public pulse feed."

Plus the spec has Chris auto-labeled "ANCHOR" with a gold crown -- Chris has to opt in to that in writing, separate from his contractor agreement. Right now the disclosure says "Chris owns the Chris re-brief: 'this is on top of your current arrangement'" -- that is a verbal sign-off path. Pri's rule: verbal consent does not exist. We need Chris's e-signature on a one-paragraph anchor-badge consent before that crown ships.

---

## Comms Gaps (TCPA + CAN-SPAM, numbered, with statute)

**C1. SMS to Chris on every drop -- there is no documented prior express written consent on file. THIS IS THE TCPA BLOCKER.** -- BLOCKER

The spec says: "Chris gets Slack DM + SMS the moment a drop is created." This is an automated marketing/transactional SMS sent via an autodialer-equivalent system to a US wireless number. Under 47 USC 227(b)(1)(A) and the FCC's PEWC requirement codified at 47 CFR 64.1200(a)(2), prior express written consent is required for any "telemarketing" call/text. Even for non-telemarketing informational texts, 47 CFR 64.1200(a)(1) still requires prior express consent (a lower bar -- can be oral or written, but must be documented).

**Three FCC rulings that govern this:**

1. **FCC 2012 TCPA Order, 27 FCC Rcd 1830 (Feb 15, 2012)** -- established PEWC for telemarketing. PEWC = "an agreement, in writing, bearing the signature of the person called that clearly authorizes the seller to deliver or cause to be delivered to the person called advertisements or telemarketing messages using an automatic telephone dialing system or an artificial or prerecorded voice, and the telephone number to which the signatory authorizes such advertisements or telemarketing messages to be delivered."

2. **FCC 2015 Omnibus TCPA Declaratory Ruling, 30 FCC Rcd 7961 (July 10, 2015)** -- expanded the ATDS definition + clarified that consent can be revoked any reasonable way. Largely vacated by ACA International v. FCC, 885 F.3d 687 (D.C. Cir. 2018) on ATDS but the consent-revocation portions survive.

3. **FCC 2023 Declaratory Ruling and Order, FCC 23-107 (Dec 13, 2023) "Closing the Lead Generator Loophole"** -- KEY ONE FOR US -- requires that consent be obtained "one seller at a time" and that the consent disclosure name the specific seller, name the topics consented to, and be logically and topically related to the page where consent was obtained. Buried consent in a ToS does NOT satisfy this rule, effective Jan 27, 2025 with a deferred effective date now in force.

**Applied to our spec:** Chris locked-in his contractor arrangement before Open Deal existed. His current contract has no PEWC for SMS notifications about Open Deal drops, because Open Deal didn't exist when he signed. Sending SMS to Chris on day 1 of Open Deal without a fresh PEWC record = statutory damages of $500/text (47 USC 227(b)(3)(B)), trebled to $1,500 if willful. One drop a day, 30 drops a month = $15k-$45k of TCPA exposure on Chris's number alone. And he's the friendly one. The day a Verified-tier buyer asks for SMS drop alerts via a UI checkbox that says "I want SMS notifications" -- without a properly-worded PEWC disclosure -- is the day we hand a class-action plaintiff's firm the template.

**The click-through "I want SMS notifications" checkbox in the build spec is NOT sufficient PEWC unless it carries the FCC 23-107 disclosure language.** A checkbox by itself is not signed writing. E-SIGN Act (15 USC 7001) lets a checkbox count as a "signature" for TCPA purposes (FCC has confirmed this), BUT the disclosure text adjacent to the checkbox must name Everlight Ventures specifically, name the message topic ("Open Deal drop notifications"), state the frequency ("up to 4 per day"), name the carrier-charge-disclaimer ("message and data rates may apply"), and offer STOP / HELP keywords. The spec has none of this.

Plus: **TN state_gates.json gates SMS to "warm only" until Deal 3.** Pri reads that as a state-level halt that supersedes any federal floor. Even if our PEWC record is perfect, we do not flip the SMS rail until Deal 3 closes. Mona-FL and Lupe-AZ already coordinate per-state SMS gates -- TN gets the same treatment.

**C2. Drop-notification emails via branded_mailer -- CAN-SPAM applies, not just to bulk.** -- FIX REQUIRED

The spec frames drop emails as "transactional" because the buyer requested drop alerts. CAN-SPAM (15 USC 7702(17)) defines a "transactional or relationship message" narrowly: confirming a transaction, providing warranty/recall/safety info, providing account-status info, etc. A drop-notification email is "commercial" under 15 USC 7702(2)(A) because its primary purpose is to facilitate a commercial transaction (the lock). 16 CFR 316.3 -- the FTC's primary-purpose rule -- says when an email contains both transactional and commercial content, the primary-purpose test asks whether a recipient would reasonably interpret the subject line and content as commercial. "New TN drop: 4435 Westminster Pl, spread $12k" reads commercial.

**Therefore every drop-notification email needs:**

- Accurate "From" line naming Everlight Ventures (15 USC 7704(a)(1))
- Non-deceptive subject (15 USC 7704(a)(2))
- Clear and conspicuous identification as a commercial message (FTC interprets this as "ad" tag NOT required if the body makes commercial nature obvious, which our drop emails will -- but the safer path is a one-line "you are receiving this because you signed up for Open Deal drop alerts at everlightventures.io" footer)
- Clear and conspicuous opt-out mechanism, processed within 10 business days (15 USC 7704(a)(3) and (a)(4))
- Valid physical postal address (15 USC 7704(a)(5))

`branded_mailer.send_branded_email()` already does most of this for the bulk template. But the drop-notification template is new and we need to verify the postal address renders in the footer + unsubscribe link routes to a working endpoint that processes the unsub within 10 business days. Per-violation: $51,744 (2024 FTC adjusted, 16 CFR 1.98). Per email. One bad bulk = $5M before lunch.

**C3. Unsubscribe must be honored across BOTH SMS and email rails when the buyer opts out of one.** -- FIX REQUIRED

If a buyer texts STOP to the SMS rail, we cannot keep emailing them about drops unless they explicitly retained email consent. The CFPB and FTC have signaled (in the 2024 FCC consent-revocation rule, FCC 24-24, effective April 11, 2025) that revocation of consent on any channel revokes for ALL channels at that seller unless the consumer explicitly limits the revocation. This is the same eradication doctrine we already enforce on DNC after the David Streubel BBB-threat incident -- now apply it to Open Deal from day 1, not after the first complaint.

**C4. SMS quiet hours.** -- FIX REQUIRED

47 CFR 64.1200(c)(1) and most state mini-TCPAs (FL FTSA, OK, WA, MD) bar telemarketing texts before 8 AM or after 9 PM in the recipient's local time. The spec sends "the moment a drop is created." Drops can be created at 2 AM if `inbound_watch_daemon` picks up a county filing overnight. We need a quiet-hours queue: SMS deferred to 8 AM recipient-local-time. Email has no federal quiet-hours rule but should observe the same window as a brand-trust matter.

---

## Privacy Gap continued (returning to numbered list from item 6)

**P6. Stripe + PCI scope -- we are SAQ-A. Confirmed.** -- CLEAN

We use Stripe Checkout (hosted page) per `EMD_LOCK_POLICY.md` lines 53-107. No card PAN, expiration, or CVV touches our servers. Stripe payment-intent IDs and metadata are stored in `drop_locks` but those are not cardholder data under PCI DSS v4.0 Glossary. We qualify as a Self-Assessment Questionnaire A (SAQ-A) merchant: e-commerce merchant, fully outsourced cardholder data functions. Annual SAQ-A attestation + quarterly ASV scan if we exceed 6M Visa transactions/year (we won't for years). Document this in the privacy program file and move on. Cleared.

**P7. Disclosure modal acceptance logging IP storage is unclear on retention.** -- See P4, same item. FIX REQUIRED.

**P8. Walked-Lock KYC data retention.** -- FIX REQUIRED

If a Verified buyer walks and we keep $50, we have an open question: how long do we retain their KYC docs (bank statement, ID, LLC papers)? CFPB has no direct rule here because we are not a covered financial institution under 12 USC 5481(15) (we are not extending credit, taking deposits, or transmitting money). But the FTC's GLBA Safeguards Rule (16 CFR 314, last amended 2023) reaches "financial institutions" defined broadly to include anyone "engaged in financial activities" -- and accepting bank statements for buyer qualification is borderline. Conservative path: classify ourselves as a "financial institution" for Safeguards Rule purposes, adopt a 3-year retention from last buyer activity, then secure-delete. Justine and I will draft the deletion runbook.

Tex. Bus. & Com. Code 503.001 (TX CUBI) requires biometric ID destruction within "a reasonable time" not to exceed one year after the purpose for collection expires. If we are holding a TX buyer's driver's license image, the purpose expires when the lock walks. One-year hard cap. Add this to the deletion runbook.

---

## Patch Language (paste-ready)

**File:** `BUYER_DISCLOSURE_LOCK_FEE.md`
**Section:** End of disclosure block, before "I have read and understood this disclosure"
**Replace:** (nothing currently exists)
**With:**

```
DATA AND COMMUNICATIONS CONSENTS (granular, each box must be checked separately):

[ ] I consent to Everlight Ventures collecting and storing the personal
    information I provide (account name, email, phone if entered, IP address,
    user agent, payment information, and -- for Verified tier -- proof of
    funds and identity documents) for the purposes of operating Open Deal,
    verifying buyer eligibility, processing payments, defending against
    disputes, and complying with law. Retention period: 3 years from last
    activity, then secure deletion (1 year cap for any government-ID image).
    Full privacy policy: everlightventures.io/legal/privacy.

[ ] (Optional) I consent to my account name and lock activity (e.g.,
    "@username locked drop X") appearing in the public pulse feed at
    everlightventures.io/drops. I may revoke this consent at any time by
    toggling the privacy setting on my dashboard.

[ ] (Optional, only check if you want SMS) I authorize Everlight Ventures
    (everlightventures.io) to send me Open Deal drop notification text
    messages, up to 4 per day, to the number provided at signup, using
    automated technology. Message and data rates may apply. Consent is not
    a condition of any purchase or service. Reply STOP to unsubscribe, HELP
    for help. SMS Privacy Policy and Terms: everlightventures.io/legal/sms.

[ ] (Optional, only check if you want email drop alerts) I agree to receive
    commercial email from Everlight Ventures regarding new property drops.
    I may unsubscribe at any time using the link in any email or by emailing
    privacy@everlightventures.io.
```

---

**File:** `OPEN_DEAL_BUILD_SPEC.md`
**Section:** "Pre-launch checklist" (around line 138)
**Replace:** "Geofence config: TN, CA, AZ, FL allowed; others blocked at signup until per-state disclosure is drafted"
**With:**

```
- [ ] Geofence config (Cloudflare Worker, edge-level, before page render):
      ALLOW: TN, CA, AZ, FL (per state_gates.json)
      BLOCK: all other US states (per-state disclosure pending)
      BLOCK: all EU member states, UK, EEA, Switzerland, Iceland, Norway,
             Liechtenstein (GDPR exclusion -- no DPO, no DSAR pipeline yet)
      BLOCK: any country sanctioned by OFAC SDN list (table refresh weekly)
- [ ] Cloudflare Worker config returns 451 Unavailable For Legal Reasons
      with a polite "Open Deal is not currently available in your region"
      page. No data captured before geofence decision.
```

---

**File:** `OPEN_DEAL_BUILD_SPEC.md`
**Section:** "Hive integration" lines 99-105
**Replace:** "`branded_mailer` -> add 5 LOC to send 'Drop locked by X' notification to non-locking buyers (creates FOMO)."
**With:**

```
- branded_mailer -> add 15 LOC to send drop-notification emails ONLY to
  buyers who have explicitly checked the email-consent box (see disclosure
  modal). All drop emails ship with:
    * From: drops@everlightventures.io
    * Accurate subject line naming the address and spread
    * Footer: "You are receiving this because you opted in to Open Deal
      drop alerts at everlightventures.io on [DATE]"
    * Working unsubscribe link routed to /api/unsubscribe?token=...
    * Postal address: Everlight Ventures, [Memphis TN mailing address]
    * 10-business-day unsubscribe processing SLA (logged + monitored)
  CAN-SPAM compliance: 15 USC 7704(a)(1)-(5). Per-violation penalty
  $51,744 (2024 FTC adjusted, 16 CFR 1.98).
```

---

**File:** `OPEN_DEAL_BUILD_SPEC.md`
**Section:** "Hive integration" -- new line after the branded_mailer entry
**Replace:** (insert)
**With:**

```
- SMS RAIL IS DEFERRED. Do not enable SMS drop notifications -- including
  to Chris Ulander -- until ALL of the following are true:
    1. PEWC disclosure language above is live in the disclosure modal AND
       Chris (or any other recipient) has clicked the SMS-consent box
       with the FCC 23-107-compliant disclosure adjacent.
    2. PEWC record (signed checkbox + timestamp + IP + UA + disclosure
       version) is written to the consent_records table for the
       recipient's number.
    3. SMS rail uses a quiet-hours queue: deferred to 8 AM - 9 PM
       recipient-local-time (47 CFR 64.1200(c)(1) + FL FTSA + state
       mini-TCPA mirror).
    4. STOP / HELP keyword handling is live and STOP revocation
       propagates to email rail within 24h (cross-channel eradication
       per the DNC doctrine).
    5. TN state_gates.json "warm-only" SMS gate is satisfied (Deal 3
       milestone) OR Pri + Theo + Lo countersign an explicit early-flip
       memo for Chris's number specifically.
  Until then, drop notifications to Chris ship via Slack DM only (Slack
  is consent-by-platform, not regulated by TCPA).
```

---

**File:** new file at `/legal/privacy/+page.svelte` (Svelte page)
**Section:** entire file
**Replace:** does not exist
**With:** see "Privacy Policy Skeleton" below.

---

**File:** `EMD_LOCK_POLICY.md`
**Section:** "Chris Ulander handling" lines 136-146
**Replace:** "Drop notification: Chris gets Slack DM + SMS the moment a drop is created"
**With:** "Drop notification: Chris gets Slack DM the moment a drop is created. SMS rail to Chris is DEFERRED pending the PEWC + state-gate conditions in OPEN_DEAL_BUILD_SPEC.md (Hive integration / SMS RAIL IS DEFERRED block). Once those conditions are met, SMS adds on top of Slack."

Also add: "ANCHOR badge on the public pulse feed requires Chris's separately e-signed consent (Anchor Badge Consent, one paragraph, generated by Marvin and countersigned by Chris before flip). Without that, Chris account shows on the pulse feed WITHOUT the gold crown."

---

## Privacy Policy Skeleton (1-page draft -- ships at /legal/privacy)

```
EVERLIGHT VENTURES -- PRIVACY POLICY
Effective: 2026-MM-DD | Version 1.0

1. WHO WE ARE
Everlight Ventures (operating as Marquise Reed, designated agent, in
Tennessee). Postal: [Memphis TN address]. Contact: privacy@everlightventures.io.
We are a real estate wholesaling business. We are not a licensed real
estate broker. See /legal/lock-fee-disclosure for our role.

2. WHAT WE COLLECT
- Account information: name, email, phone (if provided), password hash
- Buyer-tier information: tier level, signup date, payment history
- Verified tier KYC: proof of funds (bank statement excerpt), LLC docs,
  government-issued ID image
- Activity data: drops viewed, locks placed, walks, signs, dashboard logins
- Technical: IP address, user agent, browser fingerprint, session cookies
- Payment metadata: Stripe customer ID, payment intent IDs (NO card
  numbers -- those live with Stripe, PCI-compliant)
- Consent records: disclosure acceptance timestamps, communication consent
  toggles

3. WHY WE COLLECT IT
- Operate the Open Deal platform (perform the service you signed up for)
- Verify buyer eligibility and prevent fraud
- Process payments via Stripe
- Send you communications you have specifically consented to
- Comply with legal obligations (tax records, 1099s for assignment fees,
  anti-money-laundering checks where applicable)
- Defend against disputes (your IP + UA on disclosure acceptance proves
  you saw the terms)

4. WHO WE SHARE IT WITH
- Stripe (payment processor) -- only the data necessary to process payment
- Supabase (database hosting) -- as data processor, not data controller
- Mid South Title (title agent) -- only when an EMD wire is involved, and
  only the data the title company needs to escrow
- Cloudflare (hosting and DDoS protection) -- standard data-processor role
- We DO NOT sell personal information. We DO NOT share for cross-context
  behavioral advertising. (CCPA / CPRA compliance.)

5. HOW LONG WE KEEP IT
- Account data: until you delete your account, plus 3 years for legal
  defense (TN civil SOL: Tenn. Code Ann. 28-3-109)
- Verified KYC documents: until last buyer activity, plus 3 years
  (1-year hard cap for government-ID images per TX CUBI alignment)
- Payment records: 7 years (IRS records retention)
- Consent records: 5 years from last consent activity (FCC TCPA SOL: 4
  years per 28 USC 1658 + buffer)
- IP / UA on disclosure acceptance: 3 years from acceptance

6. YOUR RIGHTS
California residents (CCPA / CPRA): right to know, right to delete, right
to correct, right to opt out of sale/share (we do neither), right to
limit use of sensitive personal info, right to portability,
non-discrimination. Submit requests to privacy@everlightventures.io or
the form at /legal/privacy/request. We respond within 45 days.
Colorado, Virginia, Connecticut, Utah, Oregon, Texas: parallel rights
under CO CPA, VA VCDPA, CT CTDPA, UT UCPA, OR OCPA, TX TDPSA.
EU/EEA/UK residents: Open Deal is NOT currently offered in your region
(geofence-blocked). If you reached this page through a VPN, contact
privacy@everlightventures.io and we will delete any incidentally collected
data within 30 days per GDPR Art. 17.

7. HOW WE PROTECT IT
- TLS 1.3 in transit, AES-256 at rest (Supabase default)
- Access controls: only Marquise Reed, Justine Park (compliance), and
  Pri Bhattacharya (privacy counsel) have access to KYC docs
- Annual SAQ-A attestation for PCI scope
- Quarterly access review
- Breach response runbook activates on any unauthorized access
  (notification to affected users + state AGs as required by state
  breach-notification statutes -- CA Civ. Code 1798.82, TN Code Ann.
  47-18-2107, etc.)

8. CHANGES
We post material changes here with 30 days' notice via email to all
active users.

9. CONTACT
privacy@everlightventures.io | postal: [Memphis TN address]
Privacy Counsel: Priya Bhattacharya
```

---

## Recommendation to Rich

The build is fixable in one sprint -- not blocked, but not green either. The single highest-priority gap is the SMS rail to Chris: we cannot flip that until we have a recorded PEWC checkbox with FCC 23-107-compliant disclosure language adjacent, and per the TN state gate we shouldn't flip it at all until Deal 3 closes. Slack DM to Chris on every drop is fine, regulated by Slack's terms, not TCPA -- so the user experience for Chris does not change on day 1, only the rail.

The privacy policy is the second blocker and it does not exist yet. Skeleton is in this audit, paste-ready. Justine and I can ship the live page in 4 hours. Geofence has to add EU/UK/EEA at the Cloudflare Worker layer before public soft launch -- one Worker edit. Drop emails through `branded_mailer` need the CAN-SPAM footer added to the new template (postal address, opt-out link, "you opted in" sentence).

Net: ship the data and disclosure infrastructure first (privacy policy live, granular consent checkboxes in disclosure modal, geofence widened to block EU, retention table written), then flip the website, then layer in Verified KYC, then -- only after Deal 3 -- consider the SMS rail. Walking this in this order is the difference between a $1.5M class action and a clean revenue stream. Documented. Cleared with conditions.

---

## Coordination notes

- **Pair check pending with Mona Castile (FL):** any FL Verified buyer triggers FL FTSA review on the SMS rail. Mona's audit stamp required before first FL SMS, full stop.
- **Pair check pending with Lupe Salazar (AZ):** same as FL, AZ DNC discipline applies. Lupe's audit stamp before first AZ SMS.
- **Co-counsel notice to Imani Calder:** litigation posture if any Verified buyer disputes a charge or files a CCPA private right of action. Mani drafts the response template.
- **Compliance pair with Justine Park:** quarterly review of `recipient_class.py` extended to cover Open Deal email / SMS audience segmentation. Next review 2026-Q3.
- **Escalation logged to Theo Briggs:** novel statute interplay (TN equitable-interest doctrine + CCPA + FCC 23-107) merits Theo eyes on the final disclosure version before public launch.

What's the consent record? When it exists for SMS + email + pulse feed + KYC, we ship. Until then, gaps remain.

-- Pri
