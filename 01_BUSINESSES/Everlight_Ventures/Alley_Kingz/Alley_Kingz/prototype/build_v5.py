#!/usr/bin/env python3
"""Build game_v5.html with Twisted Metal character roster."""

import re

# Read base file
with open('/mnt/sdcard/AA_MY_DRIVE/Clash_Carbon/Alley_Kingz/prototype/game_v5.html','r') as f:
    lines = f.readlines()

# ============================================================
# NEW CARD DATA — 41 Twisted Metal-inspired Street Kingz
# ============================================================
NEW_CARDS_SECTION = r"""// ============================================================
// CARDS -- 41 Street Kingz (Twisted Metal inspired)
// ============================================================
const CARS={
  // === COMPTON (Lvl 1-10) — The Block ===
  scrapyard:{id:'scrapyard',name:'Scrapyard',cost:5,hp:2200,dmg:140,speed:0.45,range:0.9,atkSpd:1.4,type:'troop',targets:'all',isArea:true,areaRadius:1.6,count:1,carColor:'#CC6600',bodyW:1.15,bodyH:0.7,icon:'🚛',ability:'CHAIN',abilityCD:8,locked:false,syn:['heavy_metal','fire_starter'],desc:'Junkyard tow truck. CHAIN WHIP: area flail every 8s.'},
  corner_boyz:{id:'corner_boyz',name:'Corner Boyz',cost:2,hp:180,dmg:35,speed:1.4,range:0.9,atkSpd:1.2,type:'troop',targets:'all',count:3,carColor:'#FF8C00',bodyW:0.38,bodyH:0.28,icon:'🏃',ability:'SWARM',locked:false,syn:['street_gang'],desc:'3-unit block swarm. Cheap bodies.'},
  prospect:{id:'prospect',name:'Prospect',cost:1,hp:140,dmg:28,speed:1.65,range:0.9,atkSpd:0.8,type:'troop',targets:'all',count:1,carColor:'#AAA',bodyW:0.35,bodyH:0.25,icon:'🛵',locked:false,syn:['speed_demon','street_gang'],desc:'Cycle card. Fastest deploy.'},
  // === DETROIT (Lvl 11-20) — Motor City ===
  dead_mile:{id:'dead_mile',name:'Dead Mile',cost:4,hp:760,dmg:95,speed:0.88,range:0.9,atkSpd:1.2,type:'troop',targets:'all',count:1,carColor:'#8B0000',bodyW:0.95,bodyH:0.55,icon:'🚗',ability:'RAM',abilityCD:8,locked:false,syn:['heavy_metal'],desc:'Amnesiac racer. RAM: 2x first hit every 8s.'},
  axle_grind:{id:'axle_grind',name:'Axle Grind',cost:5,hp:1100,dmg:170,speed:0.55,range:0.9,atkSpd:1.5,type:'troop',targets:'all',isArea:true,areaRadius:1.4,count:1,carColor:'#B8860B',bodyW:1.1,bodyH:0.8,icon:'🎡',ability:'CRUSH',abilityCD:6,locked:false,syn:['heavy_metal','fire_starter'],desc:'Wheel rig. CRUSH: grinds everything nearby.'},
  rust_bucket:{id:'rust_bucket',name:'Rust Bucket',cost:2,hp:340,dmg:45,speed:1.05,range:0.9,atkSpd:1.0,type:'troop',targets:'all',count:1,carColor:'#8B7355',bodyW:0.85,bodyH:0.5,icon:'💀',ability:'BACKFIRE',locked:false,syn:['street_gang'],desc:'Explodes on death for 200 area dmg.'},
  // === CHICAGO (Lvl 21-30) — Chi-Town ===
  blue_line:{id:'blue_line',name:'Blue Line',cost:5,hp:1200,dmg:90,speed:0.65,range:5.5,atkSpd:1.0,type:'troop',targets:'all',count:1,carColor:'#1E90FF',bodyW:1.0,bodyH:0.7,icon:'🚔',ability:'TASER',abilityCD:7,locked:false,syn:['ghost_rider'],desc:'Police SUV. TASER: chain zap 3 targets.'},
  grim_ride:{id:'grim_ride',name:'Grim Ride',cost:3,hp:380,dmg:220,speed:1.85,range:0.9,atkSpd:2.0,type:'troop',targets:'all',count:1,carColor:'#2F4F4F',bodyW:0.6,bodyH:0.35,icon:'💀',ability:'REAPER',locked:false,syn:['speed_demon'],desc:'Death bike. Glass cannon assassin.'},
  drill_van:{id:'drill_van',name:'Drill Van',cost:4,hp:420,dmg:105,speed:0.75,range:6.0,atkSpd:1.1,type:'troop',targets:'all',count:1,carColor:'#7B2FBE',bodyW:1.0,bodyH:0.7,icon:'🔊',ability:'SPRAY',locked:false,syn:['fire_starter'],desc:'Chicago drill. Long-range spray.'},
  // === BROOKLYN (Lvl 31-40) — BK ===
  phantom:{id:'phantom',name:'Phantom',cost:4,hp:480,dmg:160,speed:1.4,range:5.0,atkSpd:1.5,type:'troop',targets:'all',count:1,carColor:'#9400D3',bodyW:0.78,bodyH:0.44,icon:'👻',ability:'GHOST_SHOT',locked:true,unlockLevel:32,syn:['speed_demon','ghost_rider'],desc:'Blacked-out racer. Homing ghost missiles.'},
  no_face:{id:'no_face',name:'No Face',cost:3,hp:550,dmg:130,speed:1.1,range:0.9,atkSpd:1.0,type:'troop',targets:'all',count:1,carColor:'#483D8B',bodyW:0.82,bodyH:0.48,icon:'🎭',ability:'SHOCK',locked:true,unlockLevel:35,syn:['heavy_metal'],desc:'Masked boxer. SHOCK RAM: stuns on hit 1s.'},
  cabbie:{id:'cabbie',name:'Cabbie',cost:3,hp:500,dmg:90,speed:1.2,range:0.9,atkSpd:1.1,type:'troop',targets:'all',count:1,carColor:'#FFD700',bodyW:0.85,bodyH:0.5,icon:'🚕',ability:'UNDERGROUND',locked:true,unlockLevel:38,syn:['ghost_rider'],desc:'Ghost taxi. Bypasses units, hits backline.'},
  // === ATLANTA (Lvl 41-50) — ATL Trap ===
  preacher:{id:'preacher',name:'Preacher',cost:5,hp:680,dmg:120,speed:0.6,range:6.5,atkSpd:1.3,type:'troop',targets:'all',count:1,carColor:'#800000',bodyW:1.0,bodyH:0.7,icon:'✝',ability:'HOLY_FIRE',locked:true,unlockLevel:42,syn:['fire_starter','ghost_rider'],desc:'Church van. Homing fire crosses. High range.'},
  trap_king:{id:'trap_king',name:'Trap King',cost:6,hp:1900,dmg:130,speed:0.42,range:0.9,atkSpd:1.2,type:'troop',targets:'all',count:1,carColor:'#DC143C',bodyW:1.15,bodyH:0.75,icon:'🛡',ability:'BARRAGE',abilityCD:10,locked:true,unlockLevel:45,syn:['heavy_metal'],desc:'APC tank. BARRAGE: 3-missile burst every 10s.'},
  dirty_south:{id:'dirty_south',name:'Dirty South',cost:3,hp:250,dmg:55,speed:1.8,range:0.9,atkSpd:1.2,type:'troop',targets:'all',count:2,carColor:'#FF2244',bodyW:0.48,bodyH:0.32,icon:'🏍',ability:'WHEELIE',abilityCD:8,locked:true,unlockLevel:48,syn:['speed_demon','street_gang'],desc:'ATL bike duo. Fast flanking pair.'},
  // === OAKLAND (Lvl 51-60) — The Town ===
  sideshow:{id:'sideshow',name:'Sideshow',cost:4,hp:720,dmg:80,speed:0.95,range:0.9,atkSpd:0.8,type:'troop',targets:'all',isArea:true,areaRadius:1.8,count:1,carColor:'#00CED1',bodyW:0.95,bodyH:0.55,icon:'🌀',ability:'DONUT',locked:true,unlockLevel:52,syn:['fire_starter','speed_demon'],desc:'Donk car. SIDESHOW spin: constant area dmg.'},
  dock_boss:{id:'dock_boss',name:'Dock Boss',cost:7,hp:3200,dmg:210,speed:0.32,range:0.9,atkSpd:1.3,type:'troop',targets:'all',isArea:true,areaRadius:2.0,count:1,carColor:'#2E8B57',bodyW:1.3,bodyH:0.9,icon:'📦',ability:'CONTAINER',locked:true,unlockLevel:55,syn:['heavy_metal','fire_starter'],desc:'Container truck. Throws shipping containers.'},
  hyphy:{id:'hyphy',name:'Hyphy',cost:2,hp:300,dmg:50,speed:1.45,range:0.9,atkSpd:1.0,type:'troop',targets:'all',count:1,carColor:'#20B2AA',bodyW:0.8,bodyH:0.45,icon:'🎶',ability:'GHOST_RIDE',locked:true,unlockLevel:58,syn:['street_gang','speed_demon'],desc:'Bay ghost ride. Keeps moving 3s after death.'},
  // === MIAMI (Lvl 61-70) — 305 Vice ===
  vice_queen:{id:'vice_queen',name:'Vice Queen',cost:4,hp:520,dmg:260,speed:1.55,range:0.9,atkSpd:1.9,type:'troop',targets:'all',count:1,carColor:'#FF1493',bodyW:0.78,bodyH:0.44,icon:'👑',ability:'NITRO',abilityCD:12,locked:true,unlockLevel:62,syn:['speed_demon'],desc:'Pink lambo. NITRO: +50% speed burst.'},
  bass_cannon:{id:'bass_cannon',name:'Bass Cannon',cost:5,hp:650,dmg:100,speed:0.55,range:6.0,atkSpd:1.2,type:'troop',targets:'all',isArea:true,areaRadius:2.0,count:1,carColor:'#FF00FF',bodyW:1.1,bodyH:0.75,icon:'🔊',ability:'BASS_DROP',locked:true,unlockLevel:65,syn:['fire_starter','ghost_rider'],desc:'Bass van. Pushback wave + area damage.'},
  jet_runner:{id:'jet_runner',name:'Jet Runner',cost:2,hp:260,dmg:65,speed:2.0,range:0.9,atkSpd:1.1,type:'troop',targets:'all',count:1,carColor:'#FF69B4',bodyW:0.55,bodyH:0.3,icon:'🏄',ability:'WAVE_DASH',locked:true,unlockLevel:68,syn:['speed_demon'],desc:'Jet ski racer. Crosses river instantly.'},
  // === LAS VEGAS (Lvl 71-80) — Sin City ===
  ice_kream:{id:'ice_kream',name:'Ice Kream',cost:6,hp:1600,dmg:280,speed:0.65,range:5.0,atkSpd:2.0,type:'troop',targets:'all',count:1,carColor:'#FF4500',bodyW:1.1,bodyH:0.75,icon:'🤡',ability:'CLOWN_MISSILE',abilityCD:15,locked:true,unlockLevel:72,syn:['heavy_metal','dark_carnival'],desc:'Flaming clown truck. Giant homing missile.'},
  high_roller:{id:'high_roller',name:'High Roller',cost:5,hp:900,dmg:155,speed:0.7,range:0.9,atkSpd:1.1,type:'troop',targets:'all',count:1,carColor:'#FFD700',bodyW:1.05,bodyH:0.6,icon:'🎰',ability:'JACKPOT',abilityCD:6,locked:true,unlockLevel:75,syn:['dark_carnival','heavy_metal'],desc:'Gold Rolls. JACKPOT: random 1x-3x damage.'},
  showgirl:{id:'showgirl',name:'Showgirl',cost:3,hp:380,dmg:60,speed:1.3,range:0.9,atkSpd:0.9,type:'troop',targets:'all',count:1,carColor:'#FF6EC7',bodyW:0.75,bodyH:0.42,icon:'💃',ability:'DAZZLE',abilityCD:8,locked:true,unlockLevel:78,syn:['dark_carnival','speed_demon'],desc:'Neon convertible. DAZZLE: AoE stun 1.5s.'},
  // === NEO TOKYO (Lvl 81-90) — Cyber District ===
  mecha:{id:'mecha',name:'Mecha',cost:7,hp:3500,dmg:95,speed:0.35,range:3.0,atkSpd:0.4,type:'troop',targets:'all',isArea:true,areaRadius:2.2,count:1,carColor:'#00FFFF',bodyW:1.3,bodyH:0.9,icon:'🤖',ability:'FLAMETHROWER',locked:true,unlockLevel:82,syn:['heavy_metal','ghost_rider'],desc:'Cyber tank. Continuous fire stream.'},
  drone_lord:{id:'drone_lord',name:'Drone Lord',cost:4,hp:260,dmg:85,speed:2.2,range:5.5,atkSpd:1.5,type:'troop',targets:'all',count:2,carColor:'#00CED1',bodyW:0.48,bodyH:0.32,icon:'✈',ability:'MISSILES',locked:true,unlockLevel:85,syn:['ghost_rider','speed_demon'],desc:'Drone pair. Air missiles from above.'},
  neon_blade:{id:'neon_blade',name:'Neon Blade',cost:3,hp:420,dmg:95,speed:1.65,range:0.9,atkSpd:1.3,type:'troop',targets:'all',count:1,carColor:'#FF00FF',bodyW:0.65,bodyH:0.38,icon:'⚔',ability:'STEALTH',locked:true,unlockLevel:88,syn:['speed_demon','ghost_rider'],desc:'Cyber ninja bike. Invisible 3s on deploy.'},
  // === KINGZ COURT (Lvl 91-100) — The Throne ===
  kingpin:{id:'kingpin',name:'Kingpin',cost:6,hp:1800,dmg:130,speed:0.55,range:0.9,atkSpd:1.0,type:'troop',targets:'all',count:1,carColor:'#FFD700',bodyW:1.1,bodyH:0.65,icon:'👑',ability:'BOSS_BUFF',locked:true,unlockLevel:92,syn:['heavy_metal','dark_carnival'],desc:'Gold limo. Buffs all allies nearby.'},
  warhawk:{id:'warhawk',name:'Warhawk',cost:8,hp:2000,dmg:250,speed:1.8,range:6.0,atkSpd:2.5,type:'troop',targets:'all',isArea:true,areaRadius:2.5,count:1,carColor:'#FF0000',bodyW:1.2,bodyH:0.6,icon:'🚁',ability:'AIRSTRIKE',locked:true,unlockLevel:95,syn:['fire_starter','ghost_rider'],desc:'Attack gunship. Ultimate air superiority.'},
  shadow_king:{id:'shadow_king',name:'Shadow King',cost:5,hp:800,dmg:170,speed:0.85,range:0.9,atkSpd:1.2,type:'troop',targets:'all',count:1,carColor:'#1C1C1C',bodyW:1.0,bodyH:0.65,icon:'⚰',ability:'COFFIN',abilityCD:10,locked:true,unlockLevel:98,syn:['dark_carnival','ghost_rider'],desc:'Death hearse. Deploys coffin bomb on death.'},
  // === SPELLS (Universal) ===
  napalm:{id:'napalm',name:'Napalm',cost:4,dmg:325,radius:2.5,type:'spell',carColor:'#FF4500',icon:'🔥',locked:false,syn:['fire_starter','spell_cycle'],desc:'Burning area damage.'},
  blackout:{id:'blackout',name:'Blackout',cost:3,dmg:144,radius:4.0,type:'spell',carColor:'#7CFC00',icon:'⚡',locked:false,syn:['spell_cycle','ghost_rider'],desc:'Wide energy blast.'},
  turbo_boost:{id:'turbo_boost',name:'Turbo',cost:3,dmg:0,radius:3.5,type:'spell',carColor:'#00CED1',icon:'💨',locked:false,syn:['speed_demon','spell_cycle'],desc:'Allies +60% speed 3s.'},
  drive_by:{id:'drive_by',name:'Drive-By',cost:2,dmg:220,radius:0.5,type:'spell',carColor:'#FF6347',icon:'🔫',locked:false,syn:['spell_cycle'],desc:'Fast targeted shot.'},
  oil_slick:{id:'oil_slick',name:'Oil Slick',cost:2,dmg:60,radius:3.0,type:'spell',carColor:'#555',icon:'🛢',locked:false,syn:['spell_cycle'],desc:'Slow + damage over time.'},
  spike_strip:{id:'spike_strip',name:'Spike Strip',cost:3,dmg:180,radius:2.0,type:'spell',carColor:'#DD5500',icon:'⛓',locked:false,syn:['spell_cycle'],desc:'Trap: damage + slow.'},
  smoke_screen:{id:'smoke_screen',name:'Smoke',cost:1,dmg:0,radius:3.0,type:'spell',carColor:'#666',icon:'🌫',locked:false,syn:['spell_cycle'],desc:'Stuns enemies 1.5s.'},
  calypso_wish:{id:'calypso_wish',name:'Calypso',cost:3,dmg:0,radius:3.0,type:'spell',carColor:'#CC44FF',icon:'🎪',locked:false,syn:['dark_carnival','spell_cycle'],desc:'Random: heal allies OR damage enemies OR speed buff.'},
  // === BUILDINGS ===
  car_bomb:{id:'car_bomb',name:'Car Bomb',cost:3,hp:500,dmg:350,speed:0,range:2.5,atkSpd:0.5,type:'building',targets:'all',count:1,carColor:'#8B4513',bodyW:0.9,bodyH:0.55,icon:'💥',ability:'TRAP',locked:false,syn:['fire_starter'],desc:'Parked explosive. Boom.'},
  chop_shop:{id:'chop_shop',name:'Chop Shop',cost:4,hp:800,dmg:0,speed:0,range:0,atkSpd:0,type:'building',targets:'all',count:1,carColor:'#AA6633',bodyW:1.1,bodyH:0.7,icon:'🔧',ability:'SPAWN',abilityCD:12,locked:false,syn:['street_gang'],desc:'Spawns Rust Bucket every 12s.'},
  turret_nest:{id:'turret_nest',name:'Turret Nest',cost:3,hp:450,dmg:75,speed:0,range:5.0,atkSpd:0.7,type:'building',targets:'all',count:1,carColor:'#556B2F',bodyW:0.7,bodyH:0.7,icon:'🗼',ability:'TURRET',locked:false,syn:['ghost_rider'],desc:'Auto-targeting defense tower.'}
};

const ALL_CAR_IDS=Object.keys(CARS);
const UNLOCKED_IDS=ALL_CAR_IDS.filter(id=>!CARS[id].locked);
const DEFAULT_DECK=['dead_mile','scrapyard','corner_boyz','grim_ride','napalm','blackout','drive_by','prospect'];

// --- PRE-BUILT DECKS (Twisted Metal Archetypes) ---
const DECK_PRESETS={
  fast_cycle:{name:'⚡ Speed Demon (1.9)',ids:['prospect','corner_boyz','grim_ride','jet_runner','drive_by','oil_slick','blackout','smoke_screen']},
  beatdown:{name:'🛻 Heavy Metal (5.0)',ids:['scrapyard','axle_grind','dead_mile','dock_boss','napalm','turbo_boost','blackout','car_bomb']},
  control:{name:'🏗 Ghost Rider (2.8)',ids:['blue_line','drill_van','turret_nest','chop_shop','blackout','oil_slick','napalm','rust_bucket']},
  bridge_spam:{name:'🏎 Street Gang (2.6)',ids:['grim_ride','dirty_south','corner_boyz','prospect','drive_by','blackout','dead_mile','rust_bucket']},
  balanced:{name:'⚖ Dark Carnival (3.4)',ids:['dead_mile','scrapyard','grim_ride','drill_van','napalm','blackout','drive_by','corner_boyz']}
};

// --- SYNERGY (Twisted Metal themed) ---
const SYN_INFO={speed_demon:{n:'Speed Demon',c:'#00BFFF'},street_gang:{n:'Street Gang',c:'#FF8C00'},heavy_metal:{n:'Heavy Metal',c:'#8B4513'},spell_cycle:{n:'Spell Cycle',c:'#7CFC00'},ghost_rider:{n:'Ghost Rider',c:'#9400D3'},fire_starter:{n:'Fire Starter',c:'#FF4500'},dark_carnival:{n:'Dark Carnival',c:'#CC44FF'}};
function getDeckSynergies(ids){const t={};ids.forEach(id=>{const c=CARS[id];if(c&&c.syn)c.syn.forEach(s=>{t[s]=(t[s]||0)+1;});});const r=[];for(const[k,v]of Object.entries(t)){if(v>=2&&SYN_INFO[k])r.push({tag:k,...SYN_INFO[k],count:v});}return r;}
"""

# ============================================================
# NEW AI DECKS
# ============================================================
NEW_AI_DECKS = r"""function getAIDeck(lvl){
  // AI picks smarter decks at higher levels
  if(lvl<=10) return['rust_bucket','corner_boyz','dead_mile','prospect','blackout','oil_slick','drive_by','scrapyard'];
  if(lvl<=20) return['dead_mile','scrapyard','grim_ride','axle_grind','napalm','blackout','drill_van','corner_boyz'];
  if(lvl<=40) return['grim_ride','phantom','no_face','dirty_south','napalm','turbo_boost','blackout','car_bomb'];
  if(lvl<=60) return['axle_grind','blue_line','preacher','sideshow','napalm','turbo_boost','dead_mile','blackout'];
  return DEFAULT_DECK;
}"""

# ============================================================
# NEW SPELL EFFECTS — updated spell IDs
# ============================================================
NEW_SPELL_FN = r"""function applySpell(card,ownerId,gx,gy){
  const r=card.radius||2,d=card.dmg||0,enemyOwner=1-ownerId;

  if(card.id==='turbo_boost'){
    units.forEach(u=>{
      if(u.owner!==ownerId||!u.alive)return;
      if(Math.hypot(u.x-gx,u.y-gy)<=r){u.nitroActive=true;u.nitroTimer=3;u.speed=u.card.speed*1.6;addEffect('ability',u.x,u.y,'TURBO!','#00CED1',0.8);}
    });
    addEffect('spell',gx,gy,'','#00CED1',0.7);addNeonTrail(gx,gy,'#00CED1');return;
  }
  if(card.id==='smoke_screen'){
    units.forEach(u=>{
      if(u.owner!==enemyOwner||!u.alive)return;
      if(Math.hypot(u.x-gx,u.y-gy)<=r){u.stunTimer=1.5;addEffect('ability',u.x,u.y,'STUN!','#666',0.8);}
    });
    addEffect('spell',gx,gy,'','#888',0.7);return;
  }
  if(card.id==='oil_slick'||card.id==='spike_strip'){
    units.forEach(u=>{
      if(u.owner!==enemyOwner||!u.alive)return;
      if(Math.hypot(u.x-gx,u.y-gy)<=r){u.takeDamage(d);u.slowTimer=3;addEffect('dmg',u.x,u.y-0.4,'-'+d,'#FF0000',0.7);}
    });
    addEffect('spell',gx,gy,'',card.carColor||'#555',0.6);return;
  }
  if(card.id==='calypso_wish'){
    const roll=Math.random();
    if(roll<0.33){
      // Heal allies
      units.forEach(u=>{if(u.owner===ownerId&&u.alive&&Math.hypot(u.x-gx,u.y-gy)<=r){u.hp=Math.min(u.maxHp,u.hp+200);addEffect('ability',u.x,u.y,'+200','#44FF44',0.8);}});
      addEffect('spell',gx,gy,'HEAL!','#44FF44',1.0);
    } else if(roll<0.66){
      // Damage enemies
      units.forEach(u=>{if(u.owner===enemyOwner&&u.alive&&Math.hypot(u.x-gx,u.y-gy)<=r){u.takeDamage(250);addEffect('dmg',u.x,u.y-0.4,'-250','#FF0000',0.7);}});
      const eTowers=ownerId===0?opponent.towers:player.towers;
      eTowers.forEach(t=>{if(!t.destroyed&&Math.hypot(t.x-gx,t.y-gy)<=r+1.2){t.takeDamage(250);sfxTowerHit();checkTowerDeath(t,ownerId);}});
      addEffect('spell',gx,gy,'CHAOS!','#FF4444',1.0);addExplosionParticles(gx,gy,'#CC44FF',10);
    } else {
      // Speed buff
      units.forEach(u=>{if(u.owner===ownerId&&u.alive&&Math.hypot(u.x-gx,u.y-gy)<=r){u.nitroActive=true;u.nitroTimer=4;u.speed=u.card.speed*1.8;addEffect('ability',u.x,u.y,'BOOST!','#CC44FF',0.8);}});
      addEffect('spell',gx,gy,'SPEED!','#CC44FF',1.0);
    }
    addNeonTrail(gx,gy,'#CC44FF');return;
  }

  // Standard damage spell (napalm, blackout, drive_by)
  units.forEach(u=>{
    if(u.owner!==enemyOwner||!u.alive)return;
    if(Math.hypot(u.x-gx,u.y-gy)<=r){u.takeDamage(d);addEffect('dmg',u.x,u.y-0.4,'-'+d,'#FF0000',0.7);}
  });
  const eTowers=ownerId===0?opponent.towers:player.towers;
  eTowers.forEach(t=>{
    if(t.destroyed)return;
    if(Math.hypot(t.x-gx,t.y-gy)<=r+1.2){t.takeDamage(d);addEffect('dmg',t.x,t.y-0.4,'-'+d,'#FF0000',0.7);sfxTowerHit();checkTowerDeath(t,ownerId);}
  });
  addEffect('spell',gx,gy,'',card.carColor||'#fff',0.6);
  addExplosionParticles(gx,gy,card.carColor,8);
}"""

# ============================================================
# NEW CHOP SHOP SPAWNER — spawns rust_bucket instead of hooptie
# ============================================================
NEW_CHOP_SHOP = r"""    // Chop Shop spawner
    if(u.card.id==='chop_shop'&&u.card.type==='building'){
      if(u.abilityCD<=0){
        u.abilityCD=12;
        const sc=CARS['rust_bucket'];
        if(sc)units.push(new Unit(sc,u.owner,u.x+(Math.random()-0.5),u.y+(u.owner===0?-1:1)));
        addEffect('ability',u.x,u.y,'SPAWN!','#AA6633',0.8);
      }
      continue;
    }"""

# ============================================================
# NEW ABILITY TRIGGERS — use ability field instead of hardcoded IDs
# ============================================================
NEW_ABILITY_TRIGGERS = r"""  if(u.card.ability==='RAM'&&u.abilityCD<=0){d*=2;u.abilityCD=u.card.abilityCD||8;addEffect('ability',u.x,u.y,'RAM!','#FF4500',0.9);}
  if(u.card.ability==='SHOCK'&&u.abilityCD<=0){u.abilityCD=5;if(u.target&&!(u.target instanceof Tower)){u.target.stunTimer=1;addEffect('ability',u.target.x,u.target.y,'STUN!','#FFFF00',0.8);}}
  if(u.card.ability==='JACKPOT'&&u.abilityCD<=0){const mult=1+Math.floor(Math.random()*3);d*=mult;u.abilityCD=u.card.abilityCD||6;addEffect('ability',u.x,u.y,mult+'x JACKPOT!','#FFD700',1.0);}
  if(u.card.ability==='DAZZLE'&&u.abilityCD<=0){u.abilityCD=u.card.abilityCD||8;units.forEach(o=>{if(o.owner!==u.owner&&o.alive&&u.dist(o.x,o.y)<=3){o.stunTimer=1.5;addEffect('ability',o.x,o.y,'DAZZLE!','#FF6EC7',0.8);}});}
  if(u.card.ability==='TASER'&&u.abilityCD<=0){u.abilityCD=u.card.abilityCD||7;let chain=0;units.forEach(o=>{if(o.owner!==u.owner&&o.alive&&u.dist(o.x,o.y)<=5.5&&chain<3){o.takeDamage(Math.floor(d*0.6));chain++;addEffect('ability',o.x,o.y,'ZAP!','#1E90FF',0.6);}});}
  if(u.card.ability==='BARRAGE'&&u.abilityCD<=0){u.abilityCD=u.card.abilityCD||10;for(let i=0;i<3;i++){setTimeout(()=>{if(u.target&&u.alive){u.target.takeDamage(Math.floor(d*0.5));addEffect('dmg',u.target.x+(Math.random()-0.5),u.target.y-0.3,'-'+Math.floor(d*0.5),'#DC143C',0.4);addSparkParticles(u.target.x,u.target.y,'#DC143C');}},i*200);}addEffect('ability',u.x,u.y,'BARRAGE!','#DC143C',0.9);}"""

NEW_NITRO_AND_JAM = r"""  if(u.card.ability==='NITRO'&&!u.nitroActive&&u.abilityCD<=0){
    u.nitroActive=true;u.nitroTimer=2.5;u.speed=u.card.speed*1.5;u.abilityCD=u.card.abilityCD||12;
    addEffect('ability',u.x,u.y,'NITRO!','#00BFFF',0.9);
  }
  // Jammer/slow aura abilities
  if(u.card.ability==='BASS_DROP'){
    units.forEach(o=>{if(o.owner!==u.owner&&o.alive&&u.dist(o.x,o.y)<=4.5)o.slowTimer=Math.max(o.slowTimer,2);});
  }"""

# ============================================================
# NEW PLAYER PROFILE
# ============================================================
NEW_PROFILE = "const playerProfile={name:'Street King',nosBottles:847,level:7,fuel:2400,gears:88,gems:35,deck:[...DEFAULT_DECK],collection:[...UNLOCKED_IDS],completedLevels:[1,2,3,4,5]};"

# ============================================================
# PERFORM REPLACEMENTS (bottom-to-top for line stability)
# ============================================================
content = ''.join(lines)

# 1. Replace ability triggers (lines 534-552)
old_ability = "  if(u.card.id==='muscle_car'&&u.abilityCD<=0){d*=2;u.abilityCD=8;addEffect('ability',u.x,u.y,'RAM!','#FF4500',0.9);}"
content = content.replace(old_ability, NEW_ABILITY_TRIGGERS)

old_nitro = """  if(u.card.id==='sports_car'&&!u.nitroActive&&u.abilityCD<=0){
    u.nitroActive=true;u.nitroTimer=2.5;u.speed=u.card.speed*1.5;u.abilityCD=12;
    addEffect('ability',u.x,u.y,'NITRO!','#00BFFF',0.9);
  }
  // Jammer slow
  if(u.card.id==='jammer_van'){
    units.forEach(o=>{if(o.owner!==u.owner&&o.alive&&u.dist(o.x,o.y)<=4.5)o.slowTimer=Math.max(o.slowTimer,2);});
  }"""
content = content.replace(old_nitro, NEW_NITRO_AND_JAM)

# 2. Replace chop shop spawner
old_chop = """    // Chop Shop spawner
    if(u.card.id==='chop_shop'&&u.card.type==='building'){
      if(u.abilityCD<=0){
        u.abilityCD=12;
        const hc=CARS['hooptie'];
        if(hc)units.push(new Unit(hc,u.owner,u.x+(Math.random()-0.5),u.y+(u.owner===0?-1:1)));
        addEffect('ability',u.x,u.y,'SPAWN!','#AA6633',0.8);
      }
      continue;
    }"""
content = content.replace(old_chop, NEW_CHOP_SHOP)

# 3. Replace applySpell function
old_spell_start = "function applySpell(card,ownerId,gx,gy){"
old_spell_end = "  addExplosionParticles(gx,gy,card.carColor,8);\n}"
spell_start_idx = content.index(old_spell_start)
spell_end_idx = content.index(old_spell_end, spell_start_idx) + len(old_spell_end)
content = content[:spell_start_idx] + NEW_SPELL_FN + "\n" + content[spell_end_idx:]

# 4. Replace getAIDeck function
old_ai_start = "function getAIDeck(lvl){"
old_ai_end_marker = "  return DEFAULT_DECK;\n}"
ai_start_idx = content.index(old_ai_start)
ai_end_idx = content.index(old_ai_end_marker, ai_start_idx) + len(old_ai_end_marker)
content = content[:ai_start_idx] + NEW_AI_DECKS + "\n" + content[ai_end_idx:]

# 5. Replace playerProfile
old_profile = "const playerProfile={name:'Street King',nosBottles:847,level:7,fuel:2400,gears:88,gems:35,deck:[...DEFAULT_DECK],collection:[...UNLOCKED_IDS],completedLevels:[1,2,3,4,5]};"
content = content.replace(old_profile, NEW_PROFILE)

# 6. Replace the entire CARDS section through synergies
cards_section_start = "// ============================================================\n// CARDS -- 30 cards with synergy tags\n// ============================================================"
cards_section_end = "function getDeckSynergies(ids){const t={};ids.forEach(id=>{const c=CARS[id];if(c&&c.syn)c.syn.forEach(s=>{t[s]=(t[s]||0)+1;});});const r=[];for(const[k,v]of Object.entries(t)){if(v>=2&&SYN_INFO[k])r.push({tag:k,...SYN_INFO[k],count:v});}return r;}"
cs_start_idx = content.index(cards_section_start)
cs_end_idx = content.index(cards_section_end) + len(cards_section_end)
content = content[:cs_start_idx] + NEW_CARDS_SECTION + "\n" + content[cs_end_idx:]

# 7. Update title
content = content.replace('Alley Kingz v0.4', 'Alley Kingz v0.5 — Street Kingz')
content = content.replace('// ALLEY KINGZ v0.4 -- Ultimate City Arena Update', '// ALLEY KINGZ v0.5 -- STREET KINGZ (Twisted Metal Edition)')

# Write output
with open('/mnt/sdcard/AA_MY_DRIVE/Clash_Carbon/Alley_Kingz/prototype/game_v5.html', 'w') as f:
    f.write(content)

print("SUCCESS: game_v5.html built with 41 Twisted Metal Street Kingz cards")
print(f"File size: {len(content)} chars, {content.count(chr(10))} lines")
