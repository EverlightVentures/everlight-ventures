# Rich Runbook -- 3 Tasks to Activate Hive Governance v2
**Created:** 2026-05-05 15:57 PT
**Purpose:** Step-by-step copy-paste runbook for the 3 manual tasks needed to flip on full Hive Governance v2 (2L/3L tier separation, legal team email comms, outbound halt-lift).

See full inline guide in chat transcript or the linked sources at the bottom.

## Task 1 -- Anthropic API Keys (2L/3L separation)
- Link: https://console.anthropic.com/settings/keys
- Create: `compliance-2L` and `audit-3L`
- Drop into `/AA_MY_DRIVE/.env` as `ANTHROPIC_API_KEY_COMPLIANCE` and `ANTHROPIC_API_KEY_AUDIT`
- Verify: `python3 -c "from two_line_dispatch import api_key_for_agent; print(api_key_for_agent('state_lo_hines_tn'))"`

## Task 2 -- Email Forwarders (21 aliases on everlightventures.io)
- Link: https://ap.www.namecheap.com/Domains/DomainControlPanel/everlightventures.io/email-forwarding
- Backup: https://app.improvmx.com/dashboard/everlightventures.io
- Tier A (7 legal): theo, imani, heck, priya, wen, lia, ethics
- Tier B (14 state): marvin, daria, king, jasper, stella, cleo, phin, lo, mags, ellie, mona, walt, bernie, lupe
- All forward to: admin@everlightventures.io

## Task 3 -- Halt-Lift Sequence
1. `bash /AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/halt_check.sh` (must be green except intentional halt WARN)
2. `python3 restart_harness.py --phase=test` (expect 14/14 PASS)
3. Justine Slack signoff in #compliance
4. `python3 restart_harness.py --phase=warm` (one Chris Ulander vip_reply)
5. Marcus Slack signoff in #compliance
6. Edit /AA_MY_DRIVE/.env: WHOLESALE_OUTBOUND_HALT=1 -> 0
7. `python3 restart_harness.py --phase=cold` (production)

## Emergency re-halt (any time)
`sed -i 's/^WHOLESALE_OUTBOUND_HALT=0/WHOLESALE_OUTBOUND_HALT=1/' /AA_MY_DRIVE/.env`

## Recommended execution order
1. Task 2 (10 min, zero risk)
2. Task 1 (3 min, activates 2L/3L separation)
3. Task 3 (highest-stakes; do last)

## References
- Governance v2: /AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/hive_mind/HIVE_GOVERNANCE_V2.md
- Action Layer: /AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/hive_mind/HIVE_ACTION_LAYER.md
- Streubel postmortem: /AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/INBOUND_WATCH_GAPS_2026-04-26.md
- Insurance packet: /AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/insurance/quote_request_packet_2026-05-05.md
- Audit log repo: https://github.com/EverlightVentures/everlight-audit-log
