# Dispatch Log
## Hive Agent Research Drops + Quarterly Intel Snapshots

This directory holds the outputs of:
1. **Quarterly Intel Engine** -- monthly law-change scans (filename: `Intel_YYYY-MM.md`)
2. **Hive agent research drops** -- when Marcus, Justine, Penny, Cipher, financial_safeguard, strategic_modeler are dispatched on specific OS questions (filename: `<Agent>_<topic>_<date>.md`)
3. **Annual recalibration sessions** -- November of each year (filename: `Annual_Recal_YYYY.md`)
4. **Decision logs** -- when major OS decisions are made (filename: `Decision_<topic>_<date>.md`)
5. **Augusta Rule documentation** -- subdirectory `Augusta/` with annual rent comp, calendar, agendas, invoices

## Dispatch Workflow

When a question arises that needs Hive analysis:

1. Lucrex classifies and dispatches via parallel Agent calls
2. Each agent writes their drop to this directory
3. Lucrex converges the drops into a single decision/recommendation
4. Decision saved as `Decision_<topic>_<date>.md`
5. OS files updated based on decision
6. Slack `#ceo-brief` post links to the decision file
7. Blinko note logged with #wealth-os tag

## Naming Convention

```
Intel_2026-04.md                # April 2026 quarterly intel snapshot
Justine_DAPT_evaluation_2026-04-25.md   # Justine's analysis of DAPT timing
Penny_QSBS_modeling_2026-05-01.md       # Penny's QSBS exit modeling
Decision_Hive_Mind_C_corp_2026-05-15.md # Decision to incorporate as C-corp
Annual_Recal_2026.md             # November 2026 annual review
```

## When To Purge

Never. Audit defense requires history. All files retained indefinitely.
