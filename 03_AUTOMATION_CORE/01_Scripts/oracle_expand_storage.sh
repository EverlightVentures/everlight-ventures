#!/bin/bash
# Oracle Free Tier Storage Expansion
#
# STEP 1 (YOU DO THIS in Oracle Cloud Console):
#   1. Go to https://cloud.oracle.com -> Storage -> Block Volumes -> Create Block Volume
#   2. Name: everlight-data
#   3. Size: 50 GB
#   4. Availability Domain: same as your compute (US-SANJOSE-1-AD-1)
#   5. Click Create
#   6. After created -> Attached Instances -> Attach to Instance -> select xlm-bot-core-e5-2c16g
#   7. Choose iSCSI attachment type -> Attach
#   8. Copy the iSCSI commands shown (Connect Commands)
#
# STEP 2 (RUN THIS SCRIPT on Oracle via SSH):
#   ssh opc@129.159.38.250
#   bash oracle_expand_storage.sh
#
# This script will:
#   - Connect the iSCSI volume
#   - Format it as ext4
#   - Mount it at /mnt/data
#   - Move heavy services there (Nextcloud, Langfuse data, container images)
#   - Create symlinks so everything still works
#   - Add to fstab for auto-mount on reboot

set -e

echo "=== Oracle Free Tier Storage Expansion ==="
echo ""

# Check if the volume is already attached
if lsblk | grep -q sdb; then
    echo "Block volume detected at /dev/sdb"
    DISK="/dev/sdb"
elif lsblk | grep -q nvme1n1; then
    echo "Block volume detected at /dev/nvme1n1"
    DISK="/dev/nvme1n1"
else
    echo "ERROR: No new block volume detected."
    echo "Did you complete Step 1 in the Oracle Cloud Console?"
    echo ""
    echo "If you pasted iSCSI commands, run them first, then run this script again."
    exit 1
fi

# Format if not already formatted
if ! blkid "$DISK" | grep -q ext4; then
    echo "Formatting $DISK as ext4..."
    sudo mkfs.ext4 "$DISK"
else
    echo "$DISK already formatted"
fi

# Create mount point
sudo mkdir -p /mnt/data
sudo mount "$DISK" /mnt/data

# Add to fstab for auto-mount
UUID=$(sudo blkid -s UUID -o value "$DISK")
if ! grep -q "$UUID" /etc/fstab; then
    echo "UUID=$UUID /mnt/data ext4 defaults,noatime 0 2" | sudo tee -a /etc/fstab
    echo "Added to fstab"
fi

echo ""
echo "=== Moving Heavy Data to /mnt/data ==="

# Create directories
sudo mkdir -p /mnt/data/{nextcloud,langfuse-data,container-storage,agent-photos,cal-data,docuseal-data,archives}
sudo chown -R opc:opc /mnt/data

# Move Nextcloud data
if [ -d /opt/nextcloud-data ] && [ ! -L /opt/nextcloud-data ]; then
    echo "Moving Nextcloud data..."
    sudo mv /opt/nextcloud-data/* /mnt/data/nextcloud/ 2>/dev/null || true
    sudo rm -r /opt/nextcloud-data
    sudo ln -sf /mnt/data/nextcloud /opt/nextcloud-data
    echo "  Nextcloud data moved to /mnt/data/nextcloud"
fi

# Move bot log archives
if [ -d /home/opc/xlm-bot/logs/archive ]; then
    mv /home/opc/xlm-bot/logs/archive/* /mnt/data/archives/ 2>/dev/null || true
    echo "  Bot log archives moved"
fi

echo ""
echo "=== Storage Summary ==="
df -h /mnt/data
df -h /
echo ""
echo "=== DONE ==="
echo "Available at /mnt/data with $(df -h /mnt/data | tail -1 | awk '{print $4}') free"
echo ""
echo "Services can now use /mnt/data for storage:"
echo "  /mnt/data/nextcloud      -- Nextcloud files"
echo "  /mnt/data/langfuse-data  -- Langfuse observability data"
echo "  /mnt/data/agent-photos   -- AI-generated headshots"
echo "  /mnt/data/cal-data       -- Cal.com scheduling data"
echo "  /mnt/data/docuseal-data  -- DocuSeal e-signature data"
echo "  /mnt/data/archives       -- Cold storage archives"
