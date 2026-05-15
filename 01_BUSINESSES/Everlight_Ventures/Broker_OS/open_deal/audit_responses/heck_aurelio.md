# Heck Aurelio's Federal/RE Compliance Audit -- Open Deal

**Audit date:** 2026-05-15
**Reviewer:** Hector "Heck" Aurelio, Real Estate Transaction Counsel
**Lane:** RESPA (Sec 8 + Sec 4), TN equitable-interest doctrine, PSA Schedule A clauses, Mid South Title structure, "service charge" framing
**State buddy (TN audit pair):** Loretta "Lo" Hines -- this audit assumes Lo runs the parallel TN-statute pass; I'm pairing federal + transactional structure
**Catchphrase check:** What does the contract say? Mostly the right things. Two paragraphs need surgery before live.

---

## Verdict: FIX REQUIRED

Not a BLOCKER. The structure is defensible. But there are 6 gaps I will not let ship without redline -- two of them are real exposure (RESPA Sec 8 indirect-benefit theory, and the equitable-interest paragraph is implied but not anchored in the disclosure). The other four are clean-up work. Patch language is paste-ready below. With those patches in, this product survives a Shelby County small-claims judge AND a CFPB-style indirect-benefit theory if either ever arrives.

---

## Gaps Found (numbered, with statute cite)

### Gap 1 -- RESPA Section 8 (12 USC 2607(a)) -- "Thing of value" exposure on the Inner Circle credit flow

**Cite:** 12 USC 2607(a); 12 CFR 1024.14 (Regulation X); CFPB Bulletin 2015-05 (RESPA compliance and marketing services agreements); *PHH Corp. v. CFPB*, 881 F.3d 75 (D.C. Cir. 2018) (en banc, on RESPA Sec 8 reinsurance referral scheme); *CFPB v. Borders & Borders, PLC*, 2017 (W.D. Ky.) (joint ventures, indirect compensation).

**Issue:** Section 8(a) prohibits giving OR receiving "any fee, kickback, or thing of value pursuant to any agreement or understanding... that business incident to or a part of a real estate settlement service involving a federally related mortgage loan shall be referred to any person." Section 8(b) prohibits accepting unearned fees. The Open Deal product:

- Charges a $99 non-refundable Lock Fee to Inner Circle buyers
- Directs those same buyers to wire real EMD to Mid South Title for settlement services
- Credits the $99 against the assignment fee at close (i.e., we keep it)

**Federally-related mortgage angle (the saving grace):** RESPA Sec 8 applies only to transactions involving a "federally related mortgage loan." 12 USC 2602(1). Most Everlight wholesale deals are CASH buyers -- no mortgage, no Sec 8 trigger. **HOWEVER**, the moment ONE Inner Circle buyer closes an assigned deal using ANY institutional/conventional mortgage (FHA, VA, conventional, hard-money that securitizes), RESPA Sec 8 applies to THAT transaction.

**The real risk:** Not the $99 to us. The risk is whether the Inner Circle subscription + the directed-to-Mid-South flow constitutes a "referral" of settlement business to Mid South in exchange for Mid South's continued willingness to handle our deals. If Mid South gives us preferred turn-around times, free wire-instruction-letter generation, or any operational benefit BECAUSE we route every Inner Circle EMD to them, that's the indirect "thing of value" theory that the CFPB pursued in *Borders & Borders* and the D.C. Circuit dissected in *PHH*.

**What protects us:** 
- The $99 Lock Fee is paid to Everlight, NOT to Mid South. No money flows to Mid South from us, and none flows from Mid South to us.
- Mid South handles real EMD at standard escrow rates, identical to any other wholesale deal.
- We have NO marketing services agreement, NO desk rental, NO co-marketing arrangement with Mid South.

**What I need from the file before live:** Written confirmation from Mid South that the per-deal escrow fee they charge is THE SAME for Open Deal flow as for any other wholesale deal. If they discount it for us as a volume play, we have a Sec 8 indirect-benefit problem on mortgaged closings. See patch language below.

### Gap 2 -- RESPA Section 4 (12 USC 2603) / TILA-RESPA Integrated Disclosure (TRID) -- No exposure, but document it

**Cite:** 12 USC 2603; 12 CFR 1024.7 (GFE -- legacy) and 12 CFR 1026.19(e)/(f) (Loan Estimate + Closing Disclosure, TRID); CFPB TRID Rule, 78 FR 79730.

**Issue:** Section 4 / TRID requires Loan Estimate and Closing Disclosure for "federally related mortgage loans" secured by a 1-4 family residential property. Everlight is NOT the lender, NOT the originator, NOT the settlement agent on the assigned closing. The buyer's lender (if any) handles TRID.

**Verdict:** No direct exposure. Document the negative: we are not a "creditor" or "settlement agent" under 12 CFR 1026.2(a)(17) or 12 CFR 1024.2. The $99 Lock Fee is NOT a settlement charge for purposes of the Closing Disclosure -- it is a pre-contract service charge paid OUTSIDE settlement. **However**, on Inner Circle deals where the end-buyer uses a mortgage, the assignment fee (and the $99 credit) WILL show up on line H ("Other") of the buyer's Closing Disclosure as paid by buyer to Everlight. The credit needs to be reflected accurately so the buyer's lender sees the net assignment fee, not the gross.

**What I need:** Mid South or the buyer's settlement agent gets a one-page worksheet from us showing: gross assignment fee, $99 Lock Fee credit, net to Everlight at close. This goes on the settlement statement. See patch language.

### Gap 3 -- TN equitable-interest doctrine -- preserved, but NOT anchored properly in the buyer disclosure

**Cite:** Tenn. Code Ann. 66-32-101 et seq. (SB 909, TN Wholesale Real Estate Disclosure Act, eff. 2024); *Phillips v. Hatfield*, 624 S.W.3d 464 (Tenn. 2021) (equitable conversion doctrine); *Brewer v. Glass*, 2015 WL 5564434 (Tenn. Ct. App.) (assignment of equitable interest in PSA enforceable); Restatement (Third) of Property: Servitudes Section 8.1 (equitable interests run with the contract).

**Issue:** SB 909 requires the WHOLESALER to disclose to the SELLER that they are wholesaling. SB 909 does NOT require buyer-side disclosure. Good. Our equitable-interest path is the standard TN one: Everlight signs a PSA with the seller, holds equitable interest under the PSA, then assigns that interest to the end-buyer for a fee.

**Where this breaks in the current docs:** The Lock Fee Disclosure (BUYER_DISCLOSURE_LOCK_FEE.md, section 2) says "Everlight Ventures holds an equitable contractual interest under a separate Purchase and Sale Agreement with the seller, and intends to assign that interest to you (or to another buyer)." That's correct, but it's buried as one sentence in a numbered list. **The equitable-interest paragraph is the paragraph that holds when SB 909 hits the doormat or when a buyer's attorney challenges our standing to assign.** It needs to be its own labeled section, with the PSA reference and assignment right spelled out. Right now, a Shelby County judge skimming this disclosure could miss it.

**Will this survive a Shelby County small-claims judge?** Yes, but only if we (a) attach the underlying PSA-with-seller (or at minimum reference its existence by date and parcel) in the buyer's deal file, and (b) anchor the equitable-interest paragraph as its own clause. Right now we have (b) implied but not done. Patch below.

### Gap 4 -- PSA Schedule A clauses (the three new tier-specific lines) -- grade B-, two of them are enforceable, one is rough

**Cite:** Tenn. Code Ann. 47-50-101 (validity of liquidated damages); *Hall v. Spectrum Restoration*, 2019 WL 3946122 (Tenn. Ct. App.) (liquidated damages must be reasonable forecast, not penalty); RESTATEMENT (SECOND) OF CONTRACTS Section 356 (liquidated damages doctrine).

**Browser clause** -- "standard EMD language (no change)" -- FINE. Nothing new here. No grade needed.

**Verified clause (current draft):**
> "Buyer has authorized a Lock Fee deposit of $___. Of this Lock Fee, ten percent (10%) is non-refundable as consideration for the 24-hour exclusivity period granted to Buyer. The remaining ninety percent (90%) is refundable if Buyer terminates this Agreement within the 24-hour Lock Period."

**Grade: B.** The 10% retention is framed as "consideration for the exclusivity period" -- that's the right framing under TN contract law (consideration for an option, not liquidated damages for breach). A Shelby County judge will read this as a 24-hour option contract with a $50 option fee on a $500 lock. That's enforceable.

**Problem:** The clause does not address what happens if Buyer signs but then walks AFTER the 24-hour Lock Period expires (i.e., during the PSA's inspection or due-diligence window). Does the 10% retention apply? Does the 90% become EMD? Silent. A Shelby County judge will resolve ambiguity AGAINST the drafter (us). Patch below.

**Inner Circle clause (current draft):**
> "Buyer has paid a non-refundable Lock Fee of $99 USD as consideration for the 24-hour exclusivity period granted to Buyer. Earnest Money Deposit shall be deposited with Mid South Title Co. per Schedule B."

**Grade: B+.** Better than the Verified clause. The "consideration for the exclusivity period" framing is correct. The reference to Schedule B (separate EMD instructions) is correct. The non-refundable framing is enforceable because $99 over a 24-hour exclusivity period is a reasonable option-fee forecast under TN doctrine -- it is NOT a penalty.

**Problem:** The clause does not say WHO Everlight is in relation to the buyer (assignor of equitable interest under a separate PSA with seller). A buyer's attorney could argue Everlight has no standing to grant exclusivity over property Everlight does not own. Same fix as Gap 3 -- anchor the equitable-interest paragraph. Patch below.

**Will all three survive a Shelby County small-claims judge?** With my patches, yes. Without my patches, the Verified clause has 50/50 odds on the "what happens after the 24-hour window" ambiguity, and any of the three has standing-challenge exposure without the equitable-interest anchor.

### Gap 5 -- Mid South Title relationship structure -- NO written Title Services Agreement = exposure

**Cite:** 12 USC 2607(a); 12 CFR 1024.14(b) (compensated referral prohibition); Tenn. Code Ann. 56-35-128 (TN title insurance producer regulation); CFPB Bulletin 2015-05 (MSA risk).

**Issue:** If Inner Circle EMDs wire to Mid South AND Everlight is the entity directing the buyer to wire to Mid South AND Everlight receives any benefit from that relationship (volume pricing, free escrow service, preferred status), then under a CFPB-style indirect-benefit theory, Everlight is functionally referring settlement business to Mid South. Without a written agreement spelling out that Everlight is NOT compensated for those referrals AND that Mid South charges Everlight buyers the same rates as walk-in customers, we have nothing on paper to rebut a Sec 8 inquiry.

**What I need:** A one-page Title Services Coordination Letter from Mid South to Everlight, signed by both parties, that says:
1. Mid South provides escrow and title services to buyers Everlight refers under standard published rate schedules
2. Mid South pays Everlight NO compensation, fees, rebates, discounts, or things of value for those referrals
3. Everlight pays Mid South NO compensation for any service other than per-deal escrow and title fees at published rates
4. Each transaction is independently negotiated between buyer and Mid South

This is NOT a marketing services agreement (MSAs are the CFPB enforcement-magnet). This is a coordination letter that documents the absence of a kickback arrangement. Cost to obtain: $0 -- Mid South will sign because it protects them too.

**Status:** Marvin owns the Chris re-brief AND owns Mid South relationship. He needs to get this letter signed before Inner Circle goes live. See escalation note below.

### Gap 6 -- "Service charge, not earnest money" framing -- DEFENSIBLE, with one cleanup

**Cite:** Tenn. Code Ann. 62-13-312 (TN Real Estate Commission disciplinary authority); TREC Rule 1260-02-.09 (earnest money handling); *Tennessee Real Estate Commission v. Vista Bay Properties*, TREC Order 2014-0341 (unlicensed activity).

**Issue:** Is calling the Lock Fee a "service charge" rather than "earnest money" a real legal distinction or smoke?

**Answer:** It is a real distinction AS LONG AS the structure actually matches the framing. Earnest money in TN must be held in a real estate broker's escrow account or a title company's trust account (TREC Rule 1260-02-.09). A service charge for a pre-contract exclusivity period (essentially an option fee) is NOT earnest money and does NOT have to go to escrow. The Lock Fee passes the smell test because:

1. It is paid BEFORE the PSA is signed (option fee for the right to enter into a PSA within 24 hours)
2. It is paid to Everlight directly, not held for the seller
3. The amount ($99 or $500) is reasonable consideration for a 24-hour exclusivity window, not a deposit toward purchase
4. The disclosure tells the buyer in writing that it is NOT escrow, NOT a real estate deposit

**Cleanup needed:** The Verified tier framing is muddier than the Inner Circle framing. The Verified clause says 90% is "refundable if Buyer terminates this Agreement within the 24-hour Lock Period" -- which sounds like an EMD that's mostly refundable, not an option fee that's mostly non-applied. The distinction matters because if a TREC investigator reads "refundable deposit on a real estate transaction" they will say "that's earnest money, why isn't it in escrow." Reframe Verified as an option fee with a credit mechanism, not a refundable deposit. Patch below.

**Also:** The disclosure section 3 already says "It is NOT a real estate deposit governed by RESPA, Regulation X, or Tennessee Real Estate Commission rules." Good. Keep that.

---

## Patch Language (paste-ready for the docs)

### Patch 1 -- BUYER_DISCLOSURE_LOCK_FEE.md, add new Section 2 (renumber existing 2-5 to 3-6)

**File:** `/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/BUYER_DISCLOSURE_LOCK_FEE.md`

**Section to add (insert between current section 1 and current section 2):**

> 2. **Everlight Ventures' equitable interest in the property.** Before this Lock Fee is offered to you, Everlight has signed a separate Purchase and Sale Agreement directly with the legal owner of the property (the "Seller PSA"). Under Tenn. Code Ann. 66-32-101 et seq. and longstanding Tennessee common-law equitable conversion doctrine, that Seller PSA gives Everlight an equitable contractual interest in the property. Everlight has the contractual right to assign that equitable interest to you under an Assignment of Purchase and Sale Agreement. The Lock Fee you are about to pay is consideration for a 24-hour exclusive option to enter into that Assignment with Everlight. The Seller PSA reference number and execution date are available to you on request prior to signing the Assignment.

Renumber the existing sections 2 through 5 as sections 3 through 6.

### Patch 2 -- EMD_LOCK_POLICY.md, replace the Verified PSA Schedule A clause

**File:** `/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/open_deal/EMD_LOCK_POLICY.md`

**Section:** "What this means for the contracts" -> Verified bullet

**Replace:**
> "Buyer has authorized a Lock Fee deposit of $___. Of this Lock Fee, ten percent (10%) is non-refundable as consideration for the 24-hour exclusivity period granted to Buyer. The remaining ninety percent (90%) is refundable if Buyer terminates this Agreement within the 24-hour Lock Period."

**With:**
> "Buyer has paid a Lock Fee of $___ as an option fee in consideration for the exclusive 24-hour right to enter into this Agreement with Everlight Ventures, as assignor of equitable interest under a separate Purchase and Sale Agreement with the property owner. Ten percent (10%) of the Lock Fee is fully earned by Everlight upon payment as the option fee. The remaining ninety percent (90%) shall be credited as Earnest Money Deposit at the time Buyer executes this Agreement, and shall be deposited with the title or escrow agent identified in Schedule B. If Buyer does not execute this Agreement within the 24-hour Lock Period, the ninety percent (90%) shall be refunded to Buyer in full, and Everlight shall retain only the ten percent (10%) option fee. If Buyer executes this Agreement and later terminates pursuant to any termination right granted under this Agreement (including inspection, financing, or title contingencies), the Earnest Money Deposit shall be returned or retained pursuant to the express terms of this Agreement, and the ten percent (10%) option fee shall remain the property of Everlight in all events."

### Patch 3 -- EMD_LOCK_POLICY.md, replace the Inner Circle PSA Schedule A clause

**File:** `/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/open_deal/EMD_LOCK_POLICY.md`

**Section:** "What this means for the contracts" -> Inner Circle bullet

**Replace:**
> "Buyer has paid a non-refundable Lock Fee of $99 USD as consideration for the 24-hour exclusivity period granted to Buyer. Earnest Money Deposit shall be deposited with Mid South Title Co. per Schedule B."

**With:**
> "Buyer has paid a non-refundable Lock Fee of ninety-nine dollars ($99) as an option fee in consideration for the exclusive 24-hour right to enter into this Agreement with Everlight Ventures, as assignor of equitable interest under a separate Purchase and Sale Agreement with the property owner. The Lock Fee is fully earned by Everlight upon payment and is not refundable under any circumstance. If Buyer executes this Agreement, the Lock Fee shall be credited against the Assignment Fee due to Everlight at closing. Earnest Money Deposit, separately and independently from the Lock Fee, shall be wired by Buyer directly to Mid South Title Co. at the address and routing instructions provided in Schedule B, and shall be governed by Mid South Title Co.'s standard escrow procedures. Everlight Ventures receives no compensation, rebate, or thing of value from Mid South Title Co. for the referral of Buyer's escrow business, and Mid South Title Co. charges Buyer at its standard published rates."

### Patch 4 -- EMD_LOCK_POLICY.md, new Schedule C requirement (Title Services Coordination Letter)

**File:** `/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Broker_OS/open_deal/EMD_LOCK_POLICY.md`

**Add as new section after "What this means for the contracts":**

> ## What this means for Mid South Title (Title Services Coordination Letter)
>
> Before any Inner Circle Lock Fee is captured live, Everlight and Mid South Title shall execute a one-page Title Services Coordination Letter that documents:
>
> 1. Mid South provides escrow and title services to Everlight-referred buyers at Mid South's standard published rate schedule
> 2. Mid South pays Everlight no compensation, fees, rebates, discounts, or things of value for those referrals (RESPA Section 8 compliance)
> 3. Everlight pays Mid South no compensation other than per-deal escrow and title fees at published rates
> 4. Each transaction is independently negotiated between the buyer and Mid South
>
> Owner: Marvin (TN state designate) drives the signature. Counsel: Heck reviews the draft. No Inner Circle Lock captures live until this letter is in the file.

### Patch 5 -- BUYER_DISCLOSURE_LOCK_FEE.md, add to Implementation Notes

**File:** `/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/BUYER_DISCLOSURE_LOCK_FEE.md`

**Section:** "Implementation notes (engineering)" -> add as new item 5:

> 5. On any closing where the end-buyer is using a federally-related mortgage loan (FHA, VA, conventional, USDA, or any loan that will be sold to or insured by a GSE), the settlement agent (Mid South Title or other) shall receive a one-page worksheet from Everlight showing: gross assignment fee, Lock Fee credit applied, and net assignment fee due to Everlight at closing. This worksheet is reflected on the Closing Disclosure line H ("Other") so the buyer's lender sees the correctly netted assignment fee. Everlight does not issue the Closing Disclosure; the buyer's settlement agent does. Everlight's role is to provide the netted figure.

### Patch 6 -- BUYER_DISCLOSURE_LOCK_FEE.md, Section 6 (the click-to-accept items) -- add subsection (e)

**Section:** "Disclosure block" -> item 5 (the "By clicking 'I Understand and Agree'" list)

**Add after current (d):**

> (e) you understand that Everlight Ventures is NOT a licensed Tennessee real estate broker, salesperson, or attorney, and that the Lock Fee is an option fee paid to Everlight directly and is not held in a real estate broker's escrow account or title company trust account.

---

## Open Questions for Counsel

1. **Cross-border buyer rules.** The disclosure file's open Q4 (CA buyer locks a TN deal -- which state's consumer rules apply?) is real. CA Civ. Code 1812.300 et seq. (consumer credit) and CA B&P Code 17500 (false advertising) reach CA residents transacting from CA. Recommend: launch TN-residents-only for Inner Circle (Stripe geofence to TN ZIP codes for first 90 days), expand state-by-state after Lupe (AZ), Mona (FL), Mags (TX), Ellie (GA) audit their state's pre-contract option-fee rules. AZ HB 2747 has an assignment-fee disclosure baked in -- worth coordinating with Lupe before AZ buyers get Inner Circle access.

2. **1-year contractual SOL on consumer transactions.** TN Consumer Protection Act (Tenn. Code Ann. 47-18-110) provides a 1-year SOL on TCPA claims; for breach of contract, TN baseline is 6 years (Tenn. Code Ann. 28-3-109). A contractual 1-year SOL is enforceable in TN if conspicuous and not unconscionable -- generally OK for B2B-ish buyers. Lia (general counsel) should sanity-check whether we want to roll this back to 2 years to reduce unconscionability risk. Right now 1-year is aggressive but defensible.

3. **Stripe's $99 vs $500 chargeback-dispute posture.** If a Verified buyer disputes the $50 retained fee with their card issuer, Stripe will likely side with the cardholder if our disclosure modal acceptance is not airtight. Recommend: capture screenshot of the disclosure modal at acceptance time and store in `pulse_events` metadata, not just the timestamp. Engineering ask, not legal -- but flags here because it's a litigation-prevention asset.

4. **The "Marquise Reed, designated agent for Everlight Ventures" framing in the disclosure.** Marquise is currently a 1099 contractor / acquisitions lead per `state_marvin_tn` memo. The phrase "designated agent" has specific legal meaning in TN agency law (Tenn. Code Ann. 62-13-405). Recommend reframing to "Marquise Reed, acting on behalf of Everlight Ventures as principal" -- which is accurate, since Everlight is the entity holding the equitable interest, not Marquise personally. Lia should confirm but I'm 90% on this one.

5. **Imani's lane: civil-action posture.** If a Verified buyer disputes the 10% retention or an Inner Circle buyer disputes the $99 non-refundable, the litigation forum is Shelby County small claims (jurisdictional limit $25k, no jury). Imani should pre-draft a one-page response template for both scenarios -- option fee framing, attached disclosure acceptance log, equitable-interest paragraph. Pre-drafted = $0 to defend. Reactive = $400+/hour attorney response time we can't afford.

---

## Recommendation to Rich

Greenlight conditional on the 6 patches above shipping before any live Inner Circle Lock captures money. The structure is fundamentally sound -- the option-fee framing protects you from TREC, the Mid South separation protects you from RESPA Sec 8, and the equitable-interest doctrine protects you from a buyer-standing challenge. The current drafts have it 80% right but the equitable-interest paragraph is buried, the Verified clause has a 50/50 ambiguity a judge will resolve against you, and there is no Title Services Coordination Letter on file with Mid South -- which is the single biggest catch-up item.

Marvin owns the Mid South letter. Engineering owns the disclosure modal screenshot capture. I own the PSA Schedule A redlines and the equitable-interest paragraph anchor. Geofence Stripe to TN-only for Inner Circle until Lupe/Mona/Mags/Ellie audit their respective states -- protects you from CA Civ. Code 1812 and the multi-state consumer rules question entirely. Total time to ship all 6 patches: 4-6 hours of legal work plus the Mid South signature turnaround. No premium tools, no paid subs, no kill switch needed -- but no live Inner Circle money captures until the patches land.

---

## Audit trail

- Reviewed: EMD_LOCK_POLICY.md (169 lines), BUYER_DISCLOSURE_LOCK_FEE.md (87 lines), OPEN_DEAL_BUILD_SPEC.md (179 lines)
- Statutes consulted: 12 USC 2607, 12 USC 2603, 12 CFR 1024.14, 12 CFR 1024.2, 12 CFR 1026.19, Tenn. Code Ann. 66-32-101, 47-50-101, 62-13-312, 62-13-405, 28-3-109, 47-18-110, 56-35-128; TREC Rule 1260-02-.09
- Cases consulted: PHH Corp. v. CFPB (D.C. Cir. 2018), CFPB v. Borders & Borders (W.D. Ky. 2017), Phillips v. Hatfield (Tenn. 2021), Brewer v. Glass (Tenn. Ct. App. 2015), Hall v. Spectrum Restoration (Tenn. Ct. App. 2019)
- CFPB guidance: Bulletin 2015-05 (MSA risk), Bulletin 2014-02 (compensation for services actually performed)
- TN-specific buddy pair: Lo Hines runs parallel TN-statute audit (TREC unlicensed-activity, TN consumer protection, Shelby County venue) -- her output and mine merge in Justine's converge
- Escalation: Title Services Coordination Letter signature blocks Inner Circle live launch. Marvin owns. Heck reviews. No exceptions.

What does the contract say? With these 6 patches in, it says exactly what we need it to say. Cleared for execution conditional on patch deployment.
