# ALLEY KINGZ -- RAID / DEFENSE / PRODUCTION SYSTEM (canon; 2026-06-19)
> Ingested from the operator's base-defense handoff JSON (alley_kings_base_defense_system). Tailored, NOT generic: crew (never clan), urban street culture, $BCARDD dogs. Companion to AK_WORLD_BIBLE.md + AK_MASTER_BLUEPRINT.md + the module plan in ALLEY_KINGZ_TODO.md.
> One-line thesis: "Your crew has your back. Your skill protects you. Your base works while you sleep." Damage is SURGICAL (only the buildings hit go down), production fuels combat power, shields are economic choices, and you can always rebuild.

## WHY THIS MATTERS (the operator's intricacy, fully specified)
This is the detailed spec for the dynamic the operator called out: a player can have a MAXED Town Hall (high HQ stats) but a LOW Spell Shop (weak card stats) -- every building has its OWN independent level, and a raid only knocks down the SPECIFIC buildings the attacker targets, which you then repair/upgrade individually. The hub `Lv` badges (shipped 2026-06-19) are the visible front end of this. The Clash shell (offline raids, stat loss) + the Dark-War/Whiteout twist (crew reinforcement, per-building levels, repair loops, Main Tower caps the rest).

## THE 6 INTERCONNECTED SUBSYSTEMS
1. CREW REINFORCEMENT DEFENSE -- your crew defends you while offline (NOT automatic; requires coordination).
   - Active (defender online, their deck, 100% skill; high reward, but if they lose THEIR buildings take 10% of your damage).
   - Passive (defender offline, their Lieutenant AI, 50% power; low risk / low reward).
   - Squad (whole 2-5 squad defends with shared deck pool; massive, once per 24h). Social: Defense Log (who defended / who didn't), Iron Wall Streak (7 days no raids = crew buff), Guardian Angel (weekly defense MVP).
2. TARGETED BUILDING DAMAGE -- raids hit SPECIFIC buildings, not the whole base.
   - Raider picks 3 Primary (full dmg) + 2 Secondary (50%). Main Tower needs a rare "Siege Permit" to be primary.
   - 1000 HP / level; dmg = level reduction; never below L1. Above-tier overflow = efficiency loss (10% per virtual level, recovers 5%/hr).
   - Visual damage states: 1-3 lvls = cracks; 4-7 = smoke/sparks; 8+ = structural fire.
3. PRODUCTION BUILDINGS (Bitcoin-Miner DNA -- "works while you sleep"): Gem Mine (gems, HIGH value), Gold Mint (gold, MED), Card Forge (card fragments, VERY HIGH), Research Lab (skill points, HIGH), Electric Generator (power for ALL buildings, CRITICAL -- no power = cascade failure). Max L100 (Generator L50). Rates scale by level; storage caps (production stops if uncollected); Lieutenant auto-collect (10% fee); crew-collect-within-1hr = +10% all.
4. SHIELD & SHOP ECONOMY -- protection is a CHOICE, 5 tiers: Street (2h/25%/1k gold/no cd), Crew (8h/50%/5k gold OR 50 gem/4h cd), Iron Curtain (24h/75%/200 gem OR 15k gold/12h cd), Fortress Dome (72h/100%/500 gem/7d cd), Panic Button (1h/100% mid-raid/50 gem/24h cd). CRYPTO GATE 2026-06-19 (the load-bearing fix 2 verifiers caught): shields are SOFT-currency / fiat-IAP ONLY -- NO ALK/$BCARDD pricing. A loot-protection shield is UTILITY, and utility-for-token is the securities/pay-to-win line; the old "5/20/100 ALK" tiers + the ALK-cosmetic-bypass Crew shield are DELETED. Attack-while-shielded = -25% shield/attack (4 attacks = gone). VIP Pass + Crew Premium + bundles. Currencies: Gold (F2P) / Gems (earnable or real-money IAP, time+cosmetic only); $BCARDD/ALK = COSMETIC + identity lane ONLY, never a shield/utility/power currency. PARITY INVARIANT: gems may only skip a TIMER, never raise a rate/cap/ceiling.
5. SKILL-BASED PROTECTION MATRIX -- your skill protects you. Defense skill tree (4 branches via Research Lab): Fortification, Intelligence, Crew Defense, Economic Defense. Card-level defense (+0.1%/lvl, rarity x1-3, full-role-set +25%). Player-skill defense (tower rank intimidation, win-streak buff, defense reputation = raiders get less loot off you).
6. POST-RAID RECOVERY -- instant repair (gold+gem+ALK by level), crew aid (donors get rep + tax credit), natural regen (1 lvl / 4-12h free), auto 1h emergency shield (anti chain-raid), revenge raid (24h, +25% loot, crew revenge +50% + attacker can't shield 6h). Insurance: production shield (damaged still makes 25-75%), fragment insurance (25% returned over 7d), SP refund (50% of paused research).

## THE SKILL LOOP (the critical connection)
Card Forge -> fragments -> Deck Lab upgrades cards -> deck power -> tower rank -> rank drives matchmaking AND base-defense intimidation. Raid someone's Card Forge -> fewer fragments -> deck stagnates -> rank drops -> easier target -> more raids (vicious cycle) -- OR repair/rebuild and climb back. Protect your production = protect your combat power.

## MODULE TIE-INS (folds into the existing plan, no new silo)
- M02 BUILDING: production buildings + independent per-building levels + HP/level + visual damage states. (Lv badges already live on the hub.)
- M03 PVP_RAID: targeted primary/secondary damage, shield system, crew reinforcement defense, revenge.
- M06 ECONOMY: 5 shield tiers, 4 currencies, VIP/Crew-Premium, bundles, ALK burn on instant-repair.
- M07 PROGRESSION: defense skill tree (4 branches), card-level defense bonus.
- M04 CREW: reinforcement coordination, Lieutenants (auto-defend/collect), crew aid, Defense Log.
- M11 WHITEOUT: Main Tower caps buildings; reputation; crew streaks.

## ART NEEDS (operator: "create graphics as needed, keep it Alley Kingz themed") -> queue to art factory
Production buildings (each with visual progression tiers): Gem Mine, Gold Mint, Card Forge (L1-25 press -> L26-50 3D printer -> L51-75 holo-weaver -> L76-100 cosmic synthesizer), Research Lab, Electric Generator. Building DAMAGE-STATE overlays (cracks / smoke+sparks / structural fire). 5 SHIELD FX (Street/Crew/Iron-Curtain/Fortress-Dome/Panic) + shield-cracking FX. Defense skill-tree icons (4 branches). Lieutenant portraits (Enforcer/Dealer/Scout x Common->Legendary). All in the gritty cyberpunk dog-gang house style; route Leonardo bulk, Seedance for hero pieces.

## SOURCE
Operator handoff JSON: alley_kings_base_defense_system (downloaded 2026-06-19). This .md is the working canon; the JSON is the source of truth if a conflict arises.
