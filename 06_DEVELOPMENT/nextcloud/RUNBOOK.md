# Nextcloud on Z Fold -- Runbook
**Everlight Node: Mobile-01**
Stack: Apache 8080 + MariaDB + PHP + Nextcloud
Data: `/mnt/sdcard/AA_MY_DRIVE/.system/nextcloud_data`

---

## One-time Setup (do this once)

### Step 0: Before you start
Edit `install_nextcloud.sh` and set a real DB password:
```
NC_DB_PASS="changeme_secure_password_here"
```
Replace with something strong and save it somewhere safe.

### Step 1: Ensure PRoot-Ubuntu is installed
```bash
# In Termux
pkg install proot-distro
proot-distro install ubuntu
```

**CHECKPOINT 1:** `proot-distro list` shows ubuntu as installed.

---

### Step 2: Run the installer
```bash
# In Termux
proot-distro login ubuntu \
    --bind /mnt/sdcard:/mnt/sdcard \
    -- bash /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/nextcloud/install_nextcloud.sh
```

This takes 10-20 minutes (downloads ~200MB).
You will be prompted to enter an admin password near the end.

**CHECKPOINT 2:** Script prints "INSTALL COMPLETE" with an IP address.

---

### Step 3: Start services and verify LAN access
```bash
# In Termux
proot-distro login ubuntu \
    --bind /mnt/sdcard:/mnt/sdcard \
    -- bash /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/nextcloud/start_services.sh
```

**CHECKPOINT 3:** Open browser on your laptop -> `http://<phone_ip>:8080`
Login with `admin` and the password you set. You should see the Nextcloud dashboard.

---

### Step 4: Set up ngrok (remote access)
```bash
# Still inside or re-enter PRoot:
proot-distro login ubuntu \
    --bind /mnt/sdcard:/mnt/sdcard \
    -- bash /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/nextcloud/setup_ngrok.sh
```

**CHECKPOINT 4:** Script prints a `https://*.ngrok-free.app` URL.
Open that URL from outside your home network and verify login works.

---

### Step 5: Set up auto-start on boot
```bash
# In Termux
cp /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/nextcloud/termux_boot_nextcloud.sh \
   ~/.termux/boot/nextcloud
chmod +x ~/.termux/boot/nextcloud
```

- Install **Termux:Boot** from F-Droid (not Play Store).
- Open Termux:Boot once to register it as an accessibility service.
- Disable battery optimization for Termux in Android Settings > Apps > Termux > Battery.

**CHECKPOINT 5:** Reboot phone, wait 60s, check `http://<phone_ip>:8080` is reachable.

---

## Daily Operations

### Start Nextcloud (after manual stop or crash)
```bash
proot-distro login ubuntu --bind /mnt/sdcard:/mnt/sdcard \
    -- bash /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/nextcloud/start_services.sh
```

### Stop Nextcloud
```bash
proot-distro login ubuntu --bind /mnt/sdcard:/mnt/sdcard \
    -- bash /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/nextcloud/stop_services.sh
```

### Add ngrok tunnel (rotates on each restart)
```bash
proot-distro login ubuntu --bind /mnt/sdcard:/mnt/sdcard \
    -- bash /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/nextcloud/setup_ngrok.sh
```

Then add the new URL to Nextcloud sync clients under server address.

### Run Nextcloud maintenance
```bash
proot-distro login ubuntu --bind /mnt/sdcard:/mnt/sdcard -- bash
cd /var/www/nextcloud
php occ maintenance:mode --on
php occ db:add-missing-indices
php occ maintenance:mode --off
```

---

## Troubleshooting

### "Untrusted domain" error on browser
```bash
# Inside PRoot
cd /var/www/nextcloud
php occ config:system:set trusted_domains 5 --value="<new_ip_or_domain>"
```

### Apache won't start
```bash
cat /mnt/sdcard/AA_MY_DRIVE/_logs/nextcloud/apache.log
# Common fix: another process on port 8080
lsof -i :8080
```

### MariaDB won't start
```bash
cat /mnt/sdcard/AA_MY_DRIVE/_logs/nextcloud/mariadb.log
# If socket missing:
mkdir -p /run/mysqld && chown root /run/mysqld
mysqld_safe --user=root --daemonize
```

### Nextcloud errors / blank page
```bash
cat /mnt/sdcard/AA_MY_DRIVE/_logs/nextcloud/nextcloud.log | tail -30
```

### Phantom Process Killer (Android 12+)
If Termux keeps dying, run from a PC via USB:
```bash
adb shell device_config put activity_manager max_phantom_processes 2147483647
```
Or: Android Settings > Developer Options > "Disable child process limits".

### ngrok URL changed -- Nextcloud sync client error
1. Run `setup_ngrok.sh` to get new URL.
2. Update the server URL in your Nextcloud desktop/mobile client.
3. (Upgrade to ngrok paid plan for a fixed static domain.)

---

## File Map

| File | Purpose |
|------|---------|
| `install_nextcloud.sh` | One-time full install inside PRoot-Ubuntu |
| `start_services.sh` | Start Apache + MariaDB (no systemctl) |
| `stop_services.sh` | Graceful shutdown |
| `setup_ngrok.sh` | Install + start ngrok tunnel |
| `termux_boot_nextcloud.sh` | Boot script for Termux:Boot |
| `RUNBOOK.md` | This file |

**Data locations:**
- Nextcloud files: `/mnt/sdcard/AA_MY_DRIVE/.system/nextcloud_data/`
- Nextcloud app: `/var/www/nextcloud/` (inside PRoot)
- Logs: `/mnt/sdcard/AA_MY_DRIVE/_logs/nextcloud/`
- MariaDB: `/var/lib/mysql/` (inside PRoot)

---

## Security checklist
- [ ] Change default DB password in `install_nextcloud.sh` before running
- [ ] Enable Nextcloud 2FA (Settings > Security > Two-factor authentication)
- [ ] Use a strong admin password (not "admin")
- [ ] Restrict ngrok access with a password if exposing publicly
- [ ] Keep phone locked when ngrok tunnel is active

---

## Sync Clients

**Desktop (Linux/Mac/Windows):** Nextcloud desktop app
Server: `http://<phone_ip>:8080` (LAN) or ngrok URL (remote)

**Android:** Nextcloud app from F-Droid or Play Store
Enable "Auto Upload" for photos to automate media ingestion.

**iOS:** Nextcloud app from App Store
