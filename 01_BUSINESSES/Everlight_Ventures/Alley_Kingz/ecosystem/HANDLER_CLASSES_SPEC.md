# ALLEY KINGZ -- HANDLER CLASSES + BATTLE SPECIALS (build-ready spec)
**Your version of DMZ active-duty operators x Clash Royale Champions -- dog-themed, with a $BCARDD class.**
Date: 2026-06-14

## WHERE THIS FITS (3 distinct layers -- don't confuse them)
1. **STREET CODE** (exists): meta perk tree, Muscle/Hustle/Tech, out-of-battle. Untouched.
2. **Card combat classes** (exists): per-card roles/abilities (classes.js taxonomy). Untouched.
3. **HANDLER (NEW):** the dog "operator" YOU bring into each match -- one tap-to-fire **Special** that
   **recharges mid-battle** (like a CR Champion ability / a DMZ field upgrade), plus passives, plus a
   per-Handler **skill tree** (diverse upgrades, DMZ-style). This is the new system.

## THE RECHARGE MECHANIC (CR Champion + DMZ field upgrade)
- Each match you have a **Handler portrait + a SPECIAL METER** on the HUD.
- The meter fills over time (and faster as you deploy cards / deal damage). When full, **tap to fire** the Special.
- Some Handlers bank **2 charges**. Upgrades shorten recharge / add a charge. Exactly the "recharge during the
  game" feel you described, and the "drop a turret" tap-ability -- but with class variety instead of one fixed turret.

## THE 6 HANDLERS (dog breeds + DMZ-perk-style specials; faction-aligned)
| Handler | Breed / role | SPECIAL (tap to fire) | Passive | Faction lean |
|---|---|---|---|---|
| **The Mender** | St. Bernard / Medic | **Field Kennel** -- drop a totem that heals friendly units in radius | friendlies regen slightly | Boneguard |
| **The Tracker** | Bloodhound / Scout | **Scent Probe** -- the DMZ recon probe: reveals the enemy's next deploys + marks them (+dmg taken) | see enemy deploys a beat early | K9 Circuitry |
| **The Shadow** | Basenji / Ninja | **Slipstream** -- target friendly gets +speed + brief untargetable stealth | your units move a touch faster | Zoomie Syndicate |
| **The Rigger** | Doberman / Engineer | **Drop Rig** -- YOU pick the turret: **Gun Nest** (ranged) / **Tesla Coil** (chain shock) / **Flak** (anti-air) | structures last longer | K9 Circuitry |
| **The Bruiser** | Pit/Mastiff / Tank | **War Cry** -- nearby friendlies get +dmg + damage-reduction (rally) | your units a bit tankier | Leashbreak Tactix |
| **The Dealer** ($BCARDD) | the coin dog (card #0001) / Wildcard | **House Edge** -- flip a $BCARDD card for a random big effect: coin-rain (econ), a free unit, a squad buff, or a double-or-nothing gamble | small bonus Gold/Scrap per match | Boneguard / $BCARDD |

The **Dealer is the memecoin woven into gameplay** -- it literally brings $BCARDD's "luck" into battle (casino/gacha
flavor, on-brand with the dealer-is-the-coin canon). Market as FUN, never investment (per the $BCARDD doctrine).

## PER-HANDLER SKILL TREE (DMZ-diverse + your MMA-notebook "Skill Constellation" UX)
- Each Handler has a small **constellation** (T1 unlock -> two T2 branches -> a T3 capstone), e.g. The Mender:
  - T1 Field Kennel | T2a +radius / +heal rate | T2b -recharge / +1 charge | T3 **Revive** (one dying friendly bounces back).
  - The Tracker T3 = **Tag** (revealed enemies take bonus dmg from everyone); Shadow T3 = **Backstab** (crit on stealth-exit);
    Rigger T3 = unlock the 3rd rig + auto-repair; Bruiser T3 = **Last Stand** (rally also briefly shields); Dealer T3 =
    **$BCARDD Blessing** (a screen-shaking coin-blast ultimate).
- Currency: **Bones** (Handler mastery -- on-brand). You earn Bones by PLAYING a Handler (mastery levels), kept SEPARATE
  from STREET CODE's SP so neither cannibalizes the other. Reuse the STREET CODE skill-tree visual + the MMA notebook
  gold-on-vanta constellation look for consistency.

## NAMING / BRANDING (stays in theme)
Handlers = dog archetypes; specials = alley/dog flavor (Field Kennel, Scent Probe, Slipstream, Drop Rig, War Cry,
House Edge). Each leans a lore faction so it ties into crews + the storyline. Art via Seedance later (handler
portraits + special VFX) -- on the gem/premium tier per PRICING_STRATEGY.md.

## BUILD PLAN (phased -- this touches the battle engine, so we go careful)
| Phase | What | Where | Effort |
|---|---|---|---|
| **1** | Handler SELECT (pre-match) + 3 starters (Mender/Tracker/Rigger) + HUD meter + tap-to-fire + their base specials + the Handler tree UI (Bones) | new `handlers.js` + engine `activeSpecial` hook + profile field | ~1 wk |
| **2** | Shadow/Bruiser/Dealer + T3 capstones + the $BCARDD Blessing ultimate + recharge/charge upgrades | engine + handlers.js | ~1 wk |
| **3** | Balance pass + Handler cosmetics (Seedance portraits/VFX -> gem tier) | data + art | ongoing |

**Engine work (the careful part):** add an `activeSpecial` system to the sim -- a meter (fills on dt + card plays +
damage), `fire()` that applies a per-special effect (heal totem = a friendly healing structure; probe = reveal +
debuff flag; slipstream = temp speed+untargetable on a unit; rig = a chosen turret structure; war cry = an AoE buff
field; house edge = a weighted random-effect roll). Each effect reuses existing sim primitives (structures, buffs,
targeting flags) so it's additive, not a rewrite. HUD: a Handler portrait + radial meter near the card hand.

## THE ONE DECISION
**Approve the 6 Handlers + the recharge-special + Bones tree, and build Phase 1** (Handler select + 3 starters +
the in-battle meter/fire + tree UI)? On yes I build Phase 1 and verify a real match fires a special cleanly.
