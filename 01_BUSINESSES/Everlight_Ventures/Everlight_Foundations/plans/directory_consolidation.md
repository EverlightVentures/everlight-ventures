# Implementation Plan - Directory Consolidation

## 1. 🔍 Analysis & Context
*   **Objective:** Move all loose, non-uniform root directories into the established 01-09 folder structure to achieve a unified, organized workspace.
*   **Affected Files/Directories:** ~30 root directories including legacy folders (`A_Rich`, `A_Projects`) and app-specific folders (`echo_mind`, `xlm_bot`).
*   **Key Dependencies:** Hive Mind Protocol, existing 01-09 architecture.
*   **Risks/Unknowns:** Potential path breakage for active Python scripts or tmux configurations (addressed in Safety Notes).

## 2. 📋 Checklist
- [ ] Step 1: Business Layer Migration (01_BUSINESSES)
- [ ] Step 2: Content & AI Layer Migration (02_CONTENT_FACTORY)
- [ ] Step 3: Automation Layer Migration (03_AUTOMATION_CORE)
- [ ] Step 4: Media Layer Consolidation (04_MEDIA_LIBRARY)
- [ ] Step 5: Personal & Documents Migration (05_PERSONAL)
- [ ] Step 6: Development & Projects Migration (06_DEVELOPMENT)
- [ ] Step 7: Staging & Backups Migration (07/08_BACKUPS)
- [ ] Step 8: Final Cleanup & Root Pruning

## 3. 📝 Step-by-Step Implementation Details

### Step 1: Business Layer Migration (`01_BUSINESSES/`)
*   **Goal:** Consolidate all business-related folders into `01_BUSINESSES`.
*   **Action:**
    *   Move `Everlight_Logistics/` -> `01_BUSINESSES/Everlight_Ventures/`
    *   Move `Shared_W_Ceo/` -> `01_BUSINESSES/Everlight_Ventures/Shared/`
    *   Move `Solar_Stuff/` -> `01_BUSINESSES/_Ideas/Solar/`
    *   Move `Clash_Carbon/` -> `01_BUSINESSES/`
    *   Move `The_Yung_Printz/` -> `01_BUSINESSES/`
*   **Verification:** `ls 01_BUSINESSES/` shows new directories.

### Step 2: Content & AI Layer Migration (`02_CONTENT_FACTORY/`)
*   **Goal:** Move content inputs and AI strategy files.
*   **Action:**
    *   Move `GPT_Conversatins/` -> `02_CONTENT_FACTORY/00_Inbox/`
    *   Move `GPT_Promts_Training/` -> `02_CONTENT_FACTORY/03_Assets/Prompts/`
    *   Move `GEMINI/AI_Workteams/` -> `02_CONTENT_FACTORY/`
*   **Verification:** `ls 02_CONTENT_FACTORY/` shows new directories.

### Step 3: Automation Layer Migration (`03_AUTOMATION_CORE/`)
*   **Goal:** Move automation workflows and scripts.
*   **Action:**
    *   Move `Slack_Workflow/` -> `03_AUTOMATION_CORE/05_Slack_Workflows/`
    *   Move `echo_mind/` -> `03_AUTOMATION_CORE/06_AI_Tools/echo_mind/`
*   **Verification:** `ls 03_AUTOMATION_CORE/` shows new directories.

### Step 4: Media Layer Consolidation (`04_MEDIA_LIBRARY/`)
*   **Goal:** Merge legacy media folders into the library.
*   **Action:**
    *   Move `B_Media/Music/` -> `04_MEDIA_LIBRARY/Music/`
    *   Move `B_Media/Photos/` -> `04_MEDIA_LIBRARY/Photos/`
    *   Move `B_Media/Videos/` -> `04_MEDIA_LIBRARY/Videos/`
*   **Verification:** `ls 04_MEDIA_LIBRARY/` shows updated counts.

### Step 5: Personal & Documents Migration (`05_PERSONAL/`)
*   **Goal:** Consolidate personal life admin and finance.
*   **Action:**
    *   Move `Finances/` -> `05_PERSONAL/01_Finance/` (Merge)
    *   Move `Daily_Schedule/` -> `05_PERSONAL/05_Life_Admin/`
    *   Move `Workout_Plans/` -> `05_PERSONAL/05_Life_Admin/`
    *   Move `FSL_ID/` -> `05_PERSONAL/00_Documents/Identity/`
    *   Move `Amazon_Ebooks/` -> `05_PERSONAL/04_Learning/`
    *   Move `Documents/` -> `05_PERSONAL/00_Documents/`
*   **Verification:** `ls 05_PERSONAL/` shows new directories.

### Step 6: Development & Projects Migration (`06_DEVELOPMENT/`)
*   **Goal:** Move all source code and system projects.
*   **Action:**
    *   Move `everlight_os/` -> `06_DEVELOPMENT/`
    *   Move `xlm_bot/` -> `06_DEVELOPMENT/`
    *   Move `A_Projects/` -> `06_DEVELOPMENT/`
    *   Move `saas_factory/` -> `06_DEVELOPMENT/`
    *   Move `GetMyOS/` -> `06_DEVELOPMENT/`
    *   Move `RG_OS/` -> `06_DEVELOPMENT/`
*   **Verification:** `ls 06_DEVELOPMENT/` shows new directories.

### Step 7: Staging & Backups Migration (`07/08_BACKUPS/`)
*   **Goal:** Archive staging area and external backups.
*   **Action:**
    *   Move `C_Downloads/` -> `07_STAGING/`
    *   Move `Takeout/` -> `08_BACKUPS/`
    *   Move `D_Backups/` -> `08_BACKUPS/`
    *   Move `D_TOOLKIT/` -> `08_BACKUPS/`
    *   Move `ProtonDrive/` -> `08_BACKUPS/`
    *   Move `My PC/` -> `08_BACKUPS/System_Artifacts/`
    *   Move `Google Earth/` -> `08_BACKUPS/System_Artifacts/`
    *   Move `A_Rich/` -> `08_BACKUPS/Trash_Dedupe/`
*   **Verification:** `ls 08_BACKUPS/` shows new directories.

## 4. 🧪 Testing Strategy
*   **Manual Verification:** Run `ls /mnt/sdcard/AA_MY_DRIVE/` and ensure only 01-09 directories, system files, and the plan directory remain.
*   **Broken Path Check:** Run `everlight_orchestrator.sh` and ensure it still initializes the war room correctly.

## 5. ✅ Success Criteria
*   Root directory contains only directories `01_BUSINESSES` through `09_DASHBOARD` plus system/manifest files.
*   All legacy folders are consolidated or archived.
*   Uniform naming across all major top-level folders.
