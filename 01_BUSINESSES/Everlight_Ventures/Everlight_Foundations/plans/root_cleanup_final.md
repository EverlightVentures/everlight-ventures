# Implementation Plan - Root Directory Cleanup

## 1. 🔍 Analysis & Context
*   **Objective:** Organize ~50 loose files in the root directory into the established 01-09 folder structure, deduplicating trash and renaming untitled documents for clarity.
*   **Affected Files:** Multiple .docx, .xlsx, .png, and .sh files in the root directory.
*   **Key Dependencies:** Hive Mind Hive Mind Protocol (`HIVE_MIND.md`), existing `01_BUSINESSES` through `09_DASHBOARD` structure.
*   **Risks/Unknowns:** Potential path hardcoding in scripts (addressed in Safety Notes).

## 2. 📋 Checklist
- [ ] Step 1: Create Backup/Trash Directory
- [ ] Step 2: Phase 1 - Trash & Deduplication
- [ ] Step 3: Phase 2 - Rename Untitled Documents
- [ ] Step 4: Phase 3 - Route Files to Destinations
- [ ] Step 5: Verification

## 3. 📝 Step-by-Step Implementation Details

### Step 1: Create Backup/Trash Directory
*   **Goal:** Provide a safe place for duplicates and trash before final deletion.
*   **Action:** Create directory `/mnt/sdcard/AA_MY_DRIVE/08_BACKUPS/Trash_Dedupe/`.
*   **Verification:** `ls /mnt/sdcard/AA_MY_DRIVE/08_BACKUPS/Trash_Dedupe/` exists.

### Step 2: Phase 1 - Trash & Deduplication
*   **Goal:** Move empty or duplicate files to the trash folder.
*   **Action:** Move the following to `/mnt/sdcard/AA_MY_DRIVE/08_BACKUPS/Trash_Dedupe/`:
    *   `Untitled document(4).docx` (empty)
    *   `Untitled document(8).docx` (empty duplicate)
    *   `Untitled document(9).docx` (empty duplicate)
    *   `Untitled document(10).docx` (gibberish)
    *   `Untitled document(13).docx` (empty duplicate)
    *   `Untitled document(14).docx` (empty duplicate)
    *   `Copy of Official $BCARDI(1).png` (MD5 duplicate)
*   **Verification:** Files no longer in root.

### Step 3: Phase 2 - Rename Untitled Documents
*   **Goal:** Give descriptive names to untitled documents before routing.
*   **Action:** Rename the following in the root:
    *   `Untitled document.docx` -> `Money_Philosophy_Quotes.docx`
    *   `Untitled document(1).docx` -> `Money_Philosophy_Facebook_Post.docx`
    *   `Untitled document(2).docx` -> `Poetry_Chase_The_Sun.docx`
    *   `Untitled document(3).docx` -> `Multi_Monitor_Workspace_Setup.docx`
    *   `Untitled document(5).docx` -> `DMV_License_Reinstatement_Letter.docx`
    *   `Untitled document(6).docx` -> `Personal_Bio_Everlight.docx`
    *   `Untitled document(7).docx` -> `Contact_Josh_D_Vacaville.docx`
    *   `Untitled document(11).docx` -> `Book_Outline_Astral_Western.docx`
    *   `Untitled document(12).docx` -> `Tech_Setup_Mobile_to_Tablet.docx`
*   **Verification:** Renamed files exist in root.

### Step 4: Phase 3 - Route Files to Destinations
*   **Goal:** Move files to their logical subfolders.
*   **Action:** Move files according to the sections below:

#### Business: BCARDI Crypto (`01_BUSINESSES/BCARDI_Crypto/`)
*   `Bacardi token INFO.docx`, `BCARDI_Project_Overview.xlsx`, `Copy of Official $BCARDI.png`, `GPT_BCRDI_DS_TRCK.docx`, `Zilcade_BCARDI_Bridge.docx`, `Zilliqa, Bitcoin, and ETF Potential.docx`, `Zilliqa, Gaming, and Market Potential.docx`, `VVS_Vault.docx`, `(Condensed) VASP_VCE.docx`, `Enhanced VASP_VCE.docx`

#### Business: Everlight Ventures (`01_BUSINESSES/Everlight_Ventures/`)
*   `CEO Dashboard (Everlight Logistics).xlsx`, `CEO Dashboard Everlight Logistics.docx`, `Everlight_Logistics- Flow Funds and EcoSystem_.docx`, `Everlight_Ventures.docx`, `Everlight_Ventures(1).docx`, `Everlight_Assistant_SOP.docx`, `Streamline_Approach_To_EL.docx`, `Everlight Token Interest _ Support Form (Responses.xlsx`, `Update_W_Braintree.docx`
*   **Subfolder `04_Automation/`:** `02_Automation_ Everlight Logistics Command Center.docx`, `GAS TO automate Alibaba and chatbots_.docx`, `Automate_GSheet.docx`, `Slack_N8N_Gpt_Output.xlsx`

#### Business: Ideas/Solar (`01_BUSINESSES/_Ideas/Solar/`)
*   `Refined Solar Pitch 1.docx`, `Sfl_Profitablity.docx`, `Sfl_discord_cheat_sheet.docx`, `EcoPulseP-Thread_Output.xlsx`, `Blaze_And_Graze.docx`

#### Personal: Documents/Legal (`05_PERSONAL/00_Documents/Legal/`)
*   `Cdcr_Complaint.docx`, `Cdcr_Complaint(1).docx`, `Updated_Complaint.docx`, `Court_Date.docx`, `Gillie_Detailed_2506397.docx`, `Gillies_Consice_2506397.docx`, `Zoom_Hearing_2506397.docx`, `MAU Defense.docx`, `MAU_REQUEST_DL.docx`, `DMV_License_Reinstatement_Letter.docx`

#### Personal: Life Admin (`05_PERSONAL/05_Life_Admin/`)
*   `Personal_Schedule.xlsx`, `Tim_s address.docx`, `Tim_s status.docx`, `To_Do_List.docx`, `Camping_Trip_List.docx`, `Supplements.docx`, `Tiny_House_Specs_Per_Person.docx`, `Short_Resume_25.txt.docx`, `Retirement strategy_.docx`, `05_29_24_Todo.txt.docx`, `Contact_Josh_D_Vacaville.docx`, `Multi_Monitor_Workspace_Setup.docx`, `Tech_Setup_Mobile_to_Tablet.docx`, `Downsize_Gmail_Steps.docx`, `Email_Label_&_Sub_Folders.docx`

#### Personal: Creative (`05_PERSONAL/03_Creative/`)
*   `Money_Philosophy_Quotes.docx`, `Money_Philosophy_Facebook_Post.docx`, `Poetry_Chase_The_Sun.docx`, `Book_Outline_Astral_Western.docx`, `Sams 4th Superpower Chapter 1.docx`, `TOC__Sam_B4.docx`

#### Personal: Finance (`05_PERSONAL/01_Finance/`)
*   `_Cash App vs PayPal 2024 10-K Reports_.docx`, `Detailed_P2P_Comparison.docx`, `CC_Distribution.xlsx`, `Bank Automation Example.xlsx`

#### Personal: Learning (`05_PERSONAL/04_Learning/`)
*   `AI_FOUNDATIONS_YOUTUBE_LINKS.docx`, `Gpt_Learning_Document.docx`, `Bj_Strategy.docx`

#### Automation Core (`03_AUTOMATION_CORE/`)
*   **Subfolder `01_Scripts/`:** `everlight_orchestrator.sh` (Note: `setup_linux.sh` and `verify_setup.sh` will stay in root per WORKSPACE_MANIFEST.md)
*   **Subfolder `02_Config/`:** (Note: `tmux_config_optimized.conf` will stay in root per WORKSPACE_MANIFEST.md)

## Files STAYING in Root (by design)
CLAUDE.md, GEMINI.md, HIVE_MIND.md, README.md, ORGANIZATION.md, WORKSPACE_MANIFEST.md, MIGRATION_CHECKLIST.md, START_HERE.md, QUICK_COMMANDS.md, TEMPLATES.md, YOUR_ACTION_PLAN.md, .gitignore, setup_linux.sh, verify_setup.sh, tmux_config_optimized.conf
*   **Manual Verification:** Run `ls *.docx`, `ls *.xlsx`, `ls *.png` in the root directory.
*   **Integration Check:** Ensure `everlight_orchestrator.sh` still functions (it uses relative/hardcoded paths to `03_AUTOMATION_CORE` which is maintained).

## 5. ✅ Success Criteria
*   Zero loose `.docx`, `.xlsx`, or `.png` files in the root (excluding system/manifest files).
*   All files present in their designated subfolders.
*   Trash/Duplicates safely stored in `08_BACKUPS/Trash_Dedupe/`.
