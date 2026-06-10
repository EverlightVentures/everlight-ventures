# Reply Draft v2: Chris Ulander @ Mid South Homebuyers

**Status:** HOLD per Marquise 2026-04-28. Do not send until he approves.
**Version:** v2 (post-Hive-strategy-synthesis). Replaces v1.
**Strategy doc:** `MIDSOUTH_STRATEGY.md` (read this first).
**Send from:** henry@everlightventures.io
**Send to:** chris@midsouthhomebuyers.com
**CC:** leads@midsouthhomebuyers.com (per his instruction)
**Subject:** Re: Private deal flow for Memphis investors
**Tone:** B2B peer-to-peer. Confident, not hungry. Match Chris's register.

---

## DRAFT v3 (contract-first model -- supersedes v2)

```
Chris -- thanks for the fast turnaround and the detailed buy box.

Captured: 15 Memphis zips, 9 Little Rock zips, 1940+ build cutoff, brick
preferred (frame condition-dependent), $30-60k sweet spot stretching to
$160k, occupancy/keybox always included, direct-to-seller or written JV
disclosed.

We work contract-first -- meaning we take properties under PSA before we
introduce them to the buyer side. So our packages will arrive with: the
signed PSA, EMD-on-deposit at a RESPA-clean Memphis title firm, photos,
ARV + repair estimate, occupancy/keybox, and TN SB 909 wholesaler
disclosure already executed with the seller. You inherit a clean
assignment chain with no seller-side legwork.

Two clarifying questions:

1. MAO formula on the $30-60k tier -- do you have a typical (% ARV minus
   repair) you'd want us to flag against during negotiation, so we lock
   contracts at numbers you'll fund? We can ship without it but a target
   tightens our pre-screen.

2. Standard turnaround on go/no-go once a complete package lands -- 48
   hours workable on your end?

first deal package to leads@midsouthhomebuyers.com when the first PSA + EMD lock complete. Targeting
TS2202 cohort (6+ year delinquent, sustained motivation) in 38106 / 38114
/ 38127 first.

Looking forward to it.

Rich
Everlight Ventures
henry@everlightventures.io
```

---

## Why This Version (deltas from v1)

| Change | Reason |
|---|---|
| Removed "looking forward to building this together" warmth | Hammer: confident peer, not hungry rookie |
| Added explicit zip + build year + brick + occupancy/keybox confirmations | Hammer: shows we read it like scripture |
| Added SB 909 compliance posture line | Slate: pre-empts the disclosure-burden risk + signals we're institutional |
| Added MAO formula ask | Cipher: leverage point. If he balks, we know he's cherry-picking |
| Added 48-hour decision window ask | Cipher: aligns expectations + prevents dead-leads-in-his-inbox |
| Specific 48-72h first delivery | Hammer: forces us to actually scout-and-ship when ready |
| Removed phone call ask | Hammer: phone call after deal #1 wires, not before |
| Removed weekly cadence promise | Slate: don't promise volume the buy-box math doesn't support |
| Cited TN SB 909 (not HB 2537) | Cipher correction; HB 2537 is marriage officiants, unrelated |

---

## Three Things to NOT Add

1. **No mention of "first deal" / "new to Memphis" / "sole prop / no LLC."** You're Everlight Ventures. A firm. Period.
2. **No website URL.** Signature has it.
3. **No exclusivity offer ("we'll send you first refusal on every Memphis deal").** Per Cipher + Slate: don't accept exclusivity, don't offer it. Anchor-plus-bench from day one.

---

## What Happens After He Replies

| Scenario | Marquise action |
|---|---|
| He gives MAO formula | Update `buyers_db.json` Chris record with `mao_formula` field. Pre-screen every Memphis lead against it. Don't ship anything that fails his MAO. |
| He says "ship raw, we'll set the offer" | OK -- ship our score >= 75 leads, attach our independent ARV + repair estimate, let him counter. Build internal MAO model from his rejections. |
| He confirms 48-hour window | Set internal SLA: anything not heard back from in 48 hr = follow-up email asking yes/no. Don't ghost-chase. |
| He asks for shorter window (24h) | Match it. Discipline up. |
| He pushes back on SB 909 line | Likely won't -- it's our compliance, not his. If he asks, share state_gates.json TN block + our recipient_classifier output. Confidence builder. |
| He goes silent for 5+ days | Ship deal-1 on day 3 anyway. He said send. Slate's exit trigger doesn't fire until 21+ days silent post-pitch OR 3 rejections without feedback. |

---

## Sequence to Hit when ready EOD

| Day | Action |
|---|---|
| Mon (today) | Strategy synthesis. Reply draft prepared. **Not sent yet.** Marquise approves first. |
| Tue 7-9 AM PT | Marquise approves reply OR edits. Reply sent. |
| Tue 10 AM-3 PM PT | Memphis scout fires (CL ATL+DFW+Memphis with 8 keywords; Shelby Probate Court; Shelby Trustee tax-delinq list). Target: 30-50 Memphis leads. |
| Wed AM | Score Memphis leads via match_to_buyer.py. Top 1-3 with score >= 80 selected. |
| Wed PM | Hammer (with Marquise) double-checks the top deal: address, ARV, repair estimate, occupancy, keybox, SB 909 disclosure status. |
| Thu AM | Send first deal email to leads@midsouthhomebuyers.com (CC chris@). Standardized format: address, beds/baths, sqft, build year, asking price, condition notes, occupancy, source channel, JV-or-direct flag. |
| Thu PM | Justine pre-clears TN compliance; PSA v3 with SB 909 disclosure ready if Chris bites. |
| Fri AM | If Chris responds positively, draft offer + PSA. Title firm pre-approval letter from Mid-South Title (Hammer's seed list) attached. |
| Fri PM | If wire is feasible -- close. If not, deal #2 and #3 queued for when ready. |

---

## What's Different About This vs Every Other Wholesaler in His Inbox

Per Hammer's "differentiator" rule: every email to Chris includes a 1-line header with **trace_confidence + state_gate + JV-disclosed flag**. Example for the first deal:

```
[Lead 0001 -- TN-cleared / SB 909 disclosed / direct-to-seller / trace 0.87]
```

He gets 30+ pitches a week. Nobody else flags compliance up-front. We do.

---

**Ready to send pending Marquise approval. The strategy stands behind the words.**
