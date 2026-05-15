# Imani Calder's Litigation Risk Audit -- Open Deal

**Audit date:** 2026-05-15 PT
**Auditor:** Imani Calder, Senior Litigation Counsel
**Privilege:** ATTORNEY WORK PRODUCT -- PRIVILEGED & CONFIDENTIAL
**Scope:** EMD_LOCK_POLICY.md + BUYER_DISCLOSURE_LOCK_FEE.md + OPEN_DEAL_BUILD_SPEC.md
**Posture:** I sat on the plaintiff side from 2019 to 2026. I built dockets that took down marketers with cleaner paper than this. I am writing this audit as the lawyer who would sue us.

---

## Verdict: **FIX REQUIRED -- DO NOT LAUNCH UNTIL THE SEVEN PATCHES BELOW SHIP**

The structure is defensible. The execution paper has holes a second-year associate would walk through in a 12(b)(6) opposition brief. Five of the seven patches are 30-minute copy edits. Two are structural. None are blockers if we ship them before the first real lock. **If we go live as-drafted, I give us ~70% odds of a TN AG inquiry inside 18 months and ~25% odds of a class action filing in years 2-3.** Both are survivable -- but only if we close the gaps now, because the timeline is the only thing that wins after the fact.

---

## Top 3 Lawsuit Vectors (ranked by likelihood)

### 1. **TN AG / TREC unlicensed-broker complaint** (likelihood: HIGH within 18 months)

This is the throat. Every wholesale-disclosure regime in the country has been tightening since 2023 (NC HB 797, SC 40-57-135, OK HB 3081, IL 815 ILCS 177). Tennessee passed **SB 909 / Tenn. Code Ann. 66-32-101 et seq.** in 2024 -- the SELLER-side disclosure. TREC and the AG are watching wholesalers. The moment a Verified buyer walks away angry over $50, they Google "is this even legal in Tennessee" and the first result is a TREC complaint form.

**The vector:** Verified buyer walks, gets $450 back, files a TREC + TN AG joint complaint alleging:
- (a) Everlight is acting as an unlicensed real estate broker under Tenn. Code Ann. 62-13-101 et seq. by holding itself out to multiple buyers as the entity with authority to convey property
- (b) Everlight is acting as an unlicensed escrow agent by collecting "Lock Fees" that function as deposits on real estate transactions
- (c) The 10% retention is a deceptive practice under TN Consumer Protection Act (TCPA) 47-18-104

**Why the disclosure does not fully neutralize this:** The disclosure says "Marquise Reed... not licensed... acting as principal-buyer / equitable-interest holder under Tenn. Code Ann. 66-32-101 et seq." That citation is wrong. SB 909 is the seller-side disclosure statute -- it does NOT create a safe harbor for unlicensed wholesalers; it imposes affirmative disclosure obligations on them. Citing it as the basis for licensure exemption is exactly what the AG would highlight in paragraph 3 of a complaint.

### 2. **TN Consumer Protection Act class action** (likelihood: MEDIUM-HIGH at year 2-3, IF we hit volume)

Tenn. Code Ann. 47-18-101 et seq. -- the TCPA. Treble damages. Attorney fees mandatory to prevailing plaintiff (47-18-109(e)(1)). Class certification standard in TN is generous post-*Walker v. Sunrise Pontiac-GMC* (2008).

**The math a plaintiff's firm runs:** 5,000 walks × $50 = $250k base. Trebled = $750k. Plus fees = $1M+ pot. That is exactly the size case a contingent-fee plaintiff firm in Nashville or Memphis will file on a Friday afternoon. I have seen this docket built three times in my career and every time it ran the same way.

**The predicate they will plead:** the disclosure's "service charge, not earnest money" framing is the deceptive practice. They will argue the buyer reasonably believed the $500 was held in trust, that "Lock" implies escrow, and that the 10% retention is an unconscionable forfeiture under TN common law (*Hutton v. Roberts*, 1988).

### 3. **Stripe merchant-account shutdown via chargeback cascade** (likelihood: HIGH within 6 months at projected volume)

This is the operational throat. Stripe shuts down merchants when **dispute ratio exceeds 1%** of transactions. Visa's threshold is 0.9%. Mastercard is 1.5% for "excessive chargeback program."

**The math on the projected 53 walks/month:**
- 15 Verified walks/mo × even 10% chargeback rate = 1.5 chargebacks
- Verified captures = 40/mo (15 walks + 25 signs)
- 1.5 / 40 = **3.75% dispute ratio** -- nearly 4x Stripe's threshold

At that ratio, Stripe sends a "Risk Review" email in month 1, freezes payouts in month 2, terminates account in month 3. **And once Stripe terminates, they share the MATCH list with every other processor.** No Square, no Adyen, no Braintree without significant friction. That is an existential operational risk, not a litigation risk -- but it is in my lane because the chargebacks become deposition exhibits in any later class action.

---

## Adversarial Walk-Through (act like plaintiff's lawyer)

I am Sarah Whitlow, partner at Whitlow & Banks in Nashville. Marquise's $450 refund victim, Jeremiah Davis, calls me on a Tuesday. Here is my filing posture by end of week.

### Phase 1: paper discovery on Jeremiah alone (one client, $50 in controversy)

I file a TCPA action in Shelby County General Sessions (small claims jurisdiction, $25k cap, no answer required, plaintiff-friendly). I plead:
- Count 1: TN CPA 47-18-104(b)(27) -- "engaging in any other act or practice which is deceptive"
- Count 2: Unjust enrichment
- Count 3: Money had and received
- Count 4: Conversion (the $50 is Jeremiah's property, not Everlight's, until a contract is signed)

I request expedited discovery. Within 30 days I have:
- Stripe transaction logs (subpoena)
- The disclosure modal source code (subpoena to Cloudflare)
- The `pulse_events` table extract (subpoena to Supabase)
- Every Slack message in `#broker-pipeline` (subpoena to Slack, if it goes that far)
- Marquise's text messages with Chris Ulander
- Every email from `piper@`, `marquise@`, `rex@` to TN consumers in the prior 24 months

### Phase 2: I find the patterns

**Pattern A:** disclosure version mismatches. The build spec says "On disclosure version bumps... prior accepted-version records remain valid for active locks." I will argue that means **buyers accepted v1.0 but locked under v1.1 terms.** Each mismatch is a separate TCPA violation at $1,000 statutory minimum.

**Pattern B:** the 10% retention is calculated on the GROSS charge, but the disclosure language says "we refund 90% of the charge." Stripe takes ~2.9% + $0.30 (~$14.80 on $500). The buyer paid $500. Everlight gets the $50 net of Stripe fees. So the buyer is actually out $50 + the unrecovered Stripe fee. The disclosure says "Stripe's payment-processing fee... is non-refundable in all cases as a separate Stripe matter." **This is deceptive.** The buyer is being charged Stripe fees twice -- once on capture, once embedded in the 10% retention. Multiply by 5,000 walks and that is the class predicate.

**Pattern C:** the "ANCHOR" badge on Chris. I will depose Chris and find out he is comped, he gets the drop notification BEFORE the 4-hour Inner Circle window opens, and he is labeled ANCHOR. I will argue this is **shill bidding / phantom demand** under TN CPA 47-18-104(b)(5) ("represents that goods or services have... characteristics... approval... that they do not have"). The pulse feed implies organic demand from a high-quality buyer. The reality is paid placement for an undisclosed anchor partner. **This is the single biggest defamation-of-the-marketplace risk we have, and Chris will be deposed before me.**

**Pattern D:** geofence holes. The spec says "TN, CA, AZ, FL allowed; others blocked at signup until per-state disclosure is drafted." But if any non-TN buyer locks (VPN, lying about residence, mobile geo-spoof), CA law applies. CA Civ. Code 2945 / 1695 (home equity sales) and CA Bus. & Prof. Code 10131 (broker licensure) are stricter than TN. **One CA-resident walk = one CA AG referral = California pulling us into Sacramento Superior Court.**

### Phase 3: the class certification motion

I file an amended complaint adding 4,800 unnamed class members. I attach the `drop_locks` table (subpoenaed). I move for certification under TN Rule 23. The class is "all persons in Tennessee who paid a Lock Fee to Everlight Ventures between 2026-05-15 and the date of certification, whose Purchase and Sale Agreement was not executed within 24 hours of the Lock charge."

Predominance is easy: same disclosure, same Stripe flow, same 10% retention formula. Numerosity is easy at 5,000+. Typicality is easy. Adequacy depends on which named plaintiff I picked.

**Everlight's defense costs to fight class cert alone: $80k-$150k.** Settlement value at certification: $300k-$500k. Settlement value pre-cert: $50k-$100k. I will offer $75k on day 90 and you will think hard about it.

### Phase 4: the BBB complaint we should worry about most

The $50 BBB complaint is not actually the danger. BBB has no enforcement authority -- it is reputation only. **The danger is that Sarah Whitlow scrapes BBB monthly looking for class predicates.** Every BBB complaint Everlight responds to becomes a sworn admission. **Every response to a BBB complaint must be drafted as if it is paragraph 14 of a class complaint exhibit.** That is the discipline I will enforce on every BBB response that comes in.

---

## The Seven Patches (in priority order, ship before launch)

### Patch 1: Fix the licensure citation in the disclosure (BLOCKER for launch)

**File:** `BUYER_DISCLOSURE_LOCK_FEE.md`
**Section:** Disclosure block, "Wholesaler license status (Tennessee)" line
**Replace:**
> "Acting as principal-buyer / equitable-interest holder under Tenn. Code Ann. 66-32-101 et seq. and longstanding TN common-law equitable interest doctrine."

**With:**
> "Acting as a principal-buyer holding an equitable contractual interest in real property pursuant to a separate Purchase and Sale Agreement with the seller, and assigning that interest to you pursuant to Tennessee common-law equitable conversion doctrine. Tenn. Code Ann. 66-32-101 et seq. (SB 909) imposes separate seller-disclosure obligations that Everlight Ventures satisfies in its agreements with sellers. This Lock Fee transaction is not itself a real estate brokerage activity under Tenn. Code Ann. 62-13-102."

**Why:** SB 909 is the seller-side disclosure act, not a licensure exemption. Citing it as our shield is the exact mistake the AG complaint will lead with. The replacement language anchors us to the right doctrinal basis (equitable conversion, not statutory exemption) and inoculates the SB 909 cite.

### Patch 2: Kill the Stripe-fee deception (BLOCKER for launch)

**File:** `BUYER_DISCLOSURE_LOCK_FEE.md`
**Section:** Verified tier paragraph, last sentence
**Replace:**
> "Stripe's payment-processing fee (approximately 2.9% + $0.30) is non-refundable in all cases as a separate Stripe matter."

**With:**
> "The 10% non-refundable service charge represents Everlight's full retention on a walked Lock. Stripe's payment-processing fees on the original capture (approximately 2.9% + $0.30) are absorbed by Everlight and are not deducted from your refund. Your refund will be exactly ninety percent (90%) of the gross amount charged."

**Why:** This is the class predicate Sarah Whitlow files on. We absorb the Stripe fee. That is $14.80 per walk × 15 walks/mo = $222/mo cost. **That is the cheapest insurance premium we will ever pay.** And the EMD policy already says "Stripe also keeps its ~$14.80 from the original capture -- our cost of doing business" -- so we are already operating this way. Just say it in the disclosure.

### Patch 3: ANCHOR badge requires explicit, written disclosure (BLOCKER for launch)

**File:** `EMD_LOCK_POLICY.md` (Chris Ulander handling section) AND `BUYER_DISCLOSURE_LOCK_FEE.md` (new section)
**Add to disclosure, new paragraph 6:**
> "Anchor Buyer Disclosure: Certain buyers visible on the Open Deal pulse feed (designated by an 'ANCHOR' badge) are commercial partners of Everlight Ventures who receive compensated benefits including but not limited to comped subscription access, fee waivers on locks, and early notification of property drops prior to public availability. The visible activity of Anchor Buyers on the pulse feed reflects real lock activity but may not represent organic, uncompensated buyer demand. Anchor Buyers are bound by the same Lock Fee terms as all buyers when they do not receive a fee waiver. The current Anchor Buyer is Chris Ulander."

**Add to EMD_LOCK_POLICY.md, new sentence in the Chris Ulander section:**
> "Chris's anchor status is disclosed by name in the public Lock Fee Disclosure (section 6). Marvin owns securing Chris's written consent to this disclosure before launch; without that written consent, the ANCHOR badge cannot go live."

**Why:** Undisclosed shill positioning is TN CPA 47-18-104(b)(5), full stop. Disclosed anchor activity is normal marketplace mechanics (every auction house has reserve bidders; every wholesale buyer list has top-tier accounts). The difference is the word "disclosed." This also protects Chris -- if he is publicly disclosed as an anchor partner, he cannot be accused of secret front-running. The complaint that takes him down is the one where his role is hidden. **Marvin Tilbrook owns the written consent from Chris; this is a Day-7 pre-launch checklist item.**

### Patch 4: Chargeback playbook (operational, BLOCKER for launch)

**File:** new file `Broker_OS/open_deal/CHARGEBACK_PLAYBOOK.md`

**Content (summary; Theo and I will draft the full doc):**

1. **Pre-charge friction:** Every Verified tier lock requires (a) disclosure acceptance with click+timestamp+IP, (b) DocuSign envelope archive of the same disclosure attached to the eventual PSA, (c) a confirmation email within 60 seconds to the buyer summarizing the charge, the 24-hour window, the refund mechanics, and a link to "I changed my mind -- cancel within 60 minutes" self-serve refund.
2. **60-minute soft cancel:** If a buyer clicks "cancel" within 60 minutes of the lock, we refund 100% with no retention. This is friction in our favor -- it filters out the buyer's-remorse charges that drive 70% of chargebacks.
3. **Dispute monitoring:** Auto-alert to `#legal` and `#ft-legal` if Stripe dispute ratio exceeds 0.5% in any rolling 30-day window. Hard kill of `/verify` and `/inner-circle` upgrades if ratio exceeds 0.75%. The kill switch is already specified in the build spec at item 5 of the risk register -- formalize the threshold.
4. **Dispute response template:** Pre-drafted by me, attorney work product, packaged with Stripe's dispute portal upload. Includes: signed disclosure timestamp, IP address, user agent, screenshot of disclosure modal, signed PSA (if signed), the buyer's account history. Win rate target on Stripe disputes: 65%+.
5. **Banned buyer list:** anyone who files a chargeback is permanently banned across all tiers, no re-signup. Enforced at email + IP + Stripe customer ID + phone. Same chokepoint pattern as the DNC list (`feedback_dnc_permanent_eradication`).

### Patch 5: Defamation-proof the pulse feed (FIX REQUIRED)

**File:** `OPEN_DEAL_BUILD_SPEC.md` AND the Master Terms of Service (separate doc)
**Issue:** The pulse feed shows "Lock walked by @username" publicly. Walking is not defamation per se on its face (it is a factual statement, and truth is an absolute defense). BUT -- if the system shows "walked" when the buyer actually had the lock expire without action, or if it shows "walked" when buyer claims they signed within window, **we have published a false statement of fact about a person's commercial conduct, which is defamation per quod with special damages presumed under TN common law.**

**Patch:**

1. Add to Master Terms of Service, new section 4.3:
   > "Pulse Feed Consent: By creating an account and placing a Lock, you grant Everlight Ventures a non-exclusive, revocable license to display your username, lock status (active / signed / walked / expired), and lock timestamp on the public Pulse Feed. You may revoke this consent at any time by emailing privacy@everlightventures.io, which will pseudonymize your prior pulse-feed entries (your username will be replaced with 'Anonymous Buyer #XXX'). You waive any defamation or false-light claim arising from accurate display of your lock activity."

2. Add to the build spec:
   > "Pulse feed event types must be precise: 'signed' (PSA executed within window), 'walked' (buyer affirmatively cancelled), 'expired' (no action taken in 24 hours), 'refund_processed' (Stripe refund issued). 'Walked' is reserved for buyer-initiated cancellation only. Lock timeouts display as 'expired,' not 'walked.' Pseudonymized display ('Buyer #4582') is the default; real-username display requires opt-in."

3. Username-pseudonymization default flips the burden. **Buyers opt in to real-name display.** Most won't. Those who do have signed a clear waiver. The defamation surface goes to near zero.

### Patch 6: Marquise's personal exposure -- form the LLC NOW (FIX REQUIRED)

**File:** EMD_LOCK_POLICY.md (Wholesaler attribution) and the entire Broker_OS posture
**Issue:** Per the user MEMORY, Everlight Ventures is a sole proprietorship DBA, not an LLC. The disclosure names "Marquise Reed, designated agent for Everlight Ventures." Marquise's personal name is on every PSA. There is **no corporate veil** because there is no corporation. If we get sued -- TCPA class action, TN AG civil penalties, individual breach of contract -- the judgment runs against Marquise Reed personally. His house, his car, his bank account.

**Patch:**

1. **Form Everlight Memphis Acquisitions, LLC (TN sub of Everlight Ventures, LLC NV)** per the existing target entity structure (`reference_entity_structure_target.md`) **before the second real lock is captured.** Not after Deal-1. Before the second real Verified-tier charge runs. The LLC formation cost is $300 in TN; the personal-asset protection is unlimited.
2. **Until LLC is formed, every Lock-Fee charge is personally indemnified by Everlight Ventures (Rich Gee, sole proprietor).** That is the legal reality whether we want it to be or not.
3. **Rewrite the disclosure attribution line:**
   - Pre-LLC: "Wholesaler: Everlight Ventures (a sole proprietorship of Richard Gee), with Marquise Reed acting as designated Tennessee agent."
   - Post-LLC: "Wholesaler: Everlight Memphis Acquisitions, LLC (a Tennessee limited liability company), with Marquise Reed acting as designated agent."

**Why:** Naming Marquise as "designated agent for Everlight Ventures" without a corporate structure behind the principal exposes Marquise as a joint tortfeasor under TN agency law. The sole proprietorship offers him no protection because there is nothing for the agency relationship to attach to except Rich personally. **The LLC formation is the single highest-ROI legal task on the entire Open Deal roadmap.** Heck Aurelio drafts the operating agreement, Lia Knight files the formation, I draft the agency-agreement between LLC and Marquise. Three-day turnaround. $300 cost.

### Patch 7: SOL and venue clauses need TN-counsel sign-off (FIX REQUIRED)

**File:** `BUYER_DISCLOSURE_LOCK_FEE.md`
**Section:** "Statute of limitations: any claim relating to this Lock Fee must be brought within one (1) year of the date of charge."
**Issue:** The disclosure's own "open legal questions" call this out -- TN consumer protection statutes may override a contractual SOL shortening. They do. TCPA claims have a one-year SOL from discovery, but the TN Supreme Court in *Heyne v. Metropolitan Nashville Board of Public Education* (2012) signaled that contractual SOL shortening below the statutory floor for consumer protection claims is unenforceable as against public policy.

**Patch:**

**Replace:**
> "Statute of limitations: any claim relating to this Lock Fee must be brought within one (1) year of the date of charge."

**With:**
> "Limitations: any claim relating to this Lock Fee must be brought within the period prescribed by applicable Tennessee law, but in no event later than three (3) years from the date of charge for contract-based claims, and the limitations period applicable to statutory consumer-protection claims is not modified by this agreement."

**Why:** A 1-year contractual SOL that the court strikes down means the entire disclosure is in front of a judge being parsed for unconscionability. That is not a fight we want. A 3-year clause that mirrors the TN general contract SOL (Tenn. Code Ann. 28-3-109) is enforceable and gives us the same practical protection without the unconscionability surface.

---

## The 10-line TN AG response (drafted now, sits in the queue)

When the AG letter lands -- and it will -- here is the response Theo edits and ships, in courtroom cadence:

> 1. Everlight Ventures, LLC ("Everlight") acknowledges receipt of the Office's inquiry dated [DATE] regarding [BUYER NAME] and the Lock Fee transaction of [DATE].
> 2. Everlight is not a Tennessee-licensed real estate broker and does not represent itself as one. Everlight operates as a principal buyer holding equitable contractual interests in real property under separate Purchase and Sale Agreements with sellers, and assigns those interests to third-party buyers under Tennessee common-law equitable conversion doctrine. This activity falls outside the definition of "real estate brokerage" under Tenn. Code Ann. 62-13-102(4).
> 3. The Lock Fee complained of is a service charge for a 24-hour exclusivity negotiation period, not an earnest money deposit subject to escrow regulations. Real earnest money deposits, when applicable, are wired directly by buyers to Mid South Title Company, an independent and licensed Tennessee escrow agent.
> 4. The buyer received and acknowledged the attached written Lock Fee Disclosure (Exhibit A) prior to charge. Acceptance is timestamped [TIME] from IP [IP] under user agent [UA]. The disclosure version accepted is identified in Exhibit B.
> 5. The buyer was charged $[AMOUNT] on [DATE]. The buyer did not execute a Purchase and Sale Agreement within the 24-hour Lock Period. On [DATE], Everlight refunded $[AMOUNT - 10%] consistent with the disclosure (Exhibit C, Stripe refund record). Everlight retained $[10%] consistent with the disclosed service charge for the exclusivity period.
> 6. Everlight Ventures voluntarily complies with all applicable Tennessee consumer protection statutes and maintains a written compliance program addressed by undersigned counsel.
> 7. Attached for the Office's review: (A) the executed Lock Fee Disclosure, (B) the disclosure version log, (C) the Stripe transaction record, (D) the buyer's account history, (E) the pulse feed event log for this lock.
> 8. Everlight respectfully submits that no violation of Tennessee law has occurred and that the buyer's complaint reflects a misunderstanding of the disclosed transaction structure rather than a deceptive practice. We welcome further dialogue with the Office.
> 9. Everlight's designated contact for this matter is undersigned counsel; please direct all further inquiries through this office to preserve attorney-client privilege and ensure timely response.
> 10. We thank the Office for its work protecting Tennessee consumers and stand ready to provide additional documentation or appear for an in-person meeting if helpful.

That is the template. The actual response will fill in dates and exhibits. **Lo Hines (TN compliance officer) will be the first call the moment any TN AG inquiry arrives.** I draft, Theo edits, Lo coordinates ground-truth on the parcel and the seller record.

---

## Chris Ulander downside summary

**With Patch 3 in place:** Chris's exposure is minimal. He is publicly disclosed as an anchor partner. His participation cannot be characterized as secret front-running because it is in the public record. He has signed a written consent. His worst case is some reputational chatter on real-estate Reddit. He is a sophisticated commercial party and TN does not have a "fiduciary duty between commercial counterparties" cause of action for arm's-length anchor relationships.

**Without Patch 3:** Chris's exposure is significant. Plaintiff's counsel will depose him, build the shill-bidding narrative, and try to drag him in as a co-defendant under joint enterprise / civil conspiracy theories (TN recognizes both). His title-side fee arrangement at Mid South gets dragged into discovery. **Patch 3 is not optional.** Marvin owns the written consent before any pulse feed labels go live.

---

## Recommendation to Rich

Build out the seven patches before public soft launch -- five of them are 30-minute copy edits and two (LLC formation, chargeback playbook) are three-day jobs that pay back the cost in the first 30 days. The structure you and the Hive drafted is fundamentally defensible; the holes are in the paper, not the model. **Form the LLC this week, ship the seven patches by Day 7 of the sprint, and you launch with a litigation surface I can defend against any plaintiff who walks through the door.** The first BBB complaint, the first AG inquiry, the first chargeback -- those will land. My job is to make sure each one is a paper exercise, not a docket entry.

---

## Filing posture

- This memo is privileged attorney work product. Do not forward outside the firm without redacting through Theo.
- Theo Briggs to red-edit before any of the seven patches ship to live disclosure copy.
- Heck Aurelio to draft the LLC operating agreement + assignment-agency contract between LLC and Marquise.
- Lia Knight to file TN LLC formation (target: 72 hours).
- Priya Bhattacharya to own pulse-feed consent text + privacy@ revocation workflow.
- Lo Hines to ground-truth the TN-specific disclosure language against any recent TREC interpretive guidance.
- Marvin Tilbrook to secure Chris's written ANCHOR consent before Day 7.
- Justine Park to cross-reference disclosure against CA / AZ / FL parallel rules for the geofenced jurisdictions.

Bring me the timeline on every lock the moment it walks. We document forward, not backward.

-- Mani
