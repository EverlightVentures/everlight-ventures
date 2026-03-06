# Nextcloud Sync Guide

Two-layer strategy:
- **GitHub** = code, configs, docs (this repo, ~lightweight)
- **Nextcloud** = media, backups, bot data, anything too big for git

---

## Layer 1: GitHub (Code + Logic)

### First push from phone

```bash
cd /mnt/sdcard/AA_MY_DRIVE

# Set your identity (one time)
git config user.email "you@example.com"
git config user.name "Your Name"

# Add remote (create the repo on github.com first, make it PRIVATE)
git remote add origin https://github.com/YOUR_USER/YOUR_REPO.git

# Initial commit
git add -A
git commit -m "Initial hive mind commit"
git push -u origin master
```

### Clone on laptop

```bash
git clone https://github.com/YOUR_USER/YOUR_REPO.git ~/AA_MY_DRIVE
cd ~/AA_MY_DRIVE
bash setup_linux.sh
```

### Daily sync (both devices)

```bash
# Pull latest before working
git pull

# Push changes after working
git add -A && git commit -m "sync" && git push
```

> Tip: run `git status` before committing to confirm no secrets are staged.

---

## Layer 2: Nextcloud (Media + Backups + Bot Data)

### Install Nextcloud server (Linux laptop or always-on machine)

Option A - Snap (simplest):
```bash
sudo snap install nextcloud
# Access at http://localhost/nextcloud
```

Option B - Docker (recommended if you have Docker):
```bash
docker run -d \
  -p 8080:80 \
  -v ~/nextcloud_data:/var/www/html \
  --name nextcloud \
  --restart always \
  nextcloud
# Access at http://localhost:8080
```

After install, create an admin account at the web UI.

### Desktop client (Linux laptop)

```bash
# Ubuntu/Debian
sudo apt install nextcloud-desktop

# Or download AppImage from nextcloud.com/install
```

Configure:
- Server URL: `http://YOUR_SERVER_IP:8080` (or `https://` with cert)
- Sync these folders: `04_MEDIA_LIBRARY/`, `08_BACKUPS/`, `D_Backups/`
- Do NOT sync the full repo root (GitHub handles code)

### Android app (phone)

1. Install "Nextcloud" from F-Droid or Google Play
2. Enter server URL + credentials
3. Enable auto-upload for photos/DCIM if desired
4. Manually sync: `04_MEDIA_LIBRARY/`, `08_BACKUPS/`

### Bot data sync (xlm_bot)

The bot runs live on Oracle Cloud. Its `data/` and `logs/` stay on the VM.
To pull them to laptop for review:

```bash
# One-time: add VM as Nextcloud external storage, OR use rsync
rsync -avz user@ORACLE_VM_IP:~/xlm_bot/data/ ~/AA_MY_DRIVE/xlm_bot/data/
rsync -avz user@ORACLE_VM_IP:~/xlm_bot/logs/ ~/AA_MY_DRIVE/xlm_bot/logs/
```

---

## Secrets - NOT in GitHub, NOT in Nextcloud (encrypted backups only)

Files that must be transferred manually (USB or encrypted SCP):

- `xlm_bot/secrets/config.json` (Coinbase API keys)
- `03_AUTOMATION_CORE/03_Credentials/` (all API keys)

Transfer command:
```bash
# Phone to laptop (run on laptop)
scp -P 8022 user@PHONE_IP:/mnt/sdcard/AA_MY_DRIVE/xlm_bot/secrets/config.json \
    ~/AA_MY_DRIVE/xlm_bot/secrets/config.json
```

Or use a password manager (Bitwarden, 1Password) to store the key values directly.

---

## Path differences: Phone vs Laptop

The `everlight_os/_meta/path_resolver.py` handles this automatically.
On laptop, you can also set:

```bash
export EVERLIGHT_ROOT="$HOME/AA_MY_DRIVE"
```

Scripts that hardcode `/mnt/sdcard/AA_MY_DRIVE` will need the env var or manual update.
Known affected files: `everlight_orchestrator.sh` (TUNNEL_SCRIPT path).

---

## Quick reference

| What | How |
|------|-----|
| Code + docs sync | Git push/pull |
| Media/backups sync | Nextcloud clients |
| Secrets | Manual SCP or password manager |
| Bot logs (Oracle) | rsync from VM |
| Path detection | path_resolver.py auto-detects |
