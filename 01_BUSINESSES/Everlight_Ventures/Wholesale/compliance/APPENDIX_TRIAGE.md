# State Disclosure Appendix Coverage Triage

**Filed by:** Justine Park, Compliance Gate
**Date:** 2026-04-26
**Status:** Operational triage. Drives next-round drafting order.
**Scope:** Resolves Escalation 2 from the pdf_autofill compliance wiring sprint (Backend Hand B, 2026-04-26).
**Attaches to:** `pdf_autofill` state-to-appendix mapper, `state_gates.json`.

> **THIS IS RESEARCH AND EDUCATION, NOT LEGAL ADVICE.** Statutory anchors below are the Hive's research starting points for next-round drafting. Each appendix, once drafted, requires state-specific real-estate counsel countersign before first live use, mirroring the CA and OH appendices already on file.

---

## Current Coverage

`pdf_autofill` ships with two state appendices:

- **CA** -> `CA_1695_APPENDIX.md` (Civ. Code 1695 home-equity sales contract)
- **OH** -> `OH_DISCLOSURE_APPENDIX.md` (ORC 4735 + 1349.61 + 5302.30 principal-buyer + lapsed-license)

`state_gates.json` lists 9 active states. Seven have no appendix. Any future distress or disclosure-triggering deal in those seven states will hard-block at autofill time. Triage below.

## Active Pipeline States Without an Appendix

| State | Active | Risk Rating | Pre-Foreclosure Allowed | Triage Bucket |
| --- | --- | --- | --- | --- |
| GA | yes | medium | yes | HIGH |
| TX | yes | high | yes | HIGH |
| FL | yes | high | yes | MEDIUM |
| MO | yes | medium | yes | MEDIUM |
| AZ | yes | medium | yes | MEDIUM |
| TN | yes | medium-high | yes | MEDIUM |
| NC | no (BLOCKED) | do_not_operate | n/a | SKIP |

## HIGH Priority -- Draft Next Round

These two states are active in the pipeline AND carry statute-driven disclosure obligations on every transaction (not just distress). An autofill block here stops live deal flow.

### GA -- Georgia

**Anchor statutes for the appendix:**

1. **OCGA 44-14-13** (Earnest money / trust account requirements). Wholesaler holding seller EMD must route through a licensed escrow / closing attorney trust account, not a personal or business operating account. The appendix must specify the closing-attorney trust account as the EMD destination and prohibit any direct EMD transfer to the wholesaler's account.
2. **OCGA 13-1-7** (Liquidated damages and fee caps). Limits on contract-level damages and fee structures. Relevant to any assignment-fee-as-liquidated-damages clause, which is a structuring choice in some GA contracts. Appendix must state the assignment fee plainly and not disguise it as liquidated damages.
3. **OCGA 43-40** (Georgia Real Estate License Law). Marquise is operating unlicensed under the principal-buyer carve-out. Appendix must mirror the OH lapsed-license disclosure: principal buyer, holds equitable interest, not a licensed GA broker or salesperson, lapsed CA license disclosed.
4. **OCGA 10-1-393** (Georgia Fair Business Practices Act). Fair-dealing standard governs seller-facing communications. Appendix should incorporate the OH-style timeline-language guardrail (no guaranteed close dates, target date subject to title clearance).

**Closing posture:** Attorney-state. EMD lives at `georgia_title_escrow_atl` per `state_gates.json`.

### TX -- Texas

**Anchor statutes for the appendix:**

1. **TX Property Code Sec. 5.086** (Wholesaler-name disclosure). Mandatory pre-contract written disclosure that the buyer is a wholesaler intending to assign the contract for profit. Disclosure must include the wholesaler's name and intent in writing before the seller signs. SB 1577 (already flagged in `state_gates.json` as `sb1577_required: true`) extends this to every marketing piece. The TX appendix must reproduce the statutory disclosure block verbatim and specify pre-contract delivery as the operational rule.
2. **TX Property Code Sec. 5.0865** (SB 1577 expanded equitable-interest disclosure, 2023). Buyer-facing disclosure on assignment that the assignee is acquiring contract rights, not the property itself. The appendix must carry this on the assignment-side as well as the seller-side. Both `required_seller_disclosure` and `required_buyer_disclosure` in `state_gates.json` are set to `equitable_interest_written_TX`.
3. **TX Insurance Code Sec. 2651** (Title insurance / escrow agency requirements). Title closing through a licensed Texas title agency, EMD via title-company escrow. The appendix must specify `texas_title_dal` (per `state_gates.json`) or equivalent licensed TX title agency as the EMD and closing destination.
4. **TX Bus. & Com. Code Sec. 302** + **TX SB 140** (effective 2025-09-01). Telephone solicitor registration + $10K bond for cold SMS. The appendix is contract-level so this is operational background, but the appendix should reference the SMS block in `state_gates.json` so the contract record carries the channel-restriction footprint.

**Closing posture:** Title-company state. ARV-in-writing to seller is BLOCKED per `state_gates.json` (`arv_in_writing_to_seller_allowed: false`). Appendix must scrub any ARV figure from seller-facing surfaces.

## MEDIUM Priority -- Queue, Draft After HIGH

These four are active but lower distress volume so far. Draft after GA and TX land. Statutory anchors logged for the queue:

- **FL** -- FS 501.1377 (foreclosure rescue / equity skimming, all-party recording disclosure already in `state_gates.json`), FS 501.059 (FTSA SMS rules, operational not contractual), Fla. Stat. Ch. 475 (RE license law for unlicensed-buyer carve-out). All-party recording state, contract must reference the recording-disclosure surface.
- **MO** -- RSMo Ch. 339 (RE license law), RSMo 407 Subdiv. 5 (Merchandising Practices Act fair-dealing standard), RSMo 442 (conveyances and EMD via title escrow). Material-defect-and-liens disclosure already flagged in `state_gates.json`.
- **AZ** -- ARS 44-5101 (HB 2747, wholesale buyer assignment intent disclosure, already flagged `hb2747_required: true`). Mandatory pre-contract written assignment-intent clause. Seller cancel right if disclosure omitted. ARS Title 32 Ch. 20 (RE license law) for principal-buyer carve-out. ARS 33-401 (conveyances).
- **TN** -- TN Code 66-32-301 et seq. (HB 2537 / SB 909, already flagged `sb909_required: true`). Bold-font equitable interest disclosure on contract surface, mandatory 3-business-day notice to seller before assignment executes. TN Code Title 62 Ch. 13 (RE license law). TN Code 47-18 (Consumer Protection Act fair-dealing standard).

## SKIP -- Not Drafting

- **NC** -- `state_gates.json` flags NC as `wholesale_legal_status: license_required` and `active_in_pipeline: false` under HB 797 (effective 2025-10-01, residential wholesaling requires NC broker license). No outbound, no contracts, no appendix needed. If NC ever re-opens (license obtained, statute amended, or BD-supervision wrapper attached), this triage entry is re-opened. Until then NC is operationally dark and no appendix work is justified.

## Backend-Side Hard-Block Behavior (Recommended)

Until the GA, TX, FL, MO, AZ, TN appendices land, `pdf_autofill` should map every state in the active pipeline as follows:

```
state_to_appendix = {
    "CA": "CA_1695_APPENDIX.md",
    "OH": "OH_DISCLOSURE_APPENDIX.md",
    "GA": None,  # HIGH priority, draft next
    "TX": None,  # HIGH priority, draft next
    "FL": None,  # MEDIUM, queued
    "MO": None,  # MEDIUM, queued
    "AZ": None,  # MEDIUM, queued
    "TN": None,  # MEDIUM, queued
    "NC": "BLOCKED",  # do not operate
}
```

When `state_to_appendix[state] is None`, autofill must hard-block, log `AppendixMissing(state)` to the compliance log, and ping `#compliance` with the deal_id. No silent default to a generic template, no fallback to the CA or OH appendix, no "best effort" template render. The block is the feature.

When `state_to_appendix[state] == "BLOCKED"`, autofill blocks earlier in the chain (state-gate enforcement, before reaching the appendix mapper) and pings Justine plus Bernard.

## Drafting Order and Owners

1. **GA appendix** -- next round. Owner: Justine, drafted with Bernard on EMD trust-account language.
2. **TX appendix** -- next round, paired with GA. Owner: Justine, drafted with Carlos on SB 1577 marketing-piece scope.
3. **MEDIUM batch** (FL, MO, AZ, TN) -- following round. Owner: Justine, with state-counsel review per state.

Each appendix follows the OH appendix's four-surface placement requirement (purchase contract, outbound email, direct mail, landing pages) and the CA appendix's counsel-review-before-first-use gate. No appendix ships to live deal flow without state real-estate counsel countersign.

## Re-Review Triggers (All Buckets)

This triage is operational until any one of the following fires, at which point Justine re-opens the file:

1. Any new state added to `state_gates.json` with `active_in_pipeline: true`.
2. Any state moved from active to blocked or vice versa.
3. Any of the named statutory anchors above amended or repealed.
4. NC HB 797 amended, repealed, or replaced.
5. Every 6 months from filing date, regardless of statutory activity. Next review: 2026-10-26.

The earliest of triggers 1 through 5 is the operative re-review date.

---

**THIS IS RESEARCH AND EDUCATION, NOT LEGAL ADVICE.**

Justine Park, Compliance Gate.
