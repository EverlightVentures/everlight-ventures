# Workspace Reorganization -- 2026-03-06

## What Changed
User reorganized the full folder tree. Key changes from old structure:

### Renames & Moves
- All ventures now under 01_BUSINESSES/Everlight_Ventures/ with Everlight_* naming
- Publishing -> Everlight_Literature
- BCARDI_Crypto -> Everlight_Crypto
- Clash_Carbon/Alley_Kingz -> Alley_Kingz (pulled up one level)
- 01_OnyxPOS -> 01_BUSINESSES/onyx_pos/ (separate from EV tree)
- Loose brand docs -> Everlight_Foundations/ (SVGs, site copy, plans, brand identity)
- Non-EV businesses -> Non_Business/ at root (needs rename from "Non-Buisness")

### New Directories
- Everlight_Cannabis (cannabis venture docs)
- Everlight_Foundations (core brand docs, logos, plans)
- Everlight_Literature (publishing, replaces old Publishing/)

### Removed from Old Tree
- 01_BUSINESSES/Clash_Carbon/ (merged into Alley_Kingz)
- 01_BUSINESSES/BCARDI_Crypto/ (now Everlight_Crypto under EV)
- 01_BUSINESSES/Customer_Support/ (moved to Non_Business)
- 01_BUSINESSES/Fintech_Research/ (merged into Everlight_Crypto or removed)
- 01_BUSINESSES/Mountain Gardens/ (moved to Non_Business)
- 01_BUSINESSES/The_Yung_Printz/ (moved to Non_Business)
- Everlight_Ventures/01_OnyxPOS/ (now 01_BUSINESSES/onyx_pos/)

## Orphan Directories to Clean Up
These exist at workspace root and should NOT be there:
- /everlight_os/ -- duplicate of 06_DEVELOPMENT/everlight_os/
- /dirs created/ -- script error artifact, likely empty
- /echo/ -- script error artifact, likely empty
- /_logs/ -- war room logs, referenced by HIVE_MIND.md (keep but document)
- /_uploads/ -- random screenshots, move to 07_STAGING/Inbox or 04_MEDIA_LIBRARY

## Duplicate Files
Everlight_Foundations has copies of files that ALSO exist at EV root level:
- BRAND_IDENTITY.md, LOVABLE_MASTER_PROMPT.md, LOVABLE_SITE_MASTER.md
- Everlight_Ventures.docx, CEO Dashboard docs, etc.
The Everlight_Foundations copies are the canonical versions. Root copies should be removed.

## Updated Docs
- WORKSPACE_MANIFEST.md -- rewritten with new tree (2026-03-06)
- CLAUDE.md -- updated with new paths and file save rules
- SITE_ARCHITECTURE_V2.md -- new site plan based on deep asset scan
