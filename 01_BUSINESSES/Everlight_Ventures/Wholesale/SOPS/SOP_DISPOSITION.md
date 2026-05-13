# SOP -- Disposition (Buyer Match to Closing)

**Trigger:** Deal stage -> `legal_review` (PSA signed, EMD held). Property has clear path to assignment or double-close.
**Owner:** Hammer Knox.
**SLA:** First buyer dispatch within 48 hours of trigger. Buyer signed within 7 days. Close within 14 days of buyer signature.

## Steps

1. Deal moves to `legal_review`. Branded buyer dispo email auto-fires via `hive_deal_orchestrator.py` to top 10 cash buyers in the property's market.
2. First-look window: 24 hours. First verified yes wins (must reply with proof-of-funds).
3. POF check: confirm buyer has approved POFRequest record OR submits one with this dispo.
4. Assignment of contract executed (template in `contracts/templates/Assignment_Agreement_template.md`).
5. Buyer's EMD wired to same title company.
6. Deal stage -> `signed`.
7. Title search continues; clearance + insurance binder ordered.
8. Closing scheduled at title company. Walk-through 24-48h before close.
9. Funding: buyer wires purchase price + assignment fee to title.
10. Close: title disburses, deeds recorded. Deal stage -> `closed_won`.
11. Commission record created. Stripe invoice if assignment-fee billing applies.
12. Post-close: `branded_calendar` follow-up event 7 days out for testimonial request.

## Failure modes + fix

- No buyer signs in 24h first-look: open to broader buyer list (next 50 buyers).
- Buyer fails inspection contingency: re-list to remaining buyer pool. Worst case, double-close out via transactional funding (track in `Deal.close_type="double_close"`).
- Title issue surfaces post-buyer-sign: notify buyer + seller, decide if curable. If not curable: Deal stage `closed_lost`, EMDs returned per PSA.

## KPIs tracked

- `dispatch_to_buyer_signed_days` (target <=7)
- `buyer_signed_to_close_days` (target <=14)
- `assignment_fee_avg` (target $5K-$15K)
