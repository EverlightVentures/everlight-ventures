# Title Company Ranking Protocol

After each deal closes (or dies), update the company's row in both the CSV and the JSON. After 3 deals with the same company, the ranking may auto-promote or demote.

## Fields updated per closed deal

| Field | How to score |
|---|---|
| `deals_closed` | +1 |
| `avg_close_days` | rolling average of calendar days from signed contract to funds disbursed |
| `ease_score` | 1-10. Responsiveness + paperwork clarity + willingness to handle assignment / double-close. 10 = returned every call same day, ran the file with zero hand-holding. 1 = ghosted us or demanded we bring our own A-B funds. |
| `profit_score` | 1-10. Net fee to Everlight after escrow / title fees vs expected. 10 = we netted full target fee. 1 = escrow fees cut 30%+ off the assignment fee. |
| `last_contact` | ISO date of last substantive contact |

## Re-rank rules (apply after every 3rd closed deal per company)

1. Compute `composite = (ease_score + profit_score) / 2` for each company in a state.
2. Sort descending by composite.
3. Top company becomes `primary: true`; all others `primary: false`.
4. Write back to both `title_companies.json` and `title_companies.csv`.
5. Post the new ranking to `#compliance` Slack channel so Harrison and Piper always know who to call first.

## Dead-deal penalty

If a deal dies specifically because the title company refused to close, killed an assignment, or held up paperwork past 30 days:
- `ease_score` floor = 2 (can't be higher than 2 afterward)
- Flag `investor_friendly: no` and move to rank 5 for that state
- Add note with dead-deal ID

## New company addition

When Piper finds a new investor-friendly closer by referral:
- Add to CSV at rank 99 (manual test tier)
- Use them on ONE low-risk deal
- Score after close; if composite >= 7, slot in by composite
- If composite < 5, retire them from the list

## Who maintains this

- Harrison Cole (closer) updates scores after every deal close
- Justine Park (compliance) reviews quarterly and enforces that the primary company for each state meets current-year state compliance (attorney-state vs title-company-state, investor-friendly confirmed)
- Chart Dawson (analytics) pulls a quarterly ranking report and posts to `#compliance`

## Current primaries (as of 2026-04-22)

| State | Primary | Backup |
|---|---|---|
| GA | Georgia Title & Escrow Co LLC | Morris Hardwick Schneider |
| TX | Texas Title | First Option Title |
| FL | Sunshine Title Corporation | Marina Title |
| MO | Investors Title Company | Eastern Title |
| AZ | University Title Agency | Magnus Title |
| TN | CLOSED Title - Nashville | Wagon Wheel Title & Escrow |
| NC | (paused - no primary until licensure resolved) | (paused) |

Initial rankings come from Apr 2026 research sweep based on public investor-friendly claims + BiggerPockets reputation. Rankings will adjust as real deal data arrives.
