# SOP -- Earnest Money Deposit (EMD) Handling

**Trigger:** PSA signed. Buyer has 5 business days to deposit EMD.
**Owner:** Hammer Knox.
**Audit critical:** Title companies expect a clean EMD record; missing or misallocated EMD is the #1 reason title comes back asking questions.

## Steps

1. PSA executed. Buyer has 5 business days from execution date to deposit EMD.
2. Buyer wires or hand-delivers EMD to title company / closing attorney listed in PSA.
3. Title issues a deposit receipt (PDF or letter). Save to `client_files` Django table linked to the Deal.
4. Update `Deal.earnest_money_deposit` (amount), `Deal.emd_status="held"`, `Deal.emd_received_at` (timestamp), `Deal.emd_held_by` (title-co name).
5. Notify seller via branded_mailer that EMD is held, target close date stands.
6. If buyer fails to deliver EMD by deadline: Deal stage -> `at_risk`. 24h grace period. After that, terminate.

## EMD return / forfeiture

- Buyer terminates within inspection contingency: `emd_status="refunded"`, return to buyer within 3 business days.
- Buyer defaults after contingencies removed: `emd_status="forfeited"`, EMD goes to seller as liquidated damages per PSA section 7.
- Deal closes: `emd_status="applied_to_close"`, applied to purchase price.

## Audit trail

Every EMD state change logs an `hive_logger.event` entry. Title-company receipt goes to ClientFile. Deal model carries the lifecycle in 4 fields. This is the immutable record that survives any seller / buyer / regulator question.
