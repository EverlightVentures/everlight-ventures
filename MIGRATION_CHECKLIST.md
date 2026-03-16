# EVERLIGHT MIGRATION CHECKLIST

**Status**: Phase 1 - Security + Foundation
**Date**: 2026-01-27

---

## ✅ COMPLETED

- [x] Proton Drive connection tested (WORKING!)
- [x] Security audit completed (7 sensitive files found)
- [x] New folder structure created
- [x] README documentation written
- [x] Credential vault script created

---

## 🔄 PHASE 1: SECURITY (DAY 1)

### Step 1: Secure Credentials

**Run the vault setup script:**
```bash
cd /mnt/sdcard/AA_MY_DRIVE
python3 03_AUTOMATION_CORE/01_Scripts/setup_vault.py
```

This will:
1. Collect all credentials (GPT keys, crypto seeds, .env, OAuth)
2. Create encrypted backup
3. Encrypt with GPG (you'll set a passphrase - SAVE IN PASSWORD MANAGER!)
4. Test decryption
5. Delete plaintext files

**Files being secured:**
- `.env` (POS system)
- `seed_phrase_phantom.py` (CRITICAL - crypto wallet)
- `gpt_passkey.md` (API key)
- `client_secret_*.json` (Google OAuth)

**After completion:**
- [ ] Vault created at: `03_AUTOMATION_CORE/03_Credentials/credentials.json.gpg`
- [ ] Backup at: `08_BACKUPS/Credentials_Plaintext_Backup/`
- [ ] Passphrase stored in password manager
- [ ] Test decryption: `gpg --decrypt 03_AUTOMATION_CORE/03_Credentials/credentials.json.gpg`

---

## 📦 PHASE 2: BUSINESS MIGRATION (DAY 1-2)

### Everlight Ventures

- [ ] Move OnyxPOS code: `A_Rich/A_Projects/A_Everlight_Ventures/Mountain Gardens POS/` → `01_BUSINESSES/Everlight_Ventures/01_OnyxPOS/app/`
- [ ] Move business docs from Downloads:
  - [ ] `Everlight_Assistant_SOP.pdf` → `00_Core/SOPs/`
  - [ ] `__ EVERLIGHT LOGISTICS_BP __.pdf` → `00_Core/Business_Plan/`
  - [ ] `Everlight_Logistics_GPT_Training_Doc.pdf` → `00_Core/Training_Docs/`
  - [ ] `Everlight_Slack_CheatSheet_Printable.pdf` → `02_Operations/Slack_Config/`
- [ ] Move n8n workflows: `C_Downloads/everlight_n8n_bundle/` → `04_Automation/n8n_workflows/`
- [ ] Move finance docs: `Everlight_DB_Payroll_With_Totals.csv` → `02_Operations/Finance/`

### Last Light Protocol (NEW)

- [ ] Create brand guidelines document
- [ ] Create Discord server setup plan
- [ ] Move game ROMs (if any): `B_Media/Games/` → `02_Games/`
- [ ] Create content calendar template

### BCARDI Crypto

- [ ] Move media: `BCARDI_OFFICIAL_COIN.*` → `01_Media/`
- [ ] Move project overview: `BCARDI_Project_Overview.csv` → `00_Core/`

### Other Businesses

- [ ] Move Personal Training: `I_Business_Ideas/Personal_Training/` → `01_BUSINESSES/Personal_Training/`
- [ ] Move Publishing: `I_Ebook_sells/` → `01_BUSINESSES/Publishing/01_Projects/`

---

## 🤖 PHASE 3: AUTOMATION MIGRATION (DAY 2-3)

- [ ] Copy Python scripts: `C_My_Docs/A_Python_Scripts/*` → `03_AUTOMATION_CORE/01_Scripts/`
- [ ] Organize by category:
  - [ ] File organizer scripts → `file_organizer/`
  - [ ] Create content tools folder → `content_tools/`
  - [ ] Create business ops folder → `business_ops/`
  - [ ] Create AI workers folder → `ai_workers/`
- [ ] Move n8n workflows: `*.json` files → `03_AUTOMATION_CORE/00_N8N/workflows/`
- [ ] Update script paths to use new structure

---

## 📱 PHASE 4: CONTENT SYSTEM (DAY 3-4)

- [ ] Create brand profiles YAML (Everlight, Last Light, BCARDI)
- [ ] Set up Slack workspace (if not exists)
- [ ] Create Slack channels:
  - [ ] `#content-inbox`
  - [ ] `#content-queue`
  - [ ] `#content-live`
  - [ ] `#content-performance`
  - [ ] `#ops-system`
  - [ ] `#ops-finance`
  - [ ] `#ai-gpt`
- [ ] Create content templates for each platform
- [ ] Build first n8n content workflow

---

## 📂 PHASE 5: MEDIA MIGRATION (DAY 4-5)

- [ ] Move music: `B_Media/Music/` → `04_MEDIA_LIBRARY/Music/`
- [ ] Future photos will go to: `04_MEDIA_LIBRARY/Photos/2026/`
- [ ] Create business media folders in `04_MEDIA_LIBRARY/Photos/Business/`

---

## 👤 PHASE 6: PERSONAL FILES (DAY 5-6)

- [ ] Map ZZ_Rich structure: `python3 map_personal_files.py`
- [ ] Flatten deep nesting (6+ levels → 2-3 levels)
- [ ] Move to appropriate `05_PERSONAL/` subfolders:
  - [ ] Identity docs → `00_Documents/Identity/`
  - [ ] Finance → `01_Finance/`
  - [ ] MMA training → `02_Training/MMA_Notebook/`
  - [ ] Security training → `02_Training/Security_Training/`
  - [ ] Writing projects → `03_Creative/Writing/`

---

## 🧹 PHASE 7: DOWNLOADS CLEANUP (DAY 6-7)

- [ ] Archive large files: `Armbian_*.img.xz` → `08_BACKUPS/System_Snapshots/`
- [ ] Delete installed APKs (after verification)
- [ ] Run deduplication: `python3 01_Scripts/2_2_delete_duplicate_files_auto.py`
- [ ] Organize remaining with: `python3 01_Scripts/file_organizer/organize_files.py`

---

## ☁️ PHASE 8: PROTON DRIVE SYNC (DAY 7-8)

- [ ] Test connection: `rclone lsd protondrive:`
- [ ] Initial sync: `python3 03_AUTOMATION_CORE/01_Scripts/file_organizer/sync_manager.py --resync`
- [ ] Enable watch daemon: `python3 03_AUTOMATION_CORE/01_Scripts/file_organizer/watch_daemon.py &`
- [ ] Clean Proton duplicates: `python3 03_AUTOMATION_CORE/01_Scripts/file_organizer/cleanup_protondrive.py --scan`

---

## 🗑️ PHASE 9: OLD STRUCTURE REMOVAL (DAY 8-9)

⚠️ **ONLY AFTER VERIFYING EVERYTHING MIGRATED**

- [ ] Create snapshot: `tar -czf 08_BACKUPS/pre_cleanup_snapshot_$(date +%Y%m%d).tar.gz A_Rich/`
- [ ] Verify all critical files in new locations
- [ ] Remove old structure: `rm -rf A_Rich/`
- [ ] Update all hardcoded paths in scripts

---

## 🚀 PHASE 10: LAUNCH SYSTEMS (DAY 9-10)

- [ ] Start file organizer watch daemon
- [ ] Start n8n workflows
- [ ] Launch Streamlit dashboard
- [ ] Test Slack commands
- [ ] Test content posting workflow
- [ ] Create first AI-generated post

---

## 📊 SUCCESS METRICS

After completion:
- [ ] All credentials encrypted (0 plaintext secrets)
- [ ] All businesses in separate folders
- [ ] Content system operational
- [ ] 1 post per business published
- [ ] Proton Drive sync running
- [ ] Dashboard accessible

---

## 🆘 TROUBLESHOOTING

### Vault setup fails
- Check GPG installed: `pkg install gnupg`
- Verify file paths exist
- Try manual encryption test

### Proton Drive CAPTCHA
- Wait 30-60 minutes between attempts
- Use: `rclone lsd protondrive:` to test

### Script errors
- Check Python version: `python3 --version` (need 3.7+)
- Install dependencies: `pip install -r requirements.txt`

---

## NEXT IMMEDIATE ACTION

**Run the vault setup script:**
```bash
python3 03_AUTOMATION_CORE/01_Scripts/setup_vault.py
```

This is the MOST CRITICAL step (securing credentials).
Do this FIRST before migrating files.
