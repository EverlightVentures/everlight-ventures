# Business Entity Status

**As of 2026-04-22. Updates immediately on any entity change.**

## Current Status: SOLE PROPRIETORSHIP

Everlight Ventures LLC is **NOT currently in good standing** and is in reinstatement pending. Until the LLC is reinstated, all business is conducted as a sole proprietorship by Richard Gee, using "Everlight Ventures" as a fictitious business name (d/b/a).

> **Operator update (2026-06-01):** The current registered entity is **Everlight Logistics** (Richard Gee, CEO), which is not presently the wholesale contracting vehicle. The plan is to **form/reform in NEVADA** under the name **Everlight Ventures**, structured as a **holding company** over the other ventures. Until that Nevada entity exists and is designated, all wholesale business stays a sole proprietorship (Richard Gee d/b/a Everlight Ventures) and every contract is signed by Richard Gee personally. When the Nevada entity is live, note (per `entity_identity.py`) that a holding company should NOT sign operating contracts directly -- the wholesale party should be an operating subsidiary under it, confirmed with counsel. The California reinstatement steps below are superseded by this Nevada plan except where needed to wind down the existing CA entity.

## What This Changes Operationally

### Contract signatory

Contracts must be signed as:

```
Richard Gee, an individual
doing business as Everlight Ventures
[Rich's signature]
```

NOT as "Everlight Ventures LLC" or "Everlight Ventures, LLC." Signing under a non-existent corporate entity is a misrepresentation risk.

Contract templates:
- `contract_generator.py` -- buyer field must default to "Richard Gee d/b/a Everlight Ventures" until LLC reinstated
- Once reinstated, flip to "Everlight Ventures LLC, a California limited liability company"

### Personal liability exposure

Sole prop = Rich is personally liable on every contract. No corporate veil.

**Mitigations while sole prop:**
1. Smaller deals only until LLC reinstated (avoid the $500K+ exposure zone)
2. Keep a defined "deal ceiling" per contract ($50K max earnest money + $100K max liquidated damages). Above that, the deal waits for LLC.
3. General-liability personal umbrella insurance policy (consult insurance broker on single-person wholesale coverage)
4. Every contract includes the 7-day Quality Assurance Review Period clause for seller walk-away (reduces rescission fights)
5. Every contract governed by mandatory binding arbitration (caps litigation cost exposure)

### Tax implications

- All business income flows to Rich's personal 1040 (Schedule C)
- Self-employment tax on net profit
- No business-account S-corp election until LLC reinstated
- **Track expenses aggressively** -- every dollar spent on the business is deductible against SE income

### Banking

- Business revenue must go into a SEPARATE personal bank account (not the LLC account) so personal / business are still separable for Schedule C accounting
- Recommend: open a new checking account titled "Richard Gee d/b/a Everlight Ventures" at Chase / Wells Fargo / local credit union
- Stripe payouts, Resend refunds, buyer commissions -- all to this account

### State registrations

**DO NOT FILE** the following while sole prop (was in the Phase 2 plan, now paused):
- Foreign LLC registration in FL, TX, GA, MO, AZ, TN -- N/A, no LLC to register
- TX Secretary of State telephone solicitor registration + $10K bond -- can file in Rich's personal name but carries personal-credit exposure. Hold until LLC reinstated unless we commit to a high-volume TX SMS campaign.

**CAN FILE** as sole prop:
- DBA / Fictitious Business Name Statement in CA (Alameda/whatever county Rich resides in) -- makes "Everlight Ventures" a legal brand for the sole prop. ~$50 filing.
- EIN for the sole prop (optional; can use Rich's SSN on Schedule C, but EIN keeps the SSN off outbound paperwork)

### Marketing / branding

- "Everlight Ventures" remains the brand name on all outreach, emails, website
- Internal legal line in email footer changes from "Everlight Ventures LLC" to just "Everlight Ventures" (no LLC)
- Website legal page clarifies: "Everlight Ventures is a registered fictitious business name of Richard Gee, a California sole proprietor. Everlight Ventures LLC is a separate entity in reinstatement status; all current business is conducted by the sole proprietorship."

### Compliance gate notes

`state_gates.json` fields to update:
- `foreign_llc_registration_required`: set to `false` in all 7 states (no LLC to register)
- Add new field `sole_prop_dba_filed` per state where we sign contracts (targets: CA yes, others TBD based on that state's DBA requirements for out-of-state sole prop)

## Reinstatement Path

Rich's to-do when ready to pursue LLC reinstatement:
1. Contact CA Secretary of State to determine current LLC status (suspended / forfeited / dissolved)
2. File reinstatement paperwork (Form LLC-3 or similar) + pay delinquent franchise tax (CA LLC = $800/yr minimum)
3. Bring any CA Franchise Tax Board filings current (back-taxes + penalties)
4. Once LLC is reinstated, ALL contracts flip back to the LLC as buyer/assignor
5. Flip `entity_identity.ENTITY_STATUS` from `"sole_prop"` to `"llc"` (single change; generator + all contract templates + sender identity follow automatically), then run `entity_guard.py` to confirm clean
6. Update this document with the reinstatement date
7. Then file foreign LLC registrations in any state with significant volume

## Priority

Reinstating the LLC is **high priority** because:
- Every day as sole prop = personal-liability exposure on every open contract
- LLC cost ($800/yr CA franchise tax + back-tax penalties) is trivial vs. one lawsuit exposure
- Once reinstated, LLC resumes without needing to re-paper existing seller relationships (we simply assign new contracts as the LLC)

Target: reinstate within 60 days of L2 first closed deal (so the first deal's revenue covers the reinstatement cost).

## Reference

- CA Secretary of State -- LLC reinstatement: https://www.sos.ca.gov/business-programs/business-entities/revivor
- CA Franchise Tax Board -- back-tax process: https://www.ftb.ca.gov
- IRS Schedule C (sole prop tax form): https://www.irs.gov/forms-pubs/about-schedule-c-form-1040

## Machine mirror (added 2026-06-01)

This document is the **human** source of truth. Its **machine mirror** is
`01_BUSINESSES/Everlight_Ventures/Broker_OS/entity_identity.py` -- one constant
(`ENTITY_STATUS`) that every contract template, the generator, and the
sender-identity config now read from. To switch posture on reinstatement, flip
that one constant from `"sole_prop"` to `"llc"`; do NOT hand-edit individual
contracts (that drift was the FATAL finding of the 2026-06-01 stress test). The
`entity_guard.py` pre-commit hook fails closed if any contract names a
non-canonical party.

## Cross-references

- `entity_identity.py` -- MACHINE MIRROR of this doc; the single canonical entity constant. Flip `ENTITY_STATUS` here on reinstatement.
- `entity_guard.py` -- fail-closed pre-commit guard; blocks any contract/template/sender-config naming a non-canonical party. Test: `test_entity_guard.py`.
- `contract_generator.py` -- reads the canonical party from `entity_identity.py` (no longer hardcoded)
- `state_gates.json` -- `foreign_llc_registration_required` field (bulk-flip to false)
- `STATE_COMPLIANCE_MATRIX.md` -- "Top 10 Sue/Jail Risks" item 7 (foreign LLC) now N/A until reinstatement
- `BRAND_POSITIONING.md` -- "Physical Office" section still accurate (physical address independent of entity)
