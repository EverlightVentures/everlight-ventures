# trace_confidence Field Design

**Plan reference:** v3 Move A + Dispatch #10.
**Owner:** Filter Banks (lead qualifier) + Forge (build).
**Why:** Per Filter's round-3 critique: without `trace_confidence`, "hot lead" lies. Skip-trace cascade hit rate is realistic 35-45% on owner-occupied, 15% on LLC. A hot 65-BANT with 0.85 trace beats a hot 80-BANT with 0.20 trace, but current scoring treats them identically. This field corrects that.

---

## Field schema

```python
# Add to broker_ops/models.py PropertyLead model
trace_confidence: float  # 0.0 - 1.0
trace_confidence_source: str  # which-step-of-cascade-set-it
trace_confidence_set_at: datetime
```

**Range:** 0.0 (no skip-trace data) to 1.0 (multi-source confirmed).
**Set by:** the skip-trace cascade module (Dispatch #2). Each cascade step writes a confidence value:

| Cascade step | Outcome | trace_confidence | trace_confidence_source |
|---|---|---|---|
| TruePeopleSearch returns name + phone, owner-occupied | Best case | 0.90 | "tps_owner_occupied" |
| TruePeopleSearch returns name + phone, owner has LLC | Decent | 0.55 | "tps_llc" |
| TruePeopleSearch 403s, FastPeopleSearch returns name + phone | Fallback hit | 0.65 | "fps_owner_occupied" |
| All search engines 403, Cuyahoga records returns owner name only (no phone) | Partial | 0.35 | "county_records_name_only" |
| County records + ZabaSearch phone match against name | Triangulated | 0.75 | "county_plus_zaba" |
| All sources fail | No data | 0.0 | "none" |
| Owner self-confirmed via warm contact (called us back) | Strongest | 1.0 | "owner_self_confirmed" |

---

## Integration into BANT score

Current scoring (per `lead_prioritizer.py`):

```python
score = (
    motivation_signal * 0.35 +
    authority_signal * 0.25 +
    timing_signal * 0.20 +
    affordability_signal * 0.20
)
# 0-100, threshold for "hot" = 70
```

**v2 with trace_confidence:**

```python
raw_score = (
    motivation_signal * 0.35 +
    authority_signal * 0.25 +
    timing_signal * 0.20 +
    affordability_signal * 0.20
)
# Authority signal is multiplied by trace_confidence -- you can't have
# authority over a contact you can't reach.
authority_signal_adjusted = authority_signal * trace_confidence
raw_score = (
    motivation_signal * 0.35 +
    authority_signal_adjusted * 0.25 +
    timing_signal * 0.20 +
    affordability_signal * 0.20
)
# Effective conversion = score x trace_hit_rate x reply_rate.
# Penny dashboard shows BOTH raw_score AND effective_score.
effective_score = raw_score * trace_confidence
```

**Why authority_signal gets the multiplier specifically:**
The "authority" signal in BANT is "are you the decision-maker we can reach." If trace_confidence is 0.20, we're 80% sure we have the WRONG person on the other end of the phone. Their authority is irrelevant if it isn't them. Multiplying authority by trace_confidence captures this directly.

**Why effective_score is also computed (separate from raw):**
For Penny's 30-day commit (3 PSAs in pipeline + 1 EMD escrow), she needs to call leads with the highest expected conversion, not the highest raw score. effective_score = raw_score * trace_confidence gives her that ranking.

---

## ATL/DFW geo-gate (Filter spec)

In addition to trace_confidence, Filter's ATL/DFW push raises the hot-lead floor to 75 raw_score AND requires geo-match:

```python
def is_hot_lead(lead) -> bool:
    if lead.metro not in ("ATL", "DFW"):
        return False  # geo gate -- Q2 push is metro-restricted
    if lead.state != lead.metro_state_match():  # ATL=GA, DFW=TX
        return False  # cross-state mismatch
    if lead.raw_score < 75:
        return False
    if lead.effective_score < 50:  # raw 75 * trace 0.67 floor
        return False
    return True
```

Effective floor of 50 means: 0.50 trace_confidence is the minimum (don't waste calls below that). Below 0.50, send direct mail (no contact required) instead.

---

## Penny's dashboard widget

New widget on :8504 dashboard, top of Wholesale section:

```
HOT LEADS (ATL + DFW only) -- 14 active
┌──────────────┬─────────┬───────┬──────────┬──────┐
│ Address      │ Metro   │ Raw   │ Trace    │ Eff. │
├──────────────┼─────────┼───────┼──────────┼──────┤
│ 123 Main     │ ATL     │ 82    │ 0.85     │ 70   │
│ 456 Oak      │ DFW     │ 91    │ 0.40     │ 36   │ <-- Filter says: skip, send mail
│ 789 Pine     │ ATL     │ 75    │ 0.92     │ 69   │
│ 1010 Birch   │ DFW     │ 88    │ 0.65     │ 57   │
│ ...          │         │       │          │      │
└──────────────┴─────────┴───────┴──────────┴──────┘

CALL ORDER (sorted by Effective Score descending):
1. 123 Main      Atlanta, GA   Eff. 70  raw 82  trace 0.85
2. 789 Pine      Atlanta, GA   Eff. 69  raw 75  trace 0.92
3. 1010 Birch    Plano, TX     Eff. 57  raw 88  trace 0.65
...
```

Penny calls in effective-score order, NOT raw-score order. The 88-raw / 0.40-trace lead drops to "send direct mail" and skips voice contact -- saves Piper's 8-12 daily call budget for higher-conversion leads.

---

## Backwards compatibility

Pre-cascade leads have `trace_confidence = 0.0`. They are excluded from hot-lead criteria (effective_score floor of 50 catches this). Once the cascade runs (Dispatch #2 -- Oracle-side), batch-update existing leads:

```python
# 03_AUTOMATION_CORE/01_Scripts/backfill_trace_confidence.py
for lead in PropertyLead.objects.filter(trace_confidence=0.0).order_by("raw_score"):
    if not lead.email and not lead.phone:
        lead.trace_confidence = 0.0  # truly no data
    else:
        # Run cascade fresh on existing leads -- may raise from 0 to 0.4-0.9
        result = skip_trace_cascade.run(lead.address, lead.owner_name)
        lead.trace_confidence = result.confidence
        lead.trace_confidence_source = result.source
        lead.trace_confidence_set_at = now()
    lead.save()
```

This is a Wave 2 task once cascade is built (Oracle-side, blocked on Oracle reachability).

---

## Why this matters for the Apple analog

Filter's rule -- "without trace_confidence, hot lead lies" -- is structurally the same as Charles's Operator Truth rule -- "without 4-point check, audit lies." Both are chokepoints that prevent the system from confidently producing wrong outputs.

In Apple terms: this is on-device fixed-cost compute applied to the lead-quality problem. The cascade pays a fixed compute cost once per lead; effective_score then comes free for every dispatch call thereafter. Like the on-device AI bet, the marginal cost approaches zero once the chokepoint is built.

---

## Validation tests once shipped

- [ ] PropertyLead model migration adds trace_confidence + trace_confidence_source + trace_confidence_set_at columns.
- [ ] `lead_prioritizer.py` returns BOTH raw_score and effective_score, with effective_score = raw_score * trace_confidence.
- [ ] Hot-lead floor enforces effective_score >= 50.
- [ ] Penny's dashboard widget shows three columns: Raw / Trace / Eff and sorts by Eff descending.
- [ ] Backfill script runs cleanly against existing 400+ leads, raises 60-80% of them above 0.0 trace.
- [ ] Effective-score ordering produces a different top-10 than raw-score ordering (proves the field actually changes behavior; if rankings match, trace data is uniform and the field is decorative).
