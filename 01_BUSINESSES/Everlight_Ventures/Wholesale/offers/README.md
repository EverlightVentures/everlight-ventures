# Wholesale Offers -- Lane Playbooks

Every distress lane has its own play. One lane closing validates the Hive.

## Lanes

| Lane | Play | Playbook | Scout Feeder |
|---|---|---|---|
| L1 | Code violations / tired landlords | `L1_code_violation.md` (TBD after L2 ships) | county code-enforcement feed |
| L2 | Pre-foreclosure assignment | `L2_preforeclosure_assignment.md` | Zillow pre-foreclosure filter + Propwire |
| L3 | Probate | `L3_probate.md` (TBD) | `rex_probate_scout.py` |
| L4 | Tax delinquency | `L4_tax_delinquency.md` (TBD) | `rex_tax_delinquency_scout.py` |
| L5 | Vacant / absentee owner | `L5_vacant_absentee.md` (TBD) | Propwire absentee filter |
| L6 | Teardown hunt (new-home builders) | `L6_teardown_hunt.md` | Zillow teardown keywords + county assessor |

## Default Offer

`teardown_assignment_80pct.md` is the default pricing play. It auto-applies inside L1 / L2 / L5 when a lead matches the teardown buy-box (see `wholesale/teardown_candidate_check.py`), AND it is the primary offer for the dedicated L6 lane.

## SMS Templates

One template per lane + one for the teardown offer, in `sms_templates/`. Every template must include STOP opt-out language. Justine Park reviews all templates before they go live (and before Twilio A2P 10DLC approval flips `A2P_APPROVED=1`).

## Launch Order

1. L2 ships first (proof-of-concept).
2. L1 + L5 + L6 in parallel after L2 sends its first contract (shared Zillow + Propwire + assessor stack).
3. L3 + L4 wait for county feeds (probate filings + tax delinquency lists take longer to source).
