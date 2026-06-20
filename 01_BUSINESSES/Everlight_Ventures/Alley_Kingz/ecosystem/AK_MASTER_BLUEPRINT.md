# ALLEY KINGZ -- MASTER DEVELOPMENT BLUEPRINT (design reference; 2026-06-19)
> Companion to ALLEY_KINGZ_TODO.md (status) + AGENT_MAILBOX.md (handoff). This is the WHAT/WHY; the TODO is the WHEN.
> Vision: a socially radioactive cross-platform PvP strategy game. Core = the tower battler. Walk OUT of it into a Sunflower-Land/Pokemon overworld with world chat, raids, crews, and real economic stakes. Friends beg each other to log in and hate each other for betraying the crew.

## CORE LOOP
WebGL/Three.js (now: 2.5D canvas hub) overworld map -> walk to a building -> enter a game mode. Core mode = tower battler. Buildings (Spell Shop, Deck Lab, Main Tower, etc.) have HP/stats and are RAIDABLE while offline (Clash-of-Clans DNA): no shield + attacked = lose building stats (e.g. 100% -> 90%).

## 27 GAMES RESEARCHED (steal the best dynamic from each)
Clash of Clans (clan wars + shield economy = infinite retention) | Clash Royale (3-5min deck battles) | Whiteout Survival (furnace = life-or-death central object + alliance help + SvS cross-server war) | Dark War Survival (alliance reinforcements + revenge chains) | Sunflower Land (browser overworld, seasonal events, prestige, tokenized assets) | Pixels (social hub, VIP gating, land NFTs, task board, staking, fee sinks) | Monopoly GO (Reward Flow: every reward triggers the next; 1-2 day events) | Coin Master (slot+raid, loss aversion, social pyramid) | Roblox + Fortnite Creative (creator economy, 70/25/5 split, regional pricing) | EVE Online (player economy, anti-whale lesson) | Genshin (gacha scarcity FOMO) | Axie (P2E collapse lesson = need sinks) | + Lords Mobile, Rise of Kingdoms, Last War, Honor of Kings, Brawl Stars, Pokemon GO, Splinterlands, Gods Unchained, Immutable X, Ronin, The Sandbox.

## "COME ON BUDDY" SOCIAL ENGINE (3 tiers)
- TIER 1 urgency notifications: "BUDDY'S BASE IS BURNING" (raid push to all crew), war countdown escalation (1h->30m->10m->2m->NOW), crew streak crisis ("4/5 online, MISSING: YOU"), revenge window (24h), emergency shield donation (reciprocity).
- TIER 2 crew chat as weapon: Betrayal Log (who reinforced/abandoned), MVP shaming/praising, crew chest timer, flash-bonus whisper, rival-crew base tagging.
- TIER 3 shared reward anxiety: Crew Chest (timed open, miss it = miss out), Rescue Mission (crew raids in an AFK member's name), Betrayal Bounty (leave during war = "Traitor" mark, open season 48h).

## DOPAMINE ENGINE (Coin Master / Monopoly GO Reward Flow)
spin/action -> building upgrade (visual progress) -> raid opportunity (variable reward, random 1-4h) -> win/lose (near-miss: raid hits 2/3 buildings) -> social share (brag/beg) -> crew reaction (validation/shame) -> loop. Loss aversion: "Spell Shop decays to 80% in 2h unless you log in."

## TOKEN ECONOMY (ALK) -- deflationary, 7 burn sinks
Inflows: daily login, raid loot, task board, crew chest, staking, event prizes. SINKS/BURNS: prestige reset (500), war declaration (200/member), emergency shield (100), building relocation (150), cosmetic reroll (50), marketplace fee (5% = 2.5% burn + 2.5% to stakers), creator mint (25). Staking: 30-day lock, share of marketplace+war fees. Targets: inflation <2%/mo, 40% staked. Monetization layers: IAP (40-50%), rewarded ads (15-20%), subscriptions/VIP/pass (20-25%), web shop D2C (10-15%), NFT marketplace (5-10%), staking (2-5).

## WHITEOUT SURVIVAL INTEGRATION (the urgency backbone, MODULE_11)
- Main Tower = furnace = Crew HQ: caps all buildings AND crew size (L1=5, L10=20, L30=100 members). Social arms race.
- Reputation Flow = heat: Main Tower generates rep/hour; decays offline; raidable; below threshold = crew members earn less + can be poached + buildings -50% output.
- Crew Help Timer = alliance help: "Call Crew" button shaves every upgrade timer; active crew = faster = bigger.
- Crew War Lanes = alliance championship: 3 arenas (5 players each, 15v15), win 2/3, rank-based fight order, deck locks at registration, leader assigns players to arenas (strategy/blame/glory).
- District vs District (DvD) = SvS: monthly cross-district war. Hype Phase (5 daily tasks) -> Siege Phase (capture Central Tower, hold 2.5h, VIP buffs OFF) -> Rebuild Phase (24h repair window, miss = permanent loss). Winner = Supreme Crew title + district buffs 2 weeks. Real-time contribution leaderboard = public shame/glory.
- Card Gear = hero gear: 4 slots per card (Frame=atk+hp, Ability Gem=spell power, Aura=def+hp, Finisher=crit). Two systems: Tower Battles (gear L1-5) vs World Raids (gear L6+).
- Training Grounds = exploration: assign deck, auto-battle offline for XP+gear; 24h-offline "Boosted Claim"; crew members boost each other +10%/active.

## MODULAR ARCHITECTURE (11 modules; rule: no direct imports, all via EventBus pub/sub; adapter pattern => port by swapping adapters)
See ALLEY_KINGZ_TODO.md "11 MODULES". Communication example: RaidController emits CREW_UNDER_SIEGE -> CrewChat + PushNotificationManager listen. Swap WebGLRendererAdapter -> UnityRendererAdapter and game logic is untouched.

## 7 CLIENT DIRECTIVES
1 socially radioactive | 2 "come on buddy" urgency | 3 prime for Unity+crypto+GooglePlay | 4 no strays (modular/clean data) | 5 account for what I'm NOT saying (fill gaps) | 6 research what makes the best the best | 7 Whiteout Survival elements.

## SPAWN BUG (origin issue, MODULE_01) -- already solved in hub_proto
Player must NOT auto-enter a building on load. Spawn in a neutral plaza; free navigation; enter a building only on intentional move onto it (the v3 proto does this with the 1/8s dwell-to-enter, pending deploy).
