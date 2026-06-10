# State-Source Authority for Deal Jurisdiction Routing

**Filed by:** Justine Park, Compliance Gate
**Date:** 2026-04-26
**Status:** Operational. Wire into `deal_to_context()` on next backend pass.
**Scope:** Resolves Escalation 1 from the pdf_autofill compliance wiring sprint (Backend Hand B, 2026-04-26).
**Attaches to:** `broker_ops` Deal model, `pdf_autofill.deal_to_context()`.

> **THIS IS RESEARCH AND EDUCATION, NOT LEGAL ADVICE.** Engage Bernard Calloway (corporate / regulatory) and Carlos Moreno (RE specialty) before any production reliance on the rule below. The state-source rule is the Hive's internal operating posture pending external counsel countersignature.

---

## The Question

The `Deal` model can be linked to either a `LeadProfile` (B2B SaaS prospect, no `state` field) or a `PropertyLead` (real-property record, has `state` field). Today `deal_to_context()` reads `state` from `lead.state`, which is `None` whenever the deal is rooted on a `LeadProfile`. We need a written posture on which model is authoritative for jurisdictional disclosure routing so the pdf_autofill state-appendix mapper does not silently default-route a CA homeowner deal through a B2B template, and does not attempt to attach an OH disclosure appendix to a Vendor SaaS deal.

## The Rule

For real-estate wholesale deals (the lane that needs jurisdictional disclosures, CA Civ. Code 1695, ORC 1349.61, ARS 44-5101, TX SB 1577, TN HB 2537, GA OCGA 44-14-13, etc.), **the property's state is authoritative, not the seller's residence state**. Disclosure statutes attach to the situs of the real property. A California-resident seller selling an Ohio rental triggers Ohio statutes, not California statutes. A Texas-resident seller selling a California principal residence triggers California Civ. Code 1695, not Texas SB 1577.

Therefore the model that carries the property record (`PropertyLead`) is authoritative. `LeadProfile` (B2B vendor prospect) is never authoritative for jurisdictional disclosure routing because it does not represent a real-property transaction.

## Resolution Chain (Verbatim, for `deal_to_context()`)

`Deal.state` resolves in this order. First non-null wins. No silent fallback to `None`.

1. **`Deal.match.property_lead.state`** if `Deal.match` is set and `Deal.match.property_lead` exists. This is the canonical path: the match record links the deal to the specific property under contract.
2. **`Deal.lead.state`** ONLY IF `isinstance(Deal.lead, PropertyLead)`. This is a fallback for deals created directly from a property lead before a match record exists (early-stage intake).
3. **Hard-block, escalate to Justine.** If neither path resolves, the deal is missing jurisdictional grounding. `pdf_autofill` raises `JurisdictionUnresolved` and Justine receives a `#compliance` Slack ping with the deal_id. No template renders, no contract generates, no PDF ships.

`LeadProfile`-rooted deals (B2B SaaS prospect lane) are excluded from this chain. They route to a separate template family that does not reference state-disclosure appendices because they are not real-property transactions. See "B2B Carve-Out" below.

## B2B Carve-Out (LeadProfile)

Deals rooted on `LeadProfile` are commercial vendor introductions. They do not require CA/OH/AZ/TN/TX/GA-style real-property appendices because no real property changes hands. The applicable compliance surface for B2B deals is:

- **CAN-SPAM** on outbound (already enforced via `branded_mailer`).
- **State finder-fee thresholds** for the deal-side commission split (tracked in the per-state finder-fee log, separate concern from disclosure routing).
- **Non-securities representation** in the introduction agreement (template at `compliance/B2B_INTRODUCTION_AGREEMENT.md`).

`pdf_autofill` should branch at the top: if `Deal.lead_type == "b2b_vendor"` or `Deal.lead` is a `LeadProfile`, route to the B2B template family and skip the state-appendix mapper entirely. The state-appendix mapper is real-property-only.

## Contract for Backend Hand B

Wire the resolution chain into `deal_to_context()` exactly as written above. Specifically:

1. Add a `_resolve_deal_state(deal)` helper that returns `(state_code, source)` where `source` is one of `"match.property_lead"`, `"lead.property_lead"`, or raises `JurisdictionUnresolved`.
2. Add a top-level branch in `deal_to_context()`: if the deal is B2B (LeadProfile-rooted or `lead_type == "b2b_vendor"`), skip the state resolver and route to the B2B context builder. Otherwise call `_resolve_deal_state(deal)`.
3. Log the `(deal_id, state_code, source)` tuple to `hive_logger` on every state resolution so the audit trail records which path won.
4. The `JurisdictionUnresolved` exception path posts to `#compliance` via `branded_slack.post_branded_alert()` with `severity="block"` and the deal_id, and writes a row to the compliance log.
5. Unit-test coverage: (a) deal with match + property_lead resolves via path 1, (b) deal with PropertyLead-rooted lead and no match resolves via path 2, (c) deal with LeadProfile-rooted lead never reaches the state resolver, (d) deal with no match and no PropertyLead lead raises and pings Justine.

## Why the Property's State, Not the Seller's

Real-property disclosure statutes are conflict-of-laws "lex situs" jurisdictions. The law of the place where the land sits governs the transaction. Every relevant statute in the active pipeline (CA Civ. Code 1695, ORC 1349.61, ARS 44-5101, TX SB 1577, GA OCGA 44-14-13, TN HB 2537) is a state-of-property statute, not a state-of-seller statute. A California seller who owns a Texas rental and sells it through Everlight triggers TX SB 1577 disclosure, not CA Civ. Code 1695. Routing on the seller's residence state would attach the wrong statute, miss the right statute, and create exposure on both sides.

The PropertyLead's `state` field is the property's state by definition (it is set from the parcel record at lead creation). The LeadProfile has no `state` field because the seller's residence is not the disclosure trigger.

## Edge Cases

1. **Multi-parcel deals across state lines.** If one Deal references multiple parcels in different states (rare, portfolio sales), the deal must be split into one Deal per state at intake. The state resolver assumes one state per Deal. This is enforced at the match-creation layer, not at autofill.
2. **State changes mid-pipeline** (a parcel re-sited via a county boundary correction, or a contract restructured to swap properties). The state resolver re-evaluates on every autofill call. Cached state values are not honored. The current PropertyLead state at autofill time is authoritative.
3. **PropertyLead state is null** (parcel imported with missing state). This is a data-quality bug, not a routing question. The resolver hard-blocks and Justine pings the data-intake owner. The deal does not progress until the parcel record is repaired.
4. **Cross-state seller representation** (CA-resident seller, OH property). The OH appendix attaches because the property is in Ohio. The CA appendix does not attach. The lapsed-CA-license disclosure in the OH appendix already addresses Marquise's CA license status; no separate CA disclosure is needed when the property is out-of-state.

## Escalation Path

Any disagreement with this rule, any new state added to `state_gates.json`, or any new `Deal` lead-source type (beyond `LeadProfile` and `PropertyLead`) goes through Bernard Calloway (corporate / regulatory) and lands back in this file as a v0.2.

---

**THIS IS RESEARCH AND EDUCATION, NOT LEGAL ADVICE.**

Justine Park, Compliance Gate.
