# AI Receptionist - 12-Month Financial Model

**Owner**: Cash Mooney (CFO)
**Date**: 2026-04-21
**Status**: Draft. Assumptions listed; adjust as real data comes in.

---

## Assumptions

### Revenue per client
- One-time build fee: $4,500 (collected before go-live; 50% deposit, 50% on launch)
- Monthly recurring: $199 for 200 calls included
- Overage: $50 per 100 extra calls (soft usage, not contractually capped)

### Cost per client (monthly)
| Cost item | Amount | Notes |
|---|---|---|
| Vapi voice + GPT-4 tokens | $100 | Based on 200 calls x 5 min avg x $0.10/min |
| Twilio phone number | $2 | $1 local rental + $1 avg usage |
| Supabase row impact | $0 | Within free tier at 10 clients |
| n8n hosting | $0 | We already run it |
| Monitoring + human ops | $30 | ~1 hour / mo of Forge or Marcus time at internal rate |
| **Total variable** | **$132** | |

### Gross margin per client
- Recurring: $199 - $132 = **$67/mo (34% margin)**
- With 30% markup on overage: +$15 marginal per 100 extra calls
- Build fee: ~70% margin after Forge labor (~$1,350 cost for 25 hours @ $54/hr internal blended, $3,150 margin per build)

### Client acquisition
- First client: Hammer cold outbound from AI Consulting pipeline (no paid ads)
- Conversion rate on discovery calls: 15% assumed (industry standard for productized services)
- Calls to close 1 client: 7 discovery calls (assumed)
- Calls per week Hammer can run: 5 to 10

### Attrition
- Month 1-3: 5% (early cancellation, not a fit)
- Month 4-12: 2% (normal churn)

---

## Scenario A: Conservative (3 sales in 12 months)

| Month | New sales | Active clients | Build rev | MRR | Monthly total | Cum revenue |
|---|---|---|---|---|---|---|
| 1 | 1 | 1 | $4,500 | $199 | $4,699 | $4,699 |
| 2 | 0 | 1 | $0 | $199 | $199 | $4,898 |
| 3 | 0 | 1 | $0 | $199 | $199 | $5,097 |
| 4 | 1 | 2 | $4,500 | $398 | $4,898 | $9,995 |
| 5 | 0 | 2 | $0 | $398 | $398 | $10,393 |
| 6 | 0 | 2 | $0 | $398 | $398 | $10,791 |
| 7 | 0 | 2 | $0 | $398 | $398 | $11,189 |
| 8 | 1 | 3 | $4,500 | $597 | $5,097 | $16,286 |
| 9 | 0 | 3 | $0 | $597 | $597 | $16,883 |
| 10 | 0 | 3 | $0 | $597 | $597 | $17,480 |
| 11 | 0 | 3 | $0 | $597 | $597 | $18,077 |
| 12 | 0 | 3 | $0 | $597 | $597 | $18,674 |

**Totals**: Gross revenue **$18,674**. Costs at 66% variable = $12,323. **Gross profit ~$6,350.**

## Scenario B: Base (5 sales in 12 months)

| Month | New sales | Active clients | Build rev | MRR | Monthly total | Cum revenue |
|---|---|---|---|---|---|---|
| 1 | 1 | 1 | $4,500 | $199 | $4,699 | $4,699 |
| 2 | 1 | 2 | $4,500 | $398 | $4,898 | $9,597 |
| 3 | 0 | 2 | $0 | $398 | $398 | $9,995 |
| 4 | 1 | 3 | $4,500 | $597 | $5,097 | $15,092 |
| 5 | 0 | 3 | $0 | $597 | $597 | $15,689 |
| 6 | 1 | 4 | $4,500 | $796 | $5,296 | $20,985 |
| 7 | 0 | 4 | $0 | $796 | $796 | $21,781 |
| 8 | 1 | 5 | $4,500 | $995 | $5,495 | $27,276 |
| 9 | 0 | 5 | $0 | $995 | $995 | $28,271 |
| 10 | 0 | 5 | $0 | $995 | $995 | $29,266 |
| 11 | 0 | 5 | $0 | $995 | $995 | $30,261 |
| 12 | 0 | 5 | $0 | $995 | $995 | $31,256 |

**Totals**: Gross revenue **$31,256**. Costs = $15,884. **Gross profit ~$15,400.**

## Scenario C: Aggressive (10 sales in 12 months)

| Month | New sales | Active | Build rev | MRR | Monthly total | Cum revenue |
|---|---|---|---|---|---|---|
| 1 | 1 | 1 | $4,500 | $199 | $4,699 | $4,699 |
| 2 | 1 | 2 | $4,500 | $398 | $4,898 | $9,597 |
| 3 | 1 | 3 | $4,500 | $597 | $5,097 | $14,694 |
| 4 | 1 | 4 | $4,500 | $796 | $5,296 | $19,990 |
| 5 | 1 | 5 | $4,500 | $995 | $5,495 | $25,485 |
| 6 | 1 | 6 | $4,500 | $1,194 | $5,694 | $31,179 |
| 7 | 1 | 7 | $4,500 | $1,393 | $5,893 | $37,072 |
| 8 | 1 | 8 | $4,500 | $1,592 | $6,092 | $43,164 |
| 9 | 1 | 9 | $4,500 | $1,791 | $6,291 | $49,455 |
| 10 | 1 | 10 | $4,500 | $1,990 | $6,490 | $55,945 |
| 11 | 0 | 10 | $0 | $1,990 | $1,990 | $57,935 |
| 12 | 0 | 10 | $0 | $1,990 | $1,990 | $59,925 |

**Totals**: Gross revenue **$59,925**. Costs = $29,245. **Gross profit ~$30,680.**

Year-end exit MRR at 10 clients: $1,990. Steady-state annual run-rate: $23,880 recurring alone.

## Key thresholds

- **Month 1 break-even on first build**: Week 3 (after Vapi + Twilio + Piper outreach time). First build is cash-positive end of Month 1.
- **Break-even on full product**: When recurring margin covers Forge's 25-hour build time amortized. At Scenario B (5 clients) that happens Month 6.
- **$1K MRR milestone**: Month 6 in Scenario B, Month 5 in Scenario C.
- **$2K MRR milestone**: Month 10 Scenario C (stated Everlight target for Hive Mind SaaS; receptionist alone could hit it faster).

## Upsell leverage after first client

Each active client becomes a case study. Second sale should close faster (6 discovery calls instead of 7). By 5 clients, testimonial videos + before/after booking stats accelerate conversion to 20%.

## Risks

1. **Vapi price changes**. We are pass-through + markup. If Vapi doubles, our margin compresses unless we re-price. Monitor quarterly.
2. **Client usage spikes**. A client hits 400 calls in a heavy month. Overage is $100 but our Vapi bill is $200. Either enforce caps or pre-bill overage estimates.
3. **High-touch clients**. Some clients will want weekly tuning. Budget 4 hours/mo, escalate to a "Premium Support" $99 addon if they need more.
4. **Slow pipeline**. If Hammer can't close 1/mo, recurring revenue lags. Mitigation: activate Everlight newsletter drip to existing contacts in Month 2.

## Recommendation to Lucrex

Run **Scenario B** as the plan, track against **Scenario C** as the stretch. Pull the trigger if Month 3 closes 2+ clients; hire a part-time SDR at Month 6 to feed Hammer.
