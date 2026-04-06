# Workspace Cleanup Plan -- 2026-03-06

## Status: AWAITING APPROVAL

---

## 1. DELETE EMPTY SCRIPT-ERROR DIRECTORIES (safe)
Both are completely empty -- created by a broken shell command.
```
rm -rf "/mnt/sdcard/AA_MY_DRIVE/dirs created/"
rm -rf /mnt/sdcard/AA_MY_DRIVE/echo/
```

## 2. MERGE ROOT everlight_os/ INTO 06_DEVELOPMENT/everlight_os/
Root orphan only has telemetry.jsonl (513 lines of hive session logs).
Append to the real location, then delete orphan.
```
cat /mnt/sdcard/AA_MY_DRIVE/everlight_os/hive_mind/telemetry.jsonl \
  >> /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/hive_mind/telemetry.jsonl
rm -rf /mnt/sdcard/AA_MY_DRIVE/everlight_os/
```

## 3. MOVE _uploads/ SCREENSHOTS TO 07_STAGING/Inbox/
These are Slack/Instagram/Facebook screenshots from March 5.
```
mv /mnt/sdcard/AA_MY_DRIVE/_uploads/* /mnt/sdcard/AA_MY_DRIVE/07_STAGING/Inbox/ 2>/dev/null
rmdir /mnt/sdcard/AA_MY_DRIVE/_uploads/
```

## 4. RENAME Non-Buisness -> Non_Business (fix typo)
```
mv /mnt/sdcard/AA_MY_DRIVE/Non-Buisness /mnt/sdcard/AA_MY_DRIVE/Non_Business
```

## 5. MOVE STALE ROOT .md FILES TO 08_BACKUPS/
These are outdated docs from Jan-Feb that reference the old structure:
- MIGRATION_CHECKLIST.md (Jan 27, references old A_Rich/ structure)
- START_HERE.md (Jan 27, Phase 1 setup guide -- long done)
- YOUR_ACTION_PLAN.md (Jan 27, old action items)
- TEMPLATES.md (Feb 25, old templates)
- ORGANIZATION.md (Feb 25, old 25-agent org chart -- paths are wrong)
- QUICK_COMMANDS.md (Feb 26, old command reference)
- README.md (Feb 17, just says "AA_MY_DRIVE" -- useless)
```
mkdir -p /mnt/sdcard/AA_MY_DRIVE/08_BACKUPS/Stale_Root_Docs_2026_03/
mv /mnt/sdcard/AA_MY_DRIVE/MIGRATION_CHECKLIST.md \
   /mnt/sdcard/AA_MY_DRIVE/START_HERE.md \
   /mnt/sdcard/AA_MY_DRIVE/YOUR_ACTION_PLAN.md \
   /mnt/sdcard/AA_MY_DRIVE/TEMPLATES.md \
   /mnt/sdcard/AA_MY_DRIVE/ORGANIZATION.md \
   /mnt/sdcard/AA_MY_DRIVE/QUICK_COMMANDS.md \
   /mnt/sdcard/AA_MY_DRIVE/README.md \
   /mnt/sdcard/AA_MY_DRIVE/08_BACKUPS/Stale_Root_Docs_2026_03/
```

## 6. KEEP AT ROOT (these are correct)
- CLAUDE.md (updated today)
- GEMINI.md (updated today)
- HIVE_MIND.md (active protocol doc)
- WORKSPACE_MANIFEST.md (updated today)
- tree.txt (reference, regenerate as needed)

## 7. _logs/ STAYS AT ROOT
Referenced by HIVE_MIND.md for war room logs. It's the right place.
No action needed -- just documenting.

---

## DOCS ALREADY UPDATED
- WORKSPACE_MANIFEST.md -- rewritten with new tree
- CLAUDE.md -- updated with new paths + file save rules
- GEMINI.md -- updated with new paths + file save rules
- .claude/memory/workspace_reorg_2026_03_06.md -- change log created
