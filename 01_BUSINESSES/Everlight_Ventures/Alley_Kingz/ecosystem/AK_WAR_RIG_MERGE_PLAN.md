# Alley Kingz -- War Rig Master Doc, merged into our canon

Read of `Alley_Kingz_War_Rig_Master_Document_v1.0.txt` (902 lines), reconciled against what
this session already built. The doc is a strong template. It agrees with us on ~90% and it
hands us the missing 10%. This is the merge, the conflicts, and the fire order.

## 1. Doc section -> our reality

| Doc part | Status vs what we have | Action |
|---|---|---|
| P1 credit budget (17,530) | MATCHES our matrix (17,750), within 1% | reconcile the dog-model line, see conflict 2 |
| P2 4-layer battle (Dog/TownHall/Rig/Weapon) | Dog+TownHall+Rig already canon; WEAPON layer is NEW | build weapon system |
| P3 DUAL-VIEW (RPG <-> FPS/TPS) + The Drop | NEW, not in our plan. Biggest addition. | design + engineer, see conflict 1 |
| P4 Garage shop (chassis/weapon/attach/paint/tune) | We have the rig+cosmetic shell; weapon+attach+tuning NEW | build |
| P5 Synergy (Dog+Rig+Weapon+Faction) | Our 3-layer bond spec covers Dog/Rig; WEAPON is a 4th layer | extend SYNERGY_SPEC to 4 layers |
| P6 Sensory (5-tier impact, rarity audio, chest seq, haptics) | ALREADY CODED in systems/juice.js this session | wire juice.js into chests |
| P7 Tripo prompt templates (generic [BREED]/[FACTION]) | We have REAL data: build_hero_prompts (106, A-pose), asset_prompts (291), weapon_prompts (88), rig bible (20 named car-DNA) | ours supersedes the templates |
| P8 UI/UX (garage states, chest sequence) | chest sequence matches juice.js; garage UI NEW | build garage UI |
| P9 Economy (Bones/Crowns/Gold/Scrap/CrewTokens/WeaponXP) | matches; Scrap Metal = the car-parts currency you wanted | wire the full loop |
| P10 6-sprint plan (12 weeks) | honest engineering timeline | see conflict 3 |
| P11 QA checklist | adopt as the definition of done | adopt |
| P12 decisions | see conflicts below | you decide |

## 2. What the doc ADDS that we must build

1. **Dual-view (RPG + FPS/TPS) + The Drop warp.** The single biggest new system. Every asset
   needs two meshes: a low-poly RPG version and a mid-poly combat version. This is what makes it
   "also an FPS."
2. **Weapon gunsmith.** 7 categories, 7 rarity tiers (to Ultra), 20 levels, held + mounted.
   BUILT the prompts: `art/weapon_prompts.json` (32 weapons x 2 views + 24 attachments = 88 meshes,
   1,760 credits, no brand names).
3. **Attachments** with stat trade-offs. Prompts built (24, in weapon_prompts.json).
4. **Rig component depth** (7-8 slots: engine/turbo/armor/mount/tires/transmission/exhaust/utility)
   and visual customization (paint/decals/wheels/body kits/exhaust/underglow/tint). Deeper than our
   3-slot mod plan.
5. **The SIM loop wiring** (your voice note, not in the doc but the real ask): needs.js exists
   (hunger/hygiene/happiness) but is NOT wired into the economy self-loop
   (happiness low -> raid -> win -> hungry -> garden -> eat -> replant -> seeds -> shop -> gold ->
   trade -> upgrade cards -> raid again). This is the "full circle" that makes it feel alive.

## 3. Conflicts that need YOUR call

**CONFLICT 1 -- scope.** The doc is a 12-week, 6-sprint build (dual-view FPS engine, gunsmith,
netcode). You said "one awesome update." Honest truth: the ART can drop in one credit blitz once
you subscribe. The dual-view FPS + weapon-code + SIM-wiring is real engineering, not one button.
Recommend: ship it in WAVES (art + sensory first, then weapons, then dual-view) so each wave is a
real update, not a 3-month silence.

**CONFLICT 2 -- dog model budget.** The doc bills all 106 dogs at H3.1 55cr = 5,830 (because the
FPS view needs detailed dogs). My tiered plan billed 2,610 (heroes premium, rest standard). If the
FPS view is real, the doc is right and dogs cost more. That swings the budget by ~3,200 credits.
Your Max plan (25,000) absorbs it either way. Decide: all-premium dogs, or tier them.

**CONFLICT 3 -- crew/district math.** The doc's Decision 1 recommends Option B. YOU already told me
Option A. Your live call wins: Option A (rebalance to ~13 per district, all 4 roles each). Already
planned in `art/plan_district_rebalance.py`. Flagging only because the doc disagrees.

## 4. Fire order (blocked until the session limit resets at 2pm PT)

The rig-bible workflow died on the usage limit. Heavy generation is blocked until 2pm Pacific.
Everything below the line is staged and ready; nothing waits on more design.

STAGED AND DONE (this session, direct):
- `art/build_hero_prompts.py` -> prompts.json (106 dogs, A-pose locked)
- `art/build_asset_prompts.py` -> asset_prompts.json (291: rigs, accessories, chests, crowns, bosses, props)
- `art/build_weapon_prompts.py` -> weapon_prompts.json (88: weapons + attachments)
- `art/build_pack_bonds.py` -> pack_bonds.json (Layer 1 dog-dog bonds, from the saga)
- `game/systems/juice.js` -> sensory package (P6) CODED, needs wiring into cdOpen
- `unity_migration/tripo_batch.py` -> resume-safe, cap-guarded batch runner

FIRES AT 2pm PT:
1. Resume the rig bible v3 (car-DNA, 20 rigs) -- cached where possible.
2. Extend SYNERGY_SPEC to 4 layers (add Weapon).
3. On your Tripo Max key: tripo_batch fires 106 dogs, then the 291 assets, then the 88 weapons.

NEEDS YOU:
- Subscribe Tripo Max (screenshot checkout: real price is $89.90/mo; $44-53 is the $647 annual).
- Answer conflicts 1 and 2.
