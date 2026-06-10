# Everlight Mesh Restore + Sync Plan
**Author:** Lucrex / Hive  **Date:** 2026-05-14  **Status:** pre-staged, awaiting box landing

## 0. The goal in one sentence

No single device runs the enterprise. Oracle is the always-on prod brain; phone
and PC are interchangeable control planes that can push work to it; the
AceMagician PC is a warm standby that can *become* prod with a one-line change
if the cloud is ever lost.

---

## 1. Verified current state (2026-05-14, ground-truthed this session)

| Thing | Reality |
|---|---|
| Old `.250` E5 "mother" | DEAD since 2026-04-30. Boot volume recovered intact -> `_oracle_e5_recovery/2026-05-07/` (3.9 GB tree, 25 systemd units, 4 docker stacks, `.env` + secrets). "FULL CAPTURE COMPLETE". |
| New instance | Phone is provisioning an **Ampere A1.Flex 4 OCPU / 24 GB** in us-sanjose-1. Shape is Always-Free-eligible -> **$0 bill** even though account is now PAYG. |
| A1 capacity | Confirmed available: limit=4 OCPU, **4/24 free, 0 used**. The hammer's earlier "service limits exceeded" was transient. PC hammer **stopped** to give the phone an uncontested launch. |
| xlm-bot Micro `.196` | **ALIVE** -- `xlm-bot.service` + `xlm-ws.service` active, up 8 days. Just ICMP-blocked. **Does NOT migrate.** (Only `xlm-dashboard` inactive -- minor fix.) |
| Tailnet | `acemagician-pc` (100.93.253.49) up, `richards-z-fold7` (phone) active, `mgn-latitude-e7240` (Dell) offline 8d. New box + Micro not yet on tailnet. |
| Git canonical | `github.com/EverlightVentures/aa-my-drive`, branch `main`. |
| PC (AceMagician) | Workspace `/AA_MY_DRIVE` (git root, 6.4 GB .git). Docker installed + running. Can host the full stack -> warm standby is viable. |

---

## 2. Target architecture

```
                    ┌──────────────────────────────┐
   git push / pull  │   GitHub  aa-my-drive (main)  │  canonical CODE + CONFIG
   from any device  └──────────────┬───────────────┘
                                   │ pull
            ┌──────────────────────┼───────────────────────┐
            │                      │                       │
      ┌─────┴─────┐         ┌───────┴────────┐       ┌───────┴───────┐
      │  PHONE    │  tailnet│  ORACLE A1     │tailnet│  ACEMAGICIAN  │
      │ (control) │◄───────►│  e5-mother     │◄─────►│  PC (control  │
      │           │  sync   │  PROD BRAIN    │ sync  │  + WARM STDBY)│
      └───────────┘         │  24/7 always-on│       └───────────────┘
            ▲               │  Blinko, hive  │              │
            │ tailnet sync  │  engines, MCP, │              │ warm-standby
            │               │  Django?, n8n✗ │              │ pull (hourly)
      ┌─────┴─────┐         └───────┬────────┘              ▼
      │   DELL    │                 │ deploy          [full stack snapshot
      │ (thin)    │                 │                  ready to boot on PC]
      └───────────┘         ┌───────┴────────┐
                            │  ORACLE MICRO  │  xlm-bot -- SEPARATE, stays put
                            │  .196  xlm-bot │  (verified live, do not touch)
                            └────────────────┘
```

**Source-of-truth rules:**
- **Code + config + agents + memory** -> Git (`aa-my-drive`). Push from any device, prod pulls.
- **Blinko notes** -> the prod box (e5-mother). Mirrored nightly.
- **Deal pipeline** -> Supabase cloud. No local sync.
- **xlm-bot** -> the Micro `.196`. Independent. Deployed via `deploy_to_oracle.sh bot`.
- **Workspace data files** -> phone has historically been SOT; post-mesh, treat the
  prod box as SOT for *runtime* data, git for *everything versionable*.

---

## 3. The keystone: "nothing changes but the IP"

Every sync / deploy / restore / failover script sources **one file**:
`03_AUTOMATION_CORE/01_Scripts/mesh/hive_hosts.env`

It addresses prod by **Tailscale MagicDNS name** (`e5-mother`), never a raw IP.
Two ways the "one change" failover works:

1. **Soft (always works):** edit `HIVE_PROD_HOST` in `hive_hosts.env`, commit,
   push. Every device picks up the new prod target on next pull. `failover_to_acemagician.sh`
   does this edit automatically.
2. **Cleanest (zero-edit):** in the Tailscale admin console, delete the dead
   cloud node and **rename the AceMagician node to `e5-mother`**. Now the name
   `e5-mother` simply resolves to the PC -- not one script changes.

Either way the blast radius of a total cloud loss is *one hostname*.

---

## 4. Execution phases

### Phase 1 — Provision (PHONE, in progress)
Phone runs `e5_mother/provision.sh <public-ip>`. Brings up the **lean replacement
stack**: Blinko (PG-backed), agentmemory MCP, Open WebUI, hive-voice, nginx
tailnet proxy. Joins the box to the tailnet as `e5-mother`.
→ **When done, phone reports back the box's public IP + confirms tailnet name.**

### Phase 2 — Restore `.250` (PC, `restore_250_to_new_instance.sh`)
Runs *after* Phase 1. Restores the half provision.sh doesn't cover:
- `.env` + `secrets/` (all production keys)
- hive orchestrators, `content_tools/`, `broker_os/`, `hive_*.py`, `hive_reports/`
- systemd units: hive-action-engine, hive-self-healer, hive-task-runner,
  hive-reports, hive-slack-agent, hive-directory, hive-dashboard, mcp-*-proxy fleet
- `documenso` docker stack (broker contract signing)
- Path/user translation: `/home/opc`→`/home/ubuntu`, `User=opc`→`User=ubuntu`,
  `/mnt/sdcard/AA_MY_DRIVE`→prod workspace path
- **Skips** Blinko/n8n/OpenWebUI/agentmemory/hive-voice (provision owns them).
- **Django gated** behind `--with-django` (deferred by recover-and-replace doctrine;
  flip the flag if you want it back now — see Open Decisions).

### Phase 3 — Wire the 3-device sync mesh
- New box + Micro **join the tailnet** (`tailscale up`). Then switch
  `HIVE_BOT_HOST` from the `.196` IP to a MagicDNS name.
- **Unify the SSH key**: add `github_deploy.pub` to the Micro's
  `authorized_keys` so the whole mesh uses one key. (Today: Micro=oracle_key.pem,
  box=github_deploy.)
- `sync_on_reconnect.sh` already implements the peer mesh — update its peer
  registry to the confirmed coordinates, drop the stale `micro|opc@oracle-e5` row.
- `claude_sync_acemagician.sh` (mature) keeps `.claude/` + memory in sync PC↔phone.

### Phase 4 — Push-to-pipeline flow (how PC/phone changes reach prod)
Two layers, both git-anchored so any device works:
1. **Code/config:** edit on phone or PC → `git push` → prod runs a pull+restart
   hook (cron `*/10`, or on-demand). Git is the merge point; conflicts resolve
   the normal way, never last-writer-wins overwrites.
2. **Runtime deploy:** `deploy_to_oracle.sh` (now hostname-addressed) pushes
   xlm-bot code to the Micro and hive scripts/Django to the prod box, then
   restarts the affected services.
> Follow-up: `deploy_to_oracle.sh`'s config block is rewritten (sources
> `hive_hosts.env`, no dead IPs, no committed token). Its `deploy_scripts/
> deploy_django` function *bodies* still carry old `/mnt/sdcard` paths + no
> `-P` port flag — reconcile once the box's real SSH coords are confirmed.

### Phase 5 — AceMagician warm standby (`acemagician_warm_standby.sh`)
Hourly (cron / on-wake) pull from prod into `/AA_MY_DRIVE/_warm_standby/`:
home tree, docker named-volume snapshots, systemd unit files, a manifest.
Also `docker pull`s prod's images locally so failover is instant.
→ The PC is always ≤1 hr behind prod, ready to boot the whole stack.

### Phase 6 — Failover drill (`failover_to_acemagician.sh --drill`)
Rehearse bringing the stack up on the PC from the snapshot **without** flipping
the prod pointer. Run this once after Phase 5 proves out, so a real failover is
muscle memory. Real failover = same script without `--drill`; `--failback`
flips back to cloud when it's restored.

---

## 5. The pre-staged kit (built 2026-05-14, in `01_Scripts/mesh/`)

| File | Role |
|---|---|
| `hive_hosts.env` | **Keystone.** Canonical host map, tailnet-name addressed, auto-detects local paths/keys. Failover = edit one line here. |
| `restore_250_to_new_instance.sh` | Phase 2. `.250` tree → new box. `--dry-run`, `--with-django`, `--only=` flags. |
| `acemagician_warm_standby.sh` | Phase 5. Pulls full prod state to the PC. `--quick`, `--dry-run`. |
| `failover_to_acemagician.sh` | Phase 6. Brings stack up on PC + flips pointer. `--drill`, `--force`, `--failback`. |
| `deploy_to_oracle.sh` (edited) | Phase 4. Config block rewritten to source `hive_hosts.env`. |
| `MESH_PLAN.md` | This document. |

All scripts carry `>>> VERIFY ON LANDING <<<` markers — the EXPECTED box
coordinates (`e5-mother`, user `ubuntu`, port `2222`) are placeholders from the
existing provisioning kit. Confirm/correct them in `hive_hosts.env` the moment
the phone reports the box up — and the whole kit picks up the change.

---

## 6. Open decisions (need Rich's call)

1. **Django** — recover-and-replace doctrine *deferred* `hive-django` to "Phase 7".
   Rich's "move .250 over" language leans toward full restore. Default: leave it
   deferred (`restore_250` skips it unless `--with-django`). Flip if you want the
   dashboard back now.
2. **`everlight-recovery-clean`** (the bare E2.1.Micro at `64.181.242.230`) — keep
   as a jumpbox, or terminate to free a boot-volume slot?
3. **Orphan boot volumes** — `xlm-bot-core-e5-2c16g` + `e5-fresh-recovery-mount`
   (~94 GB of the 200 GB cap). Safe to delete *after* the restore is verified
   end-to-end. Recommend keeping `xlm-bot-core-e5-2c16g` as cold backup until then.
4. **Two workspace copies on the PC** — `/AA_MY_DRIVE` (git root) and
   `/home/richgee/AA_MY_DRIVE` are *different* directories. Pick one canonical,
   reconcile the other, before wiring PC sync — otherwise sync ping-pongs.

---

## 7. Quick runbook (once the box lands)

```bash
cd /AA_MY_DRIVE/03_AUTOMATION_CORE/01_Scripts/mesh

# 1. confirm/correct the box's real coordinates
$EDITOR hive_hosts.env          # set HIVE_PROD_HOST/USER/PORT to what the phone used
source hive_hosts.env && hive_hosts_show && hive_prod_up && echo "prod reachable"

# 2. restore the .250 brain (dry-run first)
bash restore_250_to_new_instance.sh --dry-run
bash restore_250_to_new_instance.sh        # add --with-django if decision #1 says so

# 3. restore Blinko's 614 notes
python3 ../blinko_restore_from_lite.py

# 4. first warm-standby capture + failover drill
bash acemagician_warm_standby.sh
bash failover_to_acemagician.sh --drill

# 5. commit the mesh kit so phone + Dell get it
cd /AA_MY_DRIVE && git add 03_AUTOMATION_CORE/01_Scripts/mesh deploy_to_oracle.sh \
  && git commit -m "mesh: hostname-addressed restore + warm-standby kit" && git push
```
