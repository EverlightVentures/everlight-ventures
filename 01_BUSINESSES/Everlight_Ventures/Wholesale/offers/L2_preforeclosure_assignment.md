# L2: Pre-Foreclosure Assignment

**Status:** Proof-of-concept lane. Ship this first. One closed deal validates the entire Hive wholesale model.

## Thesis

Zillow exposes a "pre-foreclosure" filter. These sellers are behind on their mortgage and heading to auction. Offer to pay off the mortgage balance plus a modest spread, assign the contract to a cash buyer, collect a $10K fee.

## Buy-Box

- Single-family or 2-4 unit
- Pre-foreclosure filing on record (lis pendens, NOD, or scheduled auction)
- Mortgage balance + assignment fee (target $10K) < 75% of ARV
- Seller contact reachable via public records (cyberbackgroundchecks)
- Auction date 30+ days out (time to close)
- State passes the compliance gate: `compliance.state_gate.check(state, channel, "preforeclosure")` must return `ok=True`. Current allow-list: GA, TX, FL, MO, AZ, TN. **NC is OUT as of 2025-10-01 (HB 797 broker-license requirement). CA pre-foreclosure is BLOCKED (CC 2945/1695 criminal exposure).**

## State-Specific Disclosures (enforced at contract generation)

| State | Additional requirement |
|---|---|
| GA | Market contract, not property. Attorney closing mandatory. |
| TX | **SMS BLOCKED** until TX SoS solicitor registration + $10K bond. Voice + mail only for now. SB 1577 equitable-interest disclosure in every marketing piece AND contract. |
| FL | FTSA: SMS manual-click-to-send only. All-party recording disclosure on every call. Foreclosure-consultant rule (FS 501.1377) applies. |
| MO | MO DNC list scrub required (covers SMS). |
| AZ | HB 2747 disclosure: contract must state wholesale-buyer assignment intent. |
| TN | HB 2537 bold-font disclosure + 3-business-day notice to seller before assignment. TN DNC = $500/yr registration. |

## Flow

```
Zillow pre-foreclosure filter (county-scoped)
  -> Propwire address lookup (mortgage balance + recent title activity)
    -> cyberbackgroundchecks (owner name + phone)
      -> Hive outreach (email + SMS once A2P live)
        -> Seller call (Piper / Harrison)
          -> Assignment contract (Quality Assurance Review Period clause)
            -> MaxDispo buyer push (or direct buyer list match)
              -> Escrow (14-21 days)
                -> Title clears -> Fee disbursed
```

## Offer Formula

```
purchase_price   = mortgage_balance + closing_cushion  ($2K)
assignment_fee   = 10_000   (target; range 8K-19K based on spread)
buyer_pays       = purchase_price + assignment_fee
margin_ok_if     = buyer_pays <= 0.75 * ARV
```

## Fire Team

| Role | Agent | Action |
|---|---|---|
| Scout | Rex Blackwell | pull Zillow pre-foreclosure list for target counties daily |
| Qualifier | Frederick "Filter" Banks | run 75% rule + auction-date check |
| Profit | Penny Prescott | validate spread vs comps |
| Matcher | Calvin "Cupid" Hayes | match to cash buyer list or push to MaxDispo |
| Outreach | Piper Reeves | email + SMS + seller call |
| Closer | Harrison Cole | assignment contract + escrow handoff |
| Compliance | Justine Park | pre-clear SMS template + contract clauses |

## Success Metric

1 closed assignment within 60 days of going live, $10K average fee. If that fails, the problem is execution default, not the lane.

## Credentials Required

- `PROPWIRE_API_KEY` (or session cookie if no public API)
- `CYBERBG_API_KEY` (or session cookie)
- `MAXDISPO_API_KEY` + `MAXDISPO_AGENT_ID`
- `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` (hold SMS until `A2P_APPROVED=1`)

## Contract Clause

All L2 assignment contracts MUST include the "Quality Assurance Review Period" clause (see `contract_generator.py`). This protects us if we find title defects or ARV misrepresentation during the review window.

## Starter Counties

Week-1 target list (compliance-gated + active Zillow inventory):
- Fulton County, GA (Atlanta) - **ACTIVE**
- Dallas County, TX - **ACTIVE** (voice/mail only until SMS bond posted)
- Duval County, FL (Jacksonville) - **ACTIVE** (manual SMS only)
- St. Louis County, MO - **ACTIVE**

Dropped / Paused:
- Mecklenburg County, NC (Charlotte) - **PAUSED** per HB 797. Revisit if we license a NC broker.
- Los Angeles County, CA - **NOT FOR L2** (pre-foreclosure blocked by CC 2945/1695). CA is available for non-pre-foreclosure lanes only.

## Compliance Enforcement

Every send through `hive_outreach.py`, every contract generated through `contract_generator.py`, and every call dispatched through `rex_closer.py` MUST call into `compliance.state_gate.check()` first. The gate is the single source of truth for per-state legality. If the gate returns `ok=False`, the action is blocked and logged to Justine Park's weekly compliance audit.
