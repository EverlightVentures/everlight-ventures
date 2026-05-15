# Oracle E5 Mother — Recovery Log

> Append-only. Each entry dated. Single source of truth for what we restored vs what was lost.

## 2026-05-11 — Phase 1: Data Source Probe

### Blinko Lite (`_logs/blinko_lite.db`, 5.1 MB, last write 2026-04-24)

- **614 notes** in the `notes` table (more than the 449 doctrine figure).
- Schema: `id TEXT PK, content TEXT, type INTEGER default 1, tags TEXT, created_at TEXT, updated_at TEXT`.
- Date range: `2026-03-11` → `2026-04-24` (~6 weeks).
- Sample of 5 most recent rows confirms this is **real Blinko content** — hive session summaries, XLM 30-day move analysis, log archive summaries (feature_snapshots, equity_series, decisions, report_history). Not a write-ahead buffer.
- **Recovery status: GO.** Phase 4 will use this DB as the canonical restore source via `blinko_restore_from_lite.py`.

### hive_dashboard (`09_DASHBOARD/hive_dashboard/db.sqlite3`, 6.3 MB, last write 2026-04-27)

- 52 non-system tables. Substantial data, NOT test fixtures:
  - `broker_ops_brokermatch`: 1893 rows
  - `broker_ops_leadprofile`: 515 rows
  - `broker_ops_propertylead`: 436 rows
  - `broker_ops_outreachsequence`: 131 rows
  - `broker_ops_offerlisting`: 132 rows
  - `hive_hivesession`: 100 rows
  - `hive_agentresponse`: 285 rows
  - `hive_systemevent`: 56 rows
  - `hive_querylog`: 95 rows
  - `taskboard_taskitem`: 46 rows
  - `taskboard_tasktemplate`: 28 rows
  - `business_os_businessevent`: 41 rows
  - `business_os_revenuestream`: 9 rows
  - Plus rewards + blackjack tables with seed content (cosmetics 21, gem packages 5, comp thresholds 7).
- **Recovery status: HELD.** Per user decision, hive-django (`:8000`) is deferred to Phase 7. Data is preserved on the phone sdcard until Phase 7 decision is made.
- **Risk if deferred indefinitely:** 1893 broker matches + 436 property leads sit unaddressable from any UI. Branded mail / Slack workflows that referenced this DB will need re-pointing if Django stays retired.

### n8n workflows — UNRECOVERABLE

- No JSON exports anywhere in the workspace.
- Dead mother's volume not mounted (recover-and-replace, not forensic).
- **Recovery status: WRITE-OFF.** n8n is parked per doctrine (`GDOCS_DISABLE_N8N=1`). Acceptable loss.

### hive-voice handler (`03_AUTOMATION_CORE/01_Scripts/hive_voice_handler.py`, 12 KB)

- Source intact on phone.
- **Recovery status: GO.** Phase 3 deploys via systemd unit on `:8200`.

### secrets — REGENERATE

- No portable secrets vault available. `.env` files on the dead mother are lost.
- **Action on new mother:** regenerate from provider dashboards — Resend, Stripe, Supabase anon, OpenAI, Anthropic, ElevenLabs (if voice TTS reused). Save to `/home/ubuntu/.env` on mother during Phase 3, locked to ubuntu user.

## Open follow-ups

- Confirm `claude_sync_acemagician.sh` had been pushing memory to PC up through dead-mother era — if PC has a more recent memory snapshot, pull it on PC return.
- Decide Phase 7 hive-django fate after Open WebUI + Supabase have run for 2 weeks. If Supabase + Open WebUI cover the ops view, retire Django and re-route broker_ops to Supabase. If not, deploy Django from intact source.

## 2026-05-11 — OCI launch attempted, capacity locked, sequenced fallback plan

### What happened
- OCI CLI authenticated, security list port 2222 opened (user-authorized), boot-volume quota gate hit (3 × 47 GB existing = 141 GB of 200 GB free-tier). Shrank planned boot vol from 100 GB → 50 GB to fit.
- Submitted `oci compute instance launch` for VM.Standard.A1.Flex. Hit **"Out of host capacity"** at every shape tried: 4/16, 4/12, 2/12, 2/8, 1/6. Region (us-sanjose-1) is fully drained for free-tier Ampere.
- Hunter `03_AUTOMATION_CORE/01_Scripts/e5_mother/launch_when_capacity_opens.sh` running indefinitely (--max=0 --interval=300s). State at `_state/e5_mother_launch.{status,ocid,ip}`.

### Sequenced restore plan (per user direction 2026-05-11)
1. **Now:** keep hunter running, no architectural pivot. No deadline.
2. **When CC arrives:** pay for Ampere instance (or paid OCI tier) to restore `.250` capability on a real always-on VM. Once paid, capacity issue goes away.
3. **After restore:** implement architecture option 1 (Supabase pgvector for memory, Cloudflare Workers for hive-voice, AceMagician PC for Open WebUI when up). $0/month operational, max free-path.
4. **One more OCI free-tier try** for an Ampere instance after step 2 stabilizes (capacity may have opened in the interim).
5. **Backstop:** Hetzner CX22 €4.51/mo (~$5) if all else fails. 2 vCPU / 4 GB, monthly-cancellable.

### Orphan resources to clean (later, frees ~95 GB boot quota)
- `xlm-bot-core-e5-2c16g (Boot Volume)` — 47 GB AVAILABLE, from the dead .250 mother. Safe to delete.
- `everlight-recovery-clean` instance + boot volume — 1 OCPU / 1 GB E2.1.Micro + 47 GB. Aborted recovery from May 4. Verify with user before terminating.
- Won't touch xlm-bot's boot volume (currently in use by the live xlm-bot.service).

### Hunter management
- Phone-side runs aren't ideal long-term (phone sleeps, battery). Once mother is up, move the same script to e5-mother as a systemd timer per oracle-only-crons doctrine.
- Until then: if the user observes the hunter stopped, restart with `bash launch_when_capacity_opens.sh --interval=300 --max=0 &`.

## 2026-05-12 — Paid restore path confirmed, data recovery added

### User direction
- Adding credit card to Oracle to bypass free-tier capacity wall (paid Ampere has separate inventory pool, launches immediately).
- Before deleting the dead .250: extract everything possible from the orphan boot volume `xlm-bot-core-e5-2c16g (Boot Volume)` (OCID ...u3l3ua).
- Plan-B (split services across Hetzner / AceMagician / Cloudflare Workers) stays on the shelf, not for today.

### Full plan delivered as HTML per `feedback_html_not_md.md`
- `/mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/reports/oracle_paid_restore_plan_20260512.html`
- 8 sections, 239 lines, gold/dark branded template.
- Covers: capacity status, why CC unlocks paid pool, cost projections, data-recovery procedure (vgimport ocivolume + mount ro), tied-together architecture diagram, 11-step execution sequence, Plan B reference, status reference links.

### Hunter still running while waiting
- PID alive, status `polling`, ~657 capacity rejections logged across 130+ attempts. Continues indefinitely (--max=0 --interval=300s) until user adds CC and we kill it.

### Recovery procedure key insight
- The dead .250 ran Oracle Linux 9 with LVM volume group `ocivolume` (confirmed from Micro showing same pattern at `/dev/mapper/ocivolume-root`).
- New mother is Ubuntu 22.04 ARM (raw partitions, no LVM by default).
- No name collision → `sudo vgimport ocivolume && sudo vgchange -ay ocivolume && sudo mount -o ro /dev/ocivolume/root /mnt/old_e5` lands clean.
- Read-only mount is critical to preserve the orphan boot vol for verification reads.

### Open with user
- When does the CC land on Oracle account?
- Inventory review preference: full file list before rsync, or "pull everything under /home/opc and /etc/systemd"?
- Terminate `everlight-recovery-clean` instance + its 47 GB boot vol? (Aborted recovery from 2026-05-04.)
