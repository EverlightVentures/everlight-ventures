# ALLEY KINGZ -- DEPLOY CHECKPOINTS & ANTI-REVERT DOCTRINE

> Created 2026-06-18 after the v22 clobber. The live site silently reverted a WEEK of work because a
> rogue cron (`run_crown.sh`, e5 crontab `15 0,12 * * *`) auto-deployed a STALE `~/ak_crown` copy to the
> same CF Pages project. **Nothing was ever lost** -- the good build lives on e5 `~/ak_deploy` + the phone
> workspace; only the live CDN got overwritten. This doc makes that impossible going forward.

## HARD RULES (non-negotiable)
1. **ONE canonical source.** alleykingz.online deploys ONLY from **e5 `~/ak_deploy/game`** via `~/ak_deploy/ship.sh`.
   No other directory may deploy to the `alley-kingz` CF project. Ever.
2. **NO stale parallel sources.** Any other game copy on e5 (`~/ak_crown/ecosystem/game`, etc.) is either
   removed or kept as a read-only mirror of `~/ak_deploy` -- it must NEVER auto-deploy.
3. **NO auto-deploy crons/daemons.** The only deploys are explicit, from `~/ak_deploy`, by the sole-deployer chat.
   (`run_crown.sh` deploy cron REMOVED 2026-06-18; crontab backed up to `~/crontab.bak.*`.)
4. **Checkpoint before + after every significant change.** Git-commit the AK code; log the version here.
5. **Verify the LIVE edge after every deploy** (size + markers), never trust "DEPLOYED".

## HOW TO RESTORE (if the live site is ever wrong)
1. Confirm the good build on e5: `ssh e5 'grep -c AK-MAPWIRE ~/ak_deploy/game/index.html'` (good = 1; ~519KB index).
2. Re-ship: `for k in 1..10; do ssh e5 'cd ~/ak_deploy && bash ship.sh' | grep -q DEPLOYED && break; done`
3. Verify live: `curl -s 'https://alleykingz.online/?cb=$(date +%s)' | grep -c AK-MAPWIRE` (want 1, size ~519KB).
4. If e5 is wiped, restore from the git checkpoint commit (see list) or the phone workspace `.../ecosystem/game`.

## CHECKPOINT LIST (known-good versions -- newest first)
| Date | Marker / size | Git commit | Contents |
|------|---------------|-----------|----------|
| 2026-06-18 | AK-MAPWIRE + AK-SPECIALART + AK-CLASHFILL + AK-TOWERHP-VIS, ~519KB index | (committing) | Full week: 7 keyword mechanics, kill-streak evolution, handler classes + 6 PORTRAITS, spell art (hand+deck+tile), special-cast + totem/turret sprites, foldable Clash-fill, tower-HP, 64 routed Download assets, 220/400 recovered maps + themed-map wiring. THE good build. |
| (pre-2026-06-18) | v22, ~147KB index | -- | STALE. 3-tile lobby, dead shop, no custom art. **Do NOT deploy. This is what clobbered us.** |

## SAVING-PROGRESS CHECKLIST (run before declaring a deploy "done")
- [ ] Code committed to git on the phone (the SOT).
- [ ] `~/ak_deploy` is the only thing that shipped; no other source touched the CF project.
- [ ] Live edge verified: index size ~519KB+ and expected markers present (curl with `?cb=`).
- [ ] This CHECKPOINT LIST updated with the new version + git commit hash.
- [ ] No new auto-deploy cron/daemon was introduced.
