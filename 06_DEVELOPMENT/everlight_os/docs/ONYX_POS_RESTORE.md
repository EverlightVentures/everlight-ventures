# Onyx POS / Mountain Gardens POS -- Restore Runbook

**Purpose:** Get the Onyx POS (originally "MGN point of sale") code back onto a computer
(the Dell, or any new machine) and stored safely.
**Last updated:** 2026-06-21
**Owner:** Rich
**Related:** [`DISASTER_RECOVERY.md`](DISASTER_RECOVERY.md) (full-workspace recovery)

---

## TL;DR -- what you're restoring

The POS is **not a standalone repo**. It lives inside the Everlight monorepo, which is
backed up on GitHub. Two folders hold the POS code, **both tracked / both safe on GitHub**:

| Folder | Size | What it is |
|--------|------|------------|
| `01_BUSINESSES/Everlight_Ventures/01_OnyxPOS/` | 338 MB | Original "MGN point of sale" -- the live app (`operations_MGN_v8/`: `MGN_APP.py`, `POS_CORE.py`, `START_POS.sh`) + every legacy version |
| `01_BUSINESSES/onyx_pos/` | 3.2 MB | Newer SaaS scaffold (Docker, api, frontend, blueprints) |

- **GitHub repo (source of truth):** `git@github.com:EverlightVentures/everlight-ventures.git`
- Full `.git` history is **1.9 GB**, but you only need **~341 MB** of POS files -- so we clone
  *only those folders* (sparse checkout). Don't do a plain full clone.

## What you need (pick ONE before you start)

- **Path A (recommended):** GitHub access on the computer -- either an SSH key added to your
  GitHub account, **or** a Personal Access Token (PAT) for HTTPS. Most reliable, always current.
- **Path B (fallback):** The computer is on your Tailscale tailnet AND the phone (or e5) is
  reachable. No GitHub login needed, but you only get the files (no git history).

---

## Path A -- Restore from GitHub (recommended)

Run on the target computer. This downloads ONLY the two POS folders, not the 1.9 GB history.

```bash
# 1. Make a home for it
mkdir -p ~/everlight && cd ~/everlight

# 2. Clone metadata only -- no file blobs yet, nothing checked out
git clone --filter=blob:none --no-checkout \
  git@github.com:EverlightVentures/everlight-ventures.git
cd everlight-ventures

# 3. Restrict to just the POS folders
git sparse-checkout init --cone
git sparse-checkout set \
  "01_BUSINESSES/Everlight_Ventures/01_OnyxPOS" \
  "01_BUSINESSES/onyx_pos"

# 4. Pull the actual files for the default (main) branch
git checkout main
```

### If you use HTTPS + token instead of SSH
Swap the clone URL in step 2 for:
```bash
git clone --filter=blob:none --no-checkout \
  https://github.com/EverlightVentures/everlight-ventures.git
```
When prompted, username = your GitHub username, password = your **PAT** (not your real password).

### Result
You'll have a real git repo at `~/everlight/everlight-ventures/` containing only:
- `01_BUSINESSES/Everlight_Ventures/01_OnyxPOS/`
- `01_BUSINESSES/onyx_pos/`

Because it's a git repo, it's self-backing -- `git pull` later re-syncs any updates.

---

## Path B -- Restore over Tailscale (no GitHub login)

Use this only if GitHub auth on the computer is a hassle. It copies the **files** straight off
an Everlight machine that already has them. No git history.

1. Get the source device's tailnet name from the Tailscale admin console (or run
   `tailscale status` on the phone). The phone is the source-of-truth; **e5** is the always-on
   alternative (`ssh e5` -> public IP 163.192.60.35, or `e5-mother` on the tailnet).
2. On the target computer:

```bash
mkdir -p ~/everlight/onyx_restore && cd ~/everlight/onyx_restore

# Replace <SRC> with the phone's (or e5's) tailnet name/host.
# Phone workspace root: /mnt/sdcard/AA_MY_DRIVE
rsync -avz --progress \
  "<SRC>:/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/01_OnyxPOS" \
  "<SRC>:/mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/onyx_pos" \
  ./
```

> Note: if `<SRC>` is the phone, it must be running its SSH server and reachable on the tailnet.
> If that's flaky, use e5 as the source instead (path on e5 is the workspace-mirror root, e.g.
> `~/AA_MY_DRIVE/...` -- confirm with `ls` over `ssh e5` first).

---

## Verify the restore worked

```bash
# The live MGN app's launcher should exist:
ls -la 01_BUSINESSES/Everlight_Ventures/01_OnyxPOS/operations_MGN_v8/START_POS.sh

# Quick sanity count (expect a few thousand files):
find 01_BUSINESSES/Everlight_Ventures/01_OnyxPOS -type f | wc -l
```

## "Store it immediately" -- lock in a second copy

A single download isn't a backup. Right after restoring, make a second copy:

```bash
# Option 1: timestamped zip onto the same machine / a cloud-synced folder
cd ~/everlight
zip -r "onyx_pos_backup_$(date +%Y%m%d).zip" \
  everlight-ventures/01_BUSINESSES/Everlight_Ventures/01_OnyxPOS \
  everlight-ventures/01_BUSINESSES/onyx_pos

# Option 2: copy the zip to an external drive (replace the path)
cp onyx_pos_backup_*.zip /media/<you>/<external-drive>/
```

If you used **Path A**, the git repo itself is already a live backup -- `git pull` keeps it current,
and GitHub holds the canonical copy regardless of what happens to this machine.

---

## Running the POS after restore (optional)

The live Mountain Gardens app is launched from its own scripts:
```bash
cd 01_BUSINESSES/Everlight_Ventures/01_OnyxPOS/operations_MGN_v8
bash START_POS.sh     # start    | STOP_POS.sh to stop | restart_POS.sh to restart
```
The newer `onyx_pos/app/` scaffold ships a `docker-compose.yml` + `.env.example` if you want the
containerized version instead -- copy `.env.example` to `.env`, fill it in, then `docker compose up`.

---

## Quick reference card

```
REPO:    git@github.com:EverlightVentures/everlight-ventures.git
WANT:    01_BUSINESSES/Everlight_Ventures/01_OnyxPOS   (338 MB, the MGN app)
         01_BUSINESSES/onyx_pos                        (3.2 MB, SaaS scaffold)
METHOD:  sparse + blobless clone (downloads ~341 MB, not the 1.9 GB history)
FALLBACK: rsync over Tailscale from the phone or e5 (files only, no history)
```
