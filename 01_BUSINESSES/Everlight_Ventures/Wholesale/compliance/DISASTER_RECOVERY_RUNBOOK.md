# Disaster Recovery Runbook -- Everlight Wholesale

**Recovery Time Objective (RTO):** 4 hours for full system restore
**Recovery Point Objective (RPO):** 24 hours max data loss

## Threat model

1. Oracle E5 VM dies / corrupts -> 4-hour rebuild from snapshot
2. Supabase outage (their side) -> read-only for ~1-4 hours, no data loss
3. Phone (Rich's device) lost / wiped -> 1 hour to restore from cloud + git
4. Ransomware on Oracle -> 4-hour restore from snapshot, IP-block forever
5. Stripe / Twilio / ElevenLabs key compromise -> 1-hour rotation per key (see API_KEY_ROTATION_POLICY.md)

## Backup inventory

| Asset | Backup mechanism | RPO |
|-------|------------------|-----|
| Django sqlite (`db.sqlite3`) | Daily cron tarball to `~/backups/django_YYYYMMDD.tar.gz` | 24h |
| `_logs/hive.db` (475MB log store) | Auto-rotated by `rotate_logs.py`; nightly to Oracle snapshot | 24h |
| Supabase data | Provider auto-backup, 7-day retention, point-in-time recovery | 24h |
| `_logs/*.jsonl` streams | Append-only, replicated via `regenerate_index` weekly | 7d |
| `/home/opc/wholesale/` code | Git push to GitHub on every deploy via `deploy_to_oracle.sh` | minutes |
| `/home/opc/secrets/` (OAuth tokens, API keys) | Encrypted backup to `~/.secrets-backup.tar.gz.gpg` weekly | 7d |
| Phone workspace | Auto-rsync to Oracle every 10 min via deploy cron | 10 min |

## Restore procedures

### Scenario A: Oracle E5 dies

1. Provision fresh Oracle Cloud E5 VM from latest snapshot
2. Restore from snapshot at boot time (Oracle Cloud panel -> Compute -> Boot Volumes -> Create from Snapshot)
3. Sshd up; restore `/home/opc/.env` from `~/.secrets-backup.tar.gz.gpg`
4. Run `bash /home/opc/scripts/restart_all_services.sh` (rebuilds systemd units + cron from manifest)
5. Verify each service: `systemctl status xlm-bot django blinko hive-voice n8n`
6. Run `python3 /home/opc/wholesale/audit/wholesale_audit.py` -- score should match pre-disaster within 5 percentage points

**Estimated total: 2-4 hours.**

### Scenario B: Supabase outage

1. Confirm via https://status.supabase.com
2. App goes read-only via env var `SUPABASE_READ_ONLY=1`
3. Critical writes (Deal stage changes, ConsentLedger, EMD) buffered to local jsonl stream `_logs/supabase_pending.jsonl`
4. When Supabase recovers: replay buffer via `python3 /home/opc/scripts/replay_supabase_buffer.py`

### Scenario C: Phone wiped

1. Boot replacement phone, install Termux + Claude Code per `~/.termux/boot/start_hive.sh`
2. Pull workspace fresh: `git clone <repo>` to `/mnt/sdcard/AA_MY_DRIVE`
3. Restore `.env` from password manager
4. Run boot script: SSH tunnels reconnect, crons resume
5. Verify with `python3 03_AUTOMATION_CORE/01_Scripts/hive_health_monitor.py --report`

### Scenario D: Ransomware on Oracle

1. **Do NOT pay.** Trace entry vector: SSH brute force, exposed port, compromised key
2. Rebuild Oracle from snapshot taken 24-48h prior (pre-infection)
3. Rotate ALL API keys via `API_KEY_ROTATION_POLICY.md`
4. Force MFA on all dashboards
5. Audit `_logs/auth.log` for unfamiliar IPs since the last clean snapshot

## Quarterly restore test

Every Q1, Q2, Q3, Q4: run a non-destructive restore test:

```bash
ssh oracle-bot "tar tzf ~/backups/django_$(date -d 'last week' +%Y%m%d).tar.gz | head -20"
```

Verifies the backup tar is readable and contains expected file structure. Logs to `~/_logs/dr_test.jsonl` so the audit can confirm.

## Communication during incident

- Internal: Slack #hive-alerts via branded_alert
- External (sellers / buyers / title cos with active deals): templated email via branded_mailer apologizing for delay + ETA. Use category `system` to bypass budget gates.

_Owner: Rich. Reviewer: external CPA + IT consultant annually._
