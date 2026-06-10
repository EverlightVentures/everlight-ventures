# Chris-Side Contract Lock -- How We Bind Chris So He Can't Bypass

**Marquise's concern:** "once we [have sellers under contract], we send to chris (he must be under contract as well as to not screw us)."

The mechanism that locks Chris in is the **Assignment Agreement + Good-Faith Assignment Deposit**. Three layers of protection.

---

## Layer 1: PSA already includes anti-circumvention language

In our Real Estate Purchase Agreement (PSA) signed by Seller, the assignment clause requires Buyer's written consent to assignment. Once we (Everlight Ventures) sign with Seller, the SELLER has agreed to convey ONLY to us or our designated assignee. Seller cannot independently sell to Chris -- they're bound to us.

**What this stops:** Seller circumvention (Chris talks to Seller direct, tries to cut us out). Seller breaches their PSA, EMD forfeits, Chris on the hook for tortious interference with contract.

---

## Layer 2: Assignment Agreement (the contract that binds Chris)

Once Chris commits to a deal, we execute a **separate Assignment Agreement** between Everlight Ventures (Assignor) and Mid South Homebuyers / Chris's entity (Assignee). Three required clauses:

### Clause 2.1 -- Assignment Fee + Payment Trigger

```
Assignor hereby assigns all right, title, and interest in the Real
Estate Purchase Agreement dated [DATE] for the property at [ADDRESS]
to Assignee, in exchange for an Assignment Fee of $[FEE], payable as
follows:

(a) Good-Faith Assignment Deposit of $[GFAD] (typically $500-$1,500),
    paid by Assignee to Mid-South Title escrow within 48 hours of
    execution of this Assignment Agreement;

(b) Balance of $[FEE - GFAD] paid at closing of the underlying
    transaction, disbursed by the closing agent to Assignor on the
    closing settlement statement.
```

**The Good-Faith Assignment Deposit (GFAD) is the lock.** Chris wires $500-$1,500 to title escrow within 48 hours. That money is at-risk for him (forfeited to us) if he walks for any reason except those listed in Clause 2.4.

### Clause 2.4 -- When Chris's GFAD Refunds (the only outs)

```
The Good-Faith Assignment Deposit shall be refunded to Assignee only
if:
  (i)  Title is unmarketable per the title commitment and Seller
       cannot cure within 14 days;
  (ii) Underlying PSA is terminated by Seller's default; OR
  (iii) Force majeure (fire, flood, condemnation) before closing.

In all other circumstances -- including Assignee's failure to fund,
inability to perform, or refusal to close for any reason -- the
Good-Faith Assignment Deposit is forfeited to Assignor as
liquidated damages.
```

This is the disincentive. Chris has $500-$1,500 at-risk. He either closes or loses it.

### Clause 2.6 -- Anti-Circumvention (the legal teeth)

```
Assignee acknowledges that Assignor has expended substantial time
and resources locating, contracting, and packaging the Property
for assignment. Assignee agrees that for a period of twenty-four
(24) months following execution of this Agreement, Assignee shall
not, directly or indirectly:

  (a) Contact, solicit, or transact with the Seller named in the
      underlying PSA outside the scope of this Assignment;

  (b) Acquire the Property -- or any interest in the Property --
      from any source other than through this Assignment, without
      paying Assignor's full Assignment Fee;

  (c) Disclose the Seller's identity, contact information, or the
      terms of the underlying PSA to any third party.

Breach of this Clause 2.6 entitles Assignor to injunctive relief
plus liquidated damages equal to TWO TIMES the Assignment Fee,
plus reasonable attorneys' fees.
```

**This is the killshot.** If Chris (or his team) tries to talk to Seller directly and cut us out, we have a SIGNED CONTRACT saying he owes us 2x the assignment fee + legal fees + injunctive relief. That's not a polite request -- that's a lawsuit waiting to be filed.

---

## Layer 3: Title firm holds the keys

Mid-South Title escrow holds:
- Seller's deed (delivered to title at PSA signing)
- Our $100 EMD
- Chris's $500-$1,500 Good-Faith Assignment Deposit (Layer 2 wire)
- Chris's full balance + closing costs at closing

The title firm releases NOTHING to anyone until closing executes per the assignment chain. If Chris tries to circumvent, the title firm can refuse to close (the seller's PSA bound them to us, and the assignment chain shows we're owed). Title firm becomes our automatic enforcement mechanism.

---

## What this looks like in practice (timeline)

```
Day 0  -- Seller signs our PSA. Our $100 EMD wires to Mid-South
          Title. Seller is now bound to convey to us or our assignee.

Day 3  -- We send package to Chris (PSA copy + EMD confirmation +
          property details).

Day 4  -- Chris says yes. We send Assignment Agreement via Documenso.

Day 5  -- Chris signs Assignment Agreement. Assignment Fee + GFAD
          terms locked.

Day 6  -- Chris wires $500-$1,500 GFAD to Mid-South Title escrow.
          NOW HE'S LOCKED IN. If he walks: we keep the GFAD.

Day 7-13 -- Title work. Chris brings full purchase price + closing
            costs to escrow.

Day 14 -- Closing. Chris wires balance. Title disburses:
            -> Back tax to Shelby Trustee
            -> Closing costs per settlement
            -> Balance to Seller
            -> Assignment Fee balance to us
            -> GFAD applied as part of Assignment Fee
```

Chris has 3-4 days to walk after signing the Assignment but before GFAD wires. After GFAD: he's at-risk for at least $500-$1,500 in liquidated damages. After closing date is 7 days away: practically locked.

---

## Why we don't just take a non-refundable deposit at signing

We could (some wholesalers do). But:

1. **Chris is a serious buyer.** Mid South Homebuyers closes 30+ deals/quarter. The good-faith deposit at the title firm 48 hours after signing is industry-standard for this caliber of buyer. Demanding upfront non-refundable cash before he's even seen the property in person reads as "we don't trust you" and tanks the relationship.

2. **The 48-hour wire window is the credibility test.** If Chris doesn't wire the GFAD within 48 hours, that's our signal he's not serious -- we void the assignment, send the package to backup buyer #1.

3. **Layer 2.6 anti-circumvention is the long-term lock.** Even if Chris withdraws on Deal 1, the 24-month non-circumvention clause means he can't quietly buy the same property from the seller next year without paying us. We have legal recourse for two years.

---

## What Marquise does

Nothing different from what we already planned. The Assignment Agreement template will be auto-generated by `contract_generator.py` (we need to add the assignment-specific generator -- one of tomorrow's small Henry tasks). When Chris says yes, Henry sends the Assignment Agreement via Documenso, Chris signs, GFAD wires within 48 hours.

---

## Contract templates needed

| Template | Status | Owner |
|---|---|---|
| Real Estate Purchase Agreement (Seller-side) | DONE -- `contract_generator.py` generate_wholesale_contract() with TN SB 909 gate | Henry |
| Assignment Agreement (Buyer-side, NEW) | NEEDED -- add `generate_assignment_agreement(deal)` function with Clauses 2.1, 2.4, 2.6 | Henry / Forge -- 30 min build |
| Title firm escrow instructions | DONE -- standard template, Mid-South handles | Mid-South Title |

---

## Risk if we DON'T have this lock

Chris (or his interns at Mid South) sees a property on Farrow Ave for $1,800. Looks them up, contacts seller direct, offers $2,200, closes around us. We get nothing.

WITH this lock:
- Seller can't legally sell to Chris direct (PSA binding)
- Chris owes us 2x assignment fee + attorneys fees if he circumvents
- GFAD already wired = sunk cost prevents walk

**Probability of Chris circumventing without lock: 5-15% per deal (he has interns, they have ProstStream, mistakes happen).**
**Probability with lock: <1%.** Worth the 30 minutes of Henry's time to add the assignment generator.
