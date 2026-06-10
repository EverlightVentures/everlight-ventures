# PSA Boilerplate v3 -- Equitable Interest + Wholesaler Disclosure + Dual Remedy

**Plan reference:** v3 Move H + Dispatch #29.
**Owner spec from:** Contract Attorney (round 3 critique). Reviewed by Penny Vance + Justine Park.
**Why v3:** Plan v2 boilerplate had three load-bearing gaps. (a) Sole-prop signatory line was generic, exposing personal assets. (b) OH HB 132 + TN HB 2537 disclosure language missing -- contracts unenforceable in those states without it. (c) No dual-remedy clause; in TX courts, absent express liquidated-damages language, courts default to actual-damages-only (Phillips v. Phillips, 820 S.W.2d 785), meaning a buyer who walks at closing leaves Lucrex eating the marketing cost with no specific-performance lever.

**This file is the SPEC**, not the code. `contract_generator.py` consumes this to produce per-deal PSA + Assignment + Wholesaler Disclosure Exhibit. Each PSA template merge goes through `merge_field_gate.py` first (privacy-aware -- no skip-traced data in any contract field).

---

## Universal PSA structure (all states)

Every PSA produced has these blocks. State-specific language overrides per `state_gates.json` and per the addenda below.

### Block 1: Parties

```
PURCHASE AND SALE AGREEMENT

Effective Date: {effective_date}

This Purchase and Sale Agreement ("Agreement") is entered into between:

SELLER: {seller_full_legal_name}
of {seller_address}

and

BUYER (or Buyer's assignee): Richard Gee, an individual doing business as
Everlight Ventures, a sole proprietorship registered in {filing_state}
({dba_filing_reference}), with principal address at {buyer_address}.
```

**Critical:** Buyer line reads `Richard Gee, an individual doing business as Everlight Ventures` -- NOT just `Everlight Ventures` (would be a non-entity), NOT `Everlight Ventures LLC` (entity does not yet exist; would void contract for misrepresentation). The DBA filing reference cites the GA OCGA 10-1-490 stamp or TX Form 503 file number, populated from `dba_filings.md` evidence directory at PSA generation time.

**Gate:** PSA generator MUST refuse to write a PSA where `state == "GA"` and no GA DBA filing exists in evidence, OR `state == "TX"` and no TX DBA filing exists. (Per Move H Dispatch #8.)

### Block 2: Property + Earnest Money

```
PROPERTY: {street_address}, {city}, {state} {zip}
County: {county}
Parcel ID: {parcel_id}

PURCHASE PRICE: ${purchase_price_usd}
EARNEST MONEY DEPOSIT: ${emd_usd}, payable by wire to {title_firm_iolta_escrow}
within {emd_days} business days of this Agreement.
```

**EMD escrow gate:** Must reference a TitleCompany row marked `respa_clean_verified=True`. Generator refuses if no clean firm in TitleCompany table for this metro.

### Block 3: Equitable interest + assignment disclosure (NEW v3)

This block is REQUIRED in every wholesale PSA. Language drawn from OH HB 132 (effective 2024) but applied universally because (a) it strengthens enforceability everywhere and (b) prevents the "you didn't tell me you were a wholesaler" claim from killing the deal at closing.

```
BUYER'S INTEREST AND ASSIGNMENT RIGHTS:

Seller acknowledges that Buyer is acquiring an equitable interest in the
Property and intends to assign this Agreement to a third party for an
assignment fee. The assignment fee is $[ASSIGNMENT_FEE_PLACEHOLDER] and
shall be disclosed to all parties at closing on the Closing Disclosure or
HUD-1 settlement statement. Seller consents to such assignment provided
that the Buyer or Buyer's assignee fully performs all obligations under
this Agreement, including the timely funding of the Purchase Price.
```

**Placeholder:** `[ASSIGNMENT_FEE_PLACEHOLDER]` is filled at the moment Lucrex matches a buyer to the assignment, NOT at PSA-with-seller signing. Until then, the PSA carries `[TBD -- to be disclosed in writing prior to closing]`. This is the OH HB 132-compliant approach. State-specific overrides:

- **OH:** language above is mandatory verbatim (HB 132).
- **TN:** language above PLUS standalone Wholesaler Disclosure Exhibit (Block 5) signed BEFORE or same-day as PSA per HB 2537.
- **GA / TX:** language above is sufficient; no additional state-specific exhibit required. (But it does no harm.)
- **NC:** state is closed (HB 797 broker-license rule). PSA generator refuses for state=NC.
- **CA:** if the Property is in pre-foreclosure status, refuses (CC 2945/1695 equity-purchaser/foreclosure-consultant rules require either a different contract structure or a different actor).

### Block 4: Closing + remedies (DUAL-REMEDY CLAUSE -- v3 critical)

```
CLOSING:

Closing shall occur on or before {target_close_date}, at the offices of
{title_firm_name}, {title_firm_address}, or such other date as the parties
may mutually agree in writing.

Time is of the essence.

REMEDIES UPON BUYER DEFAULT:

In the event Buyer fails to close as required by this Agreement,
Seller's sole and exclusive remedies shall be EITHER (a) retention of
the Earnest Money Deposit as full and final liquidated damages,
acknowledging that actual damages would be difficult to compute and
the EMD represents a fair estimate of such damages, OR (b) an action
for specific performance to compel Buyer's performance, in Seller's
sole election. Seller waives any right to pursue both remedies and
to claim damages exceeding the Earnest Money Deposit in the event
liquidated damages is elected.

REMEDIES UPON SELLER DEFAULT:

In the event Seller fails to close as required by this Agreement,
Buyer's remedies shall include (a) return of the Earnest Money Deposit,
(b) an action for specific performance, and (c) actual damages including
but not limited to costs of title work, marketing, and lost-opportunity
expenses verifiable through Buyer's books and records.
```

**Why dual-remedy + liquidated damages floor:**

- Without express liquidated-damages language, TX courts default to actual-damages-only and refuse specific performance unless Seller proves money damages are inadequate (Phillips v. Phillips). Buyer who walks just gets EMD back.
- With both remedies as Seller's election, Lucrex (as Seller-side or Assignor) keeps both levers when the buyer is on the hook.
- Asymmetric remedy on Seller default (Buyer also gets actual damages) protects Lucrex when Seller is the defaulter -- because we eat title work, marketing, time-on-market on a deal that doesn't close.

### Block 5: Wholesaler Disclosure Exhibit (TN-required, universal-recommended)

```
EXHIBIT A: WHOLESALER DISCLOSURE

The undersigned Buyer acknowledges that Buyer:

  1. Is acting as a real estate wholesaler.
  2. Intends to assign this Agreement to a third-party investor or end-buyer
     for a fee.
  3. Is NOT a licensed real estate broker or agent.
  4. Is acquiring an equitable interest in the Property only.
  5. Has not represented and does not represent the property or its value
     to Seller as a licensed agent would.

Seller acknowledges receipt of this Disclosure prior to or contemporaneous
with execution of the Purchase and Sale Agreement and consents to the
assignment of the Agreement to a third party in accordance with its terms.

Seller's Signature: _____________________ Date: __________
Buyer's Signature:  _____________________ Date: __________
```

**Required for TN deals (HB 2537).** Generated as a separate signed document attached to PSA.
**Strongly recommended for all states** because it disarms the most common buyer-side claim ("I didn't know they were a wholesaler") in any post-closing dispute.

### Block 6: Inspection + due diligence

Standard 7-14 day inspection contingency. State-specific minima:

- **GA:** standard 10-day default acceptable.
- **TX:** TREC-style "Termination Option" -- 10 days at $100 option fee (paid from EMD).
- **OH:** 14 days default acceptable.
- **TN:** 7-day minimum per HB 2537 buyer-protection language.

Generated by `contract_generator.py` from per-state config.

### Block 7: Signatures

```
SELLER: _____________________________________  Date: __________
        {seller_full_legal_name}

BUYER:  _____________________________________  Date: __________
        Richard Gee, doing business as Everlight Ventures

WITNESS / NOTARY (where required):
        _____________________________________  Date: __________
```

**Notary requirements per state:**
- GA: not required for PSA but recommended.
- TX: not required.
- OH: not required.
- TN: not required.
- (Notarization separate from notary-required filings like deed transfer at closing.)

---

## Per-state addenda required at generation time

| State | Required additions |
|---|---|
| GA | DBA filing reference (OCGA 10-1-490) in Block 1 |
| TX | DBA filing reference (Form 503 + county) in Block 1; TREC option language in Block 6 |
| OH | Equitable interest language in Block 3 verbatim per HB 132 |
| TN | Wholesaler Disclosure Exhibit (Block 5) signed separately + 7-day minimum inspection |
| NC | **PSA generator REFUSES** -- state closed per HB 797 |
| CA | **PSA generator REFUSES if pre-foreclosure** -- CC 2945/1695 |
| FL | Watch HB 1383 -- if passes, refuses similar to NC; while pending, allowed with standard language |
| IN | Equitable interest language recommended + 3-day rescission disclosure if seller is owner-occupant (IC 32-21-13) |
| AZ | Standard PSA acceptable; no special wholesale-statute language as of 4/2026 |

---

## Documenso self-host queued BEFORE Deal 1 (per Contract Attorney)

HelloSign 3/mo free tier will burn on Deal 1: PSA + Assignment + Disclosure Exhibit + Inspection Addendum = 3-4 envelopes per single deal. Plan v3 Dispatch #13 must ship Documenso self-host BEFORE Deal 1, not after. Forge owns; deploys to Oracle E5 once Oracle reachable.

---

## ESIGN compliance check

HelloSign + Documenso both meet ESIGN Act 4 pillars: intent, consent, attribution, record retention. All 6 active states (GA, TX, OH, IN, AZ, FL) have adopted UETA. No additional state-side adoption work required.

**Audit retention:** signed PSAs and Wholesaler Disclosure Exhibits live in:
- `01_BUSINESSES/Everlight_Ventures/Wholesale/contracts/active_deals/{deal_id}/` (working copy)
- Documenso vault (signed authoritative copy)
- `_logs/contracts/signed/{deal_id}.json` (immutable audit metadata: signer IPs, timestamps, hashes)

7-year retention minimum per industry standard, even though we're not formally regulated to that level yet -- because Move D (regulated SMB consulting) will require it and the same code path ships there.

---

## Sample PSA generation flow

```python
# 03_AUTOMATION_CORE/01_Scripts/generate_psa.py

from outreach.merge_field_gate import MergeFieldGate
from contracts.psa_template import PSA_TEMPLATE
from contracts.exhibits import WHOLESALER_DISCLOSURE_EXHIBIT
from compliance.dba_check import dba_filing_complete
from compliance.state_gate_psa import psa_allowed_for_state

def generate_psa(deal_id: str, lead_id: str, buyer_terms: dict) -> dict:
    lead = PropertyLead.objects.get(id=lead_id)

    # Gate 1: state allowed for wholesale PSA?
    allowed, reason = psa_allowed_for_state(lead.state, lead.pre_foreclosure)
    if not allowed:
        raise PsaBlockedError(f"PSA blocked for {lead.state}: {reason}")

    # Gate 2: DBA filing exists for this state?
    if lead.state in ("GA", "TX") and not dba_filing_complete(lead.state):
        raise PsaBlockedError(
            f"DBA filing not complete for {lead.state}. "
            f"Run dba_filings.md steps before generating PSA."
        )

    # Gate 3: clean title firm available?
    title_firm = TitleCompany.objects.filter(
        metro=lead.metro,
        respa_clean_verified=True,
        license_active=True,
    ).order_by("rank").first()
    if not title_firm:
        raise PsaBlockedError(f"No RESPA-clean title firm for metro {lead.metro}")

    # Render PSA + Exhibit through merge gate. Privacy fields whitelist applies.
    gate = MergeFieldGate()
    psa_text, psa_audit = gate.render(
        PSA_TEMPLATE,
        lead=lead.to_dict(),
        channel="psa_generation",  # gate config allows formal-contract fields
        state=lead.state,
        agent={
            "first_name": "Richard Gee, dba Everlight Ventures",
            "callback": buyer_terms["lucrex_phone"],
            "company": "Everlight Ventures",
        },
    )

    if lead.state == "TN":
        exhibit_text, _ = gate.render(WHOLESALER_DISCLOSURE_EXHIBIT, ...)
    else:
        exhibit_text = WHOLESALER_DISCLOSURE_EXHIBIT  # universal-recommended

    # Send to Documenso for signing.
    documenso_envelope_id = documenso_client.create_envelope(
        documents=[psa_text, exhibit_text],
        signers=[
            {"name": lead.seller_name, "email": lead.seller_email, "role": "seller"},
            {"name": "Richard Gee", "email": "marquise@everlightventures.io", "role": "buyer"},
        ],
        webhook_url="https://hive.everlightventures.io/broker/webhook/documenso/",
    )

    # Record + log.
    Deal.objects.filter(id=deal_id).update(
        stage="contract_generated",
        psa_documenso_envelope_id=documenso_envelope_id,
        title_firm_id=title_firm.id,
    )
    return {"envelope_id": documenso_envelope_id, "psa_audit": psa_audit}
```

Forge implements when Documenso ships (Dispatch #13).

---

## What this PSA does NOT do (scope)

- **Does not handle short sales.** Seller-side bank approval workflow is separate; PSA generator refuses if `lead.short_sale=True` until a `short_sale_addendum.py` ships post-Deal-1.
- **Does not handle subject-to deals.** Different contract structure entirely. Out of scope until creative-finance pipeline (Penny's Q3 expansion).
- **Does not handle tenant-occupied with active lease.** Separate addendum needed for Estoppel + lease assignment. Refuses for now.
- **Does not handle commercial properties.** Residential 1-4 unit only.
- **Does not auto-record.** Memorandum of Agreement filing at the county level (cloud on title to prevent seller back-out) is a separate optional step that's NC-illegal post-HB 797. Future addition.

These exclusions are intentional. The Deal 1 path is single-family residential, owner-occupied or vacant, no tenant complications, GA or DFW. Get the simple flow working first.
