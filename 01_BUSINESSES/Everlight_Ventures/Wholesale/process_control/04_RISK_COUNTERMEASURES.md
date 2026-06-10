# Risk Countermeasures + Backup Plans

For each named risk in the FARROW scenario: detection, prevention, contingency, walk-trigger.

---

## Risk 1: Estate not closed in probate -- heir lacks signing authority

| Layer | Action |
|---|---|
| **Detection** | Day 0 -- Cipher MHTMLs Shelby County Probate Court (probatedata.shelbycountytn.gov), searches decedent name. Status returns: open / closed / no-record. |
| **Prevention** | If status is OPEN with no court order to sell: do NOT proceed past pre-call email. Save lead to "probate-pending" queue, recheck monthly. |
| **PSA representation** | Add to PSA Section 5.1: "Seller represents and warrants that Seller has full legal authority to convey title to the Property. If Seller is acting as executor, administrator, trustee, or heir, Seller represents that all required court orders, letters of authority, and beneficiary consents are in place. Misrepresentation under this Section is a material breach permitting Buyer to terminate and recover EMD." |
| **Contingency** | If probate is open but heir says "I have authority" without proof: Hammer requests a copy of letters testamentary or court order before EMD is wired. No paper, no EMD. |
| **Walk trigger** | DD Section 4(g) covers this: "Seller authority not confirmed." |

---

## Risk 2: Phone outreach goes to voicemail loop, never connects

| Layer | Action |
|---|---|
| **Detection** | After 3 unanswered calls in 24 hrs spaced morning/midday/late-afternoon. |
| **Prevention** | Pre-call email (template 01) creates expectation -- owners more likely to pick up after seeing brand. |
| **Contingency cascade** | After 3 unanswered: drop Slybroadcast 12-second cold-intro VM (`voicemail/slybroadcast_drop.py`). Day 2: send personal follow-up email referencing the email + missed calls. Day 4: send "offer holds 7 more days" email. Day 11: lead drops to dead-cold. |
| **Backup channel** | Public LinkedIn message (B2B) if owner has profile. Cold residential SMS BLOCKED in TN, ALLOWED in TX with prior consent only. |
| **Walk trigger** | 11 days no response = lead is dormant. Re-queue 90 days. |

---

## Risk 3: Seller pushes for higher offer

| Layer | Action |
|---|---|
| **Detection** | Live during the call -- Hammer hears "I want $X more" |
| **Prevention** | Penny pre-defines per-deal **opening / target / ceiling** before call: |
| | - Opening: 70% of buy-box max (room to flex up) |
| | - Target: 85% (where we close) |
| | - Ceiling: 100% of internal max (Penny's hard line) |
| **Contingency** | Hammer flexes within target -> ceiling without checking. At ceiling, pause: "Let me run the math one more time and call you back today." Calls Penny. Penny decides walk or expand. |
| **Backup** | If Penny expands ceiling, document why (deal value, lead quality, low-supply cohort). Adds 5% margin reduction max. |
| **Walk trigger** | At ceiling + seller still wants more: "I appreciate that, but our number's our number. The deal economics don't support more. If you change your mind, here's my email." Hammer doesn't budge. Most sellers come back within 48-72 hrs at our number. |

---

## Risk 4: Chris ghosts after PSA package sent (NO BACKUP BUYER PIPELINE)

This is currently the BIGGEST gap. Action item:

| Layer | Action |
|---|---|
| **Prevention -- BUILD NOW** | TODAY: Penny + Hammer scout 5 backup Memphis cash buyers from: |
| | (a) Memphis REIA member directory |
| | (b) Connected Investors Memphis filter |
| | (c) BiggerPockets investor profiles "Memphis cash buyer" |
| | (d) PropStream.com free trial -- export Memphis investor list |
| | (e) Recent cash sales from Shelby Register of Deeds (find LLC names with 3+ Memphis purchases in last 12 months) |
| **Backup buyer file** | Save to `buyers/buyers_db.json` with: name, email, phone, buy box (zips, type, price range, condition), preferred terms, response-time SLA. |
| **Detection** | Chris >36 hrs silent after package sent (his standard is 24-48 hr). |
| **Contingency** | Hour 36: Hammer pivots to backup buyer #1. Same package, replacement subject line: "Memphis off-market deal -- 117 Farrow -- contracted, EMD on file." Backups get a 24 hr decision window. |
| **Walk trigger** | If no buyer signs by Day 13 of DD: Hammer terminates per DD 4(f) ("Buyer unable to confirm assignee"). EMD returns. We don't lose money. |
| **Long-term** | Aim for 5-buyer rotation. Each new deal gets first-call to whoever's on rotation (round-robin), with the others as backup. |

---

## Risk 5: Title finds lien / cloud during DD

| Layer | Action |
|---|---|
| **Detection** | Mid-South Title runs title search Day 5-7 of DD. Returns: exceptions list (mortgage, IRS lien, mechanic's lien, code enforcement, easement, judgment). |
| **Threshold** | Most liens under 30% of buyer-side price are payable out of buyer-side proceeds at close (lien holder paid by title firm before seller gets net). |
| **Decision matrix** | |
| | - Lien <= 15% of buyer price: silently absorb out of seller's net. Don't tell seller. |
| | - Lien 15-30%: tell seller "title found a $X lien, has to come out of your net. New net to you: $Y. Still want to close?" |
| | - Lien 30%+: walk per DD 4(a). |
| | - Lien is non-monetary (boundary dispute, easement we can't accept): walk per DD 4(a) or 4(b). |
| **Common Memphis liens** | IRS lien (fixed, payable), Shelby County code enforcement ($1-3k), former mortgage not cleared (need release), mechanic's lien (rare on vacant). |
| **Walk trigger** | DD Section 4(a): "Title cloud unresolved." |

---

## Risk 6: Wire delay or BEC fraud attempt

This is the criminal-attack risk. RE wholesale wires are #1 BEC target.

| Layer | Action |
|---|---|
| **Prevention -- pre-wire** | Shield + Carlos run BEC checklist 48 hrs before close: |
| | - Buyer's wire instructions verified by call to Mid-South on a number from Mid-South's website (NOT from any email) |
| | - Last 4 of routing read back to named title agent, timestamped |
| | - Voided check + W-9 for "Richard Gee d/b/a Everlight Ventures" sent 48 hrs before close to lock name match |
| | - Penny + Hammer NEVER touch buyer funds. Direct wire buyer to title escrow. |
| **Detection** | Any of these = STOP wire: |
| | - Email-only change to wire instructions in last 24 hrs ("our bank account changed, here's the new one") |
| | - Title firm staff sounds different on phone than usual |
| | - Routing numbers don't match prior verified call |
| | - Domain spoofing on Mid-South emails (midsouthtitle.com vs midsouth-title.com) |
| **Contingency** | If suspicion: pause wire 24 hrs. Re-verify via fresh phone call. Loop in Mid-South branch manager directly. |
| **Walk trigger** | Confirmed BEC attempt = stop close, terminate per DD or post-DD via fraud-induced material adverse change. Report to FBI IC3 (ic3.gov). |
| **Insurance** | Once we have $5k+, add BEC fraud coverage to general business policy. Sole prop = exposed personally now. |

---

## Risk 7 (NEW -- not in original list): Seller dies during DD

Estate-of-decedent leads have an extra wrinkle: if the heir signing dies between PSA and close, deal can stall in re-probate.

| Layer | Action |
|---|---|
| **Prevention** | If sole heir signing: include "Successor and Heir" clause: "This Agreement binds Seller's heirs, executors, and successors. If Seller is the sole heir of an estate, this Agreement survives their incapacity or death." |
| **Detection** | Mid-South Title catches at closing when they request signed deed. |
| **Contingency** | If heir incapacitated before close: PSA re-extends, executor or new heir signs. We're the buyer either way. |
| **Walk trigger** | Probate re-opening on heir's estate would cause >30 day delay -- DD termination. |

---

## Risk 8 (NEW): Owner asks for proof we have the cash

| Layer | Action |
|---|---|
| **Prevention** | Pre-empt with "EMD on deposit at Mid-South Title" line in offer email. Mid-South emails confirmation. |
| **Contingency** | If owner pushes "show me $1,800 in your bank account": say "buyer-side funds are committed, EMD is at the title firm, you'll see the wire confirmation 24 hrs before close from the title firm directly -- they're the verified source." |
| **What we DON'T do** | Show them YOUR personal checking account (you don't have $1,800 sitting there, and even if you did, it's not how wholesale works). |
| **Walk trigger** | Owner refuses to proceed without proof of personal cash: walk. They want a retail cash buyer, not a wholesaler. |

---

## Backup buyer pipeline -- BUILD THIS WEEK

This is critical infrastructure. Without it, every deal is one-buyer-deep and we're dependent on Chris.

| # | Source | Owner action | Output |
|---|---|---|---|
| 1 | Memphis REIA membership directory | Penny pulls list of active local cash buyers | 10-20 names |
| 2 | Connected Investors Memphis filter | Hammer profiles top 20 active 90-day | 5-10 most active |
| 3 | BiggerPockets Memphis investor profiles | Penny scrapes / browses | 5 candidates |
| 4 | Shelby Register cash-deed analysis | Cipher MHTMLs deeds with no mortgage in last 12 months | 5-10 active local LLCs |
| 5 | Direct cold outreach to top 10 | Hammer sends short intro + sample deal | 3-5 reply, 1-2 add to rotation |

**Target:** 5 backup buyers in `buyers/buyers_db.json` with active buy boxes within 7 days. Timeline matters: every day we don't have backup is a day Chris owns the relationship.

---

## What "controlling the process" means in practice

Tempo and structure dictation, even when we're "going with the flow":

1. **Every milestone has a deadline.** Pre-call email Day 0. First call Day 1. Offer Day 1-2. PSA Day 2-3. Package to Chris Day 3. Yes/no Day 4-5. Title work Day 5-13. Close Day 14.
2. **Every conversation pre-frames the next step.** Pre-call email tells them we're going to call. First call tells them next step is the offer. Offer tells them next step is the PSA. PSA tells them next step is closing. They're never surprised, we never have to chase.
3. **Every decision has a documented owner.** Penny owns offer ceiling. Hammer owns PSA terms. Justine owns compliance walk. Marcus owns vertical-CEO veto. No "let me check with..." back-and-forth.
4. **Every contingency has a written response.** This document is the playbook. Hammer doesn't improvise; he reads.
5. **Every external party gets things in writing.** Email confirmations, signed PSAs, voided checks, wire instructions. Verbal-only is fraud-friendly and loss-prone.
6. **Every step has a walk trigger.** DD period, Penny ceiling, BEC stop, lien threshold. We can always walk. That's leverage.
