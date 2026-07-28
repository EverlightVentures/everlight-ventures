# Phone-Cron Doctrine Conflict (documented 2026-06-30, decision DEFERRED by Rich)

**Status:** Open. Rich chose "document only" during the 2026-06-30 AIOS audit. No cron jobs were modified. This note exists so the conflict is written down and resolvable later.

## The conflict
- **Doctrine (HARD LAW):** `feedback_oracle_only_crons` + `reference_phone_crond_not_installed` say the phone is the control plane and **NEVER a cron host**; all crons live on Oracle/e5. Memory also claims "phone crond NOT installed."
- **Reality (verified 2026-06-30):** `cron` is running as a live daemon on the phone with **101 active crontab lines** driving wholesale outreach, Kalshi, Blinko, deploys, and watchdogs. The "crond not installed" claim is factually false.

These two cannot both be true. Until resolved, every "verify against source of truth" rule downstream is reading a doctrine that contradicts the running machine.

## Evidence
- Live daemon: `cron` PID confirmed running; `crontab -l` = 101 non-comment lines.
- Full read-only snapshot: `phone_crontab_manifest_2026-06-30.txt` (same folder).

## Broken / stale jobs found in the live crontab (NOT fixed, per Rich's "document only")
| Line | Job | Problem |
|---|---|---|
| 48 | `*/2` n8n healthz tunnel to **129.159.38.250** | Pings the DEAD mother (replaced by e5-mother 2026-05-11). Wasted SSH every 2 min. |
| 57 | `*/10` `deploy_to_oracle.sh` | Log frozen since 2026-05-26 (35 days); last runs "e5-mother unreachable". Auto-deploy guarantee is dead. |
| 82 | `*/5` `oracle_reachability_watchdog.py` | Crashing: "OSError [Errno 24] Too many open files" (fd leak). Stray copy parked at PID 28397. |
| 160 | `*/20` `cron_catchup.py` | Silent since 2026-05-26, same cluster as deploy_oracle. |

Note: line 50 shows a job was already RETIRED 2026-06-03 as a "zombie SCP from dead 129.159.38.250", so the dead-mother cleanup was started but not finished.

## The two ways to resolve (when Rich rules)
1. **Update doctrine to match reality.** Rewrite `feedback_oracle_only_crons` + `reference_phone_crond_not_installed` to state the phone IS the live cron host today. Fastest, zero migration risk. Cost: phone stays the single point of failure.
2. **Migrate to e5.** Port the 101 lines to e5-mother systemd timers, leave only the Termux:Boot bootstrap on the phone. Matches the law and removes the SPOF. Cost: bigger job, needs e5 reachable from a host that can push.

**Likely-cheapest correct path:** fix the shared root cause first. The fd-exhaustion leak in the watchdog (line 82) is the probable common cause of the whole ~2026-05-26 silent-cron cluster (lines 57 + 160). One fix may revive several loops regardless of which doctrine path is chosen.

## Cross-links
- [[feedback_oracle_only_crons]] · [[reference_phone_crond_not_installed]] · [[reference_infrastructure_hierarchy]] · [[feedback_cron_failover_phone_e5_required]]
- Parent audit: `aios_2026-06-30.html`
