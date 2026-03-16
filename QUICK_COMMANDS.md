# 🚀 EVERLIGHT QUICK COMMANDS

**Your terminal is now supercharged with AI workers and automation tools.**

---

## 🤖 AI WORKERS

### Launch the Hive Mind (Simultaneous Agents)
```bash
./everlight_orchestrator.sh
# or simply map an alias in your .zshrc:
# alias hivemind="/mnt/sdcard/AA_MY_DRIVE/everlight_orchestrator.sh"
```

### Ask GPT from Terminal
```bash
ai "your question here"
```

**Examples**:
```bash
ai "Write a Python function to parse CSV files"
ai "Explain what this error means: ModuleNotFoundError"
ai "Create a business plan outline for a gaming clan"
ai "What's the best way to organize files on Android?"
```

### Ask Perplexity (Research with Sources)
```bash
ppx "your research question"
```

**Examples**:
```bash
ppx "Latest trends in gaming Discord servers 2026"
ppx "Best payment rails for crypto in 2026"
ppx "How to grow TikTok gaming content"
ppx "Current USDC gas fees on Solana"
```

### Gemini Orchestrator (Mode + JSON Contract)
```bash
gmx --mode plan "Create a safe implementation plan for xlm_bot risk module"
gmx --mode explain --output-format text "Explain dashboard.py data flow"
gmx --mode execute "Implement change X and summarize risks"
```

### Start Interactive Gemini Mode Session
```bash
gem-mode execute
gem-mode plan
gem-mode explain
```

### Claude Orchestrator (Mode + JSON Contract)
```bash
clx --mode plan "Create a safe implementation plan for xlm_bot execution changes"
clx --mode review --output-format text "Review dashboard.py for regressions"
clx --mode execute "Implement approved change and include rollback"
```

### Start Interactive Claude Mode Session
```bash
claude-mode execute
claude-mode plan
claude-mode review
```

---

## 📂 FILE MANAGEMENT

### Organize Downloads
```bash
organize                    # Organize files with smart routing
organize --dry-run          # Preview without changes
```

### Merge Duplicate Folders
```bash
merge-folders               # Scan and preview merge plan
merge-folders --execute     # Actually merge folders
```

### Remove Duplicate Files
```bash
dedupe                      # Scan for duplicates (dry run)
dedupe --execute            # Delete duplicates
dedupe --min-size 10240     # Only files >10KB
```

---

## ☁️ PROTON DRIVE SYNC

### Check Sync Status
```bash
sync-status                 # Show what needs syncing
```

### Sync Now
```bash
sync-now                    # Full bidirectional sync
sync-now --sync-only        # Skip file organization
sync-proton                 # Direct rclone sync (one-way)
```

### Test Connection
```bash
rclone lsd protondrive:     # List Proton Drive folders
```

---

## 🔐 SECURITY

### Setup Encrypted Vault
```bash
vault-setup                 # Interactive credential encryption
```

**What it does**:
1. Finds all plaintext credentials
2. Creates encrypted backup
3. Encrypts with GPG (AES256)
4. Deletes plaintext files

---

## 🗂️ NAVIGATION SHORTCUTS

```bash
ev          # Go to Everlight Ventures
llp         # Go to Last Light Protocol
content     # Go to Content Factory
auto        # Go to Automation Core
cdw         # Go to AA_MY_DRIVE root
```

---

## 🔧 SYSTEM OPERATIONS

### Full Cleanup Workflow
```bash
# 1. Organize new files
organize

# 2. Merge duplicate folders
merge-folders --execute

# 3. Remove duplicate files
dedupe --execute

# 4. Sync to Proton Drive
sync-now

# Done! Everything organized and backed up.
```

### Quick Status Check
```bash
# Check Proton connection
rclone lsd protondrive:

# Check sync status
sync-status

# Check disk space
df -h /mnt/sdcard
```

---

## 📊 BEFORE YOU START

### 1. Secure Credentials FIRST
```bash
vault-setup
```
**Do this BEFORE migrating files!**

### 2. Test AI Workers
```bash
# Test GPT (will use existing key location for now)
ai "hello"

# Test Perplexity (if you have API key)
ppx "test query"
```

If GPT works, you're good to go!
If not, you'll need to either:
- Run `vault-setup` to encrypt existing key, OR
- Set API key as environment variable temporarily

### 3. Clean Up Files
```bash
# Preview what will be merged
merge-folders

# Preview what will be deduplicated
dedupe

# If looks good, execute:
merge-folders --execute
dedupe --execute
```

### 4. Sync Everything
```bash
# Initial sync to Proton Drive
sync-proton
```

---

## 💡 PRO TIPS

### AI Worker Best Practices
- **ai**: Fast answers, code generation, explanations
- **ppx**: Research with sources, current events, market data
- **gmx**: Headless Gemini delegation with mode control + JSON output
- **gem-mode**: Interactive mode folder sessions using hierarchical GEMINI.md files
- **clx**: Headless Claude delegation with permission mode + JSON output
- **claude-mode**: Interactive Claude plan/execute/review sessions with project hooks

### File Organization
- Run `organize` regularly (daily)
- Run `dedupe` weekly
- Run `sync-proton` after organizing

### Sync Strategy
- `sync-now`: Smart bidirectional sync (recommended)
- `sync-proton`: Fast one-way push (when you know local is correct)
- Always check `sync-status` first

### Security
- Keep vault passphrase in password manager
- Never commit `.env` or credential files to git
- Test decryption after vault setup:
  ```bash
  gpg --decrypt $EL_HOME/03_AUTOMATION_CORE/03_Credentials/credentials.json.gpg
  ```

---

## 🖥️ ORACLE CLOUD / DASHBOARD ACCESS

### SSH into Oracle VM (from laptop or Termux)
```bash
ssh -i ~/.ssh/oracle_key.pem opc@163.192.19.196
```

### Check bot + dashboard status
```bash
ssh -i ~/.ssh/oracle_key.pem opc@163.192.19.196 \
  "docker ps; curl -s --max-time 3 http://127.0.0.1:8502 | head -c 50"
```

### Restart container (fixes zombie/stale heartbeat)
```bash
ssh -i ~/.ssh/oracle_key.pem opc@163.192.19.196 \
  "cd ~/xlm_bot && docker compose restart xlm-bot"
```

### Fix iptables (if port 8502 blocked on VM -- run once)
```bash
ssh -i ~/.ssh/oracle_key.pem opc@163.192.19.196 \
  "sudo iptables -I INPUT -p tcp --dport 8502 -j ACCEPT && sudo netfilter-persistent save"
```

### Setup ngrok tunnel (bypass firewall entirely)
```bash
# 1. Copy setup script to Oracle VM
rsync -avz /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/ngrok_tunnel.sh \
  -e "ssh -i ~/.ssh/oracle_key.pem" \
  opc@163.192.19.196:~/ngrok_tunnel.sh

# 2. SSH in and run first-time setup (get token from https://dashboard.ngrok.com)
ssh -i ~/.ssh/oracle_key.pem opc@163.192.19.196 \
  "bash ~/ngrok_tunnel.sh --authtoken YOUR_NGROK_TOKEN"

# 3. Start tunnel in background WITH basic auth (recommended)
ssh -i ~/.ssh/oracle_key.pem opc@163.192.19.196 \
  "bash ~/ngrok_tunnel.sh --background --basic-auth 'admin:YOUR_PASSWORD'"

# 4. Start tunnel WITHOUT auth (quick test only)
ssh -i ~/.ssh/oracle_key.pem opc@163.192.19.196 \
  "bash ~/ngrok_tunnel.sh --background"

# 5. Get the URL
ssh -i ~/.ssh/oracle_key.pem opc@163.192.19.196 "cat ~/ngrok_url.txt"
```

### Launch War Room with tunnel
```bash
# Open 4-pane war room + auto-start ngrok tunnel to dashboard
ws --tunnel

# Open war room + tunnel + broadcast a prompt
ws --tunnel "analyze my bot performance"
```

---

## 🚨 TROUBLESHOOTING

### "ai: command not found"
```bash
source ~/.zshrc              # Reload shell config
```

### "ModuleNotFoundError: requests"
```bash
pip install requests
```

### "Proton Drive CAPTCHA"
```bash
# Wait 30-60 minutes, then:
rclone lsd protondrive:
```

### "Permission denied"
```bash
chmod +x $EL_HOME/03_AUTOMATION_CORE/01_Scripts/**/*.py
```

---

## 📖 NEXT STEPS

1. **Secure your system**: `vault-setup`
2. **Test AI workers**: `ai "hello"` and `ppx "test"`
3. **Clean up files**: `merge-folders --execute && dedupe --execute`
4. **Sync to cloud**: `sync-proton`
5. **Read full plan**: `cat /tmp/everlight_autonomous_system_plan.md`

---

**Your terminal is now your command center. Use it wisely.** 🚀
