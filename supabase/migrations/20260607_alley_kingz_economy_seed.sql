-- ============================================================================
-- ALLEY KINGZ economy SEED -- GENERATED from cards.json by _build_economy_seed.py
-- Generated: 2026-06-07  | DO NOT hand-edit; regenerate.
-- Idempotent: INSERT ... ON CONFLICT DO UPDATE. Safe to re-run.
-- Economy numbers are a TUNABLE first draft (LiveOps owns final values).
-- ============================================================================

-- ---- ak_card_catalog : 48 cards + 5 spells ----
insert into public.ak_card_catalog
  (card_id, name, rarity, faction_id, is_spell, cost, role, domain, scrap_value, card_shop_price, description)
values
  ('0001','$BCARDD','Mythic','boneguard_crew',false,10,'Vanguard','ground',1000,10,'Mythic Vanguard of the Boneguard Crew. Crownbreaker: Shields self for 18% HP; can strike the Queen. Targets ground. Splash damage. Can strike the Queen.'),
  ('0002','Stonejaw','Legendary','boneguard_crew',false,7,'Vanguard','ground',250,5,'Legendary Vanguard of the Boneguard Crew. Armor Pulse: Aura cuts nearby ally damage taken by 15%. Targets ground.'),
  ('0003','Balboa','Epic','boneguard_crew',false,6,'Striker','ground',25,3,'Epic Striker of the Boneguard Crew. Haymaker: First hit stuns the target for 1s. Targets ground.'),
  ('0004','Iron Rottweiler','Epic','boneguard_crew',false,9,'Vanguard','ground',25,3,'Epic Vanguard of the Boneguard Crew. Overclock Rage: Below 40% HP its bite damage spikes. Targets ground.'),
  ('0005','Granite Saint','Rare','boneguard_crew',false,8,'Vanguard','ground',5,2,'Rare Vanguard of the Boneguard Crew. Bodywall: Bodywall aura soaks nearby damage for the pack. Targets ground.'),
  ('0006','Grit Bulldog','Rare','boneguard_crew',false,5,'Striker','ground',5,2,'Rare Striker of the Boneguard Crew. Brawler: Powers up its own bite the longer it brawls. Targets ground.'),
  ('0007','Alloy Akita','Rare','boneguard_crew',false,6,'Lancer','ground',5,2,'Rare Lancer of the Boneguard Crew. Shock Push: Knockback cone shoves a melee line back. Targets ground.'),
  ('0010','Tank Pug','Common','boneguard_crew',false,3,'Support','air',1,1,'Common Support of the Boneguard Crew. Shield Bark: Drops a small temporary shield on one ally. Targets air.'),
  ('0011','Copper Chow','Common','boneguard_crew',false,4,'Striker','ground',1,1,'Common Striker of the Boneguard Crew. Bitechain: Each consecutive hit ramps its damage. Targets ground.'),
  ('0008','Warden Newfie','Rare','boneguard_crew',false,7,'Support','ground',5,2,'Rare Support of the Boneguard Crew. Fortify: Raises max HP of allies in an aura. Targets ground.'),
  ('0009','Rust Cane Corso','Rare','boneguard_crew',false,8,'Vanguard','ground',5,2,'Rare Vanguard of the Boneguard Crew. Grav Pull: Pulses a shove that scatters the nearest foes. Targets ground.'),
  ('0012','Brick Bullmastiff','Common','boneguard_crew',false,6,'Vanguard','ground',1,1,'Common Vanguard of the Boneguard Crew. Stonehide: Short window of heavy damage resistance. Targets ground.'),
  ('0013','Jagged','Mythic','zoomie_syndicate',false,11,'Assassin','ground',1000,10,'Mythic Assassin of the Zoomie Syndicate. Shadow Fang: Teleports onto the Queen for a kill window. Targets ground. Can strike the Queen.'),
  ('0016','Pixel Greyhound','Rare','zoomie_syndicate',false,3,'Skirmisher','air',5,2,'Rare Skirmisher of the Zoomie Syndicate. Dash Loop: Refreshes its dash on a kill. Targets air.'),
  ('0017','Circuit Shiba','Rare','zoomie_syndicate',false,4,'Striker','ground',5,2,'Rare Striker of the Zoomie Syndicate. Blink Bite: Blinks a short hop on its first attack. Targets ground.'),
  ('0021','Neon Whippet','Common','zoomie_syndicate',false,2,'Skirmisher','air',1,1,'Common Skirmisher of the Zoomie Syndicate. Slipstream: Ignores slows and gains brief evasion. Targets air.'),
  ('0022','Turbo Jack','Common','zoomie_syndicate',false,3,'Striker','ground',1,1,'Common Striker of the Zoomie Syndicate. Burst Bite: Crits on the first strike after deploy. Targets ground.'),
  ('0014','Razor Vizsla','Epic','zoomie_syndicate',false,5,'Lancer','ground',25,3,'Epic Lancer of the Zoomie Syndicate. Pierce Rush: Lunges a line that pierces every foe hit. Targets ground.'),
  ('0018','Flash Saluki','Rare','zoomie_syndicate',false,4,'Skirmisher','air',5,2,'Rare Skirmisher of the Zoomie Syndicate. Sidecut: Dashes lane to lane to flank the backline. Targets air.'),
  ('0019','Bolt Corgi','Rare','zoomie_syndicate',false,4,'Spawner','air',5,2,'Rare Spawner of the Zoomie Syndicate. Spark Pups: Spawns three fast mini zoomers. Targets air. Splash damage.'),
  ('0020','Glitch Basenji','Rare','zoomie_syndicate',false,3,'Hacker','ground',5,2,'Rare Hacker of the Zoomie Syndicate. Signal Scramble: Silences a target ability briefly. Targets ground.'),
  ('0015','Aero Malinois','Epic','zoomie_syndicate',false,6,'Striker','ground',25,3,'Epic Striker of the Zoomie Syndicate. Twin Strike: Strikes twice in one attack swing. Targets ground.'),
  ('0023','Drift Sheltie','Common','zoomie_syndicate',false,2,'Support','air',1,1,'Common Support of the Zoomie Syndicate. Tag Boost: Boosts the move speed of nearby allies. Targets air.'),
  ('0024','Byte Beagle','Common','zoomie_syndicate',false,3,'Blaster','ground',1,1,'Common Blaster of the Zoomie Syndicate. Tracer Round: Long shots that pierce shields; can hit Queen. Targets ground. Can strike the Queen.'),
  ('0025','Rosco','Mythic','leashbreak_tactix',false,10,'Controller','ground',1000,10,'Mythic Controller of the Leashbreak Tactix. Leashbreak: Disables a tower fire; can strike the Queen. Targets ground. Can strike the Queen.'),
  ('0026','Synth Collie','Epic','leashbreak_tactix',false,5,'Hacker','ground',25,3,'Epic Hacker of the Leashbreak Tactix. Hack Jam: Jams a tower so it cannot fire. Targets ground.'),
  ('0029','Holo Husky','Rare','leashbreak_tactix',false,5,'Support','ground',5,2,'Rare Support of the Leashbreak Tactix. Heal Beacon: Pulsing area heal for the pack. Targets ground.'),
  ('0030','Chill Samoyed','Rare','leashbreak_tactix',false,4,'Support','ground',5,2,'Rare Support of the Leashbreak Tactix. Frost Bark: Wide frost cone slows everything caught. Targets ground.'),
  ('0031','Prism Poodle','Rare','leashbreak_tactix',false,4,'Controller','ground',5,2,'Rare Controller of the Leashbreak Tactix. Shatter: Strips enemy shields, then wards an ally. Targets ground.'),
  ('0034','Echo Dalmatian','Common','leashbreak_tactix',false,3,'Controller','ground',1,1,'Common Controller of the Leashbreak Tactix. Echo Howl: Rolling area slow down the lane. Targets ground.'),
  ('0035','Static Sheba Inu','Common','leashbreak_tactix',false,2,'Hacker','ground',1,1,'Common Hacker of the Leashbreak Tactix. Ping: Quick silence on the first target. Targets ground.'),
  ('0036','Vibe Shih Tzu','Common','leashbreak_tactix',false,2,'Support','ground',1,1,'Common Support of the Leashbreak Tactix. Soothe: Small steady heal to a wounded ally. Targets ground.'),
  ('0027','Noir Setter','Epic','leashbreak_tactix',false,6,'Controller','ground',25,3,'Epic Controller of the Leashbreak Tactix. Blackout: Blinds ranged foes so their shots miss. Targets ground.'),
  ('0032','Signal Pointer','Rare','leashbreak_tactix',false,4,'Lancer','ground',5,2,'Rare Lancer of the Leashbreak Tactix. Tag Shot: Tags a target, revealing stealth and weakening it. Targets ground.'),
  ('0033','Ghost Spaniel','Rare','leashbreak_tactix',false,3,'Skirmisher','air',5,2,'Rare Skirmisher of the Leashbreak Tactix. Phase: Phases out for a brief untargetable window. Targets air.'),
  ('0028','Pulse Border Collie','Epic','leashbreak_tactix',false,5,'Support','ground',25,3,'Epic Support of the Leashbreak Tactix. Barrier Ring: Drops an area shield over the front line. Targets ground.'),
  ('0037','Crown Foxhound','Mythic','k9_circuitry',false,11,'Assassin','ground',1000,10,'Mythic Assassin of the K9 Circuitry. Royal Hunt: Shreds structures; can strike the Queen. Targets ground. Splash damage. Can strike the Queen.'),
  ('0040','Laser Beagle','Rare','k9_circuitry',false,4,'Structure','ground',5,2,'Rare Structure of the K9 Circuitry. Overheat: Static turret that ramps fire the longer it shoots. Targets ground.'),
  ('0045','Neon Dachshund','Common','k9_circuitry',false,3,'Spawner','air',1,1,'Common Spawner of the K9 Circuitry. Tunnel Drones: Tunnels up two attack drones. Targets air. Splash damage.'),
  ('0041','Volt Corgi','Rare','k9_circuitry',false,4,'Spawner','ground',5,2,'Rare Spawner of the K9 Circuitry. Spark Pups: Spawns three spark drones. Targets ground. Splash damage.'),
  ('0042','Grid Schnauzer','Rare','k9_circuitry',false,5,'Structure','ground',5,2,'Rare Structure of the K9 Circuitry. Grid Lock: Turret field that slows attackers in range. Targets ground.'),
  ('0046','Flux Pomeranian','Common','k9_circuitry',false,2,'Support','ground',1,1,'Common Support of the K9 Circuitry. Battery: Boosts the fire rate of nearby turrets. Targets ground.'),
  ('0047','Rail Terrier','Common','k9_circuitry',false,3,'Blaster','ground',1,1,'Common Blaster of the K9 Circuitry. Rail Shot: Long rail shots deal bonus vs structures. Targets ground.'),
  ('0038','Circuit Retriever','Epic','k9_circuitry',false,6,'Support','ground',25,3,'Epic Support of the K9 Circuitry. Drone Swarm: Releases five swarm drones. Targets ground. Splash damage.'),
  ('0043','Chrome Airedale','Rare','k9_circuitry',false,5,'Lancer','ground',5,2,'Rare Lancer of the K9 Circuitry. Arc Shot: Arc that chains to three targets. Targets ground. Splash damage.'),
  ('0044','Beacon Basset','Rare','k9_circuitry',false,4,'Support','ground',5,2,'Rare Support of the K9 Circuitry. Beacon: Reveals stealth and marks foes for the pack. Targets ground.'),
  ('0048','Pixel Pug','Common','k9_circuitry',false,2,'Spawner','air',1,1,'Common Spawner of the K9 Circuitry. Mini Pup: Deploys a single guard drone. Targets air. Splash damage.'),
  ('0039','Nova Shepherd','Epic','k9_circuitry',false,7,'Structure','ground',25,3,'Epic Structure of the K9 Circuitry. Overclock: Heavy static turret with a burst fire window. Targets ground. Splash damage.'),
  ('S001','Boneshatter Freeze','Epic','boneguard_crew',true,5,'Spell','freeze',25,3,'SPELL. Enemies in the area STOP (no move, no attack) for ~3s. Towers freeze too. (radius 3.0, ~3.0s, cost 5, cd 14s).'),
  ('S002','Tar Pour','Rare','leashbreak_tactix',true,4,'Spell','slow',5,2,'SPELL. Tar slick: -35% move + -35% attack speed to enemies in the area for ~4s. (radius 3.2, ~4.0s, cost 4, cd 12s).'),
  ('S003','Snare Trap','Rare','k9_circuitry',true,3,'Spell','trap',5,2,'SPELL. Plants a hidden trap. Arms, then roots + small damage when an enemy crosses it. Zone control. (radius 1.8, ~1.6s, cost 3, cd 13s).'),
  ('S004','Jolt','Common','zoomie_syndicate',true,3,'Spell','zap',1,1,'SPELL. Instant AOE damage + 0.5s stun. Kills swarms, resets attacks. (radius 2.4, ~0.5s, cost 3, cd 9s).'),
  ('S005','Strike','Epic','neutral',true,4,'Spell','strike',25,3,'SPELL. The fireball: medium AOE burst damage at a point. (radius 2.6, ~0s, cost 4, cd 11s).')
on conflict (card_id) do update set
  name=excluded.name, rarity=excluded.rarity, faction_id=excluded.faction_id,
  is_spell=excluded.is_spell, cost=excluded.cost, role=excluded.role,
  domain=excluded.domain, scrap_value=excluded.scrap_value,
  card_shop_price=excluded.card_shop_price, description=excluded.description,
  updated_at=now();

-- ---- ak_level_costs : card upgrade bands (copies + coins per from_level) ----
insert into public.ak_level_costs (entity_type, rarity, from_level, copies_required, coins_required)
values
  ('card','Common',1,2,5),
  ('card','Common',2,4,20),
  ('card','Common',3,6,50),
  ('card','Common',4,10,100),
  ('card','Common',5,20,250),
  ('card','Common',6,40,500),
  ('card','Common',7,80,1000),
  ('card','Common',8,150,2000),
  ('card','Common',9,300,4000),
  ('card','Rare',1,1,50),
  ('card','Rare',2,2,150),
  ('card','Rare',3,4,400),
  ('card','Rare',4,8,1000),
  ('card','Rare',5,16,2000),
  ('card','Rare',6,30,4000),
  ('card','Rare',7,60,8000),
  ('card','Rare',8,120,15000),
  ('card','Rare',9,250,30000),
  ('card','Epic',1,1,400),
  ('card','Epic',2,1,800),
  ('card','Epic',3,2,2000),
  ('card','Epic',4,4,4000),
  ('card','Epic',5,8,8000),
  ('card','Epic',6,16,15000),
  ('card','Epic',7,30,30000),
  ('card','Epic',8,60,60000),
  ('card','Epic',9,120,120000),
  ('card','Legendary',1,1,2000),
  ('card','Legendary',2,0,5000),
  ('card','Legendary',3,1,10000),
  ('card','Legendary',4,0,20000),
  ('card','Legendary',5,2,40000),
  ('card','Legendary',6,0,60000),
  ('card','Legendary',7,4,90000),
  ('card','Legendary',8,0,120000),
  ('card','Legendary',9,8,150000),
  ('card','Mythic',1,1,5000),
  ('card','Mythic',2,0,10000),
  ('card','Mythic',3,0,25000),
  ('card','Mythic',4,1,50000),
  ('card','Mythic',5,0,80000),
  ('card','Mythic',6,0,120000),
  ('card','Mythic',7,1,170000),
  ('card','Mythic',8,0,210000),
  ('card','Mythic',9,1,250000),
  ('tower',NULL,1,1,200),
  ('tower',NULL,2,1,500),
  ('tower',NULL,3,2,1000),
  ('tower',NULL,4,3,2000),
  ('tower',NULL,5,4,4000),
  ('tower',NULL,6,6,8000),
  ('tower',NULL,7,8,15000),
  ('tower',NULL,8,10,25000),
  ('tower',NULL,9,12,40000)
on conflict (entity_type, rarity, from_level) do update set
  copies_required=excluded.copies_required, coins_required=excluded.coins_required;

-- ---- ak_shop_products : gems, chests, consumables, passes ----
-- Gem packs: price_usd + checkout_slug (route to create-checkout TEST price IDs).
-- Deterministic chests (is_random=false): SHIP -- fixed disclosed contents, open-able.
-- Random chests (is_random=true): odds disclosed but edge fn GATES open (PACK_RIP + Gate 3).
insert into public.ak_shop_products
  (sku, kind, title, description, price_usd, price_gems, checkout_slug, grants, odds, is_random, sort_order)
values
  ('ak-gems-rookie','gems','Rookie Stash','500 Gems. In-game value only, no cash value.',4.99,NULL,'ak-gems-rookie','{"gems":500}'::jsonb,NULL,false,10),
  ('ak-gems-player','gems','Player Pack','1,100 Gems (+10%).',9.99,NULL,'ak-gems-player','{"gems":1100}'::jsonb,NULL,false,11),
  ('ak-gems-baller','gems','Baller Bag','2,500 Gems (+25%).',19.99,NULL,'ak-gems-baller','{"gems":2500}'::jsonb,NULL,false,12),
  ('ak-gems-highroller','gems','High Roller Crate','6,500 Gems (+30%).',49.99,NULL,'ak-gems-highroller','{"gems":6500}'::jsonb,NULL,false,13),
  ('ak-gems-kingpin','gems','Kingpin Vault','14,000 Gems (+40%).',99.99,NULL,'ak-gems-kingpin','{"gems":14000}'::jsonb,NULL,false,14),
  ('chest_scrap_crate','chest','Scrap Crate','Fixed contents: 200 Coins + 5 Common Scrap. No random draw.',NULL,40,NULL,'{"coins":200,"scrap_Common":5}'::jsonb,NULL,false,20),
  ('chest_crew','chest','Crew Chest','Fixed contents: 500 Coins + 10 Common Scrap + 3 Rare Scrap. No random draw.',NULL,150,NULL,'{"coins":500,"scrap_Common":10,"scrap_Rare":3}'::jsonb,NULL,false,21),
  ('chest_chop_shop','chest','Chop-Shop Chest','Random: epic-guaranteed + rare + scrap. GATED until legal Gate 3.',NULL,400,NULL,'{}'::jsonb,'{"Epic":1.0,"Rare":2.0,"scrap_Epic":[3,8]}'::jsonb,true,22),
  ('chest_kingpin','chest','Kingpin Chest','Random: legendary chance + epic + tokens. GATED until legal Gate 3.',NULL,900,NULL,'{}'::jsonb,'{"Legendary":0.15,"Epic":1.0,"scrap_Legendary":[1,3]}'::jsonb,true,23),
  ('chest_mythic_vault','chest','Mythic Vault','Event-only random: mythic chance + guaranteed legendary tokens. GATED.',NULL,2000,NULL,'{}'::jsonb,'{"Mythic":0.02,"scrap_Legendary":[5,5]}'::jsonb,true,24),
  ('nitro_can','consumable','Nitro Can','Pre-PvE-match: +1 starting energy. PvE-only (never ranked).',NULL,50,NULL,'{"pve_only":true,"effect":"+1_start_energy"}'::jsonb,NULL,false,30),
  ('spell_emp','consumable','Lane EMP','One-shot PvE lane EMP. PvE-only (never ranked).',NULL,80,NULL,'{"pve_only":true,"effect":"lane_emp"}'::jsonb,NULL,false,31),
  ('pass-master','pass','Master Pass','Arcade-wide: 2x earn, seasonal card track, +chest slot. $14.99/mo.',14.99,NULL,'master-pass','{"perk":"arcade_master_pass"}'::jsonb,NULL,false,40),
  ('pass-crew-ak','pass','AK Crew Pass','Alley Kingz only season track. $4.99/season.',4.99,NULL,'ak-season-pass','{"perk":"ak_crew_pass"}'::jsonb,NULL,false,41)
on conflict (sku) do update set
  kind=excluded.kind, title=excluded.title, description=excluded.description,
  price_usd=excluded.price_usd, price_gems=excluded.price_gems,
  checkout_slug=excluded.checkout_slug, grants=excluded.grants, odds=excluded.odds,
  is_random=excluded.is_random, sort_order=excluded.sort_order, updated_at=now();

-- 48 cards + 5 spells, 54 cost bands, 14 shop products.
-- END SEED.
