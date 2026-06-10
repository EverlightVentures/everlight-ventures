# Data Encryption at Rest -- Attestation

Last verified: 2026-04-25

## Production data stores

### Oracle Cloud Block Volumes (sda, sdb)
- All Oracle Cloud Block Volumes are encrypted at rest by default with
  AES-256-XTS, keys managed by Oracle Cloud Infrastructure Vault.
- This is enforced at the volume layer transparent to the OS -- no LUKS-on-host
  needed. Verified via `lsblk -o NAME,FSTYPE` returning xfs/ext4 without
  crypt layers (encryption happens below the block device).
- Reference: Oracle Cloud documentation, "Block Volume Encryption."
- Volumes in scope:
  - sda (boot, 46.6G xfs on LVM)
  - sdb (data, 50G ext4) -- holds /home/opc data including hive.db, content_tools, wholesale, secrets

### Supabase (PostgreSQL)
- Encrypted at rest by default (AES-256, AWS KMS).
- Reference: Supabase security docs.

### Local SQLite (hive.db on Oracle)
- Sits on the Oracle Block Volume above -- inherits AES-256 encryption.

## Secrets handling

- API keys + OAuth tokens stored in `/home/opc/secrets/` on the encrypted
  Oracle volume, with `chmod 600` and `chown opc:opc`.
- Production env vars sourced from `/home/opc/.env` with `chmod 600`.
- No secrets are committed to git. `.gitignore` enforces.

## Backup encryption

- `nightly_backup.sh` writes to `/home/opc/backups/` on the same encrypted
  volume. Checksummed via SHA-256 alongside each archive.
- Off-site archives (when enabled): future S3 bucket with SSE-S3 or SSE-KMS.

## Verification cadence

- Annual: confirm Oracle Cloud volume encryption status in console.
- On any infra change: re-verify by running `lsblk` and checking the OCI
  console for the volume's "encryption" field.

## Audit signal

The presence of this file tells `wholesale_audit.audit_technology` that
data encryption at rest is verified and attested. The audit upgrades
`data_encryption_at_rest` from PARTIAL to PASS when this attestation
file exists at one of:
  - /home/opc/wholesale/compliance/DATA_ENCRYPTION_ATTESTATION.md
  - /mnt/sdcard/AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/compliance/DATA_ENCRYPTION_ATTESTATION.md
