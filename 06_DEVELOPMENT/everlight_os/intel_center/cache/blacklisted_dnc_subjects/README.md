# Blacklisted DNC Subjects

This folder holds OSINT investigation caches and intel artifacts for subjects
on the permanent DNC list. These files are quarantined out of the active
investigation cache so autonomous pipelines (OSINT-to-outreach loops, lead
enrichment, recycler, etc.) cannot pick them back up.

**Rule:** No script reads from this folder. The files exist as evidence /
memory of "do not re-add" only.

Each subject is also in:
- `Wholesale/compliance/dnc_list.json` (canonical DNC)
- `Broker_OS/wholesale_agent/opted_out_emails.json` (opt-out)
- `03_AUTOMATION_CORE/01_Scripts/content_tools/eradication_gate.py` (hardcoded)
- `/root/.claude/projects/-mnt-sdcard-AA-MY-DRIVE/memory/feedback_streubel_permanent_eradication.md` (memory)

Triggered 2026-05-15 by Streubel 2nd-strike: OSINT files were re-cached on
2026-05-12, a week AFTER eradication. That re-caching is the leak Rich flagged:
"never should those DNC contacts be part of an autonomous process."
