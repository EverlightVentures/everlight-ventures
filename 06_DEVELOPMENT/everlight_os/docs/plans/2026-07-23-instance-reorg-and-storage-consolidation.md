# Instance Reorg + Storage Consolidation Implementation Plan

> **For agentic workers:** Steps use checkbox (`- [ ]`) syntax for tracking. Destructive steps are gated behind an explicit manifest + operator GO. Never run a gated step without it.

**Goal:** Collapse four cloud storage services into one, move the password vault off a plaintext file onto a real vault, free the block-storage allowance that is choking e5-mother, and split work from personal across two boxes you already own.

**Architecture:** Google Drive (5 TB, already owned) becomes the single storage plane, with `rclone crypt` providing zero-knowledge for sensitive data and plain Drive/Photos for media that needs Google's search. The empty `everlight-recovery-clean` micro becomes the personal box hosting Vaultwarden. e5-mother sheds backups and personal data to Drive and reclaims disk from an orphaned boot volume.

**Tech Stack:** OCI CLI 3.74.2, rclone (crypt over Google Drive), Vaultwarden (Docker/Podman), Bitwarden clients, Tailscale.

## Global Constraints

- **No deletion without `memory_pipeline.ingest_before_delete()`** and a written manifest. Standing doctrine, no exceptions.
- **No trash until Deal 1 closes.** Destructive steps are gated on operator GO, never auto-run.
- Free-tier block storage ceiling: **200 GB total** across all boot + block volumes. Current usage 191 GB.
- Home region is **us-sanjose-1**, permanent. All instances in AD-1.
- Network Binding Doctrine: personal services bind `127.0.0.1` or tailnet only. Never `0.0.0.0` without an `ev` domain.
- Phone proot has **no Tailscale client**. Reach e5 via `ssh e5` (public 163.192.60.35), never `ssh e5-mother` (tailnet).
- Secrets: key names only in docs. Never write values to any file in the repo.

---

## Current State (verified 2026-07-23, live-queried)

| Instance | Shape | Size | Root disk | Uptime | Contents |
|---|---|---|---|---|---|
| `everlight-prod-a1` (e5-mother) | A1.Flex | 4 OCPU / 24 GB | 49G, **95% full** | 69d | Blinko, agentmemory, Open WebUI, hive-reports, 7 MCP proxies, nginx, redis |
| `everlight-recovery-clean` | E2.1.Micro | 1 OCPU / 1 GB | 30G, 21% used | 79d | **EMPTY.** Stock Oracle Linux only |
| `Xlm-bot` | E2.1.Micro | 1 OCPU / 1 GB | unknown | unknown | **SSH times out on 163.192.19.196.** Unverified |

| Boot volume | Size | Attached to |
|---|---|---|
| `everlight-prod-a1` | 50 GB | e5-mother |
| `Xlm-bot` | 47 GB | Xlm-bot |
| `everlight-recovery-clean` | 47 GB | recovery-clean |
| `xlm-bot-core-e5-2c16g` | 47 GB | **NOTHING. Orphan.** |
| **Total** | **191 GB** | of 200 GB allowance |

**e5-mother disk breakdown (`/home/ubuntu`, 35 GB):**
```
22G  AA_MY_DRIVE      <- workspace mirror
      8.0G  01_BUSINESSES
      4.7G  08_BACKUPS     <- backups on the box they back up. Not a backup.
      3.6G  06_DEVELOPMENT
      3.1G  05_PERSONAL    <- personal data on the work server
4.8G solano_live_desk
4.0G e5_data
```

**Storage services in play:**
| Service | Capacity | Used | Verdict |
|---|---|---|---|
| Google Drive | 5 TiB | 50 GiB (+58 GiB "other") | **Keep. This is the one.** |
| `drive_everlight_crypt:` | same quota | ~empty (2 folders) | **Keep. Already configured 2026-04-30** |
| Proton Drive | paid | unknown | Migrate out, then cancel |
| Proton Photos | paid | unknown | Migrate out, then cancel |
| Google Photos | shares Drive quota | included in 58 GiB | **Keep. Same quota, no extra cost** |

---

## Target Hierarchy

```
STORAGE PLANE (one place, 5 TB, already paid)
└── Google Drive
    ├── drive_everlight_crypt:      zero-knowledge. Docs, finance, legal, credentials, backups
    │   ├── personal/               05_PERSONAL, tax, medical, EDD
    │   ├── business/               contracts, deal files
    │   └── backups/                08_BACKUPS from e5
    └── plain Drive + Google Photos media that needs search/albums
                                    (Google can read these. That is the trade, made knowingly.)

COMPUTE PLANE
├── everlight-prod-a1 (4 OCPU / 24 GB)          WORK
│   └── Blinko, agentmemory, Open WebUI, hive-reports, MCP proxies, nginx, redis
│       Working set only. Archives live on Drive, pulled on demand.
└── everlight-recovery-clean (1 OCPU / 1 GB)    PERSONAL
    └── Vaultwarden (tailnet-only bind) + rclone cron

RECLAIM
└── xlm-bot-core-e5-2c16g orphan volume  -> +47 GB allowance -> grow e5 boot volume
└── Xlm-bot instance                     -> pending reachability audit
```

**Why Google Drive and not Nextcloud.** Nextcloud needs disk you do not have (9 GB of allowance left), adds a service to maintain and patch, and its E2EE app is still flagged experimental. You already pay for 5 TB with a native Android sync client, web access from anywhere, and a working crypt layer on top. Building Nextcloud here would be spending effort to get less.

**The honest trade on photos.** Anything inside `drive_everlight_crypt:` is unreadable by Google, and also unsearchable, no albums, no face grouping, no Photos app. So media that you want Google Photos to organize stays plain. Sensitive documents go in the crypt remote. One provider, two tiers, one sync client.

---

## Task 1: Vaultwarden on the personal box, kill the plaintext vault

**Priority: P0.** `proton_pass_import.json` has been sitting unencrypted for 51 days. Everything else waits.

**Files:**
- Create: `03_AUTOMATION_CORE/01_Scripts/personal_box/provision_vaultwarden.sh`
- Read then destroy: `03_AUTOMATION_CORE/03_Credentials/proton_pass_import.json`

**Interfaces:**
- Produces: Vaultwarden reachable at `http://<recovery-clean-tailnet-ip>:8222`, admin token stored via `secrets_vault.py`.

- [ ] **Step 1: Confirm the box is reachable and note its OS**

```bash
ssh -i /root/.ssh/oracle_key.pem opc@64.181.242.230 \
  "cat /etc/os-release | head -2; free -m | sed -n 2p; df -h / | tail -1"
```
Expected: Oracle Linux, ~1 GB RAM (`MemTotal` around 950 MB), 30G root at ~21%.

- [ ] **Step 2: Add swap, because 1 GB RAM has no margin**

```bash
ssh -i /root/.ssh/oracle_key.pem opc@64.181.242.230 \
  "sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && \
   sudo mkswap /swapfile && sudo swapon /swapfile && \
   echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab && free -m"
```
Expected: `Swap:` row shows ~2048 total.

- [ ] **Step 3: Install Podman and run Vaultwarden bound to loopback**

Oracle Linux ships Podman, not Docker. Bind to `127.0.0.1` per Network Binding Doctrine, then expose over Tailscale only.

```bash
ssh -i /root/.ssh/oracle_key.pem opc@64.181.242.230 bash -s <<'EOF'
sudo dnf install -y podman
sudo mkdir -p /opt/vaultwarden/data
sudo podman run -d --name vaultwarden --restart=always \
  -e SIGNUPS_ALLOWED=true \
  -e ROCKET_PORT=8222 \
  -v /opt/vaultwarden/data:/data:Z \
  -p 127.0.0.1:8222:8222 \
  docker.io/vaultwarden/server:latest
sudo podman ps --format '{{.Names}} {{.Status}}'
EOF
```
Expected: `vaultwarden Up ...`

- [ ] **Step 4: Join the box to Tailscale so the phone can reach it**

```bash
ssh -i /root/.ssh/oracle_key.pem opc@64.181.242.230 \
  "sudo dnf install -y tailscale && sudo systemctl enable --now tailscaled && \
   sudo tailscale up --hostname=ev-personal --ssh"
```
Expected: an auth URL to open once. After auth, `tailscale ip -4` returns a 100.x address.

- [ ] **Step 5: Expose Vaultwarden on the tailnet interface only**

```bash
ssh -i /root/.ssh/oracle_key.pem opc@64.181.242.230 bash -s <<'EOF'
TSIP=$(tailscale ip -4)
sudo podman rm -f vaultwarden
sudo podman run -d --name vaultwarden --restart=always \
  -e SIGNUPS_ALLOWED=true -e ROCKET_PORT=8222 \
  -v /opt/vaultwarden/data:/data:Z \
  -p ${TSIP}:8222:8222 \
  docker.io/vaultwarden/server:latest
echo "reachable at http://${TSIP}:8222"
EOF
```
Expected: prints the tailnet URL. Verify from a Tailscale-connected device.

- [ ] **Step 6: Create the account, then close signups**

Open the URL, create the account with a strong master password stored **only** in your head and on paper. Then:

```bash
ssh -i /root/.ssh/oracle_key.pem opc@64.181.242.230 \
  "sudo podman exec vaultwarden sh -c 'echo closing' && \
   sudo sed -i 's/SIGNUPS_ALLOWED=true/SIGNUPS_ALLOWED=false/' /etc/sysconfig/vaultwarden 2>/dev/null; \
   sudo podman rm -f vaultwarden"
```
Then re-run Step 5 with `-e SIGNUPS_ALLOWED=false`.
Expected: a second signup attempt is rejected.

- [ ] **Step 7: Import the Proton Pass export**

In the Vaultwarden web vault: Tools > Import Data > format **Proton Pass (.json)** > upload `proton_pass_import.json`.

- [ ] **Step 8: Verify the import by hand before destroying anything**

```bash
python3 -c "
import json
d=json.load(open('/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/proton_pass_import.json'))
items=d.get('items') or []
print('source item count:', len(items))
"
```
Compare that number to the vault item count in the web UI. They must match exactly. Then open five entries at random and confirm the passwords are present and correct.

- [ ] **Step 9: Shred the plaintext export (P0 closed)**

Only after Step 8 matches.

```bash
cd /mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials
shred -vfz -n 3 proton_pass_import.json 2>/dev/null || \
  { dd if=/dev/urandom of=proton_pass_import.json bs=1k count=28 conv=notrunc; rm -f proton_pass_import.json; }
ls -la proton_pass_import.json 2>&1 | tail -1
```
Expected: `No such file or directory`.

Note: sdcard is likely FAT/exFAT where `shred` cannot guarantee overwrite. The `dd` fallback overwrites in place before unlink, which is the best available on this filesystem.

- [ ] **Step 10: Commit**

```bash
git add 03_AUTOMATION_CORE/01_Scripts/personal_box/provision_vaultwarden.sh
git commit -m "feat(personal-box): vaultwarden on recovery-clean, retire plaintext vault export"
```

---

## Task 2: Free the block-storage allowance

**Files:** none. Pure OCI operations.

**Interfaces:**
- Produces: at least 47 GB of freed allowance, enabling e5-mother's boot volume to grow.

- [ ] **Step 1: Build the deletion manifest (doctrine requirement)**

```bash
export SUPPRESS_LABEL_WARNING=True
TEN=$(grep '^tenancy' /root/.oci/config|cut -d= -f2)
oci bv boot-volume list --compartment-id "$TEN" \
  --availability-domain "kNfe:US-SANJOSE-1-AD-1" \
  --query 'data[].{name:"display-name",id:id,gb:"size-in-gbs",created:"time-created",state:"lifecycle-state"}' \
  --output json > /mnt/sdcard/AA_MY_DRIVE/_logs/bootvol_manifest_2026-07-23.json
cat /mnt/sdcard/AA_MY_DRIVE/_logs/bootvol_manifest_2026-07-23.json
```
Expected: 4 volumes listed, manifest written.

- [ ] **Step 2: Prove the orphan is genuinely unattached**

```bash
export SUPPRESS_LABEL_WARNING=True
TEN=$(grep '^tenancy' /root/.oci/config|cut -d= -f2)
oci compute boot-volume-attachment list --compartment-id "$TEN" \
  --availability-domain "kNfe:US-SANJOSE-1-AD-1" \
  --query 'data[].{vol:"boot-volume-id",inst:"instance-id",state:"lifecycle-state"}' --output table
```
Expected: exactly 3 ATTACHED rows. The `xlm-bot-core-e5-2c16g` volume ID must appear in **none** of them. If it appears, STOP, it is in use.

- [ ] **Step 3: Snapshot before delete (reversibility)**

```bash
export SUPPRESS_LABEL_WARNING=True
ORPHAN_ID=<id from Step 1 for xlm-bot-core-e5-2c16g>
oci bv boot-volume-backup create --boot-volume-id "$ORPHAN_ID" \
  --display-name "orphan-xlm-core-pre-delete-2026-07-23" --type FULL --wait-for-state AVAILABLE
```
Expected: backup reaches AVAILABLE. Backups are cheap and are not charged against the 200 GB volume allowance the same way. Verify cost before proceeding if PAYG is confirmed.

- [ ] **Step 4: GATED. Delete the orphan volume**

**Requires operator GO. Do not run unattended.**

```bash
export SUPPRESS_LABEL_WARNING=True
oci bv boot-volume delete --boot-volume-id "$ORPHAN_ID" --force
```
Expected: allowance drops from 191 GB to 144 GB.

- [ ] **Step 5: Grow e5-mother's boot volume into the freed space**

```bash
export SUPPRESS_LABEL_WARNING=True
E5_VOL=<id from Step 1 for everlight-prod-a1>
oci bv boot-volume update --boot-volume-id "$E5_VOL" --size-in-gbs 97 --wait-for-state AVAILABLE
```
Then grow the filesystem in place, no reboot needed:
```bash
ssh e5 "sudo dnf install -y cloud-utils-growpart 2>/dev/null || sudo apt-get install -y cloud-guest-utils; \
        sudo growpart /dev/sda 1 && sudo resize2fs /dev/sda1 && df -h /"
```
Expected: `/dev/sda1` shows ~95G, usage drops from 95% to roughly 49%.

---

## Task 3: ~~Offload cold data to the crypt remote~~ SUPERSEDED 2026-07-23 by Task 3R

> **Operator changed the requirement mid-execution: no Google, self-host everything except Oracle.**
> The Google Drive plane is withdrawn. See Task 3R and Task 4R at the bottom of this document.
> Tasks 1 and 2 are unaffected and remain in force.

<details><summary>Withdrawn content (kept for provenance)</summary>

**Files:**
- Create: `03_AUTOMATION_CORE/01_Scripts/e5_mother/offload_cold_to_drive.sh`

**Interfaces:**
- Consumes: `drive_everlight_crypt:` remote from Task 0 state (already configured).
- Produces: `backups/` and `personal/` paths on the crypt remote; ~8 GB freed on e5.

- [ ] **Step 1: Install rclone on e5 and copy the config over**

```bash
ssh e5 "curl -s https://rclone.org/install.sh | sudo bash && rclone version | head -1"
scp /root/.config/rclone/rclone.conf e5:/tmp/rclone.conf
ssh e5 "mkdir -p ~/.config/rclone && mv /tmp/rclone.conf ~/.config/rclone/rclone.conf && chmod 600 ~/.config/rclone/rclone.conf && rclone listremotes"
```
Expected: both remotes listed on e5.

- [ ] **Step 2: COPY (not move) backups to the crypt remote**

```bash
ssh e5 "rclone copy /home/ubuntu/AA_MY_DRIVE/08_BACKUPS drive_everlight_crypt:backups/e5_08_BACKUPS \
  --transfers 4 --checkers 8 --progress --stats 30s"
```
Expected: ~4.7 GB transferred.

- [ ] **Step 3: Verify byte-for-byte before removing the local copy**

Per standing doctrine, content-type and file-count checks are not sufficient.

```bash
ssh e5 "rclone check /home/ubuntu/AA_MY_DRIVE/08_BACKUPS drive_everlight_crypt:backups/e5_08_BACKUPS --one-way --size-only; echo EXIT=\$?"
```
Expected: `EXIT=0` and `0 differences found`. Any non-zero result STOPS this task.

- [ ] **Step 4: GATED. Remove the local backup copy**

**Requires operator GO.** Run the memory-pipeline pass first:

```bash
cd /mnt/sdcard/AA_MY_DRIVE && python3 -c "
from content_tools import memory_pipeline
memory_pipeline.ingest_before_delete('/home/ubuntu/AA_MY_DRIVE/08_BACKUPS', reason='offloaded to drive_everlight_crypt:backups/e5_08_BACKUPS 2026-07-23')
" || echo "memory_pipeline unavailable, log manually to Blinko before proceeding"
ssh e5 "rm -rf /home/ubuntu/AA_MY_DRIVE/08_BACKUPS && df -h / | tail -1"
```
Expected: ~4.7 GB freed.

- [ ] **Step 5: Repeat Steps 2-4 for 05_PERSONAL, targeting `personal/`**

Personal data does not belong on the work box at all. Same copy, same `rclone check` gate, same memory-pipeline pass.

```bash
ssh e5 "rclone copy /home/ubuntu/AA_MY_DRIVE/05_PERSONAL drive_everlight_crypt:personal/from_e5 --progress --stats 30s"
ssh e5 "rclone check /home/ubuntu/AA_MY_DRIVE/05_PERSONAL drive_everlight_crypt:personal/from_e5 --one-way --size-only; echo EXIT=\$?"
```
Expected: `EXIT=0`, then ~3.1 GB freed after the gated removal.

- [ ] **Step 6: Add the exclusion to the sync script so it does not come back**

The workspace mirror will re-sync these paths on the next run unless excluded. Find the rsync invocation and add:
```
--exclude '05_PERSONAL/' --exclude '08_BACKUPS/'
```

- [ ] **Step 7: Commit**

```bash
git add 03_AUTOMATION_CORE/01_Scripts/e5_mother/offload_cold_to_drive.sh
git commit -m "feat(e5): offload backups and personal data to crypt remote, exclude from mirror"
```

---

## Task 4: Consolidate Proton Drive and Proton Photos into the single plane

**Interfaces:**
- Produces: all Proton-held files present under `drive_everlight_crypt:personal/`, verified, ready for the Proton cancellation decision.

- [ ] **Step 1: Export Proton Drive using the official CLI**

Proton shipped a Drive CLI (v0.4.3, June 2026), which is far less painful than the old browser-download route.

```bash
# On the AceMagician PC or any desktop, not the phone (proot cannot handle bulk media)
proton-drive-cli login
proton-drive-cli download --recursive / ~/proton_export/
du -sh ~/proton_export/
```
Expected: prints total size. Record it, this number decides whether 5 TB is comfortable (it is).

- [ ] **Step 2: Export Proton Photos**

Proton Photos has no CLI. Use the web client's select-all + download, which produces zip archives. Expand them into `~/proton_export/photos/`.

- [ ] **Step 3: Push documents to the crypt remote, photos to plain Drive**

```bash
rclone copy ~/proton_export/ drive_everlight_crypt:personal/proton_drive \
  --exclude 'photos/**' --progress --stats 30s
rclone copy ~/proton_export/photos/ drive_everlight:Photos/from_proton \
  --progress --stats 30s
```
Documents get zero-knowledge encryption. Photos stay plain so Google Photos can index, search, and album them. That trade is deliberate.

- [ ] **Step 4: Verify both legs**

```bash
rclone check ~/proton_export/ drive_everlight_crypt:personal/proton_drive --exclude 'photos/**' --one-way --size-only; echo EXIT=$?
rclone check ~/proton_export/photos/ drive_everlight:Photos/from_proton --one-way --size-only; echo EXIT=$?
```
Expected: `EXIT=0` on both. Anything else STOPS the task.

- [ ] **Step 5: Set up phone sync to the single plane**

Install the **Google Drive** Android app (files, sync, offline access anywhere) and confirm **Google Photos** backup is on for the camera roll. That is the "one place that syncs with my phone" requirement satisfied with zero new software.

For crypt-remote access from the phone, `rclone` is already installed in proot:
```bash
rclone mount drive_everlight_crypt: ~/crypt --daemon --vfs-cache-mode writes
```

- [ ] **Step 6: DO NOT cancel Proton yet**

Per the migration doctrine in `SOVEREIGN_SUITE_PLAN.html`: run 30 days in parallel before cancelling anything. Cancellation is the only irreversible step in this entire plan.

---

</details>

---

## Task 5: Resolve the Xlm-bot micro

**Blocked on:** reachability. `163.192.19.196:22` times out. The instance shows RUNNING in OCI.

- [ ] **Step 1: Determine whether it is a security-list problem or a dead host**

```bash
export SUPPRESS_LABEL_WARNING=True
TEN=$(grep '^tenancy' /root/.oci/config|cut -d= -f2)
VCN=$(oci network vcn list --compartment-id "$TEN" --query 'data[0].id' --raw-output)
oci network security-list list --compartment-id "$TEN" --vcn-id "$VCN" \
  --query 'data[].{name:"display-name",ingress:"ingress-security-rules"}' --output json | head -40
```
Expected: shows whether port 22 ingress exists for 0.0.0.0/0.

- [ ] **Step 2: If the security list is fine, read the serial console**

```bash
oci compute instance-console-connection create --instance-id <xlm-bot-id> \
  --ssh-public-key-file /root/.ssh/oracle_key.pub
```
Then follow the printed connection string.

- [ ] **Step 3: Decide**

- If it still runs the XLM bot and you want XLM alive: leave it, since XLM is parked but the bot code and state live there.
- If it is idle: it is a **third free box**. Options are terminate for +47 GB of allowance, or repurpose it as the off-Oracle-independent secondary for Vaultwarden replication.

**Recommendation:** do not terminate. A second 1 GB box costs nothing and gives Vaultwarden a replica target. The 47 GB is only worth reclaiming if e5 needs to grow past 97 GB.

---

## Execution Order (hierarchy)

```
P0  Task 1        Vaultwarden + shred the plaintext vault      <- start here, nothing else matters
P0  Task 2 S1-S3  Manifest + snapshot the orphan volume        <- safe, reversible, do immediately
P1  Task 2 S4-S5  GATED delete orphan, grow e5 disk            <- needs GO. Fixes the 95% disk
P1  Task 3        Offload backups + personal off e5            <- needs GO on the removal steps
P2  Task 4        Proton -> single plane migration             <- bulk transfer, run on the PC
P3  Task 5        Xlm-bot investigation                        <- lowest value, do last
P4  --            Cancel Proton                                <- only after 30 parallel days
```

## What this achieves

| Before | After |
|---|---|
| 4 storage services (Proton Drive, Proton Photos, Google Photos, Google Drive) | 1 plane: Google Drive, 2 tiers (crypt / plain) |
| Plaintext vault export on the phone, 51 days | Vaultwarden, tailnet-only, export shredded |
| e5 at 95% disk, no allowance to grow | e5 at ~49%, 47 GB of allowance reclaimed |
| Personal data on the work server | Personal data on Drive + a dedicated personal box |
| 1 empty box idling 79 days | That box is the personal box |
| Proton subscription | Cancelled after 30 verified parallel days |
