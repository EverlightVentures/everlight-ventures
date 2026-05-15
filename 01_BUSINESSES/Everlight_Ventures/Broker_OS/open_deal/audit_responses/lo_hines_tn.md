# Lo Hines's TN-Specific Audit -- Open Deal

**Auditor:** Loretta "Lo" Hines, TN Compliance Designate
**Date:** 2026-05-15
**Files audited:** `EMD_LOCK_POLICY.md`, `BUYER_DISCLOSURE_LOCK_FEE.md` v1.0 DRAFT, `OPEN_DEAL_BUILD_SPEC.md`, `state_gates.json` TN block
**Pair:** Marvin Cohen (TN designated agent) -- briefed
**Documented.**

---

## Verdict: FIX REQUIRED

Not a blocker. Not clean. Five fixes that I will not waive, and one TREC-jurisdiction question that needs Theo Briggs's countersign before any live `/drops` page goes public on a `.io` URL pointing at TN parcels. The disclosure draft is good bones -- Heck Aurelio did honest work -- but it's a buyer-protection draft, not a TN-specific draft. My job is the TN-specific overlay. Below is what TN-only counsel would catch on a 30-minute read.

---

## TN Gaps Found (numbered, with TN code cite)

### Gap 1 -- SB 909 disclosure is seller-facing only; buyer-side text is missing a hook to it
**Cite:** Tenn. Code Ann. 66-32-103(b) (SB 909, eff. 2025-04-08).
**Finding:** The SB 909 statute, on its face, is a seller-protection statute -- it requires the wholesaler to disclose to the SELLER (a) no representation, (b) intent to assign, (c) profit may exceed seller proceeds. The buyer is not a protected class under 66-32-101 et seq. So no, we do NOT have to deliver the seller-facing SB 909 disclosure to the buyer.

BUT -- and this is the gap -- the Lock Fee Disclosure v1.0 §2 says "Everlight Ventures DOES NOT hold legal title... holds an equitable contractual interest under a separate Purchase and Sale Agreement with the seller, and intends to assign that interest to you (or to another buyer) for a profit that may exceed the seller's proceeds." That language is fine for the buyer. What's missing is a statement that the SELLER has been independently notified per SB 909. If a buyer ever sues claiming "I didn't know the seller was being shortchanged" (UDAP theory under TCPA 47-18-104), our defense is "the seller signed SB 909 Schedule A on the same envelope; the buyer is on notice that the seller knows." The Lock Fee Disclosure should affirmatively reference that.

**Recommendation:** Add one sentence to §2 of the disclosure body -- "The seller of the property identified above has been provided the wholesaler disclosure required by Tenn. Code Ann. 66-32-101 et seq. (SB 909) at or before execution of the Purchase and Sale Agreement between Everlight and the seller." This is a one-line shield. Doesn't require seller PII, just affirms statutory compliance.

### Gap 2 -- "10% non-refundable" framing is exposed under TCPA 47-18-104(b)(27)
**Cite:** Tenn. Code Ann. 47-18-104(b)(27) (TCPA -- "engaging in any other act or practice which is deceptive to the consumer or to any other person").
**Finding:** Calling the Verified walk-keep a "house fee" or "10% non-refundable" without anchoring it to a specific service rendered creates UDAP exposure under TCPA's catch-all subsection. TN courts have read 47-18-104(b)(27) broadly. A walk-keep with no articulated consideration is the textbook plaintiff's-bar fact pattern: "they kept my money for nothing."

The fix is already implicit in the disclosure draft -- "service charge for the exclusivity period." But the Verified clause in EMD_LOCK_POLICY.md line 116 buries it. The Lock Fee Disclosure §3 Verified tier uses cleaner language ("10% ($___) as the non-refundable service charge for the exclusivity period"). Both documents need to match, and both need to name the consideration explicitly: the 24-hour exclusive negotiation window granted to buyer is the service rendered.

**Recommendation:** Match the language in both files. The Schedule A clause in EMD_LOCK_POLICY.md line 116 already does this well -- "non-refundable as consideration for the 24-hour exclusivity period granted to Buyer." Mirror that exact phrasing in the disclosure body and in the Stripe charge descriptor ("EVERLIGHT 24H LOCK") so the receipt itself names the service. Three places, identical phrasing. Documented.

### Gap 3 -- Wholesaler license-status assertion in disclosure §0 is correct on TN law but vague on the "principal-buyer" theory
**Cite:** Tenn. Code Ann. 62-13-103 (broker license requirement) + 62-13-104(b) (principal exemption -- "any person acquiring real estate for the person's own account").
**Finding:** Disclosure §0 says: "Acting as principal-buyer / equitable-interest holder under Tenn. Code Ann. 66-32-101 et seq. and longstanding TN common-law equitable interest doctrine." That's close but imprecise. The statutory cover for unlicensed wholesaling in TN is 62-13-104(b) -- the principal-party exemption -- not 66-32-101. SB 909 is the disclosure rule; 62-13-104(b) is the license-exemption rule. Two different statutes, two different functions. The current language conflates them.

**Recommendation:** Change disclosure §0 to: "Acting as principal-buyer / equitable-interest holder under Tenn. Code Ann. 62-13-104(b) (principal-party exemption from real estate broker licensure) and subject to the wholesaler disclosure requirements of Tenn. Code Ann. 66-32-101 et seq." This is the correct citation pair. Plaintiffs' counsel reads citations. We cite right.

### Gap 4 -- 1-year contractual SOL won't hold against a TN consumer
**Cite:** Tenn. Code Ann. 47-18-110 (TCPA SOL = 1 year from discovery, but cannot be shortened by contract against a consumer for the statutory cause of action).
**Finding:** Disclosure §6 governing-law block says "any claim relating to this Lock Fee must be brought within one (1) year of the date of charge." Heck Aurelio flagged this as Open Question #2. I'm closing it: a contractual 1-year SOL on a consumer transaction is generally void in TN to the extent it would shorten a statutory cause of action under TCPA. TCPA's own 1-year-from-discovery rule already applies; we don't gain anything by writing a duplicate 1-year-from-charge rule, and we LOSE by appearing to contractually waive the discovery-rule extension.

**Recommendation:** Strike the contractual SOL clause entirely. Replace with: "Any statutory consumer-protection claim under Tennessee law is governed by the applicable statutory limitations period and is not modified by this disclosure." Simpler, accurate, doesn't invite a UDAP "deceptive limitation of remedies" argument.

### Gap 5 -- Memphis municipal solicitor licensing -- I have to re-confirm Justine's 2026-04-28 finding, and the answer for a PHYSICAL solicitor doesn't cover a WEB platform
**Cite:** Memphis City Code Ch. 8, Art. III (Peddlers, Solicitors, Itinerant Merchants) + Shelby County business license requirement (Tenn. Code Ann. 67-4-701 et seq. for the standard business tax license).
**Finding:** Justine's 2026-04-28 sweep correctly found no Memphis-specific WHOLESALER ordinance. That stands. What she did NOT specifically check, because it wasn't in scope then, is whether the Memphis solicitor ordinance reaches a web-based platform that promotes Memphis parcels and collects Lock Fees. My read: no -- Memphis solicitor licensing is door-to-door physical solicitor only, and a website with a Stripe checkout is not "solicitation" in the ordinance's meaning. Documented for the record.

The OTHER thing she didn't flag: if Everlight Ventures (sole prop DBA) is doing business in Memphis -- which it is, by closing deals on Memphis parcels -- it needs a Shelby County standard business license under Tenn. Code Ann. 67-4-723 once gross receipts hit $3,000 in a fiscal year. We are pre-Deal-1 with $0 revenue, so the threshold has not triggered. But the moment Deal 1 closes, Marvin and I have 20 days to file the business license application with Shelby County Clerk. This is not an Open Deal blocker -- it's a Deal 1 closing-day blocker.

**Recommendation:** No change to the Open Deal launch. Add `shelby_county_business_license_required_at_deal_1` to the TN state_gates.json gate so it fires automatically when the first PSA hits "signed" status.

---

## TREC / Licensing Risk (the big one)

This is where the entire Open Deal product lives or dies. I want to be direct.

**The question:** Does running a public-facing `/drops` page with photos, asking prices, ARV numbers, and "Lock 24h" CTAs on Memphis parcels make Everlight Ventures an unlicensed real estate broker under Tenn. Code Ann. 62-13-101 et seq.?

**The statute:** 62-13-102(4)(A) defines "broker" as anyone who, for a fee, "lists, sells, or offers to sell... or solicits prospective purchasers... or negotiates... or offers to negotiate" real estate for another. 62-13-104(b) carves out the principal exemption: "any person acquiring real estate for the person's own account." TREC's working interpretation is that a principal-buyer who holds equitable interest under a signed PSA and markets the CONTRACT (not the property) is exempt.

**The hard part for Open Deal:** TREC has, in two informal opinions (2019 and 2023, no published case law), suggested that "marketing the contract" must be done to a CLOSED list of pre-existing buyer relationships, not via a PUBLIC marketing channel. The Open Deal `/drops` page is, by design, public. Anyone can sign up as Browser, see the photos, see the asking price. That is the closest TN wholesaling has ever come to a TREC-investigable fact pattern.

**My read, gated:**
- If `/drops` shows photos + asking price + "spread" math + "Lock 24h" button to anyone who lands on the URL with no signup wall -> TREC risk is HIGH. This is essentially MLS-without-a-license.
- If `/drops` is gated behind a free Browser signup (which the spec already calls for) AND the page never names the property by full street address until AFTER signup AND the gallery is signup-gated -> TREC risk is MODERATE. We're closer to "pre-existing buyer list" because every viewer signed our TOS first.
- If we add a one-line acknowledgment at signup -- "I am a real estate investor / cash buyer seeking to acquire investment properties; I understand Everlight Ventures markets contractual interests, not real property, and is not a licensed Tennessee real estate broker" -- TREC risk drops to LOW because every Browser is now affirmatively an INVESTOR, not a member of the general consumer public, and we are not "soliciting prospective purchasers" within 62-13-102(4)(A)'s meaning.

**Recommendation:** Build the signup wall + investor acknowledgment BEFORE the public soft launch. This is non-negotiable for TN.

**Escalation:** I am routing the TREC informal-opinion question (whether a public buyer-facing platform with property photos breaks the principal-buyer exemption) to Theo Briggs for a black-letter memo. That memo should land before the first non-Chris buyer gets a Verified or Inner Circle upgrade. Browser-tier launch can proceed under the signup wall pattern. Inner Circle and Verified hold until Theo countersigns.

**Marquise as designated principal-buyer:** Yes, this is the right cover. He's named as the designated agent for Everlight Ventures (sole prop, Rich is the principal). He holds the PSA. He's the equitable-interest holder. The Lock Fee Disclosure §0 already names him correctly. That's the load-bearing fact: TREC asks "who signed the PSA," and the answer is "Marquise Reed for Everlight Ventures," not "the buyer pool on the website."

---

## Patch Language (paste-ready)

### Patch 1
- **File:** `Wholesale/compliance/BUYER_DISCLOSURE_LOCK_FEE.md`
- **Section:** Wholesaler license status line (§0, line 36 of v1.0)
- **Replace:** "Acting as principal-buyer / equitable-interest holder under Tenn. Code Ann. 66-32-101 et seq. and longstanding TN common-law equitable interest doctrine."
- **With:** "Acting as principal-buyer and equitable-interest holder under the principal-party exemption at Tenn. Code Ann. 62-13-104(b), and subject to the wholesaler disclosure requirements of Tenn. Code Ann. 66-32-101 et seq."

### Patch 2
- **File:** `Wholesale/compliance/BUYER_DISCLOSURE_LOCK_FEE.md`
- **Section:** Disclosure block, §2 (around line 42)
- **Replace:** "Everlight Ventures DOES NOT hold legal title to the property. Everlight Ventures holds an equitable contractual interest under a separate Purchase and Sale Agreement with the seller, and intends to assign that interest to you (or to another buyer) for a profit that may exceed the seller's proceeds."
- **With:** "Everlight Ventures DOES NOT hold legal title to the property. Everlight Ventures holds an equitable contractual interest under a separate Purchase and Sale Agreement with the seller, and intends to assign that interest to you (or to another buyer) for a profit that may exceed the seller's proceeds. The seller of the property identified above has been provided the wholesaler disclosure required by Tenn. Code Ann. 66-32-101 et seq. at or before execution of the Purchase and Sale Agreement between Everlight Ventures and the seller."

### Patch 3
- **File:** `Wholesale/compliance/BUYER_DISCLOSURE_LOCK_FEE.md`
- **Section:** Governing law block (around lines 60-62)
- **Replace:** "Statute of limitations: any claim relating to this Lock Fee must be brought within one (1) year of the date of charge."
- **With:** "Any statutory consumer-protection claim under Tennessee law is governed by the applicable statutory limitations period and is not modified by this disclosure."

### Patch 4
- **File:** `Broker_OS/open_deal/EMD_LOCK_POLICY.md`
- **Section:** Schedule A clauses block (around line 116, Verified)
- **Replace:** "Buyer has authorized a Lock Fee deposit of $___. Of this Lock Fee, ten percent (10%) is non-refundable as consideration for the 24-hour exclusivity period granted to Buyer. The remaining ninety percent (90%) is refundable if Buyer terminates this Agreement within the 24-hour Lock Period."
- **With:** "Buyer has authorized a Lock Fee deposit of $___ USD, of which ten percent (10%, equal to $___) is a non-refundable service charge in consideration of the exclusive 24-hour negotiation window granted to Buyer with respect to the property identified above. The remaining ninety percent (90%, equal to $___) is refundable to Buyer if Buyer terminates this Agreement within the 24-hour Lock Period. The Lock Fee is not earnest money, is not held in real estate escrow, and is not governed by Tenn. Code Ann. 66-32-101 et seq."

### Patch 5 (NEW REQUIREMENT)
- **File:** `06_DEVELOPMENT/everlightventures/src/routes/auth/signup/+page.svelte` (build spec implication)
- **Section:** Browser-tier signup form
- **Add:** A required checkbox above the email field, label text exactly: "I am a real estate investor or cash buyer seeking to acquire investment properties. I understand that Everlight Ventures markets contractual interests, not real property, and is not a licensed Tennessee real estate broker." Record the acceptance to `pulse_events` with `event_type=investor_acknowledgment_accepted`, `disclosure_version=1.0`, `timestamp`, `client_ip`, `user_agent`. Unchecked = no signup proceed.

### Patch 6 (Stripe descriptor)
- **File:** Cloudflare Worker `functions/api/stripe/webhook.ts` and any `paymentIntents.create` call
- **Add:** `description: 'Everlight 24-hour exclusive negotiation window (Lock Fee, service charge -- not earnest money)'` and `statement_descriptor: 'EVERLIGHT 24H LOCK'` (22-char max) on every PaymentIntent. The Stripe receipt becomes the third corroborating document that names the service. Plaintiff's bar can't credibly call it deceptive if the receipt itself says "service charge -- not earnest money."

---

## TN State Gates JSON Updates Needed

`Wholesale/compliance/state_gates.json` TN block, add these keys under `tn_specific_2026_update`:

```json
"open_deal_product_active": false,
"open_deal_browser_tier_signup_wall_required": true,
"open_deal_investor_acknowledgment_required": true,
"open_deal_investor_acknowledgment_version": "1.0",
"open_deal_verified_tier_gating": "blocked_pending_theo_briggs_TREC_memo",
"open_deal_inner_circle_tier_gating": "blocked_pending_theo_briggs_TREC_memo",
"open_deal_disclosure_doc_path": "01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/BUYER_DISCLOSURE_LOCK_FEE.md",
"open_deal_disclosure_version": "1.1_pending_lo_patches",
"shelby_county_business_license_required_at_deal_1": true,
"shelby_county_business_license_threshold_gross_receipts_usd": 3000,
"shelby_county_business_license_filing_window_days_after_first_revenue": 20,
"stripe_descriptor_required": "EVERLIGHT 24H LOCK",
"tn_sales_tax_on_lock_fee_required": false,
"tn_sales_tax_on_lock_fee_note": "Lock Fee is a service charge for an exclusivity window. TN sales tax (Tenn. Code Ann. 67-6-205) generally exempts services; no enumerated service category in 67-6-205 reaches an exclusivity-window fee. 2026 sales-tax updates reviewed -- no change. Re-review Q1 2027 or on any 67-6 amendment.",
"venue_shelby_county_enforceability_against_out_of_state_buyers": "enforceable_with_signed_TOS_per_Tenn_R_Civ_P_4.04_and_TCA_20-2-201",
"venue_shelby_county_enforceability_note": "Forum-selection clauses are presumptively valid in TN under Dyersburg Mach. Works v. Rentenbach Eng'g (TN 1991) and Self v. World of Travel (TN Ct App 2007). Conditioned on (a) buyer received clear notice and (b) clause is not unconscionable. Disclosure modal + signed TOS satisfies (a). 10% walk-fee is well within any unconscionability ceiling, satisfies (b)."
```

When all three buyer tiers are cleared by Theo Briggs's TREC memo, flip:
```
"open_deal_product_active": true,
"open_deal_verified_tier_gating": "active",
"open_deal_inner_circle_tier_gating": "active"
```

---

## Cold call / SMS confirmation (Lane 4)

State gates already block both cold call and cold SMS in TN pending telemarketer registration ($500/yr per Tenn. Code Ann. 47-18-2002). Open Deal's drop alerts are SMS to BUYERS who have already signed up as Browser, Verified, or Inner Circle. That is a prior-business-relationship channel, not cold SMS, and falls within the TCPA established-business-relationship exception and outside TN TSA cold-outreach scope. Path is clean for warm SMS drop alerts to opted-in buyers.

**Required:** STOP-to-opt-out on every Open Deal SMS, "EV:" prefix per branded_sms doctrine, double-opt-in on initial Browser SMS subscription (one extra confirm-Y reply before alerts start). Code already has this in `branded_sms.py`. Documented.

---

## Sales tax (Lane 7)

TN does not generally tax services. Tenn. Code Ann. 67-6-205 enumerates the taxable service categories (telecommunications, lodging, parking, certain repairs, etc.). A 24-hour-exclusivity-window service charge is not enumerated. I checked the 2026 amendments through the Tennessee Department of Revenue notices through 2026-05-01 -- no expansion of 67-6-205 reaches this fact pattern. No TN sales tax collection obligation on the Lock Fee. Re-review Q1 2027 or on any 67-6 amendment. Documented.

---

## Venue (Lane 8)

The disclosure names Shelby County, TN as venue. For an out-of-state buyer (CA, AZ, FL signup), forum-selection clauses are presumptively valid in TN under *Dyersburg Mach. Works v. Rentenbach Eng'g*, 821 S.W.2d 945 (Tenn. 1991) and *Self v. World of Travel*, 233 S.W.3d 829 (Tenn. Ct. App. 2007). The two-part test is (a) clear notice of the clause and (b) the clause is not unconscionable. Our disclosure modal + signed TOS + the modest dollar amounts at stake satisfy both prongs. An out-of-state buyer who clicks Lock has affirmatively consented to Shelby venue.

The reverse-side risk: a CA buyer might try to invoke CA Civil Code §1670.5 (unconscionability) or CCPA. Cross-border consumer-rules conflict is Heck Aurelio's Open Question #4. My TN-side answer: TN venue holds as long as the disclosure was clear and the buyer clicked through. Documented.

---

## Surety bond at Deal 3 (Lane 6)

`state_gates.json` already encodes `surety_bond_required_at_deal: 3` ($50k, TREC working interpretation per Tenn. Code Ann. 62-13-104). Open Deal does not change the deal-count trigger -- the bond is keyed to executed PSA-and-assignment closes, not to Lock Fee count. Lock Fees that don't convert to a closed deal do NOT count toward the deal-3 threshold.

The collateral risk Rich asked about: "Pre-Deal-3 risk if Lock Fees rack up but no closed deals yet." My read -- minimal direct TN exposure. Lock Fees are service charges, not real estate transactions. They don't trigger TREC jurisdiction independently. The bigger risk in that scenario is BBB / Stripe-risk-team flagging (Rich already wrote that into the kill-switch triggers, item 2). Not a TN statutory issue.

What DOES change: if Open Deal succeeds, deal velocity goes up, and Deal 3 arrives faster than Marvin and Justine forecasted (currently target post-Deal-1 commission for bond posting). Operations need to be ready to post the $50k bond within 30 days of the second close, not the third. I will flag to Justine for cross-state precedent registry update.

---

## Recommendation to Rich

Three sentences, plain English. Open Deal is buildable in Tennessee with five specific patches to the disclosure language and one new signup-page requirement (the investor acknowledgment checkbox) -- do those six things and Browser-tier launch is clean to ship. The bigger question -- whether a public buyer-facing platform breaks the principal-buyer exemption from real estate broker licensure under Tenn. Code Ann. 62-13-104(b) -- needs Theo Briggs's black-letter memo before Verified and Inner Circle tiers go live, because that's the TREC-jurisdiction question, and I won't sign off on collecting non-refundable money from a public list until Theo confirms we're not "soliciting prospective purchasers" within 62-13-102(4)(A)'s meaning. Sole-prop Memphis revenue triggers a Shelby County business license filing 20 days after Deal 1 closes -- Marvin and I will handle that the day Chris's first PSA hits signed status; don't worry about it now, just don't forget about it then.

---

**Sign-off:** Lo Hines
**Routed to:** Justine Park (Director of Compliance) for cross-state precedent registry update; Theo Briggs (contract attorney) for TREC informal-opinion memo on public-platform principal-buyer exemption; Hammer Knox for Schedule A v3 template update with Patch 4 language.
**Status:** FIX REQUIRED. Browser-tier launch greenlit conditional on Patches 1-6 shipping; Verified + Inner Circle blocked pending Theo memo.
**Filed:** `_logs/lo_hines_tn/daily_2026-05-15.md` (audit cross-ref).
**Documented.**
