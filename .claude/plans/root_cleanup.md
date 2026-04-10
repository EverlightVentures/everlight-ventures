# War Room Execution Plan: Root Directory Cleanup

## Context
The Hive Mind war room session `hive_d5d05e06_20260228_034803` analyzed the cluttered root directory and recommended organizing ~50 loose files into the established 01-09 folder structure. The root has 47+ .docx/.xlsx/.png files mixed with 15 "Untitled" docs, duplicates, and misplaced scripts.

## Phase 1: Delete Trash & Duplicates (7 files)

Move to `08_BACKUPS/Trash_Dedupe/` (create folder first):
- `Untitled document(4).docx` - empty
- `Untitled document(8).docx` - empty duplicate
- `Untitled document(9).docx` - empty duplicate
- `Untitled document(10).docx` - gibberish ("nnneeeeeeddd")
- `Untitled document(13).docx` - empty duplicate
- `Untitled document(14).docx` - empty duplicate
- `Copy of Official $BCARDI(1).png` - exact MD5 duplicate of non-numbered version

## Phase 2: Rename Remaining Untitled Docs (9 files)

| Old Name | New Name |
|----------|----------|
| Untitled document.docx | Money_Philosophy_Quotes.docx |
| Untitled document(1).docx | Money_Philosophy_Facebook_Post.docx |
| Untitled document(2).docx | Poetry_Chase_The_Sun.docx |
| Untitled document(3).docx | Multi_Monitor_Workspace_Setup.docx |
| Untitled document(5).docx | DMV_License_Reinstatement_Letter.docx |
| Untitled document(6).docx | Personal_Bio_Everlight.docx |
| Untitled document(7).docx | Contact_Josh_D_Vacaville.docx |
| Untitled document(11).docx | Book_Outline_Astral_Western.docx |
| Untitled document(12).docx | Tech_Setup_Mobile_to_Tablet.docx |

## Phase 3: Route Files to Destinations (~40 moves)

### 01_BUSINESSES/BCARDI_Crypto/
- Bacardi token INFO.docx
- BCARDI_Project_Overview.xlsx
- Copy of Official $BCARDI.png
- GPT_BCRDI_DS_TRCK.docx
- Zilcade_BCARDI_Bridge.docx
- Zilliqa, Bitcoin, and ETF Potential.docx
- Zilliqa, Gaming, and Market Potential.docx
- VVS_Vault.docx
- (Condensed) VASP_VCE.docx
- Enhanced VASP_VCE.docx

### 01_BUSINESSES/Everlight_Ventures/
- CEO Dashboard (Everlight Logistics).xlsx
- CEO Dashboard Everlight Logistics.docx
- Everlight_Logistics- Flow Funds and EcoSystem_.docx
- Everlight_Ventures.docx
- Everlight_Ventures(1).docx
- Everlight_Assistant_SOP.docx
- Streamline_Approach_To_EL.docx
- Everlight Token Interest _ Support Form (Responses.xlsx
- Update_W_Braintree.docx

### 01_BUSINESSES/Everlight_Ventures/04_Automation/
- 02_Automation_ Everlight Logistics Command Center.docx
- GAS TO automate Alibaba and chatbots_.docx
- Automate_GSheet.docx
- Slack_N8N_Gpt_Output.xlsx

### 01_BUSINESSES/_Ideas/Solar/
- Refined Solar Pitch 1.docx
- Sfl_Profitablity.docx
- Sfl_discord_cheat_sheet.docx
- EcoPulseP-Thread_Output.xlsx
- Blaze_And_Graze.docx

### 05_PERSONAL/00_Documents/Legal/
- Cdcr_Complaint.docx
- Cdcr_Complaint(1).docx
- Updated_Complaint.docx
- Court_Date.docx
- Gillie_Detailed_2506397.docx
- Gillies_Consice_2506397.docx
- Zoom_Hearing_2506397.docx
- MAU Defense.docx
- MAU_REQUEST_DL.docx
- DMV_License_Reinstatement_Letter.docx (renamed Untitled 5)

### 05_PERSONAL/05_Life_Admin/
- Personal_Schedule.xlsx
- Tim_s address.docx
- Tim_s status.docx
- To_Do_List.docx
- Camping_Trip_List.docx
- Supplements.docx
- Tiny_House_Specs_Per_Person.docx
- Short_Resume_25.txt.docx
- Retirement strategy_.docx
- 05_29_24_Todo.txt.docx
- Contact_Josh_D_Vacaville.docx (renamed Untitled 7)
- Multi_Monitor_Workspace_Setup.docx (renamed Untitled 3)
- Tech_Setup_Mobile_to_Tablet.docx (renamed Untitled 12)
- Downsize_Gmail_Steps.docx
- Email_Label_& Sub_Folders.docx

### 05_PERSONAL/03_Creative/
- Money_Philosophy_Quotes.docx (renamed Untitled)
- Money_Philosophy_Facebook_Post.docx (renamed Untitled 1)
- Poetry_Chase_The_Sun.docx (renamed Untitled 2)
- Book_Outline_Astral_Western.docx (renamed Untitled 11)
- Sams 4th Superpower Chapter 1.docx
- TOC__Sam_B4.docx

### 05_PERSONAL/01_Finance/
- _Cash App vs PayPal 2024 10-K Reports_.docx
- Detailed_P2P_Comparison.docx
- CC_Distribution.xlsx
- Bank Automation Example.xlsx

### 05_PERSONAL/04_Learning/
- AI_FOUNDATIONS_YOUTUBE_LINKS.docx
- Gpt_Learning_Document.docx
- Bj_Strategy.docx

### 02_CONTENT_FACTORY/03_Assets/
- Voice_Transcript_Prompts.docx
- Personal_Bio_Everlight.docx (renamed Untitled 6)
- GPT_Instructions.docx
- Hands_off_Helulium_Gpt.docx

### 03_AUTOMATION_CORE/01_Scripts/
- everlight_orchestrator.sh
- setup_linux.sh
- verify_setup.sh

### 03_AUTOMATION_CORE/02_Config/
- tmux_config_optimized.conf

### 06_DEVELOPMENT/
- App_List.docx
- Outline_&Strategy.docx

### 01_BUSINESSES/ (root)
- Toby_Collab.docx

## Files STAYING in Root (by design)
CLAUDE.md, GEMINI.md, HIVE_MIND.md, README.md, ORGANIZATION.md, WORKSPACE_MANIFEST.md, MIGRATION_CHECKLIST.md, START_HERE.md, QUICK_COMMANDS.md, TEMPLATES.md, YOUR_ACTION_PLAN.md, .gitignore

## Safety Notes
- everlight_orchestrator.sh hardcoded path already points to 03_AUTOMATION_CORE - safe to move
- All moves use `mv` - no data loss
- Duplicates go to Trash_Dedupe, not deleted - user can review later
- Root folders (A_Rich, B_Media, C_Downloads, etc.) NOT touched - covered by MIGRATION_CHECKLIST separately

## Verification
- `ls /mnt/sdcard/AA_MY_DRIVE/*.docx` should return 0 results
- `ls /mnt/sdcard/AA_MY_DRIVE/*.xlsx` should return 0 results
- `ls /mnt/sdcard/AA_MY_DRIVE/*.png` should return 0 results
