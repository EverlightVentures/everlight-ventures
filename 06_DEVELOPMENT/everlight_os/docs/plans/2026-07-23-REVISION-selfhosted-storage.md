# REVISION 2026-07-23: Self-Hosted Only (no Google, Oracle permitted)

> Supersedes Tasks 3 and 4 of `2026-07-23-instance-reorg-and-storage-consolidation.md`.
> Tasks 1 (Vaultwarden) and 2 (volume reclaim) are unchanged and still in force.

**What changed.** The operator withdrew Google as a storage plane mid-execution. Everything self-hosts on Oracle.

## Verified prerequisites (live-checked 2026-07-23)

| Requirement | Status |
|---|---|
| RAM for Nextcloud on e5 | **23,980 MB total, 19,829 MB available.** Ample |
| Docker on e5 | Running (Open WebUI on 127.0.0.1:8080) |
| nginx on e5 | 1.18.0, running |
| Cloudflare Tunnel | **Already working.** `cloudflared tunnel run solano`, config `/home/ubuntu/.cloudflared/config.yml` |
| CF credentials | `CF_API_TOKEN`, `CF_ZONE_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_EMAIL` present |
| Architecture | e5 is Ampere **arm64**. Nextcloud, PostgreSQL, Redis all publish arm64 images |
| Orphan volume backup | **DONE.** `orphan-xlm-core-pre-delete-2026-07-23`, 47 GB, AVAILABLE |

## Storage budget (the binding constraint)

```
allowance                          200 GB
currently used                     191 GB   (4 boot volumes)
headroom today                       9 GB   <- why the disk fix was impossible

after reclaiming the orphan        144 GB used,  56 GB free
after also terminating Xlm-bot      97 GB used, 103 GB free   <- max free capacity
```

**What has to fit:** Google Drive 50.2 GiB + Google "other" 57.9 GiB (Photos and Gmail share the quota) = **~108 GB**, plus Proton Drive and Proton Photos, both **unmeasured**.

**So 103 GB is probably not enough.** Oracle block storage past the free allowance bills at $0.0255/GB/month:

| Total | Extra over 200 GB | Cost |
|---|---|---|
| 300 GB | 100 GB | **$2.55/mo** |
| 500 GB | 300 GB | $7.65/mo |
| 1000 GB | 800 GB | $20.40/mo |

Against Proton Unlimited at $9.99/mo plus the Google 5 TB plan, $2.55/mo for fully self-hosted storage is a large net win. **This is a spend decision requiring operator GO per the free-first rule.** Do not provision paid capacity without it.

**Gate:** measure Proton Drive and Proton Photos first. Never buy capacity for an unmeasured number.

---

## Task 3R: Nextcloud on e5 as the single self-hosted plane

**Why Nextcloud.** It is the only self-hosted option covering all four services in one app: files, photos with camera auto-upload, calendar, contacts, browser access from anywhere, an Android sync client, and a WebDAV/OCS API for automation. Immich is better at photos specifically, but that would be two things and the requirement is one thing.

**Files:**
- Create: `03_AUTOMATION_CORE/01_Scripts/e5_mother/nextcloud/docker-compose.yml`
- Create: `03_AUTOMATION_CORE/01_Scripts/e5_mother/nextcloud/provision.sh`
- Modify on e5: `/home/ubuntu/.cloudflared/config.yml`

**Interfaces:**
- Produces: Nextcloud at `https://drive.everlightventures.io`, data on `/mnt/ncdata`, WebDAV at `https://drive.everlightventures.io/remote.php/dav/files/<user>/`

- [ ] **Step 1: GATED. Delete the orphan volume (backup already exists)**

```bash
export SUPPRESS_LABEL_WARNING=True
ORPHAN=$(python3 -c "
import json
v=json.load(open('/mnt/sdcard/AA_MY_DRIVE/_logs/bootvol_manifest_2026-07-23.json'))
a=set(json.load(open('/mnt/sdcard/AA_MY_DRIVE/_logs/bootvol_attached_2026-07-23.json')))
print([x['id'] for x in v if x['id'] not in a][0])")
oci bv boot-volume delete --boot-volume-id "$ORPHAN" --force
```
Expected: allowance 191 -> 144 GB. Restore path: create a boot volume from backup `orphan-xlm-core-pre-delete-2026-07-23`.

- [ ] **Step 2: Grow e5's boot volume to clear the 95% alarm**

```bash
export SUPPRESS_LABEL_WARNING=True
E5=$(python3 -c "
import json;v=json.load(open('/mnt/sdcard/AA_MY_DRIVE/_logs/bootvol_manifest_2026-07-23.json'))
print([x['id'] for x in v if 'prod-a1' in x['name']][0])")
oci bv boot-volume update --boot-volume-id "$E5" --size-in-gbs 70 --wait-for-state AVAILABLE
ssh e5 "sudo apt-get install -y cloud-guest-utils >/dev/null 2>&1; sudo growpart /dev/sda 1; sudo resize2fs /dev/sda1; df -h /"
```
Expected: `/dev/sda1` about 69G, usage 95% -> roughly 67%. Allowance then 164 GB used, 36 GB free.

- [ ] **Step 3: Create and attach the Nextcloud data volume**

Sized to remaining free allowance. Raise only after the spend decision.

```bash
export SUPPRESS_LABEL_WARNING=True
TEN=$(grep '^tenancy' /root/.oci/config|cut -d= -f2)
oci bv volume create --compartment-id "$TEN" --availability-domain "kNfe:US-SANJOSE-1-AD-1" \
  --display-name "nextcloud-data" --size-in-gbs 36 --wait-for-state AVAILABLE
INST=$(oci compute instance list --compartment-id "$TEN" --all \
  --query 'data[?"display-name"==`everlight-prod-a1`].id|[0]' --raw-output)
VOL=$(oci bv volume list --compartment-id "$TEN" --all \
  --query 'data[?"display-name"==`nextcloud-data`].id|[0]' --raw-output)
oci compute volume-attachment attach --instance-id "$INST" --volume-id "$VOL" \
  --type paravirtualized --wait-for-state ATTACHED
```

- [ ] **Step 4: Format and mount**

Run these on e5 directly (the phone's shell guard blocks filesystem-creation verbs, which is correct behavior):

```
ssh e5
DEV=$(lsblk -dnpo NAME,SIZE | grep -v sda | awk '$2!="0B"{print $1}' | head -1)
sudo mkfs.ext4 -F "$DEV"
sudo mkdir -p /mnt/ncdata
echo "$(sudo blkid -s UUID -o value $DEV) /mnt/ncdata ext4 defaults,_netdev,nofail 0 2" | sudo tee -a /etc/fstab
sudo mount -a && df -h /mnt/ncdata
```
Expected: `/mnt/ncdata` mounted at the provisioned size.

- [ ] **Step 5: Bring up Nextcloud, PostgreSQL and Redis**

Bound to loopback. The tunnel provides ingress, per Network Binding Doctrine.

`~/nextcloud/docker-compose.yml` on e5:
```yaml
services:
  db:
    image: postgres:16-alpine
    restart: always
    volumes: ["/mnt/ncdata/db:/var/lib/postgresql/data"]
    environment:
      POSTGRES_DB: nextcloud
      POSTGRES_USER: nextcloud
      POSTGRES_PASSWORD_FILE: /run/secrets/dbpass
    secrets: [dbpass]
  redis:
    image: redis:alpine
    restart: always
  app:
    image: nextcloud:apache
    restart: always
    ports: ["127.0.0.1:8081:80"]
    volumes:
      - "/mnt/ncdata/html:/var/www/html"
      - "/mnt/ncdata/data:/var/www/html/data"
    environment:
      POSTGRES_HOST: db
      POSTGRES_DB: nextcloud
      POSTGRES_USER: nextcloud
      POSTGRES_PASSWORD_FILE: /run/secrets/dbpass
      REDIS_HOST: redis
      NEXTCLOUD_TRUSTED_DOMAINS: drive.everlightventures.io
      OVERWRITEPROTOCOL: https
    depends_on: [db, redis]
    secrets: [dbpass]
secrets:
  dbpass:
    file: /mnt/ncdata/.dbpass
```

```bash
ssh e5 "sudo mkdir -p /mnt/ncdata && openssl rand -base64 32 | sudo tee /mnt/ncdata/.dbpass >/dev/null && sudo chmod 600 /mnt/ncdata/.dbpass && cd ~/nextcloud && sudo docker compose up -d && sleep 45 && sudo docker compose ps"
```
Expected: three containers Up. `curl -sI localhost:8081` returns 302 to `/login`.

- [ ] **Step 6: Route the hostname through the existing tunnel**

```bash
ssh e5 "cp ~/.cloudflared/config.yml ~/.cloudflared/config.yml.bak.2026-07-23; cat ~/.cloudflared/config.yml"
```
Add under `ingress:`, **above** the catch-all `- service: http_status:404`:
```yaml
  - hostname: drive.everlightventures.io
    service: http://localhost:8081
```
Then:
```bash
ssh e5 "~/.local/bin/cloudflared tunnel route dns solano drive.everlightventures.io; sudo systemctl restart cloudflared 2>/dev/null || pkill -f 'cloudflared tunnel run'"
curl -sI -L https://drive.everlightventures.io | head -3
```
Expected: HTTP 200, Nextcloud login. Cloudflare returns 308 first, hence `-L`.

- [ ] **Step 7: Create the admin account and harden**

Via the web UI, then:
```bash
ssh e5 "cd ~/nextcloud && sudo docker compose exec -u www-data app php occ config:system:set overwrite.cli.url --value=https://drive.everlightventures.io && sudo docker compose exec -u www-data app php occ status"
```

- [ ] **Step 8: Phone sync, the actual requirement**

Install **Nextcloud** from the Play Store, sign in to `drive.everlightventures.io`, enable **Auto upload** for the camera folder. That one app replaces Proton Drive, Proton Photos, Google Drive and Google Photos. Files reachable from any browser at the same URL.

- [ ] **Step 9: Commit**

```bash
git add 03_AUTOMATION_CORE/01_Scripts/e5_mother/nextcloud/
git commit -m "feat(e5): self-hosted nextcloud as single storage plane behind cloudflare tunnel"
```

---

## Task 4R: Migrate all four services in, then cancel

- [ ] **Step 1: Measure before buying anything**

```bash
# From the AceMagician PC. proot cannot handle bulk media.
proton-drive-cli login && proton-drive-cli download --recursive / ~/proton_export/ && du -sh ~/proton_export/
```
Google Photos: request a **Google Takeout** export and read its reported size. Sum all four. If the total exceeds free allowance, present the spend decision and **wait for GO**.

- [ ] **Step 2: Add a WebDAV remote pointing at Nextcloud**

```bash
rclone config create ncloud webdav \
  url https://drive.everlightventures.io/remote.php/dav/files/<user>/ \
  vendor nextcloud user <user> pass <app-password>
rclone lsd ncloud:
```
Use a Nextcloud **app password**, never the account password.

- [ ] **Step 3: Migrate each source, verifying every leg**

```bash
rclone copy ~/proton_export/         ncloud:Documents/proton_drive  --progress --stats 30s
rclone copy ~/proton_photos/         ncloud:Photos/proton           --progress --stats 30s
rclone copy drive_everlight:         ncloud:Documents/google_drive  --progress --stats 30s
rclone copy ~/google_takeout/photos/ ncloud:Photos/google           --progress --stats 30s
```
After each:
```bash
rclone check <source> <dest> --one-way --size-only; echo EXIT=$?
```
`EXIT=0` required. Per doctrine, size and count checks are the floor: spot-check that ten random files actually open.

- [ ] **Step 4: Offsite backup, non-negotiable**

Self-hosted with one copy is one disk failure from total loss. The AceMagician PC is the designated full holder in `TRI_DEVICE_VAULT_DESIGN.md`.

```bash
# nightly on the PC
rclone sync ncloud: /mnt/vault/nextcloud_mirror --backup-dir /mnt/vault/nextcloud_versions/$(date +%F)
```
Plus an Oracle volume-backup policy so the data volume itself is snapshotted.

- [ ] **Step 5: Run 30 days in parallel, then cancel**

Proton and Google both stay live for 30 days while Nextcloud carries real traffic. Cancellation is the only irreversible step here. After 30 clean days and a verified export: cancel Proton, then cancel the Google plan.

---

## Revised execution order

```
P0  Task 1          Vaultwarden + shred plaintext vault    IN PROGRESS
P0  Task 2 S1-S3    Manifest, prove orphan, snapshot       DONE
P1  Task 3R S1-S2   GATED delete orphan, grow e5 disk      needs GO
P1  Task 3R S3-S9   Nextcloud + tunnel + phone app         after S2
P2  Task 4R S1      Measure Proton and Google volumes      gates the spend decision
P2  Task 4R S2-S4   Migrate + verify + offsite backup      after sizing
P3  Task 5          Xlm-bot investigation                  optional, frees another 47 GB
P4  Task 4R S5      Cancel Proton, then Google             only after 30 parallel days
```

## Open risk: the personal box is 503 MB, not 1 GB

`everlight-recovery-clean` reports `MemTotal` of 503 MB despite the shape advertising 1 GB. A `dnf install podman` saturated it and dropped sshd mid-session. 2 GB of swap has been added, and the install was restarted detached via `nohup`. Vaultwarden itself idles near 50 MB and will run fine; only the install is painful. If it keeps failing, the fallback is to host Vaultwarden on e5 in its own Docker network and accept weaker work/personal isolation until a larger personal box exists.
