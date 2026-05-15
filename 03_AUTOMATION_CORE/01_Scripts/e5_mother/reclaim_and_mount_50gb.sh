#!/usr/bin/env bash
# reclaim_and_mount_50gb.sh -- paste-ready for the operator to run on phone.
#
# Three sections. Pick one of A/B/C, then run section 4 always.
#
# Always Free quota math (as of 2026-05-15):
#   used    : 191 GB (4 boot volumes)
#   pool    : 200 GB
#   to add  :  50 GB (new block volume)
#   reclaim :  47 GB first
#
# Tenancy: ocid1.tenancy.oc1..aaaaaaaacm32hkslhfxorfn7jubhjqjffr4roltyj...
# AD     : kNfe:US-SANJOSE-1-AD-1

set -euo pipefail
export SUPPRESS_LABEL_WARNING=True

TENANCY="$(grep '^tenancy=' /root/.oci/config | cut -d= -f2)"
AD="kNfe:US-SANJOSE-1-AD-1"
EMOTHER_OCID="ocid1.instance.oc1.us-sanjose-1.anzwuljrwtpnzgacbhg6hxpfs6i3..."   # everlight-prod-a1
RECOVERY_CLEAN_OCID="ocid1.instance.oc1.us-sanjose-1.anzwuljrwtpnzgac7wfzosatmr4mugiut2l654fme2oqp6puk75yzbg7zqzq"
ORPHAN_BV_OCID="ocid1.bootvolume.oc1.us-sanjose-1.abzwuljrzmlkhudjg2iauamz6zr4mhrygp6kmxurur4d7wrh73qrfvlmg3oq"

# ============================================================================
# OPTION A -- mount orphan first, diff, then delete (safest)
# ============================================================================
# This path uses OCI Console because the CLI returns 409 "currently attached"
# (the orphan is in a stuck transient state from a prior recovery attempt).
#
# Console steps (do these in browser):
#   1. cloud.oracle.com -> Storage -> Block Volumes -> Boot Volumes
#   2. Click "xlm-bot-core-e5-2c16g (Boot Volume)"
#   3. If it shows ATTACHED somewhere, detach via the listed instance
#      ("Detach" button on the instance's Attached Block Volumes tab)
#   4. Once truly detached, click "Attach to Instance" -> everlight-prod-a1
#      -> Attach as: Paravirtualized -> Volume Access: Read-only
#   5. On e5-mother, run:
#        sudo dmesg | tail -10        # find the device, usually /dev/sdb
#        sudo mkdir -p /mnt/orphan
#        sudo mount -o ro,nouuid /dev/sdb3 /mnt/orphan  # 3rd partition is root
#        diff -rq /mnt/orphan/home/opc /home/ubuntu/e5_data | head -50
#        sudo umount /mnt/orphan
#   6. Back in Console: detach + delete the boot volume.

# ============================================================================
# OPTION B -- terminate everlight-recovery-clean (quickest, recommended)
# ============================================================================
# Run from phone with OCI CLI configured.
# This is a hard termination -- the boot volume is deleted with the instance
# by default. If you want to keep the boot vol, add --preserve-boot-volume true.
#
# 1. Verify what we'd lose
oci compute instance get --instance-id "$RECOVERY_CLEAN_OCID" 2>&1 | grep -E '(time-created|metadata|display-name)' | head -5
#
# 2. Terminate (commented out -- uncomment to execute)
# oci compute instance terminate --instance-id "$RECOVERY_CLEAN_OCID" --force
#
# 3. Verify quota freed
# oci bv boot-volume list --compartment-id "$TENANCY" --all 2>&1 | grep -v Warning | python3 -c "
# import sys,json; d=json.load(sys.stdin)
# print(sum(int(v.get('size-in-gbs',0)) for v in d.get('data',[])))"

# ============================================================================
# OPTION C -- just delete the orphan boot volume (most aggressive)
# ============================================================================
# Risks: lose dispatcher_relay.py original, journald history, unique configs.
# Mitigations: dispatcher_relay rebuilt from memory; doctrine + audit log
# preserved on phone + GitHub.
#
# oci bv boot-volume delete --boot-volume-id "$ORPHAN_BV_OCID" --force

# ============================================================================
# OPTION 4 (always) -- create + attach a new 50 GB block volume to e5-mother
# ============================================================================
# After reclaiming 47 GB above, run this to add the new volume.

# 4a. Create the volume
oci bv volume create \
  --compartment-id "$TENANCY" \
  --availability-domain "$AD" \
  --display-name "everlight-data-50gb" \
  --size-in-gbs 50 \
  --vpus-per-gb 0 \
  --wait-for-state AVAILABLE

# 4b. Get the new volume's OCID (replace with output from 4a)
# NEW_VOLUME_OCID="ocid1.volume.oc1.us-sanjose-1...."

# 4c. Attach as paravirtualized (no iSCSI fiddling)
# oci compute volume-attachment attach-paravirtualized-volume \
#   --instance-id "$EMOTHER_OCID" \
#   --volume-id "$NEW_VOLUME_OCID" \
#   --wait-for-state ATTACHED \
#   --is-read-only false

# 4d. On e5-mother, format and mount
# ssh -i /root/.ssh/github_deploy ubuntu@100.125.115.95 <<'REMOTE'
#   # find the new device
#   lsblk
#   # usually /dev/sdb -- format XFS
#   sudo mkfs.xfs -L everlight-data /dev/sdb
#   sudo mkdir -p /data
#   sudo mount /dev/sdb /data
#   # persist in fstab
#   echo 'LABEL=everlight-data /data xfs defaults,noatime,nofail 0 2' | sudo tee -a /etc/fstab
#   df -h /data
# REMOTE

# 4e. Move workspace mirror + snapshots to the new volume
# ssh -i /root/.ssh/github_deploy ubuntu@100.125.115.95 <<'REMOTE'
#   sudo mv /home/ubuntu/AA_MY_DRIVE /data/AA_MY_DRIVE
#   sudo ln -s /data/AA_MY_DRIVE /home/ubuntu/AA_MY_DRIVE
#   sudo mv /home/ubuntu/blinko_backups /data/blinko_backups
#   sudo ln -s /data/blinko_backups /home/ubuntu/blinko_backups
#   df -h / /data
# REMOTE

# After this: e5-mother root drops from 35 GB used to ~13 GB used (74% free).
# /data has plenty of headroom for snapshots, archives, growth.
