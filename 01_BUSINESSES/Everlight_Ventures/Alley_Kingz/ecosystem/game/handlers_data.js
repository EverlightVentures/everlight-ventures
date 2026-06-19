/* ==========================================================================
 * handlers_data.js -- Alley Kingz HANDLER roster (data layer, no logic).
 *
 * Six Handlers. Each one carries: a SPECIAL (the tap-fired ability that spends
 * a charge off the radial meter), a PASSIVE (always-on aura), and a Bones
 * SKILL TREE (nodes the player unlocks by spending Bones; each node carries a
 * machine-readable `mods` patch the engine folds onto the base special).
 *
 * This file is pure DATA -- vanilla JS, no imports, browser + node-harness safe.
 * The engine reads it through window.AK_HANDLERS / window.AK_HANDLERS_BY_ID.
 * The integration contract (which engine primitive each special calls, how the
 * meter fills, how mods resolve) is in ../HANDLER_BUILD_PLAN.md.
 *
 * SCHEMA per handler:
 *   id, name, breed, portrait (emoji glyph fallback), art (asset path), accent
 *   special: { name, desc, primitive, recharge_sec, charges, ...resolved params }
 *   passive: { id, name, desc, ...resolved params }
 *   skill_tree: [ { id, name, effect, bones, requires?, mods:{...} } ]
 *
 * RESOLVED PARAMS are engine units (tiles, seconds, fractions-of-maxHp), NOT
 * prose -- fireSpecial() reads them directly. The text designs are preserved
 * verbatim in `desc`/`effect` for the UI tooltip.
 *
 * RESOURCE NOTE (The Dealer): the in-match economy currency is ENERGY (0..10,
 * AK.ENERGY_MAX), there is no separate "Gold" pool mid-match. The design's
 * "Gold" values are carried as `goldRaw` and converted at fire time via
 * GOLD_TO_ENERGY (1/3), clamped to ENERGY_MAX. See the plan, section 6.
 * ======================================================================== */
(function (root) {
  'use strict';

  // Gold (design unit) -> in-match ENERGY (engine unit). +18 gold => +6 energy,
  // +40 => +13 (clamps to the 10 cap = a full bar), -12 => -4 energy.
  var GOLD_TO_ENERGY = 1 / 3;

  var HANDLERS = [

    /* ====================================================================
     * 1. THE MENDER -- St. Bernard / Medic. spawn-structure healer.
     * ==================================================================== */
    {
      id: 'handler_mender',
      name: 'The Mender',
      breed: 'St. Bernard / Medic',
      portrait: '⛑',                 // rescue helmet glyph fallback
      art: 'assets/handlers/handler_mender.jpg',
      accent: '#7FE3A0',
      special: {
        name: 'Field Kennel',
        desc: 'Deploy a healing totem (3.5 tile radius) that heals friendly units at 8% maxHp/sec and persists for 35 seconds. Tap to place the totem anywhere on your side of the arena.',
        primitive: 'spawn-structure',     // fireSpecial -> new Unit(totemCard) + registerHandlerZone(heal)
        kind: 'heal-totem',
        recharge_sec: 25,
        charges: 1,
        // resolved engine params:
        radius: 3.5,                      // heal-zone radius (tiles)
        healPct: 0.08,                    // maxHp/sec healed inside the zone
        lifeT: 35,                        // totem lifetime (sec) -> Unit.lifeT
        totemHp: 250,                     // totem structure maxHp
        totemDR: 0.20,                    // totem self damage-reduction (20%)
        ownSideOnly: true,                // placement gate (player half + bridges)
        // optional layers turned on by skill nodes (off by default):
        armorAura: null,                  // { radius, drPct } -> Resilient Shelter
        revive: null                      // { chance, hpPct } -> Revive Protocol
      },
      passive: {
        id: 'pack_scent',
        name: 'Pack Scent',
        desc: 'All friendly units regenerate 2% of their maxHp per second (passive regen aura, always active, stacks with other healing).',
        regenPct: 0.02                    // per-sec maxHp regen on every friendly unit
      },
      skill_tree: [
        { id: 'mender_kennel', name: 'Field Kennel', bones: 0,
          effect: 'Base special: Deploy a healing totem with 3.5 tile radius, 8% maxHp/sec heal rate, 35sec lifetime.',
          mods: {} },
        { id: 'mender_aura_expand', name: 'Expanded Aura', bones: 15,
          effect: 'Increase Field Kennel radius from 3.5 to 4.0 tiles (+0.5 range, covers more of the arena).',
          mods: { radius: 4.0 } },
        { id: 'mender_healing_boost', name: 'Enhanced Healing', bones: 18,
          effect: 'Increase heal rate from 8% to 11% maxHp/sec (+3% healing output per tick).',
          mods: { healPct: 0.11 } },
        { id: 'mender_recharge_speed', name: 'Quick Recharge', bones: 20,
          effect: 'Reduce special recharge time from 25 seconds to 17 seconds (-8 sec cooldown, fire more often).',
          mods: { recharge_sec: 17 } },
        { id: 'mender_resilience', name: 'Resilient Shelter', bones: 25,
          effect: 'Totem radiates a 2.5 tile armor aura: allied units within range gain 8% damage reduction. Stacks with other defenses.',
          mods: { armorAura: { radius: 2.5, drPct: 0.08 } } },
        { id: 'mender_revive', name: 'Revive Protocol', bones: 30,
          effect: 'When an allied unit dies within Field Kennel radius, 30% chance to revive it at 40% HP (once per totem deployment; revived unit resets with fresh buffs).',
          mods: { revive: { chance: 0.30, hpPct: 0.40, oncePerTotem: true } } }
      ]
    },

    /* ====================================================================
     * 2. THE TRACKER -- Bloodhound. apply-buff-flag (reveal + mark).
     * ==================================================================== */
    {
      id: 'tracker',
      name: 'The Tracker',
      breed: 'Bloodhound',
      portrait: '🐕',           // dog glyph fallback
      art: 'assets/handlers/tracker.jpg',
      accent: '#E2B23A',
      special: {
        name: 'Scent Probe',
        desc: 'Reveal enemy units in a 6-tile radius around target location. Marked units take +25% damage for 8 seconds. Can bank 2 charges.',
        primitive: 'apply-buff-flag',     // fireSpecial -> stamp markT/markMul on enemies in radius
        kind: 'mark',
        recharge_sec: 25,
        charges: 2,
        // resolved engine params:
        radius: 6.0,                      // reveal + mark radius (tiles)
        markDur: 8,                       // mark lifetime (sec) on each hit enemy
        markMul: 1.25,                    // damage-TAKEN multiplier while marked
        reveal: true,                     // un-hide stealthed enemies in radius
        // optional layers from nodes:
        noStealthForMarked: false,        // Tag capstone
        accuracyVsMarked: 0              // Tag capstone (+15% accuracy flavor)
      },
      passive: {
        id: 'keen_senses',
        name: 'Keen Senses',
        desc: 'You gain +0.5sec vision preview on all enemy unit deploys (shows cards 0.5sec before they spawn). Minion kills extend the next special\'s meter by 0.75sec (rewards aggressive scouting).',
        visionPreviewSec: 0.5,
        killMeterBonusSec: 0.75           // each player minion kill adds 0.75s to game.special.meter
      },
      skill_tree: [
        { id: 'scent_probe_unlock', name: 'Scent Probe', bones: 0,
          effect: 'Base handler special: Activate at target location to reveal + mark enemies (25% more damage taken)',
          mods: {} },
        { id: 'bloodhound_nose', name: "Bloodhound's Nose", bones: 20,
          effect: 'Mark duration +2 seconds (8s -> 10s total). Enemies stay vulnerable longer.',
          mods: { markDur: 10 } },
        { id: 'trail_blazer', name: 'Trail Blazer', bones: 25,
          effect: 'Scent Probe recharge -5 seconds (25s -> 20s). Fire more often.',
          mods: { recharge_sec: 20 } },
        { id: 'pack_tactics', name: 'Pack Tactics', bones: 30,
          effect: 'Marked enemies take +10% additional damage from ALL friendly units (not just future attacks). Stacks additively with mark.',
          mods: { markMul: 1.35 } },       // 1.25 + 0.10 additive
        { id: 'tag_capstone', name: 'Tag', bones: 40,
          effect: 'CAPSTONE: Marked enemies cannot use stealth/invisibility abilities. Also grants your units +15% accuracy vs marked targets (flavor: impossible to hide from the pack).',
          mods: { noStealthForMarked: true, accuracyVsMarked: 0.15 } }
      ]
    },

    /* ====================================================================
     * 3. THE SHADOW -- Basenji. apply-buff-flag (speed + stealth on an ally).
     * ==================================================================== */
    {
      id: 'handler_shadow',
      name: 'The Shadow',
      breed: 'Basenji',
      portrait: '🌑',           // new-moon glyph fallback
      art: 'assets/handlers/handler_shadow.jpg',
      accent: '#9B8CFF',
      special: {
        name: 'Slipstream',
        desc: 'Target friendly unit gains 25% move speed and becomes untargetable (stealth) for 1.5s',
        primitive: 'apply-buff-flag',     // fireSpecial -> buff nearest friendly to tap
        kind: 'slipstream',
        recharge_sec: 18,
        charges: 2,
        // resolved engine params:
        targetSide: 'friendly',
        pickRadius: 5.0,                  // grab the friendly nearest the tap within this
        speedMul: 1.25,                   // move-speed buff
        stealthDur: 1.5,                  // untargetable + invuln window (sec)
        critNext: 0                       // Assassin's Edge crit on stealth-exit hit (0 = off)
      },
      passive: {
        id: 'swift_paw',
        name: 'Swift Paw',
        desc: 'All friendly units move 8% faster',
        allMoveMul: 1.08
      },
      skill_tree: [
        { id: 't1_slipstream', name: 'Slipstream', bones: 0,
          effect: 'Base special (target unit: +25% speed, 1.5s stealth)',
          mods: {} },
        { id: 't2a_shadow_runner', name: 'Shadow Runner', bones: 7,
          effect: 'Passive move speed +10% (18.8% total with Swift Paw)',
          mods: { passiveMove: 1.188 } }, // 1.08 * 1.10
        { id: 't2b_quick_escape', name: 'Quick Escape', bones: 9,
          effect: 'Stealth duration +0.5s, recharge -2s (16s cycle)',
          mods: { stealthDur: 2.0, recharge_sec: 16 } },
        { id: 't3_assassins_edge', name: "Assassin's Edge", bones: 13,
          effect: 'Stealth-exit: next attack deals +50% crit damage (one hit)',
          mods: { critNext: 1.5 } }
      ]
    },

    /* ====================================================================
     * 4. THE RIGGER -- Doberman / Engineer. deploy-a-unit (pick-a-turret).
     * ==================================================================== */
    {
      id: 'the-rigger',
      name: 'The Rigger',
      breed: 'Doberman, Engineer',
      portrait: '🔧',           // wrench glyph fallback
      art: 'assets/handlers/the-rigger.jpg',
      accent: '#D45A2C',
      special: {
        name: 'Drop Rig',
        desc: 'Deploy one of three turret rigs: Gun Nest (ranged damage), Tesla Coil (chain shock), or Flak Turret (anti-air splash). Player selects turret type at tap. Turret deploys to cursor location with 30-second lifespan.',
        primitive: 'deploy-a-unit',       // fireSpecial -> new Unit(rigCards[choice]) structure
        kind: 'drop-rig',
        recharge_sec: 16,
        charges: 2,
        ownSideOnly: true,
        rigChoices: ['gun_nest', 'tesla_coil', 'flak'],   // tap opens a 3-way picker
        // per-rig stat tables. lifeT 30 here; passive structure_durability x1.40
        // is applied at deploy (=> 42s) so it matches the design note.
        rigCards: {
          gun_nest:   { name: 'Gun Nest',   hp: 1050, dmg: 95, range: 5.0, atkSpd: 1.0,  lifeT: 30, domain: 'both', weaponType: 'bullet' },
          tesla_coil: { name: 'Tesla Coil', hp: 950,  dmg: 80, range: 4.5, atkSpd: 0.85, lifeT: 30, domain: 'both', weaponType: 'beam', chain: 3 },
          flak:       { name: 'Flak Turret',hp: 900,  dmg: 70, range: 4.0, atkSpd: 1.1,  lifeT: 30, domain: 'air',  weaponType: 'cannon', splash: 1.8 },
          // unlocked only by the Forge Protocol capstone:
          suppressor: { name: 'Suppressor', hp: 900,  dmg: 60, range: 3.0, atkSpd: 1.0,  lifeT: 30, domain: 'both', weaponType: 'beam', slowAura: { radius: 2.4, slowPct: 0.25 } }
        },
        // node-driven multipliers folded onto rigCards at deploy time:
        rigHpMul: 1.0,
        rigDmgMul: 1.0,
        rigLifeMul: 1.0
      },
      passive: {
        id: 'structure_durability',
        name: 'Structure Durability',
        desc: 'Structures deployed by The Rigger or summoned via cards last 40% longer (nests: 42s instead of 30s; turrets: 56s instead of 40s). Reuses the existing lifeT field in the Unit struct -- multiply by 1.40 at deploy time when the structure owner is the player.',
        structLifeMul: 1.40               // applied to player structure lifeT at deploy
      },
      skill_tree: [
        { id: 'rig_foundation', name: 'Rig Foundation (T1)', bones: 0,
          effect: 'Unlock Drop Rig special. Gain 1 charge slot for recharge cycling.',
          mods: {} },
        { id: 'rapid_deploy', name: 'Rapid Reload (T2a)', bones: 20,
          effect: '-20% special recharge time (16s -> 12.8s). Turrets become available faster mid-battle.',
          mods: { recharge_sec: 12.8 } },
        { id: 'reinforced_rigs', name: 'Reinforced Plating (T2b)', bones: 22,
          effect: '+30% deployed turret max HP. Gun Nest: 1050 -> 1365 | Tesla Coil: 950 -> 1235 | Flak: 900 -> 1170. Reuses maxHp scaling at deploy time.',
          mods: { rigHpMul: 1.30 } },
        { id: 'heavy_ordinance', name: 'Heavy Ordinance (T2c)', bones: 18,
          effect: '+15% turret damage. Gun Nest: 95 -> 109 | Tesla Coil: 80 -> 92 | Flak: 70 -> 80.5. Scales the .dmg field at deploy time.',
          mods: { rigDmgMul: 1.15 } },
        { id: 'third_rig_choice', name: 'Forge Protocol (T3 Capstone)', bones: 35,
          effect: 'Unlock a 4th rig option: Suppressor (utility, 60 dmg, range 3, 30s duration, applies -25% enemy move speed in 2.4 tile aura). Turrets gain +20% lifespan. Gain +1 max charge (2 -> 3). Engineer\'s ultimate loadout flexibility.',
          mods: { addRigChoice: 'suppressor', rigLifeMul: 1.20, addCharge: 1 } }
      ]
    },

    /* ====================================================================
     * 5. THE BRUISER -- Pit Bull / Mastiff. apply-buff-flag (AoE rally).
     * ==================================================================== */
    {
      id: 'bruiser_handler',
      name: 'The Bruiser',
      breed: 'Pit Bull / Mastiff -- tank archetype',
      portrait: '💪',           // flexed-biceps glyph fallback
      art: 'assets/handlers/bruiser_handler.jpg',
      accent: '#C0392B',
      special: {
        name: 'War Cry',
        desc: 'Nearby friendly units gain +20% damage and +18% max-HP shield (rally). AoE persists 3.5s.',
        primitive: 'apply-buff-flag',     // fireSpecial -> dmgBuffT + shieldHp on allies in radius
        kind: 'war-cry',
        recharge_sec: 12,
        charges: 1,
        // resolved engine params (centered on the handler / tap point):
        radius: 3.5,
        dmgBuffDur: 3.5,                  // -> ally.dmgBuffT
        dmgBuffMul: 1.20,                 // doAttack reads this while dmgBuffT > 0
        shieldPct: 0.18,                  // -> ally.shieldHp = maxHp * shieldPct
        blockedHitDR: 0,                  // Last Stand layer (0 = off)
        blockedHitDur: 0
      },
      passive: {
        id: 'squad_toughness',
        name: 'Squad Toughness',
        desc: 'Units under your command take 8% less damage (squad toughness) + gain +15% shield from Bone Wall synergy (Boneguard faction bonus stacks with War Cry shields).',
        allyDamageTakenMul: 0.92,         // 8% less damage taken on every friendly
        boneWallShieldAdd: 0.15           // +15% synergy-shield cap for Boneguard crew
      },
      skill_tree: [
        { id: 'wc_radius_up', name: 'Wider Call', bones: 8,
          effect: '+0.8 tiles to War Cry radius (3.5 -> 4.3). Friendlies further back catch the rally.',
          mods: { radius: 4.3 } },
        { id: 'wc_shield_up', name: 'Iron Hide', bones: 10,
          effect: '+4% shield from War Cry (18% -> 22% maxHp). Stacks with passive + synergy.',
          mods: { shieldPct: 0.22 } },
        { id: 'wc_recharge_down', name: 'Rally Again', bones: 12,
          effect: '-2 sec War Cry recharge (12s -> 10s). Meter fills faster mid-battle.',
          mods: { recharge_sec: 10 } },
        { id: 'wc_charge_add', name: 'Double Rally', bones: 14, requires: 'wc_recharge_down',
          effect: '+1 charge to War Cry (bank 2 uses back-to-back). T2a prerequisite: Rally Again.',
          mods: { addCharge: 1 } },
        { id: 'wc_damage_buff_up', name: 'Apex Roar', bones: 12,
          effect: '+5% damage buff from War Cry (20% -> 25%). Allied attackers hit harder.',
          mods: { dmgBuffMul: 1.25 } },
        { id: 'last_stand_shield', name: 'Last Stand', bones: 20, requires: 'wc_recharge_down,wc_shield_up',
          effect: 'War Cry shield also grants brief +12% damage reduction to blocked hits for 2s. T3 capstone: Rally Again + Iron Hide paths converge.',
          mods: { blockedHitDR: 0.12, blockedHitDur: 2 } }
      ]
    },

    /* ====================================================================
     * 6. THE DEALER -- Coin Dog (Card #0001, $BCARDD mascot). mixed primitive.
     * ==================================================================== */
    {
      id: 'the-dealer',
      name: 'The Dealer',
      breed: 'Coin Dog (Card #0001, $BCARDD mascot)',
      portrait: '🎰',           // slot-machine glyph fallback
      art: 'assets/handlers/the-dealer.jpg',
      accent: '#D4AF37',
      special: {
        name: 'House Edge',
        desc: 'Flip a $BCARDD card for a random big effect: gain 18 Gold (30%), spawn 2 cheap pups (25%), activate a 6-sec healing zone (25%), or gamble 12 Gold for 50/50 +40 Gold (20%). House Edge favors luck.',
        primitive: 'mixed',               // deploy-unit + spawn-zone-heal + apply-buff-flag + adjust-resource
        kind: 'house-edge',
        recharge_sec: 25,
        charges: 2,
        goldToEnergy: GOLD_TO_ENERGY,     // converts design "Gold" -> in-match ENERGY
        // weighted outcome table. fireSpecial rolls weights (after node deltas),
        // then runs the matching engine effect. Weights need not sum to 1 -- the
        // resolver normalizes.
        outcomes: {
          coin_rain:        { weight: 0.30, goldRaw: 18,  fx: 'coin' },          // adjust-resource (+energy)
          pup_swarm:        { weight: 0.25, spawnPups: 2, pupCostMax: 3 },        // deploy-unit x2 (cheap cards)
          blessing_aura:    { weight: 0.25, zone: { radius: 2.5, healPct: 0.03, shieldPct: 0.12, lifeT: 6 } }, // spawn-zone-heal
          double_or_nothing:{ weight: 0.20, gambleRaw: 12, winRaw: 40, winChance: 0.50 } // adjust-resource gamble
          // house_stake added by the House of Cards node (see mods.addOutcome)
        },
        goldGainMul: 1.0                  // permanent gold-gain mult (set by $BCARDD Blessing)
      },
      passive: {
        id: 'small_blessing',
        name: 'Small Blessing',
        desc: 'Gain +0.5% bonus Gold per 30 seconds of match elapsed. Stacks multiplicatively on top of all other Gold sources (loot, economy, perks). Flavor: the luck dog brings fortune to every card deploy.',
        goldBonusPctPer30s: 0.005         // compounding gold/energy bonus each 30s elapsed
      },
      skill_tree: [
        { id: 'house-edge-t1', name: 'House Edge', bones: 0,
          effect: 'Base special unlocked. Tap to fire a random outcome (Coin Rain, Pup Swarm, Blessing Aura, or Double or Nothing). Recharges over 25s, banks up to 2 charges.',
          mods: {} },
        { id: 'flush-luck-t2a', name: 'Flush Luck', bones: 50,
          effect: 'Better odds: Increase premium outcomes (Pup Swarm, Blessing Aura) by +15% weight each, reduce bad-RNG (Double or Nothing) by -10%. Coin Rain stays 30%. Flavor: the deck is stacked in your favor.',
          mods: { weightDelta: { pup_swarm: 0.15, blessing_aura: 0.15, double_or_nothing: -0.10 } } },
        { id: 'quick-turn-t2b', name: 'Quick Turn', bones: 60,
          effect: 'Faster reload: -50% base recharge time (12.5s instead of 25s). +1 additional charge bank (3 total instead of 2). Flavor: the house never stops dealing.',
          mods: { recharge_sec: 12.5, addCharge: 1 } },
        { id: 'house-of-cards-t3a', name: 'House of Cards', bones: 100, requires: 'flush-luck-t2a',
          effect: "Unlock a 5th guaranteed outcome: 'House Stake' (spawn 1 free Support unit + gain 8 Gold). Only unlocks from Flush Luck path. Rebalances outcomes to include House Stake at 20%, slightly reduces others. Flavor: you control the game.",
          mods: { addOutcome: { house_stake: { weight: 0.20, spawnSupport: 1, goldRaw: 8 } } } },
        { id: 'bcardd-blessing-t3b', name: '$BCARDD Blessing', bones: 150, requires: 'quick-turn-t2b',
          effect: 'Ultimate capstone: Coin Explosion -- slam 300 AOE damage in 2-tile radius + permanent +20% Gold gain for rest of match + 2s screen shake + blinding coin-burst VFX. Recharge 60s (premium ultimate). Unlocks from Quick Turn path. Flavor: the ultimate gamble pays off.',
          mods: { ultimate: { aoeDmg: 300, aoeRadius: 2, goldGainMul: 1.20, shakeDur: 2 }, recharge_sec: 60 } }
      ]
    }

  ];

  // id -> handler convenience map (the engine resolver + HUD read this).
  var BY_ID = {};
  for (var i = 0; i < HANDLERS.length; i++) BY_ID[HANDLERS[i].id] = HANDLERS[i];

  root.AK_HANDLERS = HANDLERS;
  root.AK_HANDLERS_BY_ID = BY_ID;
  root.AK_HANDLERS_GOLD_TO_ENERGY = GOLD_TO_ENERGY;

})(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this));
