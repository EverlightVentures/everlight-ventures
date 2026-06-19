// ==========================================================================
// ALLEY KINGZ -- CANON DATA (inlined for offline play)
// SOURCE OF TRUTH: ecosystem/data/cards.json (48 dogs) + ability_params.json + decks.json
// This file is GENERATED. Do not hand-edit stats -- re-run the canon merge instead.
// Stats (hp/damage/attack_speed/move_speed/range/cost) are byte-faithful to the canon.
// ==========================================================================
const CANON_META = {
  "title": "Alley Kingz -- Canonical Card Roster",
  "ticker": "$BCARDD",
  "chain": "solana",
  "cardCount": 106,
  "factions": [
    "Boneguard Crew",
    "Zoomie Syndicate",
    "Leashbreak Tactix",
    "K9 Circuitry"
  ],
  "mythics": [
    "$BCARDD",
    "Jagged",
    "Rosco",
    "Crown Foxhound"
  ],
  "legendary": [
    "Stonejaw"
  ],
  "canon_date": "2026-06-03"
};

const CANON_CARDS = [
 {
  "name": "$BCARDD",
  "breed": "Dogo Argentino",
  "class": "Boneguard Crew",
  "factionId": "boneguard_crew",
  "rarity": "Mythic",
  "cost": 10,
  "role": "Vanguard",
  "hp": 2850,
  "damage": 180,
  "attack_speed": 0.7,
  "move_speed": 0.55,
  "range": 1,
  "ability": {
   "name": "Crownbreaker",
   "description": "Shields self for 18% HP; can strike the Queen",
   "cooldown": 18
  },
  "abilityType": "shield",
  "queen_target": true,
  "cardNumber": "0001",
  "isMythic": true,
  "rig": {
   "name": "The Crown Rig",
   "rigClass": "bruiser",
   "weaponMod": "ram_plow",
   "sourceCar": "Muscle Car",
   "flavor": "matte-black armored war-truck, gold trim, ram plow. The coin/dealer dog."
  }
 },
 {
  "name": "Stonejaw",
  "breed": "Mastiff",
  "class": "Boneguard Crew",
  "factionId": "boneguard_crew",
  "rarity": "Legendary",
  "cost": 7,
  "role": "Vanguard",
  "hp": 2850,
  "damage": 145,
  "attack_speed": 0.7,
  "move_speed": 0.55,
  "range": 1,
  "ability": {
   "name": "Armor Pulse",
   "description": "Aura cuts nearby ally damage taken by 15%",
   "cooldown": 16
  },
  "abilityType": "dr",
  "queen_target": false,
  "cardNumber": "0002",
  "isMythic": false,
  "rig": {
   "name": "Mastiff Rig",
   "rigClass": "bruiser",
   "weaponMod": "ram_plow",
   "sourceCar": "Muscle Car",
   "flavor": ""
  }
 },
 {
  "name": "Balboa",
  "breed": "Boxer",
  "class": "Boneguard Crew",
  "factionId": "boneguard_crew",
  "rarity": "Epic",
  "cost": 6,
  "role": "Striker",
  "hp": 1500,
  "damage": 175,
  "attack_speed": 1.05,
  "move_speed": 0.85,
  "range": 1,
  "ability": {
   "name": "Haymaker",
   "description": "First hit stuns the target for 1s",
   "cooldown": 12
  },
  "abilityType": "stun",
  "queen_target": false,
  "cardNumber": "0003",
  "isMythic": false,
  "rig": {
   "name": "Boxer Rig",
   "rigClass": "bruiser",
   "weaponMod": "ram_plow",
   "sourceCar": "Muscle Car",
   "flavor": ""
  }
 },
 {
  "name": "Iron Rottweiler",
  "breed": "Rottweiler",
  "class": "Boneguard Crew",
  "factionId": "boneguard_crew",
  "rarity": "Epic",
  "cost": 9,
  "role": "Vanguard",
  "hp": 2850,
  "damage": 155,
  "attack_speed": 0.7,
  "move_speed": 0.55,
  "range": 1,
  "ability": {
   "name": "Overclock Rage",
   "description": "Below 40% HP its bite damage spikes",
   "cooldown": 14
  },
  "abilityType": "crit",
  "queen_target": false,
  "cardNumber": "0004",
  "isMythic": false,
  "rig": {
   "name": "Rottweiler Rig",
   "rigClass": "bruiser",
   "weaponMod": "ram_plow",
   "sourceCar": "Muscle Car",
   "flavor": ""
  }
 },
 {
  "name": "Granite Saint",
  "breed": "St. Bernard",
  "class": "Boneguard Crew",
  "factionId": "boneguard_crew",
  "rarity": "Rare",
  "cost": 8,
  "role": "Vanguard",
  "hp": 2650,
  "damage": 135,
  "attack_speed": 0.7,
  "move_speed": 0.55,
  "range": 1,
  "ability": {
   "name": "Bodywall",
   "description": "Bodywall aura soaks nearby damage for the pack",
   "cooldown": 14
  },
  "abilityType": "dr",
  "queen_target": false,
  "cardNumber": "0005",
  "isMythic": false,
  "rig": {
   "name": "St. Bernard Rig",
   "rigClass": "bruiser",
   "weaponMod": "ram_plow",
   "sourceCar": "Muscle Car",
   "flavor": ""
  }
 },
 {
  "name": "Grit Bulldog",
  "breed": "Bulldog",
  "class": "Boneguard Crew",
  "factionId": "boneguard_crew",
  "rarity": "Rare",
  "cost": 5,
  "role": "Striker",
  "hp": 1300,
  "damage": 150,
  "attack_speed": 1.05,
  "move_speed": 0.85,
  "range": 1,
  "ability": {
   "name": "Brawler",
   "description": "Powers up its own bite the longer it brawls",
   "cooldown": 10
  },
  "abilityType": "buff",
  "queen_target": false,
  "cardNumber": "0006",
  "isMythic": false,
  "rig": {
   "name": "Bulldog Rig",
   "rigClass": "bruiser",
   "weaponMod": "ram_plow",
   "sourceCar": "Muscle Car",
   "flavor": ""
  }
 },
 {
  "name": "Alloy Akita",
  "breed": "Akita",
  "class": "Boneguard Crew",
  "factionId": "boneguard_crew",
  "rarity": "Rare",
  "cost": 6,
  "role": "Lancer",
  "hp": 1100,
  "damage": 180,
  "attack_speed": 0.95,
  "move_speed": 0.85,
  "range": 2,
  "ability": {
   "name": "Shock Push",
   "description": "Knockback cone shoves a melee line back",
   "cooldown": 12
  },
  "abilityType": "knockback",
  "queen_target": false,
  "cardNumber": "0007",
  "isMythic": false,
  "rig": {
   "name": "Akita Rig",
   "rigClass": "bruiser",
   "weaponMod": "ram_plow",
   "sourceCar": "Muscle Car",
   "flavor": ""
  }
 },
 {
  "name": "Tank Pug",
  "breed": "Pug",
  "class": "Boneguard Crew",
  "factionId": "boneguard_crew",
  "rarity": "Common",
  "cost": 3,
  "role": "Support",
  "hp": 750,
  "damage": 45,
  "attack_speed": 0.9,
  "move_speed": 0.85,
  "range": 3,
  "ability": {
   "name": "Shield Bark",
   "description": "Drops a small temporary shield on one ally",
   "cooldown": 10
  },
  "abilityType": "shield",
  "queen_target": false,
  "cardNumber": "0010",
  "isMythic": false,
  "rig": {
   "name": "Pug Rig",
   "rigClass": "bruiser",
   "weaponMod": "ram_plow",
   "sourceCar": "Muscle Car",
   "flavor": ""
  }
 },
 {
  "name": "Copper Chow",
  "breed": "Chow",
  "class": "Boneguard Crew",
  "factionId": "boneguard_crew",
  "rarity": "Common",
  "cost": 4,
  "role": "Striker",
  "hp": 1100,
  "damage": 125,
  "attack_speed": 1.05,
  "move_speed": 0.85,
  "range": 1,
  "ability": {
   "name": "Bitechain",
   "description": "Each consecutive hit ramps its damage",
   "cooldown": 10
  },
  "abilityType": "ramp",
  "queen_target": false,
  "cardNumber": "0011",
  "isMythic": false,
  "rig": {
   "name": "Chow Rig",
   "rigClass": "bruiser",
   "weaponMod": "ram_plow",
   "sourceCar": "Muscle Car",
   "flavor": ""
  }
 },
 {
  "name": "Warden Newfie",
  "breed": "Newfoundland",
  "class": "Boneguard Crew",
  "factionId": "boneguard_crew",
  "rarity": "Rare",
  "cost": 7,
  "role": "Support",
  "hp": 1100,
  "damage": 70,
  "attack_speed": 0.9,
  "move_speed": 0.85,
  "range": 2,
  "ability": {
   "name": "Fortify",
   "description": "Raises max HP of allies in an aura",
   "cooldown": 16
  },
  "abilityType": "buff",
  "queen_target": false,
  "cardNumber": "0008",
  "isMythic": false,
  "rig": {
   "name": "Newfoundland Rig",
   "rigClass": "bruiser",
   "weaponMod": "ram_plow",
   "sourceCar": "Muscle Car",
   "flavor": ""
  }
 },
 {
  "name": "Rust Cane Corso",
  "breed": "Cane Corso",
  "class": "Boneguard Crew",
  "factionId": "boneguard_crew",
  "rarity": "Rare",
  "cost": 8,
  "role": "Vanguard",
  "hp": 2650,
  "damage": 135,
  "attack_speed": 0.7,
  "move_speed": 0.55,
  "range": 1,
  "ability": {
   "name": "Grav Pull",
   "description": "Pulses a shove that scatters the nearest foes",
   "cooldown": 14
  },
  "abilityType": "knockback",
  "queen_target": false,
  "cardNumber": "0009",
  "isMythic": false,
  "rig": {
   "name": "Cane Corso Rig",
   "rigClass": "bruiser",
   "weaponMod": "ram_plow",
   "sourceCar": "Muscle Car",
   "flavor": ""
  }
 },
 {
  "name": "Brick Bullmastiff",
  "breed": "Bullmastiff",
  "class": "Boneguard Crew",
  "factionId": "boneguard_crew",
  "rarity": "Common",
  "cost": 6,
  "role": "Vanguard",
  "hp": 2250,
  "damage": 110,
  "attack_speed": 0.7,
  "move_speed": 0.55,
  "range": 1,
  "ability": {
   "name": "Stonehide",
   "description": "Short window of heavy damage resistance",
   "cooldown": 12
  },
  "abilityType": "dr",
  "queen_target": false,
  "cardNumber": "0012",
  "isMythic": false,
  "rig": {
   "name": "Bullmastiff Rig",
   "rigClass": "bruiser",
   "weaponMod": "ram_plow",
   "sourceCar": "Muscle Car",
   "flavor": ""
  }
 },
 {
  "name": "Jagged",
  "breed": "Doberman",
  "class": "Zoomie Syndicate",
  "factionId": "zoomie_syndicate",
  "rarity": "Mythic",
  "cost": 11,
  "role": "Assassin",
  "hp": 1900,
  "damage": 230,
  "attack_speed": 1.1,
  "move_speed": 1.1,
  "range": 1,
  "ability": {
   "name": "Shadow Fang",
   "description": "Teleports onto the Queen for a kill window",
   "cooldown": 18
  },
  "abilityType": "teleport",
  "queen_target": true,
  "cardNumber": "0013",
  "isMythic": true,
  "rig": {
   "name": "Shadowblade",
   "rigClass": "sprinter",
   "weaponMod": "ram_plow",
   "sourceCar": "GTR",
   "flavor": "low-slung nitro muscle car, blade fenders"
  }
 },
 {
  "name": "Pixel Greyhound",
  "breed": "Greyhound",
  "class": "Zoomie Syndicate",
  "factionId": "zoomie_syndicate",
  "rarity": "Rare",
  "cost": 3,
  "role": "Skirmisher",
  "hp": 700,
  "damage": 95,
  "attack_speed": 1.3,
  "move_speed": 1.4,
  "range": 1,
  "ability": {
   "name": "Dash Loop",
   "description": "Refreshes its dash on a kill",
   "cooldown": 8
  },
  "abilityType": "dash",
  "queen_target": false,
  "cardNumber": "0016",
  "isMythic": false,
  "rig": {
   "name": "Greyhound Rig",
   "rigClass": "sprinter",
   "weaponMod": "ram_plow",
   "sourceCar": "GTR",
   "flavor": ""
  }
 },
 {
  "name": "Circuit Shiba",
  "breed": "Shiba Inu",
  "class": "Zoomie Syndicate",
  "factionId": "zoomie_syndicate",
  "rarity": "Rare",
  "cost": 4,
  "role": "Striker",
  "hp": 1200,
  "damage": 135,
  "attack_speed": 1.05,
  "move_speed": 1.1,
  "range": 1,
  "ability": {
   "name": "Blink Bite",
   "description": "Blinks a short hop on its first attack",
   "cooldown": 10
  },
  "abilityType": "dash",
  "queen_target": false,
  "cardNumber": "0017",
  "isMythic": false,
  "rig": {
   "name": "Shiba Inu Rig",
   "rigClass": "sprinter",
   "weaponMod": "ram_plow",
   "sourceCar": "GTR",
   "flavor": ""
  }
 },
 {
  "name": "Neon Whippet",
  "breed": "Whippet",
  "class": "Zoomie Syndicate",
  "factionId": "zoomie_syndicate",
  "rarity": "Common",
  "cost": 2,
  "role": "Skirmisher",
  "hp": 600,
  "damage": 75,
  "attack_speed": 1.3,
  "move_speed": 1.4,
  "range": 1,
  "ability": {
   "name": "Slipstream",
   "description": "Ignores slows and gains brief evasion",
   "cooldown": 8
  },
  "abilityType": "evasion",
  "queen_target": false,
  "cardNumber": "0021",
  "isMythic": false,
  "rig": {
   "name": "Whippet Rig",
   "rigClass": "sprinter",
   "weaponMod": "ram_plow",
   "sourceCar": "GTR",
   "flavor": ""
  }
 },
 {
  "name": "Turbo Jack",
  "breed": "Jack Russell",
  "class": "Zoomie Syndicate",
  "factionId": "zoomie_syndicate",
  "rarity": "Common",
  "cost": 3,
  "role": "Striker",
  "hp": 1050,
  "damage": 110,
  "attack_speed": 1.05,
  "move_speed": 1.1,
  "range": 1,
  "ability": {
   "name": "Burst Bite",
   "description": "Crits on the first strike after deploy",
   "cooldown": 9
  },
  "abilityType": "crit",
  "queen_target": false,
  "cardNumber": "0022",
  "isMythic": false,
  "rig": {
   "name": "Jack Russell Rig",
   "rigClass": "sprinter",
   "weaponMod": "ram_plow",
   "sourceCar": "GTR",
   "flavor": ""
  }
 },
 {
  "name": "Razor Vizsla",
  "breed": "Vizsla",
  "class": "Zoomie Syndicate",
  "factionId": "zoomie_syndicate",
  "rarity": "Epic",
  "cost": 5,
  "role": "Lancer",
  "hp": 1150,
  "damage": 180,
  "attack_speed": 0.95,
  "move_speed": 0.85,
  "range": 2,
  "ability": {
   "name": "Pierce Rush",
   "description": "Lunges a line that pierces every foe hit",
   "cooldown": 12
  },
  "abilityType": "pierce",
  "queen_target": false,
  "cardNumber": "0014",
  "isMythic": false,
  "rig": {
   "name": "Vizsla Rig",
   "rigClass": "sprinter",
   "weaponMod": "ram_plow",
   "sourceCar": "GTR",
   "flavor": ""
  }
 },
 {
  "name": "Flash Saluki",
  "breed": "Saluki",
  "class": "Zoomie Syndicate",
  "factionId": "zoomie_syndicate",
  "rarity": "Rare",
  "cost": 4,
  "role": "Skirmisher",
  "hp": 750,
  "damage": 110,
  "attack_speed": 1.3,
  "move_speed": 1.4,
  "range": 1,
  "ability": {
   "name": "Sidecut",
   "description": "Dashes lane to lane to flank the backline",
   "cooldown": 10
  },
  "abilityType": "dash",
  "queen_target": false,
  "cardNumber": "0018",
  "isMythic": false,
  "rig": {
   "name": "Saluki Rig",
   "rigClass": "sprinter",
   "weaponMod": "ram_plow",
   "sourceCar": "GTR",
   "flavor": ""
  }
 },
 {
  "name": "Bolt Corgi",
  "breed": "Corgi",
  "class": "Zoomie Syndicate",
  "factionId": "zoomie_syndicate",
  "rarity": "Rare",
  "cost": 4,
  "role": "Spawner",
  "hp": 750,
  "damage": 55,
  "attack_speed": 0.9,
  "move_speed": 0.85,
  "range": 2,
  "ability": {
   "name": "Spark Pups",
   "description": "Spawns three fast mini zoomers",
   "cooldown": 12
  },
  "abilityType": "spawn",
  "queen_target": false,
  "cardNumber": "0019",
  "isMythic": false,
  "rig": {
   "name": "Corgi Rig",
   "rigClass": "sprinter",
   "weaponMod": "ram_plow",
   "sourceCar": "GTR",
   "flavor": ""
  }
 },
 {
  "name": "Glitch Basenji",
  "breed": "Basenji",
  "class": "Zoomie Syndicate",
  "factionId": "zoomie_syndicate",
  "rarity": "Rare",
  "cost": 3,
  "role": "Hacker",
  "hp": 700,
  "damage": 70,
  "attack_speed": 1.0,
  "move_speed": 0.85,
  "range": 3,
  "ability": {
   "name": "Signal Scramble",
   "description": "Silences a target ability briefly",
   "cooldown": 10
  },
  "abilityType": "silence",
  "queen_target": false,
  "cardNumber": "0020",
  "isMythic": false,
  "rig": {
   "name": "Basenji Rig",
   "rigClass": "sprinter",
   "weaponMod": "ram_plow",
   "sourceCar": "GTR",
   "flavor": ""
  }
 },
 {
  "name": "Aero Malinois",
  "breed": "Malinois",
  "class": "Zoomie Syndicate",
  "factionId": "zoomie_syndicate",
  "rarity": "Epic",
  "cost": 6,
  "role": "Striker",
  "hp": 1500,
  "damage": 175,
  "attack_speed": 1.05,
  "move_speed": 1.1,
  "range": 1,
  "ability": {
   "name": "Twin Strike",
   "description": "Strikes twice in one attack swing",
   "cooldown": 12
  },
  "abilityType": "double_hit",
  "queen_target": false,
  "cardNumber": "0015",
  "isMythic": false,
  "rig": {
   "name": "Malinois Rig",
   "rigClass": "sprinter",
   "weaponMod": "ram_plow",
   "sourceCar": "GTR",
   "flavor": ""
  }
 },
 {
  "name": "Drift Sheltie",
  "breed": "Sheltie",
  "class": "Zoomie Syndicate",
  "factionId": "zoomie_syndicate",
  "rarity": "Common",
  "cost": 2,
  "role": "Support",
  "hp": 700,
  "damage": 40,
  "attack_speed": 0.9,
  "move_speed": 1.1,
  "range": 3,
  "ability": {
   "name": "Tag Boost",
   "description": "Boosts the move speed of nearby allies",
   "cooldown": 10
  },
  "abilityType": "buff",
  "queen_target": false,
  "cardNumber": "0023",
  "isMythic": false,
  "rig": {
   "name": "Sheltie Rig",
   "rigClass": "sprinter",
   "weaponMod": "ram_plow",
   "sourceCar": "GTR",
   "flavor": ""
  }
 },
 {
  "name": "Byte Beagle",
  "breed": "Beagle",
  "class": "Zoomie Syndicate",
  "factionId": "zoomie_syndicate",
  "rarity": "Common",
  "cost": 3,
  "role": "Blaster",
  "hp": 550,
  "damage": 80,
  "attack_speed": 1.1,
  "move_speed": 0.85,
  "range": 4,
  "ability": {
   "name": "Tracer Round",
   "description": "Long shots that pierce shields; can hit Queen",
   "cooldown": 10
  },
  "abilityType": "pierce",
  "queen_target": true,
  "cardNumber": "0024",
  "isMythic": false,
  "rig": {
   "name": "Beagle Rig",
   "rigClass": "sprinter",
   "weaponMod": "ram_plow",
   "sourceCar": "GTR",
   "flavor": ""
  }
 },
 {
  "name": "Rosco",
  "breed": "Australian Cattle Dog",
  "class": "Leashbreak Tactix",
  "factionId": "leashbreak_tactix",
  "rarity": "Mythic",
  "cost": 10,
  "role": "Controller",
  "hp": 1600,
  "damage": 170,
  "attack_speed": 0.95,
  "move_speed": 0.85,
  "range": 3,
  "ability": {
   "name": "Leashbreak",
   "description": "Disables a tower fire; can strike the Queen",
   "cooldown": 18
  },
  "abilityType": "disable_tower",
  "queen_target": true,
  "cardNumber": "0025",
  "isMythic": true,
  "rig": {
   "name": "The Jammer",
   "rigClass": "tech_ops",
   "weaponMod": "emp_array",
   "sourceCar": "Van",
   "flavor": "antenna-bristled tech van, EMP dish"
  }
 },
 {
  "name": "Synth Collie",
  "breed": "Border Collie",
  "class": "Leashbreak Tactix",
  "factionId": "leashbreak_tactix",
  "rarity": "Epic",
  "cost": 5,
  "role": "Hacker",
  "hp": 900,
  "damage": 90,
  "attack_speed": 1.0,
  "move_speed": 0.85,
  "range": 3,
  "ability": {
   "name": "Hack Jam",
   "description": "Jams a tower so it cannot fire",
   "cooldown": 12
  },
  "abilityType": "disable_tower",
  "queen_target": false,
  "cardNumber": "0026",
  "isMythic": false,
  "rig": {
   "name": "Border Collie Rig",
   "rigClass": "tech_ops",
   "weaponMod": "emp_array",
   "sourceCar": "Van",
   "flavor": ""
  }
 },
 {
  "name": "Holo Husky",
  "breed": "Husky",
  "class": "Leashbreak Tactix",
  "factionId": "leashbreak_tactix",
  "rarity": "Rare",
  "cost": 5,
  "role": "Support",
  "hp": 950,
  "damage": 60,
  "attack_speed": 0.9,
  "move_speed": 0.85,
  "range": 3,
  "ability": {
   "name": "Heal Beacon",
   "description": "Pulsing area heal for the pack",
   "cooldown": 12
  },
  "abilityType": "heal",
  "queen_target": false,
  "cardNumber": "0029",
  "isMythic": false,
  "rig": {
   "name": "Husky Rig",
   "rigClass": "tech_ops",
   "weaponMod": "emp_array",
   "sourceCar": "Van",
   "flavor": ""
  }
 },
 {
  "name": "Chill Samoyed",
  "breed": "Samoyed",
  "class": "Leashbreak Tactix",
  "factionId": "leashbreak_tactix",
  "rarity": "Rare",
  "cost": 4,
  "role": "Support",
  "hp": 900,
  "damage": 55,
  "attack_speed": 0.9,
  "move_speed": 0.85,
  "range": 3,
  "ability": {
   "name": "Frost Bark",
   "description": "Wide frost cone slows everything caught",
   "cooldown": 10
  },
  "abilityType": "slow",
  "queen_target": false,
  "cardNumber": "0030",
  "isMythic": false,
  "rig": {
   "name": "Samoyed Rig",
   "rigClass": "tech_ops",
   "weaponMod": "emp_array",
   "sourceCar": "Van",
   "flavor": ""
  }
 },
 {
  "name": "Prism Poodle",
  "breed": "Poodle",
  "class": "Leashbreak Tactix",
  "factionId": "leashbreak_tactix",
  "rarity": "Rare",
  "cost": 4,
  "role": "Controller",
  "hp": 850,
  "damage": 85,
  "attack_speed": 0.95,
  "move_speed": 0.85,
  "range": 3,
  "ability": {
   "name": "Shatter",
   "description": "Strips enemy shields, then wards an ally",
   "cooldown": 10
  },
  "abilityType": "shield",
  "queen_target": false,
  "cardNumber": "0031",
  "isMythic": false,
  "rig": {
   "name": "Poodle Rig",
   "rigClass": "tech_ops",
   "weaponMod": "emp_array",
   "sourceCar": "Van",
   "flavor": ""
  }
 },
 {
  "name": "Echo Dalmatian",
  "breed": "Dalmatian",
  "class": "Leashbreak Tactix",
  "factionId": "leashbreak_tactix",
  "rarity": "Common",
  "cost": 3,
  "role": "Controller",
  "hp": 750,
  "damage": 70,
  "attack_speed": 0.95,
  "move_speed": 0.85,
  "range": 3,
  "ability": {
   "name": "Echo Howl",
   "description": "Rolling area slow down the lane",
   "cooldown": 9
  },
  "abilityType": "slow",
  "queen_target": false,
  "cardNumber": "0034",
  "isMythic": false,
  "rig": {
   "name": "Dalmatian Rig",
   "rigClass": "tech_ops",
   "weaponMod": "emp_array",
   "sourceCar": "Van",
   "flavor": ""
  }
 },
 {
  "name": "Static Sheba Inu",
  "breed": "Shiba Inu",
  "class": "Leashbreak Tactix",
  "factionId": "leashbreak_tactix",
  "rarity": "Common",
  "cost": 2,
  "role": "Hacker",
  "hp": 600,
  "damage": 55,
  "attack_speed": 1.0,
  "move_speed": 0.85,
  "range": 3,
  "ability": {
   "name": "Ping",
   "description": "Quick silence on the first target",
   "cooldown": 8
  },
  "abilityType": "silence",
  "queen_target": false,
  "cardNumber": "0035",
  "isMythic": false,
  "rig": {
   "name": "Shiba Inu Rig",
   "rigClass": "tech_ops",
   "weaponMod": "emp_array",
   "sourceCar": "Van",
   "flavor": ""
  }
 },
 {
  "name": "Vibe Shih Tzu",
  "breed": "Shih Tzu",
  "class": "Leashbreak Tactix",
  "factionId": "leashbreak_tactix",
  "rarity": "Common",
  "cost": 2,
  "role": "Support",
  "hp": 700,
  "damage": 40,
  "attack_speed": 0.9,
  "move_speed": 0.85,
  "range": 3,
  "ability": {
   "name": "Soothe",
   "description": "Small steady heal to a wounded ally",
   "cooldown": 8
  },
  "abilityType": "heal",
  "queen_target": false,
  "cardNumber": "0036",
  "isMythic": false,
  "rig": {
   "name": "Shih Tzu Rig",
   "rigClass": "tech_ops",
   "weaponMod": "emp_array",
   "sourceCar": "Van",
   "flavor": ""
  }
 },
 {
  "name": "Noir Setter",
  "breed": "Setter",
  "class": "Leashbreak Tactix",
  "factionId": "leashbreak_tactix",
  "rarity": "Epic",
  "cost": 6,
  "role": "Controller",
  "hp": 1100,
  "damage": 110,
  "attack_speed": 0.95,
  "move_speed": 0.85,
  "range": 3,
  "ability": {
   "name": "Blackout",
   "description": "Blinds ranged foes so their shots miss",
   "cooldown": 12
  },
  "abilityType": "blind",
  "queen_target": false,
  "cardNumber": "0027",
  "isMythic": false,
  "rig": {
   "name": "Setter Rig",
   "rigClass": "tech_ops",
   "weaponMod": "emp_array",
   "sourceCar": "Van",
   "flavor": ""
  }
 },
 {
  "name": "Signal Pointer",
  "breed": "Pointer",
  "class": "Leashbreak Tactix",
  "factionId": "leashbreak_tactix",
  "rarity": "Rare",
  "cost": 4,
  "role": "Lancer",
  "hp": 1000,
  "damage": 150,
  "attack_speed": 0.95,
  "move_speed": 0.85,
  "range": 3,
  "ability": {
   "name": "Tag Shot",
   "description": "Tags a target, revealing stealth and weakening it",
   "cooldown": 10
  },
  "abilityType": "reveal",
  "queen_target": false,
  "cardNumber": "0032",
  "isMythic": false,
  "rig": {
   "name": "Pointer Rig",
   "rigClass": "tech_ops",
   "weaponMod": "emp_array",
   "sourceCar": "Van",
   "flavor": ""
  }
 },
 {
  "name": "Ghost Spaniel",
  "breed": "Spaniel",
  "class": "Leashbreak Tactix",
  "factionId": "leashbreak_tactix",
  "rarity": "Rare",
  "cost": 3,
  "role": "Skirmisher",
  "hp": 700,
  "damage": 95,
  "attack_speed": 1.3,
  "move_speed": 1.1,
  "range": 2,
  "ability": {
   "name": "Phase",
   "description": "Phases out for a brief untargetable window",
   "cooldown": 10
  },
  "abilityType": "invuln",
  "queen_target": false,
  "cardNumber": "0033",
  "isMythic": false,
  "rig": {
   "name": "Spaniel Rig",
   "rigClass": "tech_ops",
   "weaponMod": "emp_array",
   "sourceCar": "Van",
   "flavor": ""
  }
 },
 {
  "name": "Pulse Border Collie",
  "breed": "Border Collie",
  "class": "Leashbreak Tactix",
  "factionId": "leashbreak_tactix",
  "rarity": "Epic",
  "cost": 5,
  "role": "Support",
  "hp": 1050,
  "damage": 65,
  "attack_speed": 0.9,
  "move_speed": 0.85,
  "range": 3,
  "ability": {
   "name": "Barrier Ring",
   "description": "Drops an area shield over the front line",
   "cooldown": 12
  },
  "abilityType": "shield",
  "queen_target": false,
  "cardNumber": "0028",
  "isMythic": false,
  "rig": {
   "name": "Border Collie Rig",
   "rigClass": "tech_ops",
   "weaponMod": "emp_array",
   "sourceCar": "Van",
   "flavor": ""
  }
 },
 {
  "name": "Crown Foxhound",
  "breed": "Foxhound",
  "class": "K9 Circuitry",
  "factionId": "k9_circuitry",
  "rarity": "Mythic",
  "cost": 11,
  "role": "Assassin",
  "hp": 1900,
  "damage": 230,
  "attack_speed": 1.1,
  "move_speed": 1.1,
  "range": 1,
  "ability": {
   "name": "Royal Hunt",
   "description": "Shreds structures; can strike the Queen",
   "cooldown": 18
  },
  "abilityType": "turret_break",
  "queen_target": true,
  "cardNumber": "0037",
  "isMythic": true,
  "rig": {
   "name": "Railhound",
   "rigClass": "turret_util",
   "weaponMod": "incendiary",
   "sourceCar": "Monster Truck",
   "flavor": "turret-platform rig, rail-cannon mount"
  }
 },
 {
  "name": "Laser Beagle",
  "breed": "Beagle",
  "class": "K9 Circuitry",
  "factionId": "k9_circuitry",
  "rarity": "Rare",
  "cost": 4,
  "role": "Structure",
  "hp": 1050,
  "damage": 85,
  "attack_speed": 1.0,
  "move_speed": 0.0,
  "range": 5,
  "ability": {
   "name": "Overheat",
   "description": "Static turret that ramps fire the longer it shoots",
   "cooldown": 12
  },
  "abilityType": "ramp",
  "queen_target": false,
  "cardNumber": "0040",
  "isMythic": false,
  "rig": {
   "name": "Beagle Rig",
   "rigClass": "turret_util",
   "weaponMod": "incendiary",
   "sourceCar": "Monster Truck",
   "flavor": ""
  }
 },
 {
  "name": "Neon Dachshund",
  "breed": "Dachshund",
  "class": "K9 Circuitry",
  "factionId": "k9_circuitry",
  "rarity": "Common",
  "cost": 3,
  "role": "Spawner",
  "hp": 650,
  "damage": 45,
  "attack_speed": 0.9,
  "move_speed": 0.85,
  "range": 2,
  "ability": {
   "name": "Tunnel Drones",
   "description": "Tunnels up two attack drones",
   "cooldown": 10
  },
  "abilityType": "spawn",
  "queen_target": false,
  "cardNumber": "0045",
  "isMythic": false,
  "rig": {
   "name": "Dachshund Rig",
   "rigClass": "turret_util",
   "weaponMod": "incendiary",
   "sourceCar": "Monster Truck",
   "flavor": ""
  }
 },
 {
  "name": "Volt Corgi",
  "breed": "Corgi",
  "class": "K9 Circuitry",
  "factionId": "k9_circuitry",
  "rarity": "Rare",
  "cost": 4,
  "role": "Spawner",
  "hp": 750,
  "damage": 55,
  "attack_speed": 0.9,
  "move_speed": 0.85,
  "range": 2,
  "ability": {
   "name": "Spark Pups",
   "description": "Spawns three spark drones",
   "cooldown": 12
  },
  "abilityType": "spawn",
  "queen_target": false,
  "cardNumber": "0041",
  "isMythic": false,
  "rig": {
   "name": "Corgi Rig",
   "rigClass": "turret_util",
   "weaponMod": "incendiary",
   "sourceCar": "Monster Truck",
   "flavor": ""
  }
 },
 {
  "name": "Grid Schnauzer",
  "breed": "Schnauzer",
  "class": "K9 Circuitry",
  "factionId": "k9_circuitry",
  "rarity": "Rare",
  "cost": 5,
  "role": "Structure",
  "hp": 1150,
  "damage": 95,
  "attack_speed": 1.0,
  "move_speed": 0.0,
  "range": 4,
  "ability": {
   "name": "Grid Lock",
   "description": "Turret field that slows attackers in range",
   "cooldown": 12
  },
  "abilityType": "slow",
  "queen_target": false,
  "cardNumber": "0042",
  "isMythic": false,
  "rig": {
   "name": "Schnauzer Rig",
   "rigClass": "turret_util",
   "weaponMod": "incendiary",
   "sourceCar": "Monster Truck",
   "flavor": ""
  }
 },
 {
  "name": "Flux Pomeranian",
  "breed": "Pomeranian",
  "class": "K9 Circuitry",
  "factionId": "k9_circuitry",
  "rarity": "Common",
  "cost": 2,
  "role": "Support",
  "hp": 700,
  "damage": 40,
  "attack_speed": 0.9,
  "move_speed": 0.85,
  "range": 3,
  "ability": {
   "name": "Battery",
   "description": "Boosts the fire rate of nearby turrets",
   "cooldown": 8
  },
  "abilityType": "buff",
  "queen_target": false,
  "cardNumber": "0046",
  "isMythic": false,
  "rig": {
   "name": "Pomeranian Rig",
   "rigClass": "turret_util",
   "weaponMod": "incendiary",
   "sourceCar": "Monster Truck",
   "flavor": ""
  }
 },
 {
  "name": "Rail Terrier",
  "breed": "Terrier",
  "class": "K9 Circuitry",
  "factionId": "k9_circuitry",
  "rarity": "Common",
  "cost": 3,
  "role": "Blaster",
  "hp": 550,
  "damage": 80,
  "attack_speed": 1.1,
  "move_speed": 0.85,
  "range": 4,
  "ability": {
   "name": "Rail Shot",
   "description": "Long rail shots deal bonus vs structures",
   "cooldown": 9
  },
  "abilityType": "turret_break",
  "queen_target": false,
  "cardNumber": "0047",
  "isMythic": false,
  "rig": {
   "name": "Terrier Rig",
   "rigClass": "turret_util",
   "weaponMod": "incendiary",
   "sourceCar": "Monster Truck",
   "flavor": ""
  }
 },
 {
  "name": "Circuit Retriever",
  "breed": "Retriever",
  "class": "K9 Circuitry",
  "factionId": "k9_circuitry",
  "rarity": "Epic",
  "cost": 6,
  "role": "Support",
  "hp": 1100,
  "damage": 70,
  "attack_speed": 0.9,
  "move_speed": 0.85,
  "range": 3,
  "ability": {
   "name": "Drone Swarm",
   "description": "Releases five swarm drones",
   "cooldown": 12
  },
  "abilityType": "spawn",
  "queen_target": false,
  "cardNumber": "0038",
  "isMythic": false,
  "rig": {
   "name": "Retriever Rig",
   "rigClass": "turret_util",
   "weaponMod": "incendiary",
   "sourceCar": "Monster Truck",
   "flavor": ""
  }
 },
 {
  "name": "Chrome Airedale",
  "breed": "Airedale",
  "class": "K9 Circuitry",
  "factionId": "k9_circuitry",
  "rarity": "Rare",
  "cost": 5,
  "role": "Lancer",
  "hp": 1050,
  "damage": 165,
  "attack_speed": 0.95,
  "move_speed": 0.85,
  "range": 3,
  "ability": {
   "name": "Arc Shot",
   "description": "Arc that chains to three targets",
   "cooldown": 10
  },
  "abilityType": "chain",
  "queen_target": false,
  "cardNumber": "0043",
  "isMythic": false,
  "rig": {
   "name": "Airedale Rig",
   "rigClass": "turret_util",
   "weaponMod": "incendiary",
   "sourceCar": "Monster Truck",
   "flavor": ""
  }
 },
 {
  "name": "Beacon Basset",
  "breed": "Basset",
  "class": "K9 Circuitry",
  "factionId": "k9_circuitry",
  "rarity": "Rare",
  "cost": 4,
  "role": "Support",
  "hp": 900,
  "damage": 55,
  "attack_speed": 0.9,
  "move_speed": 0.85,
  "range": 3,
  "ability": {
   "name": "Beacon",
   "description": "Reveals stealth and marks foes for the pack",
   "cooldown": 10
  },
  "abilityType": "reveal",
  "queen_target": false,
  "cardNumber": "0044",
  "isMythic": false,
  "rig": {
   "name": "Basset Rig",
   "rigClass": "turret_util",
   "weaponMod": "incendiary",
   "sourceCar": "Monster Truck",
   "flavor": ""
  }
 },
 {
  "name": "Pixel Pug",
  "breed": "Pug",
  "class": "K9 Circuitry",
  "factionId": "k9_circuitry",
  "rarity": "Common",
  "cost": 2,
  "role": "Spawner",
  "hp": 550,
  "damage": 40,
  "attack_speed": 0.9,
  "move_speed": 0.85,
  "range": 2,
  "ability": {
   "name": "Mini Pup",
   "description": "Deploys a single guard drone",
   "cooldown": 8
  },
  "abilityType": "spawn",
  "queen_target": false,
  "cardNumber": "0048",
  "isMythic": false,
  "rig": {
   "name": "Pug Rig",
   "rigClass": "turret_util",
   "weaponMod": "incendiary",
   "sourceCar": "Monster Truck",
   "flavor": ""
  }
 },
 {
  "name": "Nova Shepherd",
  "breed": "German Shepherd",
  "class": "K9 Circuitry",
  "factionId": "k9_circuitry",
  "rarity": "Epic",
  "cost": 7,
  "role": "Structure",
  "hp": 1450,
  "damage": 125,
  "attack_speed": 1.0,
  "move_speed": 0.0,
  "range": 4,
  "ability": {
   "name": "Overclock",
   "description": "Heavy static turret with a burst fire window",
   "cooldown": 14
  },
  "abilityType": "ramp",
  "queen_target": false,
  "cardNumber": "0039",
  "isMythic": false,
  "rig": {
   "name": "German Shepherd Rig",
   "rigClass": "turret_util",
   "weaponMod": "incendiary",
   "sourceCar": "Monster Truck",
   "flavor": ""
  }
 },
{
 "name": "Cinderblock",
 "breed": "Boxer",
 "class": "Boneguard Crew",
 "factionId": "boneguard_crew",
 "rarity": "Legendary",
 "cost": 7,
 "role": "Striker",
 "hp": 1920,
 "damage": 149,
 "attack_speed": 0.95,
 "move_speed": 0.75,
 "range": 1,
 "ability": {
  "name": "Haymaker",
  "description": "First hit stuns the target for 1s",
  "cooldown": 14
 },
 "abilityType": "stun",
 "queen_target": false,
 "cardNumber": "0049",
 "isMythic": false,
 "rig": {
  "name": "Cinderblock Rig",
  "rigClass": "bruiser",
  "weaponMod": "ram_plow",
  "sourceCar": "Muscle Car",
  "flavor": "bunkered Armored bruiser rig -- ram plow, plate armor, slow and unstoppable"
 },
 "variant": "HEAVY",
 "family": "Balboa",
 "desc": "Cinderblock -- the bunkered [HEAVY] build of Balboa's line (Striker, Boneguard). Up-armored: +28% HP and heavier plating soak hits, trading bite and speed for a slower, near-unkillable frame. Same job: first hit stuns the target for 1s."
},
{
 "name": "Knuckles",
 "breed": "Boxer",
 "class": "Boneguard Crew",
 "factionId": "boneguard_crew",
 "rarity": "Rare",
 "cost": 5,
 "role": "Striker",
 "hp": 1080,
 "damage": 185,
 "attack_speed": 1.18,
 "move_speed": 0.94,
 "range": 1,
 "ability": {
  "name": "Haymaker",
  "description": "First hit stuns the target for 1s",
  "cooldown": 10
 },
 "abilityType": "stun",
 "queen_target": false,
 "cardNumber": "0050",
 "isMythic": false,
 "rig": {
  "name": "Knuckles Rig",
  "rigClass": "bruiser",
  "weaponMod": "ram_plow",
  "sourceCar": "Muscle Car",
  "flavor": "stripped chop-shop Armored bruiser rig -- ram plow, plate armor, slow and unstoppable"
 },
 "variant": "STREET",
 "family": "Balboa",
 "desc": "Knuckles -- the stripped [STREET] build of Balboa's line (Striker, Boneguard). Glass-cannon: +25% damage and quicker, panels torn off for the kill, but folds to one clean shot. Same job: first hit stuns the target for 1s."
},
{
 "name": "Tombstone",
 "breed": "Rottweiler",
 "class": "Boneguard Crew",
 "factionId": "boneguard_crew",
 "rarity": "Legendary",
 "cost": 10,
 "role": "Vanguard",
 "hp": 2850,
 "damage": 132,
 "attack_speed": 0.63,
 "move_speed": 0.48,
 "range": 1,
 "ability": {
  "name": "Overclock Rage",
  "description": "Below 40% HP its bite damage spikes",
  "cooldown": 16
 },
 "abilityType": "crit",
 "queen_target": false,
 "cardNumber": "0051",
 "isMythic": false,
 "rig": {
  "name": "Tombstone Rig",
  "rigClass": "bruiser",
  "weaponMod": "ram_plow",
  "sourceCar": "Muscle Car",
  "flavor": "bunkered Armored bruiser rig -- ram plow, plate armor, slow and unstoppable"
 },
 "variant": "HEAVY",
 "family": "Iron Rottweiler",
 "desc": "Tombstone -- the bunkered [HEAVY] build of Iron Rottweiler's line (Vanguard, Boneguard). Up-armored: +28% HP and heavier plating soak hits, trading bite and speed for a slower, near-unkillable frame. Same job: below 40% HP its bite damage spikes."
},
{
 "name": "Razorgums",
 "breed": "Rottweiler",
 "class": "Boneguard Crew",
 "factionId": "boneguard_crew",
 "rarity": "Rare",
 "cost": 8,
 "role": "Vanguard",
 "hp": 2052,
 "damage": 194,
 "attack_speed": 0.78,
 "move_speed": 0.61,
 "range": 1,
 "ability": {
  "name": "Overclock Rage",
  "description": "Below 40% HP its bite damage spikes",
  "cooldown": 12
 },
 "abilityType": "crit",
 "queen_target": false,
 "cardNumber": "0052",
 "isMythic": false,
 "rig": {
  "name": "Razorgums Rig",
  "rigClass": "bruiser",
  "weaponMod": "ram_plow",
  "sourceCar": "Muscle Car",
  "flavor": "stripped chop-shop Armored bruiser rig -- ram plow, plate armor, slow and unstoppable"
 },
 "variant": "STREET",
 "family": "Iron Rottweiler",
 "desc": "Razorgums -- the stripped [STREET] build of Iron Rottweiler's line (Vanguard, Boneguard). Glass-cannon: +25% damage and quicker, panels torn off for the kill, but folds to one clean shot. Same job: below 40% HP its bite damage spikes."
},
{
 "name": "Anvil",
 "breed": "St. Bernard",
 "class": "Boneguard Crew",
 "factionId": "boneguard_crew",
 "rarity": "Epic",
 "cost": 9,
 "role": "Vanguard",
 "hp": 2850,
 "damage": 115,
 "attack_speed": 0.63,
 "move_speed": 0.48,
 "range": 1,
 "ability": {
  "name": "Bodywall",
  "description": "Bodywall aura soaks nearby damage for the pack",
  "cooldown": 16
 },
 "abilityType": "dr",
 "queen_target": false,
 "cardNumber": "0053",
 "isMythic": false,
 "rig": {
  "name": "Anvil Rig",
  "rigClass": "bruiser",
  "weaponMod": "ram_plow",
  "sourceCar": "Muscle Car",
  "flavor": "bunkered Armored bruiser rig -- ram plow, plate armor, slow and unstoppable"
 },
 "variant": "HEAVY",
 "family": "Granite Saint",
 "desc": "Anvil -- the bunkered [HEAVY] build of Granite Saint's line (Vanguard, Boneguard). Up-armored: +28% HP and heavier plating soak hits, trading bite and speed for a slower, near-unkillable frame. Same job: bodywall aura soaks nearby damage for the pack."
},
{
 "name": "Hatchet",
 "breed": "St. Bernard",
 "class": "Boneguard Crew",
 "factionId": "boneguard_crew",
 "rarity": "Common",
 "cost": 7,
 "role": "Vanguard",
 "hp": 1908,
 "damage": 169,
 "attack_speed": 0.78,
 "move_speed": 0.61,
 "range": 1,
 "ability": {
  "name": "Bodywall",
  "description": "Bodywall aura soaks nearby damage for the pack",
  "cooldown": 12
 },
 "abilityType": "dr",
 "queen_target": false,
 "cardNumber": "0054",
 "isMythic": false,
 "rig": {
  "name": "Hatchet Rig",
  "rigClass": "bruiser",
  "weaponMod": "ram_plow",
  "sourceCar": "Muscle Car",
  "flavor": "stripped chop-shop Armored bruiser rig -- ram plow, plate armor, slow and unstoppable"
 },
 "variant": "STREET",
 "family": "Granite Saint",
 "desc": "Hatchet -- the stripped [STREET] build of Granite Saint's line (Vanguard, Boneguard). Glass-cannon: +25% damage and quicker, panels torn off for the kill, but folds to one clean shot. Same job: bodywall aura soaks nearby damage for the pack."
},
{
 "name": "Bonecrusher",
 "breed": "Bulldog",
 "class": "Boneguard Crew",
 "factionId": "boneguard_crew",
 "rarity": "Epic",
 "cost": 6,
 "role": "Striker",
 "hp": 1664,
 "damage": 128,
 "attack_speed": 0.95,
 "move_speed": 0.75,
 "range": 1,
 "ability": {
  "name": "Brawler",
  "description": "Powers up its own bite the longer it brawls",
  "cooldown": 12
 },
 "abilityType": "buff",
 "queen_target": false,
 "cardNumber": "0055",
 "isMythic": false,
 "rig": {
  "name": "Bonecrusher Rig",
  "rigClass": "bruiser",
  "weaponMod": "ram_plow",
  "sourceCar": "Muscle Car",
  "flavor": "bunkered Armored bruiser rig -- ram plow, plate armor, slow and unstoppable"
 },
 "variant": "HEAVY",
 "family": "Grit Bulldog",
 "desc": "Bonecrusher -- the bunkered [HEAVY] build of Grit Bulldog's line (Striker, Boneguard). Up-armored: +28% HP and heavier plating soak hits, trading bite and speed for a slower, near-unkillable frame. Same job: powers up its own bite the longer it brawls."
},
{
 "name": "Switch",
 "breed": "Bulldog",
 "class": "Boneguard Crew",
 "factionId": "boneguard_crew",
 "rarity": "Common",
 "cost": 4,
 "role": "Striker",
 "hp": 936,
 "damage": 188,
 "attack_speed": 1.18,
 "move_speed": 0.94,
 "range": 1,
 "ability": {
  "name": "Brawler",
  "description": "Powers up its own bite the longer it brawls",
  "cooldown": 8
 },
 "abilityType": "buff",
 "queen_target": false,
 "cardNumber": "0056",
 "isMythic": false,
 "rig": {
  "name": "Switch Rig",
  "rigClass": "bruiser",
  "weaponMod": "ram_plow",
  "sourceCar": "Muscle Car",
  "flavor": "stripped chop-shop Armored bruiser rig -- ram plow, plate armor, slow and unstoppable"
 },
 "variant": "STREET",
 "family": "Grit Bulldog",
 "desc": "Switch -- the stripped [STREET] build of Grit Bulldog's line (Striker, Boneguard). Glass-cannon: +25% damage and quicker, panels torn off for the kill, but folds to one clean shot. Same job: powers up its own bite the longer it brawls."
},
{
 "name": "Warhorse",
 "breed": "Akita",
 "class": "Boneguard Crew",
 "factionId": "boneguard_crew",
 "rarity": "Epic",
 "cost": 7,
 "role": "Lancer",
 "hp": 1408,
 "damage": 153,
 "attack_speed": 0.85,
 "move_speed": 0.75,
 "range": 2,
 "ability": {
  "name": "Shock Push",
  "description": "Knockback cone shoves a melee line back",
  "cooldown": 14
 },
 "abilityType": "knockback",
 "queen_target": false,
 "cardNumber": "0057",
 "isMythic": false,
 "rig": {
  "name": "Warhorse Rig",
  "rigClass": "bruiser",
  "weaponMod": "ram_plow",
  "sourceCar": "Muscle Car",
  "flavor": "bunkered Armored bruiser rig -- ram plow, plate armor, slow and unstoppable"
 },
 "variant": "HEAVY",
 "family": "Alloy Akita",
 "desc": "Warhorse -- the bunkered [HEAVY] build of Alloy Akita's line (Lancer, Boneguard). Up-armored: +28% HP and heavier plating soak hits, trading bite and speed for a slower, near-unkillable frame. Same job: knockback cone shoves a melee line back."
},
{
 "name": "Lugnut",
 "breed": "Akita",
 "class": "Boneguard Crew",
 "factionId": "boneguard_crew",
 "rarity": "Common",
 "cost": 5,
 "role": "Lancer",
 "hp": 792,
 "damage": 225,
 "attack_speed": 1.06,
 "move_speed": 0.94,
 "range": 2,
 "ability": {
  "name": "Shock Push",
  "description": "Knockback cone shoves a melee line back",
  "cooldown": 10
 },
 "abilityType": "knockback",
 "queen_target": false,
 "cardNumber": "0058",
 "isMythic": false,
 "rig": {
  "name": "Lugnut Rig",
  "rigClass": "bruiser",
  "weaponMod": "ram_plow",
  "sourceCar": "Muscle Car",
  "flavor": "stripped chop-shop Armored bruiser rig -- ram plow, plate armor, slow and unstoppable"
 },
 "variant": "STREET",
 "family": "Alloy Akita",
 "desc": "Lugnut -- the stripped [STREET] build of Alloy Akita's line (Lancer, Boneguard). Glass-cannon: +25% damage and quicker, panels torn off for the kill, but folds to one clean shot. Same job: knockback cone shoves a melee line back."
},
{
 "name": "Ironhide",
 "breed": "Newfoundland",
 "class": "Boneguard Crew",
 "factionId": "boneguard_crew",
 "rarity": "Epic",
 "cost": 8,
 "role": "Support",
 "hp": 1408,
 "damage": 60,
 "attack_speed": 0.81,
 "move_speed": 0.75,
 "range": 2,
 "ability": {
  "name": "Fortify",
  "description": "Raises max HP of allies in an aura",
  "cooldown": 18
 },
 "abilityType": "buff",
 "queen_target": false,
 "cardNumber": "0059",
 "isMythic": false,
 "rig": {
  "name": "Ironhide Rig",
  "rigClass": "bruiser",
  "weaponMod": "ram_plow",
  "sourceCar": "Muscle Car",
  "flavor": "bunkered Armored bruiser rig -- ram plow, plate armor, slow and unstoppable"
 },
 "variant": "HEAVY",
 "family": "Warden Newfie",
 "desc": "Ironhide -- the bunkered [HEAVY] build of Warden Newfie's line (Support, Boneguard). Up-armored: +28% HP and heavier plating soak hits, trading bite and speed for a slower, near-unkillable frame. Same job: raises max HP of allies in an aura."
},
{
 "name": "Snaggle",
 "breed": "Newfoundland",
 "class": "Boneguard Crew",
 "factionId": "boneguard_crew",
 "rarity": "Common",
 "cost": 6,
 "role": "Support",
 "hp": 792,
 "damage": 88,
 "attack_speed": 1.01,
 "move_speed": 0.94,
 "range": 2,
 "ability": {
  "name": "Fortify",
  "description": "Raises max HP of allies in an aura",
  "cooldown": 14
 },
 "abilityType": "buff",
 "queen_target": false,
 "cardNumber": "0060",
 "isMythic": false,
 "rig": {
  "name": "Snaggle Rig",
  "rigClass": "bruiser",
  "weaponMod": "ram_plow",
  "sourceCar": "Muscle Car",
  "flavor": "stripped chop-shop Armored bruiser rig -- ram plow, plate armor, slow and unstoppable"
 },
 "variant": "STREET",
 "family": "Warden Newfie",
 "desc": "Snaggle -- the stripped [STREET] build of Warden Newfie's line (Support, Boneguard). Glass-cannon: +25% damage and quicker, panels torn off for the kill, but folds to one clean shot. Same job: raises max HP of allies in an aura."
},
{
 "name": "Slab",
 "breed": "Cane Corso",
 "class": "Boneguard Crew",
 "factionId": "boneguard_crew",
 "rarity": "Epic",
 "cost": 9,
 "role": "Vanguard",
 "hp": 2850,
 "damage": 115,
 "attack_speed": 0.63,
 "move_speed": 0.48,
 "range": 1,
 "ability": {
  "name": "Grav Pull",
  "description": "Pulses a shove that scatters the nearest foes",
  "cooldown": 16
 },
 "abilityType": "knockback",
 "queen_target": false,
 "cardNumber": "0061",
 "isMythic": false,
 "rig": {
  "name": "Slab Rig",
  "rigClass": "bruiser",
  "weaponMod": "ram_plow",
  "sourceCar": "Muscle Car",
  "flavor": "bunkered Armored bruiser rig -- ram plow, plate armor, slow and unstoppable"
 },
 "variant": "HEAVY",
 "family": "Rust Cane Corso",
 "desc": "Slab -- the bunkered [HEAVY] build of Rust Cane Corso's line (Vanguard, Boneguard). Up-armored: +28% HP and heavier plating soak hits, trading bite and speed for a slower, near-unkillable frame. Same job: pulses a shove that scatters the nearest foes."
},
{
 "name": "Brassknuck",
 "breed": "Cane Corso",
 "class": "Boneguard Crew",
 "factionId": "boneguard_crew",
 "rarity": "Common",
 "cost": 7,
 "role": "Vanguard",
 "hp": 1908,
 "damage": 169,
 "attack_speed": 0.78,
 "move_speed": 0.61,
 "range": 1,
 "ability": {
  "name": "Grav Pull",
  "description": "Pulses a shove that scatters the nearest foes",
  "cooldown": 12
 },
 "abilityType": "knockback",
 "queen_target": false,
 "cardNumber": "0062",
 "isMythic": false,
 "rig": {
  "name": "Brassknuck Rig",
  "rigClass": "bruiser",
  "weaponMod": "ram_plow",
  "sourceCar": "Muscle Car",
  "flavor": "stripped chop-shop Armored bruiser rig -- ram plow, plate armor, slow and unstoppable"
 },
 "variant": "STREET",
 "family": "Rust Cane Corso",
 "desc": "Brassknuck -- the stripped [STREET] build of Rust Cane Corso's line (Vanguard, Boneguard). Glass-cannon: +25% damage and quicker, panels torn off for the kill, but folds to one clean shot. Same job: pulses a shove that scatters the nearest foes."
},
{
 "name": "Roadblock",
 "breed": "Greyhound",
 "class": "Zoomie Syndicate",
 "factionId": "zoomie_syndicate",
 "rarity": "Epic",
 "cost": 4,
 "role": "Skirmisher",
 "hp": 896,
 "damage": 81,
 "attack_speed": 1.17,
 "move_speed": 1.23,
 "range": 1,
 "ability": {
  "name": "Dash Loop",
  "description": "Refreshes its dash on a kill",
  "cooldown": 10
 },
 "abilityType": "dash",
 "queen_target": false,
 "cardNumber": "0063",
 "isMythic": false,
 "rig": {
  "name": "Roadblock Rig",
  "rigClass": "sprinter",
  "weaponMod": "ram_plow",
  "sourceCar": "GTR",
  "flavor": "bunkered Sport speed rig -- nitro, drag body, glass-cannon velocity"
 },
 "variant": "HEAVY",
 "family": "Pixel Greyhound",
 "desc": "Roadblock -- the bunkered [HEAVY] build of Pixel Greyhound's line (Skirmisher, Zoomie). Up-armored: +28% HP and heavier plating soak hits, trading bite and speed for a slower, near-unkillable frame. Same job: refreshes its dash on a kill."
},
{
 "name": "Nitro",
 "breed": "Greyhound",
 "class": "Zoomie Syndicate",
 "factionId": "zoomie_syndicate",
 "rarity": "Common",
 "cost": 2,
 "role": "Skirmisher",
 "hp": 420,
 "damage": 105,
 "attack_speed": 1.46,
 "move_speed": 1.54,
 "range": 1,
 "ability": {
  "name": "Dash Loop",
  "description": "Refreshes its dash on a kill",
  "cooldown": 6
 },
 "abilityType": "dash",
 "queen_target": false,
 "cardNumber": "0064",
 "isMythic": false,
 "rig": {
  "name": "Nitro Rig",
  "rigClass": "sprinter",
  "weaponMod": "ram_plow",
  "sourceCar": "GTR",
  "flavor": "stripped chop-shop Sport speed rig -- nitro, drag body, glass-cannon velocity"
 },
 "variant": "STREET",
 "family": "Pixel Greyhound",
 "desc": "Nitro -- the stripped [STREET] build of Pixel Greyhound's line (Skirmisher, Zoomie). Glass-cannon: +25% damage and quicker, panels torn off for the kill, but folds to one clean shot. Same job: refreshes its dash on a kill."
},
{
 "name": "Bullbar",
 "breed": "Shiba Inu",
 "class": "Zoomie Syndicate",
 "factionId": "zoomie_syndicate",
 "rarity": "Epic",
 "cost": 5,
 "role": "Striker",
 "hp": 1536,
 "damage": 115,
 "attack_speed": 0.95,
 "move_speed": 0.97,
 "range": 1,
 "ability": {
  "name": "Blink Bite",
  "description": "Blinks a short hop on its first attack",
  "cooldown": 12
 },
 "abilityType": "dash",
 "queen_target": false,
 "cardNumber": "0065",
 "isMythic": false,
 "rig": {
  "name": "Bullbar Rig",
  "rigClass": "sprinter",
  "weaponMod": "ram_plow",
  "sourceCar": "GTR",
  "flavor": "bunkered Sport speed rig -- nitro, drag body, glass-cannon velocity"
 },
 "variant": "HEAVY",
 "family": "Circuit Shiba",
 "desc": "Bullbar -- the bunkered [HEAVY] build of Circuit Shiba's line (Striker, Zoomie). Up-armored: +28% HP and heavier plating soak hits, trading bite and speed for a slower, near-unkillable frame. Same job: blinks a short hop on its first attack."
},
{
 "name": "Switchblade",
 "breed": "Shiba Inu",
 "class": "Zoomie Syndicate",
 "factionId": "zoomie_syndicate",
 "rarity": "Common",
 "cost": 3,
 "role": "Striker",
 "hp": 864,
 "damage": 155,
 "attack_speed": 1.18,
 "move_speed": 1.21,
 "range": 1,
 "ability": {
  "name": "Blink Bite",
  "description": "Blinks a short hop on its first attack",
  "cooldown": 8
 },
 "abilityType": "dash",
 "queen_target": false,
 "cardNumber": "0066",
 "isMythic": false,
 "rig": {
  "name": "Switchblade Rig",
  "rigClass": "sprinter",
  "weaponMod": "ram_plow",
  "sourceCar": "GTR",
  "flavor": "stripped chop-shop Sport speed rig -- nitro, drag body, glass-cannon velocity"
 },
 "variant": "STREET",
 "family": "Circuit Shiba",
 "desc": "Switchblade -- the stripped [STREET] build of Circuit Shiba's line (Striker, Zoomie). Glass-cannon: +25% damage and quicker, panels torn off for the kill, but folds to one clean shot. Same job: blinks a short hop on its first attack."
},
{
 "name": "Rollcage",
 "breed": "Vizsla",
 "class": "Zoomie Syndicate",
 "factionId": "zoomie_syndicate",
 "rarity": "Legendary",
 "cost": 6,
 "role": "Lancer",
 "hp": 1472,
 "damage": 153,
 "attack_speed": 0.85,
 "move_speed": 0.75,
 "range": 2,
 "ability": {
  "name": "Pierce Rush",
  "description": "Lunges a line that pierces every foe hit",
  "cooldown": 14
 },
 "abilityType": "pierce",
 "queen_target": false,
 "cardNumber": "0067",
 "isMythic": false,
 "rig": {
  "name": "Rollcage Rig",
  "rigClass": "sprinter",
  "weaponMod": "ram_plow",
  "sourceCar": "GTR",
  "flavor": "bunkered Sport speed rig -- nitro, drag body, glass-cannon velocity"
 },
 "variant": "HEAVY",
 "family": "Razor Vizsla",
 "desc": "Rollcage -- the bunkered [HEAVY] build of Razor Vizsla's line (Lancer, Zoomie). Up-armored: +28% HP and heavier plating soak hits, trading bite and speed for a slower, near-unkillable frame. Same job: lunges a line that pierces every foe hit."
},
{
 "name": "Ricochet",
 "breed": "Vizsla",
 "class": "Zoomie Syndicate",
 "factionId": "zoomie_syndicate",
 "rarity": "Rare",
 "cost": 4,
 "role": "Lancer",
 "hp": 828,
 "damage": 205, // AK-FACTION: Ricochet (Zoomie Street Lancer) 225->205, trims a non-excluded high outlier toward parity (p/e 111->~106); within dmg clamp
 "attack_speed": 1.06,
 "move_speed": 0.94,
 "range": 2,
 "ability": {
  "name": "Pierce Rush",
  "description": "Lunges a line that pierces every foe hit",
  "cooldown": 10
 },
 "abilityType": "pierce",
 "queen_target": false,
 "cardNumber": "0068",
 "isMythic": false,
 "rig": {
  "name": "Ricochet Rig",
  "rigClass": "sprinter",
  "weaponMod": "ram_plow",
  "sourceCar": "GTR",
  "flavor": "stripped chop-shop Sport speed rig -- nitro, drag body, glass-cannon velocity"
 },
 "variant": "STREET",
 "family": "Razor Vizsla",
 "desc": "Ricochet -- the stripped [STREET] build of Razor Vizsla's line (Lancer, Zoomie). Glass-cannon: +25% damage and quicker, panels torn off for the kill, but folds to one clean shot. Same job: lunges a line that pierces every foe hit."
},
{
 "name": "Crashcage",
 "breed": "Saluki",
 "class": "Zoomie Syndicate",
 "factionId": "zoomie_syndicate",
 "rarity": "Epic",
 "cost": 5,
 "role": "Skirmisher",
 "hp": 960,
 "damage": 94,
 "attack_speed": 1.17,
 "move_speed": 1.23,
 "range": 1,
 "ability": {
  "name": "Sidecut",
  "description": "Dashes lane to lane to flank the backline",
  "cooldown": 12
 },
 "abilityType": "dash",
 "queen_target": false,
 "cardNumber": "0069",
 "isMythic": false,
 "rig": {
  "name": "Crashcage Rig",
  "rigClass": "sprinter",
  "weaponMod": "ram_plow",
  "sourceCar": "GTR",
  "flavor": "bunkered Sport speed rig -- nitro, drag body, glass-cannon velocity"
 },
 "variant": "HEAVY",
 "family": "Flash Saluki",
 "desc": "Crashcage -- the bunkered [HEAVY] build of Flash Saluki's line (Skirmisher, Zoomie). Up-armored: +28% HP and heavier plating soak hits, trading bite and speed for a slower, near-unkillable frame. Same job: dashes lane to lane to flank the backline."
},
{
 "name": "Hotwire",
 "breed": "Saluki",
 "class": "Zoomie Syndicate",
 "factionId": "zoomie_syndicate",
 "rarity": "Common",
 "cost": 3,
 "role": "Skirmisher",
 "hp": 540,
 "damage": 125,
 "attack_speed": 1.46,
 "move_speed": 1.54,
 "range": 1,
 "ability": {
  "name": "Sidecut",
  "description": "Dashes lane to lane to flank the backline",
  "cooldown": 8
 },
 "abilityType": "dash",
 "queen_target": false,
 "cardNumber": "0070",
 "isMythic": false,
 "rig": {
  "name": "Hotwire Rig",
  "rigClass": "sprinter",
  "weaponMod": "ram_plow",
  "sourceCar": "GTR",
  "flavor": "stripped chop-shop Sport speed rig -- nitro, drag body, glass-cannon velocity"
 },
 "variant": "STREET",
 "family": "Flash Saluki",
 "desc": "Hotwire -- the stripped [STREET] build of Flash Saluki's line (Skirmisher, Zoomie). Glass-cannon: +25% damage and quicker, panels torn off for the kill, but folds to one clean shot. Same job: dashes lane to lane to flank the backline."
},
{
 "name": "Bumper",
 "breed": "Corgi",
 "class": "Zoomie Syndicate",
 "factionId": "zoomie_syndicate",
 "rarity": "Epic",
 "cost": 5,
 "role": "Spawner",
 "hp": 960,
 "damage": 47,
 "attack_speed": 0.81,
 "move_speed": 0.75,
 "range": 2,
 "ability": {
  "name": "Spark Pups",
  "description": "Spawns three fast mini zoomers",
  "cooldown": 14
 },
 "abilityType": "spawn",
 "queen_target": false,
 "cardNumber": "0071",
 "isMythic": false,
 "rig": {
  "name": "Bumper Rig",
  "rigClass": "sprinter",
  "weaponMod": "ram_plow",
  "sourceCar": "GTR",
  "flavor": "bunkered Sport speed rig -- nitro, drag body, glass-cannon velocity"
 },
 "variant": "HEAVY",
 "family": "Bolt Corgi",
 "desc": "Bumper -- the bunkered [HEAVY] build of Bolt Corgi's line (Spawner, Zoomie). Up-armored: +28% HP and heavier plating soak hits, trading bite and speed for a slower, near-unkillable frame. Same job: spawns three fast mini zoomers."
},
{
 "name": "Backfire",
 "breed": "Corgi",
 "class": "Zoomie Syndicate",
 "factionId": "zoomie_syndicate",
 "rarity": "Common",
 "cost": 3,
 "role": "Spawner",
 "hp": 540,
 "damage": 69,
 "attack_speed": 1.01,
 "move_speed": 0.94,
 "range": 2,
 "ability": {
  "name": "Spark Pups",
  "description": "Spawns three fast mini zoomers",
  "cooldown": 10
 },
 "abilityType": "spawn",
 "queen_target": false,
 "cardNumber": "0072",
 "isMythic": false,
 "rig": {
  "name": "Backfire Rig",
  "rigClass": "sprinter",
  "weaponMod": "ram_plow",
  "sourceCar": "GTR",
  "flavor": "stripped chop-shop Sport speed rig -- nitro, drag body, glass-cannon velocity"
 },
 "variant": "STREET",
 "family": "Bolt Corgi",
 "desc": "Backfire -- the stripped [STREET] build of Bolt Corgi's line (Spawner, Zoomie). Glass-cannon: +25% damage and quicker, panels torn off for the kill, but folds to one clean shot. Same job: spawns three fast mini zoomers."
},
{
 "name": "Gridiron",
 "breed": "Basenji",
 "class": "Zoomie Syndicate",
 "factionId": "zoomie_syndicate",
 "rarity": "Epic",
 "cost": 4,
 "role": "Hacker",
 "hp": 896,
 "damage": 60,
 "attack_speed": 0.9,
 "move_speed": 0.75,
 "range": 3,
 "ability": {
  "name": "Signal Scramble",
  "description": "Silences a target ability briefly",
  "cooldown": 12
 },
 "abilityType": "silence",
 "queen_target": false,
 "cardNumber": "0073",
 "isMythic": false,
 "rig": {
  "name": "Gridiron Rig",
  "rigClass": "sprinter",
  "weaponMod": "ram_plow",
  "sourceCar": "GTR",
  "flavor": "bunkered Sport speed rig -- nitro, drag body, glass-cannon velocity"
 },
 "variant": "HEAVY",
 "family": "Glitch Basenji",
 "desc": "Gridiron -- the bunkered [HEAVY] build of Glitch Basenji's line (Hacker, Zoomie). Up-armored: +28% HP and heavier plating soak hits, trading bite and speed for a slower, near-unkillable frame. Same job: silences a target ability briefly."
},
{
 "name": "Skidmark",
 "breed": "Basenji",
 "class": "Zoomie Syndicate",
 "factionId": "zoomie_syndicate",
 "rarity": "Common",
 "cost": 2,
 "role": "Hacker",
 "hp": 504,
 "damage": 88,
 "attack_speed": 1.12,
 "move_speed": 0.94,
 "range": 3,
 "ability": {
  "name": "Signal Scramble",
  "description": "Silences a target ability briefly",
  "cooldown": 8
 },
 "abilityType": "silence",
 "queen_target": false,
 "cardNumber": "0074",
 "isMythic": false,
 "rig": {
  "name": "Skidmark Rig",
  "rigClass": "sprinter",
  "weaponMod": "ram_plow",
  "sourceCar": "GTR",
  "flavor": "stripped chop-shop Sport speed rig -- nitro, drag body, glass-cannon velocity"
 },
 "variant": "STREET",
 "family": "Glitch Basenji",
 "desc": "Skidmark -- the stripped [STREET] build of Glitch Basenji's line (Hacker, Zoomie). Glass-cannon: +25% damage and quicker, panels torn off for the kill, but folds to one clean shot. Same job: silences a target ability briefly."
},
{
 "name": "Deadweight",
 "breed": "Malinois",
 "class": "Zoomie Syndicate",
 "factionId": "zoomie_syndicate",
 "rarity": "Legendary",
 "cost": 7,
 "role": "Striker",
 "hp": 1920,
 "damage": 149,
 "attack_speed": 0.95,
 "move_speed": 0.97,
 "range": 1,
 "ability": {
  "name": "Twin Strike",
  "description": "Strikes twice in one attack swing",
  "cooldown": 14
 },
 "abilityType": "double_hit",
 "queen_target": false,
 "cardNumber": "0075",
 "isMythic": false,
 "rig": {
  "name": "Deadweight Rig",
  "rigClass": "sprinter",
  "weaponMod": "ram_plow",
  "sourceCar": "GTR",
  "flavor": "bunkered Sport speed rig -- nitro, drag body, glass-cannon velocity"
 },
 "variant": "HEAVY",
 "family": "Aero Malinois",
 "desc": "Deadweight -- the bunkered [HEAVY] build of Aero Malinois's line (Striker, Zoomie). Up-armored: +28% HP and heavier plating soak hits, trading bite and speed for a slower, near-unkillable frame. Same job: strikes twice in one attack swing."
},
{
 "name": "Flatline",
 "breed": "Malinois",
 "class": "Zoomie Syndicate",
 "factionId": "zoomie_syndicate",
 "rarity": "Rare",
 "cost": 5,
 "role": "Striker",
 "hp": 1080,
 "damage": 185,
 "attack_speed": 1.18,
 "move_speed": 1.21,
 "range": 1,
 "ability": {
  "name": "Twin Strike",
  "description": "Strikes twice in one attack swing",
  "cooldown": 10
 },
 "abilityType": "double_hit",
 "queen_target": false,
 "cardNumber": "0076",
 "isMythic": false,
 "rig": {
  "name": "Flatline Rig",
  "rigClass": "sprinter",
  "weaponMod": "ram_plow",
  "sourceCar": "GTR",
  "flavor": "stripped chop-shop Sport speed rig -- nitro, drag body, glass-cannon velocity"
 },
 "variant": "STREET",
 "family": "Aero Malinois",
 "desc": "Flatline -- the stripped [STREET] build of Aero Malinois's line (Striker, Zoomie). Glass-cannon: +25% damage and quicker, panels torn off for the kill, but folds to one clean shot. Same job: strikes twice in one attack swing."
},
{
 "name": "Firewall",
 "breed": "Border Collie",
 "class": "Leashbreak Tactix",
 "factionId": "leashbreak_tactix",
 "rarity": "Legendary",
 "cost": 6,
 "role": "Hacker",
 "hp": 1152,
 "damage": 76,
 "attack_speed": 0.9,
 "move_speed": 0.75,
 "range": 3,
 "ability": {
  "name": "Hack Jam",
  "description": "Jams a tower so it cannot fire",
  "cooldown": 14
 },
 "abilityType": "disable_tower",
 "queen_target": false,
 "cardNumber": "0077",
 "isMythic": false,
 "rig": {
  "name": "Firewall Rig",
  "rigClass": "tech_ops",
  "weaponMod": "emp_array",
  "sourceCar": "Van",
  "flavor": "bunkered Tech-ops rig -- jammer van, EMP array, signal-warfare"
 },
 "variant": "HEAVY",
 "family": "Synth Collie",
 "desc": "Firewall -- the bunkered [HEAVY] build of Synth Collie's line (Hacker, Leashbreak). Up-armored: +28% HP and heavier plating soak hits, trading bite and speed for a slower, near-unkillable frame. Same job: jams a tower so it cannot fire."
},
{
 "name": "Glitchfork",
 "breed": "Border Collie",
 "class": "Leashbreak Tactix",
 "factionId": "leashbreak_tactix",
 "rarity": "Rare",
 "cost": 4,
 "role": "Hacker",
 "hp": 648,
 "damage": 112,
 "attack_speed": 1.12,
 "move_speed": 0.94,
 "range": 3,
 "ability": {
  "name": "Hack Jam",
  "description": "Jams a tower so it cannot fire",
  "cooldown": 10
 },
 "abilityType": "disable_tower",
 "queen_target": false,
 "cardNumber": "0078",
 "isMythic": false,
 "rig": {
  "name": "Glitchfork Rig",
  "rigClass": "tech_ops",
  "weaponMod": "emp_array",
  "sourceCar": "Van",
  "flavor": "stripped chop-shop Tech-ops rig -- jammer van, EMP array, signal-warfare"
 },
 "variant": "STREET",
 "family": "Synth Collie",
 "desc": "Glitchfork -- the stripped [STREET] build of Synth Collie's line (Hacker, Leashbreak). Glass-cannon: +25% damage and quicker, panels torn off for the kill, but folds to one clean shot. Same job: jams a tower so it cannot fire."
},
{
 "name": "Deadbolt",
 "breed": "Husky",
 "class": "Leashbreak Tactix",
 "factionId": "leashbreak_tactix",
 "rarity": "Epic",
 "cost": 6,
 "role": "Support",
 "hp": 1216,
 "damage": 51,
 "attack_speed": 0.81,
 "move_speed": 0.75,
 "range": 3,
 "ability": {
  "name": "Heal Beacon",
  "description": "Pulsing area heal for the pack",
  "cooldown": 14
 },
 "abilityType": "heal",
 "queen_target": false,
 "cardNumber": "0079",
 "isMythic": false,
 "rig": {
  "name": "Deadbolt Rig",
  "rigClass": "tech_ops",
  "weaponMod": "emp_array",
  "sourceCar": "Van",
  "flavor": "bunkered Tech-ops rig -- jammer van, EMP array, signal-warfare"
 },
 "variant": "HEAVY",
 "family": "Holo Husky",
 "desc": "Deadbolt -- the bunkered [HEAVY] build of Holo Husky's line (Support, Leashbreak). Up-armored: +28% HP and heavier plating soak hits, trading bite and speed for a slower, near-unkillable frame. Same job: pulsing area heal for the pack."
},
{
 "name": "Static",
 "breed": "Husky",
 "class": "Leashbreak Tactix",
 "factionId": "leashbreak_tactix",
 "rarity": "Common",
 "cost": 4,
 "role": "Support",
 "hp": 684,
 "damage": 75,
 "attack_speed": 1.01,
 "move_speed": 0.94,
 "range": 3,
 "ability": {
  "name": "Heal Beacon",
  "description": "Pulsing area heal for the pack",
  "cooldown": 10
 },
 "abilityType": "heal",
 "queen_target": false,
 "cardNumber": "0080",
 "isMythic": false,
 "rig": {
  "name": "Static Rig",
  "rigClass": "tech_ops",
  "weaponMod": "emp_array",
  "sourceCar": "Van",
  "flavor": "stripped chop-shop Tech-ops rig -- jammer van, EMP array, signal-warfare"
 },
 "variant": "STREET",
 "family": "Holo Husky",
 "desc": "Static -- the stripped [STREET] build of Holo Husky's line (Support, Leashbreak). Glass-cannon: +25% damage and quicker, panels torn off for the kill, but folds to one clean shot. Same job: pulsing area heal for the pack."
},
{
 "name": "Bunkerlink",
 "breed": "Samoyed",
 "class": "Leashbreak Tactix",
 "factionId": "leashbreak_tactix",
 "rarity": "Epic",
 "cost": 5,
 "role": "Support",
 "hp": 1152,
 "damage": 47,
 "attack_speed": 0.81,
 "move_speed": 0.75,
 "range": 3,
 "ability": {
  "name": "Frost Bark",
  "description": "Wide frost cone slows everything caught",
  "cooldown": 12
 },
 "abilityType": "slow",
 "queen_target": false,
 "cardNumber": "0081",
 "isMythic": false,
 "rig": {
  "name": "Bunkerlink Rig",
  "rigClass": "tech_ops",
  "weaponMod": "emp_array",
  "sourceCar": "Van",
  "flavor": "bunkered Tech-ops rig -- jammer van, EMP array, signal-warfare"
 },
 "variant": "HEAVY",
 "family": "Chill Samoyed",
 "desc": "Bunkerlink -- the bunkered [HEAVY] build of Chill Samoyed's line (Support, Leashbreak). Up-armored: +28% HP and heavier plating soak hits, trading bite and speed for a slower, near-unkillable frame. Same job: wide frost cone slows everything caught."
},
{
 "name": "Shortcircuit",
 "breed": "Samoyed",
 "class": "Leashbreak Tactix",
 "factionId": "leashbreak_tactix",
 "rarity": "Common",
 "cost": 3,
 "role": "Support",
 "hp": 648,
 "damage": 69,
 "attack_speed": 1.01,
 "move_speed": 0.94,
 "range": 3,
 "ability": {
  "name": "Frost Bark",
  "description": "Wide frost cone slows everything caught",
  "cooldown": 8
 },
 "abilityType": "slow",
 "queen_target": false,
 "cardNumber": "0082",
 "isMythic": false,
 "rig": {
  "name": "Shortcircuit Rig",
  "rigClass": "tech_ops",
  "weaponMod": "emp_array",
  "sourceCar": "Van",
  "flavor": "stripped chop-shop Tech-ops rig -- jammer van, EMP array, signal-warfare"
 },
 "variant": "STREET",
 "family": "Chill Samoyed",
 "desc": "Shortcircuit -- the stripped [STREET] build of Chill Samoyed's line (Support, Leashbreak). Glass-cannon: +25% damage and quicker, panels torn off for the kill, but folds to one clean shot. Same job: wide frost cone slows everything caught."
},
{
 "name": "Faraday",
 "breed": "Poodle",
 "class": "Leashbreak Tactix",
 "factionId": "leashbreak_tactix",
 "rarity": "Epic",
 "cost": 5,
 "role": "Controller",
 "hp": 1088,
 "damage": 72,
 "attack_speed": 0.85,
 "move_speed": 0.75,
 "range": 3,
 "ability": {
  "name": "Shatter",
  "description": "Strips enemy shields, then wards an ally",
  "cooldown": 12
 },
 "abilityType": "shield",
 "queen_target": false,
 "cardNumber": "0083",
 "isMythic": false,
 "rig": {
  "name": "Faraday Rig",
  "rigClass": "tech_ops",
  "weaponMod": "emp_array",
  "sourceCar": "Van",
  "flavor": "bunkered Tech-ops rig -- jammer van, EMP array, signal-warfare"
 },
 "variant": "HEAVY",
 "family": "Prism Poodle",
 "desc": "Faraday -- the bunkered [HEAVY] build of Prism Poodle's line (Controller, Leashbreak). Up-armored: +28% HP and heavier plating soak hits, trading bite and speed for a slower, near-unkillable frame. Same job: strips enemy shields, then wards an ally."
},
{
 "name": "Hexer",
 "breed": "Poodle",
 "class": "Leashbreak Tactix",
 "factionId": "leashbreak_tactix",
 "rarity": "Common",
 "cost": 3,
 "role": "Controller",
 "hp": 612,
 "damage": 106,
 "attack_speed": 1.06,
 "move_speed": 0.94,
 "range": 3,
 "ability": {
  "name": "Shatter",
  "description": "Strips enemy shields, then wards an ally",
  "cooldown": 8
 },
 "abilityType": "shield",
 "queen_target": false,
 "cardNumber": "0084",
 "isMythic": false,
 "rig": {
  "name": "Hexer Rig",
  "rigClass": "tech_ops",
  "weaponMod": "emp_array",
  "sourceCar": "Van",
  "flavor": "stripped chop-shop Tech-ops rig -- jammer van, EMP array, signal-warfare"
 },
 "variant": "STREET",
 "family": "Prism Poodle",
 "desc": "Hexer -- the stripped [STREET] build of Prism Poodle's line (Controller, Leashbreak). Glass-cannon: +25% damage and quicker, panels torn off for the kill, but folds to one clean shot. Same job: strips enemy shields, then wards an ally."
},
{
 "name": "Sandbag",
 "breed": "Setter",
 "class": "Leashbreak Tactix",
 "factionId": "leashbreak_tactix",
 "rarity": "Legendary",
 "cost": 7,
 "role": "Controller",
 "hp": 1408,
 "damage": 94,
 "attack_speed": 0.85,
 "move_speed": 0.75,
 "range": 3,
 "ability": {
  "name": "Blackout",
  "description": "Blinds ranged foes so their shots miss",
  "cooldown": 14
 },
 "abilityType": "blind",
 "queen_target": false,
 "cardNumber": "0085",
 "isMythic": false,
 "rig": {
  "name": "Sandbag Rig",
  "rigClass": "tech_ops",
  "weaponMod": "emp_array",
  "sourceCar": "Van",
  "flavor": "bunkered Tech-ops rig -- jammer van, EMP array, signal-warfare"
 },
 "variant": "HEAVY",
 "family": "Noir Setter",
 "desc": "Sandbag -- the bunkered [HEAVY] build of Noir Setter's line (Controller, Leashbreak). Up-armored: +28% HP and heavier plating soak hits, trading bite and speed for a slower, near-unkillable frame. Same job: blinds ranged foes so their shots miss."
},
{
 "name": "Whitenoise",
 "breed": "Setter",
 "class": "Leashbreak Tactix",
 "factionId": "leashbreak_tactix",
 "rarity": "Rare",
 "cost": 5,
 "role": "Controller",
 "hp": 792,
 "damage": 138,
 "attack_speed": 1.06,
 "move_speed": 0.94,
 "range": 3,
 "ability": {
  "name": "Blackout",
  "description": "Blinds ranged foes so their shots miss",
  "cooldown": 10
 },
 "abilityType": "blind",
 "queen_target": false,
 "cardNumber": "0086",
 "isMythic": false,
 "rig": {
  "name": "Whitenoise Rig",
  "rigClass": "tech_ops",
  "weaponMod": "emp_array",
  "sourceCar": "Van",
  "flavor": "stripped chop-shop Tech-ops rig -- jammer van, EMP array, signal-warfare"
 },
 "variant": "STREET",
 "family": "Noir Setter",
 "desc": "Whitenoise -- the stripped [STREET] build of Noir Setter's line (Controller, Leashbreak). Glass-cannon: +25% damage and quicker, panels torn off for the kill, but folds to one clean shot. Same job: blinds ranged foes so their shots miss."
},
{
 "name": "Blacksite",
 "breed": "Pointer",
 "class": "Leashbreak Tactix",
 "factionId": "leashbreak_tactix",
 "rarity": "Epic",
 "cost": 5,
 "role": "Lancer",
 "hp": 1280,
 "damage": 128,
 "attack_speed": 0.85,
 "move_speed": 0.75,
 "range": 3,
 "ability": {
  "name": "Tag Shot",
  "description": "Tags a target, revealing stealth and weakening it",
  "cooldown": 12
 },
 "abilityType": "reveal",
 "queen_target": false,
 "cardNumber": "0087",
 "isMythic": false,
 "rig": {
  "name": "Blacksite Rig",
  "rigClass": "tech_ops",
  "weaponMod": "emp_array",
  "sourceCar": "Van",
  "flavor": "bunkered Tech-ops rig -- jammer van, EMP array, signal-warfare"
 },
 "variant": "HEAVY",
 "family": "Signal Pointer",
 "desc": "Blacksite -- the bunkered [HEAVY] build of Signal Pointer's line (Lancer, Leashbreak). Up-armored: +28% HP and heavier plating soak hits, trading bite and speed for a slower, near-unkillable frame. Same job: tags a target, revealing stealth and weakening it."
},
{
 "name": "Carrier",
 "breed": "Pointer",
 "class": "Leashbreak Tactix",
 "factionId": "leashbreak_tactix",
 "rarity": "Common",
 "cost": 3,
 "role": "Lancer",
 "hp": 720,
 "damage": 175,
 "attack_speed": 1.06,
 "move_speed": 0.94,
 "range": 3,
 "ability": {
  "name": "Tag Shot",
  "description": "Tags a target, revealing stealth and weakening it",
  "cooldown": 8
 },
 "abilityType": "reveal",
 "queen_target": false,
 "cardNumber": "0088",
 "isMythic": false,
 "rig": {
  "name": "Carrier Rig",
  "rigClass": "tech_ops",
  "weaponMod": "emp_array",
  "sourceCar": "Van",
  "flavor": "stripped chop-shop Tech-ops rig -- jammer van, EMP array, signal-warfare"
 },
 "variant": "STREET",
 "family": "Signal Pointer",
 "desc": "Carrier -- the stripped [STREET] build of Signal Pointer's line (Lancer, Leashbreak). Glass-cannon: +25% damage and quicker, panels torn off for the kill, but folds to one clean shot. Same job: tags a target, revealing stealth and weakening it."
},
{
 "name": "Hardline",
 "breed": "Spaniel",
 "class": "Leashbreak Tactix",
 "factionId": "leashbreak_tactix",
 "rarity": "Epic",
 "cost": 4,
 "role": "Skirmisher",
 "hp": 896,
 "damage": 81,
 "attack_speed": 1.17,
 "move_speed": 0.97,
 "range": 2,
 "ability": {
  "name": "Phase",
  "description": "Phases out for a brief untargetable window",
  "cooldown": 12
 },
 "abilityType": "invuln",
 "queen_target": false,
 "cardNumber": "0089",
 "isMythic": false,
 "rig": {
  "name": "Hardline Rig",
  "rigClass": "tech_ops",
  "weaponMod": "emp_array",
  "sourceCar": "Van",
  "flavor": "bunkered Tech-ops rig -- jammer van, EMP array, signal-warfare"
 },
 "variant": "HEAVY",
 "family": "Ghost Spaniel",
 "desc": "Hardline -- the bunkered [HEAVY] build of Ghost Spaniel's line (Skirmisher, Leashbreak). Up-armored: +28% HP and heavier plating soak hits, trading bite and speed for a slower, near-unkillable frame. Same job: phases out for a brief untargetable window."
},
{
 "name": "Spike",
 "breed": "Spaniel",
 "class": "Leashbreak Tactix",
 "factionId": "leashbreak_tactix",
 "rarity": "Common",
 "cost": 2,
 "role": "Skirmisher",
 "hp": 420,
 "damage": 105,
 "attack_speed": 1.46,
 "move_speed": 1.21,
 "range": 2,
 "ability": {
  "name": "Phase",
  "description": "Phases out for a brief untargetable window",
  "cooldown": 8
 },
 "abilityType": "invuln",
 "queen_target": false,
 "cardNumber": "0090",
 "isMythic": false,
 "rig": {
  "name": "Spike Rig",
  "rigClass": "tech_ops",
  "weaponMod": "emp_array",
  "sourceCar": "Van",
  "flavor": "stripped chop-shop Tech-ops rig -- jammer van, EMP array, signal-warfare"
 },
 "variant": "STREET",
 "family": "Ghost Spaniel",
 "desc": "Spike -- the stripped [STREET] build of Ghost Spaniel's line (Skirmisher, Leashbreak). Glass-cannon: +25% damage and quicker, panels torn off for the kill, but folds to one clean shot. Same job: phases out for a brief untargetable window."
},
{
 "name": "Bulwark",
 "breed": "Border Collie",
 "class": "Leashbreak Tactix",
 "factionId": "leashbreak_tactix",
 "rarity": "Legendary",
 "cost": 6,
 "role": "Support",
 "hp": 1344,
 "damage": 55,
 "attack_speed": 0.81,
 "move_speed": 0.75,
 "range": 3,
 "ability": {
  "name": "Barrier Ring",
  "description": "Drops an area shield over the front line",
  "cooldown": 14
 },
 "abilityType": "shield",
 "queen_target": false,
 "cardNumber": "0091",
 "isMythic": false,
 "rig": {
  "name": "Bulwark Rig",
  "rigClass": "tech_ops",
  "weaponMod": "emp_array",
  "sourceCar": "Van",
  "flavor": "bunkered Tech-ops rig -- jammer van, EMP array, signal-warfare"
 },
 "variant": "HEAVY",
 "family": "Pulse Border Collie",
 "desc": "Bulwark -- the bunkered [HEAVY] build of Pulse Border Collie's line (Support, Leashbreak). Up-armored: +28% HP and heavier plating soak hits, trading bite and speed for a slower, near-unkillable frame. Same job: drops an area shield over the front line."
},
{
 "name": "Brownout",
 "breed": "Border Collie",
 "class": "Leashbreak Tactix",
 "factionId": "leashbreak_tactix",
 "rarity": "Rare",
 "cost": 4,
 "role": "Support",
 "hp": 756,
 "damage": 81,
 "attack_speed": 1.01,
 "move_speed": 0.94,
 "range": 3,
 "ability": {
  "name": "Barrier Ring",
  "description": "Drops an area shield over the front line",
  "cooldown": 10
 },
 "abilityType": "shield",
 "queen_target": false,
 "cardNumber": "0092",
 "isMythic": false,
 "rig": {
  "name": "Brownout Rig",
  "rigClass": "tech_ops",
  "weaponMod": "emp_array",
  "sourceCar": "Van",
  "flavor": "stripped chop-shop Tech-ops rig -- jammer van, EMP array, signal-warfare"
 },
 "variant": "STREET",
 "family": "Pulse Border Collie",
 "desc": "Brownout -- the stripped [STREET] build of Pulse Border Collie's line (Support, Leashbreak). Glass-cannon: +25% damage and quicker, panels torn off for the kill, but folds to one clean shot. Same job: drops an area shield over the front line."
},
{
 "name": "Bunker",
 "breed": "Beagle",
 "class": "K9 Circuitry",
 "factionId": "k9_circuitry",
 "rarity": "Epic",
 "cost": 5,
 "role": "Structure",
 "hp": 1344,
 "damage": 80, // AK-FACTION: Bunker (K9 Heavy Structure) 72->80 (Heavy-structure relief ~0.85->0.95 mult), lifts the lowest non-excluded K9 outlier toward parity (p/e 74->~78)
 "attack_speed": 0.9,
 "move_speed": 0.0,
 "range": 5,
 "ability": {
  "name": "Overheat",
  "description": "Static turret that ramps fire the longer it shoots",
  "cooldown": 14
 },
 "abilityType": "ramp",
 "queen_target": false,
 "cardNumber": "0093",
 "isMythic": false,
 "rig": {
  "name": "Bunker Rig",
  "rigClass": "turret_util",
  "weaponMod": "incendiary",
  "sourceCar": "Monster Truck",
  "flavor": "bunkered Turret-utility rig -- mounted gun, drone bay, rail platform"
 },
 "variant": "HEAVY",
 "family": "Laser Beagle",
 "desc": "Bunker -- the bunkered [HEAVY] build of Laser Beagle's line (Structure, K9). Up-armored: +28% HP and heavier plating soak hits, trading bite and speed for a slower, near-unkillable frame. Same job: static turret that ramps fire the longer it shoots."
},
{
 "name": "Buckshot",
 "breed": "Beagle",
 "class": "K9 Circuitry",
 "factionId": "k9_circuitry",
 "rarity": "Common",
 "cost": 3,
 "role": "Structure",
 "hp": 756,
 "damage": 106,
 "attack_speed": 1.12,
 "move_speed": 0.0,
 "range": 5,
 "ability": {
  "name": "Overheat",
  "description": "Static turret that ramps fire the longer it shoots",
  "cooldown": 10
 },
 "abilityType": "ramp",
 "queen_target": false,
 "cardNumber": "0094",
 "isMythic": false,
 "rig": {
  "name": "Buckshot Rig",
  "rigClass": "turret_util",
  "weaponMod": "incendiary",
  "sourceCar": "Monster Truck",
  "flavor": "stripped chop-shop Turret-utility rig -- mounted gun, drone bay, rail platform"
 },
 "variant": "STREET",
 "family": "Laser Beagle",
 "desc": "Buckshot -- the stripped [STREET] build of Laser Beagle's line (Structure, K9). Glass-cannon: +25% damage and quicker, panels torn off for the kill, but folds to one clean shot. Same job: static turret that ramps fire the longer it shoots."
},
{
 "name": "Howitzer",
 "breed": "Corgi",
 "class": "K9 Circuitry",
 "factionId": "k9_circuitry",
 "rarity": "Epic",
 "cost": 5,
 "role": "Spawner",
 "hp": 960,
 "damage": 47,
 "attack_speed": 0.81,
 "move_speed": 0.75,
 "range": 2,
 "ability": {
  "name": "Spark Pups",
  "description": "Spawns three spark drones",
  "cooldown": 14
 },
 "abilityType": "spawn",
 "queen_target": false,
 "cardNumber": "0095",
 "isMythic": false,
 "rig": {
  "name": "Howitzer Rig",
  "rigClass": "turret_util",
  "weaponMod": "incendiary",
  "sourceCar": "Monster Truck",
  "flavor": "bunkered Turret-utility rig -- mounted gun, drone bay, rail platform"
 },
 "variant": "HEAVY",
 "family": "Volt Corgi",
 "desc": "Howitzer -- the bunkered [HEAVY] build of Volt Corgi's line (Spawner, K9). Up-armored: +28% HP and heavier plating soak hits, trading bite and speed for a slower, near-unkillable frame. Same job: spawns three spark drones."
},
{
 "name": "Tripwire",
 "breed": "Corgi",
 "class": "K9 Circuitry",
 "factionId": "k9_circuitry",
 "rarity": "Common",
 "cost": 3,
 "role": "Spawner",
 "hp": 540,
 "damage": 69,
 "attack_speed": 1.01,
 "move_speed": 0.94,
 "range": 2,
 "ability": {
  "name": "Spark Pups",
  "description": "Spawns three spark drones",
  "cooldown": 10
 },
 "abilityType": "spawn",
 "queen_target": false,
 "cardNumber": "0096",
 "isMythic": false,
 "rig": {
  "name": "Tripwire Rig",
  "rigClass": "turret_util",
  "weaponMod": "incendiary",
  "sourceCar": "Monster Truck",
  "flavor": "stripped chop-shop Turret-utility rig -- mounted gun, drone bay, rail platform"
 },
 "variant": "STREET",
 "family": "Volt Corgi",
 "desc": "Tripwire -- the stripped [STREET] build of Volt Corgi's line (Spawner, K9). Glass-cannon: +25% damage and quicker, panels torn off for the kill, but folds to one clean shot. Same job: spawns three spark drones."
},
{
 "name": "Flakwall",
 "breed": "Schnauzer",
 "class": "K9 Circuitry",
 "factionId": "k9_circuitry",
 "rarity": "Epic",
 "cost": 6,
 "role": "Structure",
 "hp": 1472,
 "damage": 90,
 "attack_speed": 0.9,
 "move_speed": 0.0,
 "range": 4,
 "ability": {
  "name": "Grid Lock",
  "description": "Turret field that slows attackers in range",
  "cooldown": 14
 },
 "abilityType": "slow",
 "queen_target": false,
 "cardNumber": "0097",
 "isMythic": false,
 "rig": {
  "name": "Flakwall Rig",
  "rigClass": "turret_util",
  "weaponMod": "incendiary",
  "sourceCar": "Monster Truck",
  "flavor": "bunkered Turret-utility rig -- mounted gun, drone bay, rail platform"
 },
 "variant": "HEAVY",
 "family": "Grid Schnauzer",
 "desc": "Flakwall -- the bunkered [HEAVY] build of Grid Schnauzer's line (Structure, K9). Up-armored: +28% HP and heavier plating soak hits, trading bite and speed for a slower, near-unkillable frame. Same job: turret field that slows attackers in range."
},
{
 "name": "Deadeye",
 "breed": "Schnauzer",
 "class": "K9 Circuitry",
 "factionId": "k9_circuitry",
 "rarity": "Common",
 "cost": 4,
 "role": "Structure",
 "hp": 828,
 "damage": 119,
 "attack_speed": 1.12,
 "move_speed": 0.0,
 "range": 4,
 "ability": {
  "name": "Grid Lock",
  "description": "Turret field that slows attackers in range",
  "cooldown": 10
 },
 "abilityType": "slow",
 "queen_target": false,
 "cardNumber": "0098",
 "isMythic": false,
 "rig": {
  "name": "Deadeye Rig",
  "rigClass": "turret_util",
  "weaponMod": "incendiary",
  "sourceCar": "Monster Truck",
  "flavor": "stripped chop-shop Turret-utility rig -- mounted gun, drone bay, rail platform"
 },
 "variant": "STREET",
 "family": "Grid Schnauzer",
 "desc": "Deadeye -- the stripped [STREET] build of Grid Schnauzer's line (Structure, K9). Glass-cannon: +25% damage and quicker, panels torn off for the kill, but folds to one clean shot. Same job: turret field that slows attackers in range."
},
{
 "name": "Casemate",
 "breed": "Retriever",
 "class": "K9 Circuitry",
 "factionId": "k9_circuitry",
 "rarity": "Legendary",
 "cost": 7,
 "role": "Support",
 "hp": 1408,
 "damage": 60,
 "attack_speed": 0.81,
 "move_speed": 0.75,
 "range": 3,
 "ability": {
  "name": "Drone Swarm",
  "description": "Releases five swarm drones",
  "cooldown": 14
 },
 "abilityType": "spawn",
 "queen_target": false,
 "cardNumber": "0099",
 "isMythic": false,
 "rig": {
  "name": "Casemate Rig",
  "rigClass": "turret_util",
  "weaponMod": "incendiary",
  "sourceCar": "Monster Truck",
  "flavor": "bunkered Turret-utility rig -- mounted gun, drone bay, rail platform"
 },
 "variant": "HEAVY",
 "family": "Circuit Retriever",
 "desc": "Casemate -- the bunkered [HEAVY] build of Circuit Retriever's line (Support, K9). Up-armored: +28% HP and heavier plating soak hits, trading bite and speed for a slower, near-unkillable frame. Same job: releases five swarm drones."
},
{
 "name": "Shrapnel",
 "breed": "Retriever",
 "class": "K9 Circuitry",
 "factionId": "k9_circuitry",
 "rarity": "Rare",
 "cost": 5,
 "role": "Support",
 "hp": 792,
 "damage": 88,
 "attack_speed": 1.01,
 "move_speed": 0.94,
 "range": 3,
 "ability": {
  "name": "Drone Swarm",
  "description": "Releases five swarm drones",
  "cooldown": 10
 },
 "abilityType": "spawn",
 "queen_target": false,
 "cardNumber": "0100",
 "isMythic": false,
 "rig": {
  "name": "Shrapnel Rig",
  "rigClass": "turret_util",
  "weaponMod": "incendiary",
  "sourceCar": "Monster Truck",
  "flavor": "stripped chop-shop Turret-utility rig -- mounted gun, drone bay, rail platform"
 },
 "variant": "STREET",
 "family": "Circuit Retriever",
 "desc": "Shrapnel -- the stripped [STREET] build of Circuit Retriever's line (Support, K9). Glass-cannon: +25% damage and quicker, panels torn off for the kill, but folds to one clean shot. Same job: releases five swarm drones."
},
{
 "name": "Pillbox",
 "breed": "Airedale",
 "class": "K9 Circuitry",
 "factionId": "k9_circuitry",
 "rarity": "Epic",
 "cost": 6,
 "role": "Lancer",
 "hp": 1344,
 "damage": 140,
 "attack_speed": 0.85,
 "move_speed": 0.75,
 "range": 3,
 "ability": {
  "name": "Arc Shot",
  "description": "Arc that chains to three targets",
  "cooldown": 12
 },
 "abilityType": "chain",
 "queen_target": false,
 "cardNumber": "0101",
 "isMythic": false,
 "rig": {
  "name": "Pillbox Rig",
  "rigClass": "turret_util",
  "weaponMod": "incendiary",
  "sourceCar": "Monster Truck",
  "flavor": "bunkered Turret-utility rig -- mounted gun, drone bay, rail platform"
 },
 "variant": "HEAVY",
 "family": "Chrome Airedale",
 "desc": "Pillbox -- the bunkered [HEAVY] build of Chrome Airedale's line (Lancer, K9). Up-armored: +28% HP and heavier plating soak hits, trading bite and speed for a slower, near-unkillable frame. Same job: arc that chains to three targets."
},
{
 "name": "Hairtrigger",
 "breed": "Airedale",
 "class": "K9 Circuitry",
 "factionId": "k9_circuitry",
 "rarity": "Common",
 "cost": 4,
 "role": "Lancer",
 "hp": 756,
 "damage": 206,
 "attack_speed": 1.06,
 "move_speed": 0.94,
 "range": 3,
 "ability": {
  "name": "Arc Shot",
  "description": "Arc that chains to three targets",
  "cooldown": 8
 },
 "abilityType": "chain",
 "queen_target": false,
 "cardNumber": "0102",
 "isMythic": false,
 "rig": {
  "name": "Hairtrigger Rig",
  "rigClass": "turret_util",
  "weaponMod": "incendiary",
  "sourceCar": "Monster Truck",
  "flavor": "stripped chop-shop Turret-utility rig -- mounted gun, drone bay, rail platform"
 },
 "variant": "STREET",
 "family": "Chrome Airedale",
 "desc": "Hairtrigger -- the stripped [STREET] build of Chrome Airedale's line (Lancer, K9). Glass-cannon: +25% damage and quicker, panels torn off for the kill, but folds to one clean shot. Same job: arc that chains to three targets."
},
{
 "name": "Stronghold",
 "breed": "Basset",
 "class": "K9 Circuitry",
 "factionId": "k9_circuitry",
 "rarity": "Epic",
 "cost": 5,
 "role": "Support",
 "hp": 1152,
 "damage": 47,
 "attack_speed": 0.81,
 "move_speed": 0.75,
 "range": 3,
 "ability": {
  "name": "Beacon",
  "description": "Reveals stealth and marks foes for the pack",
  "cooldown": 12
 },
 "abilityType": "reveal",
 "queen_target": false,
 "cardNumber": "0103",
 "isMythic": false,
 "rig": {
  "name": "Stronghold Rig",
  "rigClass": "turret_util",
  "weaponMod": "incendiary",
  "sourceCar": "Monster Truck",
  "flavor": "bunkered Turret-utility rig -- mounted gun, drone bay, rail platform"
 },
 "variant": "HEAVY",
 "family": "Beacon Basset",
 "desc": "Stronghold -- the bunkered [HEAVY] build of Beacon Basset's line (Support, K9). Up-armored: +28% HP and heavier plating soak hits, trading bite and speed for a slower, near-unkillable frame. Same job: reveals stealth and marks foes for the pack."
},
{
 "name": "Snubnose",
 "breed": "Basset",
 "class": "K9 Circuitry",
 "factionId": "k9_circuitry",
 "rarity": "Common",
 "cost": 3,
 "role": "Support",
 "hp": 648,
 "damage": 69,
 "attack_speed": 1.01,
 "move_speed": 0.94,
 "range": 3,
 "ability": {
  "name": "Beacon",
  "description": "Reveals stealth and marks foes for the pack",
  "cooldown": 8
 },
 "abilityType": "reveal",
 "queen_target": false,
 "cardNumber": "0104",
 "isMythic": false,
 "rig": {
  "name": "Snubnose Rig",
  "rigClass": "turret_util",
  "weaponMod": "incendiary",
  "sourceCar": "Monster Truck",
  "flavor": "stripped chop-shop Turret-utility rig -- mounted gun, drone bay, rail platform"
 },
 "variant": "STREET",
 "family": "Beacon Basset",
 "desc": "Snubnose -- the stripped [STREET] build of Beacon Basset's line (Support, K9). Glass-cannon: +25% damage and quicker, panels torn off for the kill, but folds to one clean shot. Same job: reveals stealth and marks foes for the pack."
},
{
 "name": "Emplacement",
 "breed": "German Shepherd",
 "class": "K9 Circuitry",
 "factionId": "k9_circuitry",
 "rarity": "Legendary",
 "cost": 8,
 "role": "Structure",
 "hp": 1856,
 "damage": 120,
 "attack_speed": 0.9,
 "move_speed": 0.0,
 "range": 4,
 "ability": {
  "name": "Overclock",
  "description": "Heavy static turret with a burst fire window",
  "cooldown": 16
 },
 "abilityType": "ramp",
 "queen_target": false,
 "cardNumber": "0105",
 "isMythic": false,
 "rig": {
  "name": "Emplacement Rig",
  "rigClass": "turret_util",
  "weaponMod": "incendiary",
  "sourceCar": "Monster Truck",
  "flavor": "bunkered Turret-utility rig -- mounted gun, drone bay, rail platform"
 },
 "variant": "HEAVY",
 "family": "Nova Shepherd",
 "desc": "Emplacement -- the bunkered [HEAVY] build of Nova Shepherd's line (Structure, K9). Up-armored: +28% HP and heavier plating soak hits, trading bite and speed for a slower, near-unkillable frame. Same job: heavy static turret with a burst fire window."
},
{
 "name": "Salvo",
 "breed": "German Shepherd",
 "class": "K9 Circuitry",
 "factionId": "k9_circuitry",
 "rarity": "Rare",
 "cost": 6,
 "role": "Structure",
 "hp": 1044,
 "damage": 156,
 "attack_speed": 1.12,
 "move_speed": 0.0,
 "range": 4,
 "ability": {
  "name": "Overclock",
  "description": "Heavy static turret with a burst fire window",
  "cooldown": 12
 },
 "abilityType": "ramp",
 "queen_target": false,
 "cardNumber": "0106",
 "isMythic": false,
 "rig": {
  "name": "Salvo Rig",
  "rigClass": "turret_util",
  "weaponMod": "incendiary",
  "sourceCar": "Monster Truck",
  "flavor": "stripped chop-shop Turret-utility rig -- mounted gun, drone bay, rail platform"
 },
 "variant": "STREET",
 "family": "Nova Shepherd",
 "desc": "Salvo -- the stripped [STREET] build of Nova Shepherd's line (Structure, K9). Glass-cannon: +25% damage and quicker, panels torn off for the kill, but folds to one clean shot. Same job: heavy static turret with a burst fire window."
}
];

const CANON_DECKS = [
{
 "name": "CROWN MARCH",
 "class": "Boneguard Crew",
 "archetype": "Beatdown",
 "avgCost": 6.2,
 "wildcard": false,
 "winCon": "One unstoppable splash-tank push behind $BCARDD they cannot answer in time.",
 "cards": [
  "$BCARDD",
  "Iron Rottweiler",
  "Stonejaw",
  "Warden Newfie",
  "Balboa",
  "Alloy Akita",
  "Brick Bullmastiff",
  "Grit Bulldog",
  "Boneshatter Freeze",
  "Copper Chow",
  "Tank Pug"
 ]
},
{
 "name": "HYPER LOOP",
 "class": "Zoomie Syndicate",
 "archetype": "Cycle",
 "avgCost": 3.3,
 "wildcard": false,
 "winCon": "Death by a thousand cuts: cheapest deck, fastest hand, never stop chipping.",
 "cards": [
  "Neon Whippet",
  "Drift Sheltie",
  "Pixel Greyhound",
  "Turbo Jack",
  "Byte Beagle",
  "Glitch Basenji",
  "Jolt",
  "Circuit Shiba",
  "Flash Saluki",
  "Bolt Corgi",
  "Razor Vizsla"
 ]
},
{
 "name": "SIGNAL LOCKDOWN",
 "class": "Leashbreak Tactix",
 "archetype": "Control",
 "avgCost": 4.5,
 "wildcard": false,
 "winCon": "Out-resource and outlast: slow, silence and disable every push, win the chip war with Rosco.",
 "cards": [
  "Rosco",
  "Noir Setter",
  "Synth Collie",
  "Pulse Border Collie",
  "Chill Samoyed",
  "Prism Poodle",
  "Signal Pointer",
  "Tar Pour",
  "Echo Dalmatian",
  "Static Sheba Inu",
  "Vibe Shih Tzu"
 ]
},
{
 "name": "TURRET TRAP",
 "class": "K9 Circuitry",
 "archetype": "Siege",
 "avgCost": 4.5,
 "wildcard": false,
 "winCon": "Park static turrets and protect the engine while it chips from range.",
 "cards": [
  "Crown Foxhound",
  "Nova Shepherd",
  "Grid Schnauzer",
  "Chrome Airedale",
  "Laser Beagle",
  "Beacon Basset",
  "Volt Corgi",
  "Rail Terrier",
  "Snare Trap",
  "Flux Pomeranian",
  "Pixel Pug"
 ]
},
{
 "name": "SKY PACK",
 "class": "Zoomie Syndicate",
 "archetype": "Air",
 "avgCost": 3.2,
 "wildcard": false,
 "winCon": "Flood with AIR a ground-only army physically cannot hit; punish light anti-air.",
 "cards": [
  "Bolt Corgi",
  "Flash Saluki",
  "Neon Dachshund",
  "Pixel Greyhound",
  "Ghost Spaniel",
  "Tank Pug",
  "Jolt",
  "Pixel Pug",
  "Neon Whippet",
  "Drift Sheltie",
  "Aero Malinois"
 ]
},
{
 "name": "IRON WALL",
 "class": "Boneguard Crew",
 "archetype": "Heavy-Tank",
 "avgCost": 6.6,
 "wildcard": false,
 "winCon": "Build an immortal tank ball (double Vanguard + heal + shield) that does not die on the walk.",
 "cards": [
  "$BCARDD",
  "Iron Rottweiler",
  "Granite Saint",
  "Rust Cane Corso",
  "Stonejaw",
  "Warden Newfie",
  "Alloy Akita",
  "Holo Husky",
  "Pulse Border Collie",
  "Boneshatter Freeze",
  "Tank Pug"
 ]
},
{
 "name": "DRONE FLOOD",
 "class": "K9 Circuitry",
 "archetype": "Swarm-Bait",
 "avgCost": 3.7,
 "wildcard": false,
 "winCon": "Bait the one splash or spell, then overwhelm with constant spawned drones.",
 "cards": [
  "Circuit Retriever",
  "Grid Schnauzer",
  "Chrome Airedale",
  "Bolt Corgi",
  "Volt Corgi",
  "Beacon Basset",
  "Neon Dachshund",
  "Rail Terrier",
  "Snare Trap",
  "Flux Pomeranian",
  "Pixel Pug"
 ]
},
{
 "name": "HEX STORM",
 "class": "Leashbreak Tactix",
 "archetype": "Spell-heavy",
 "avgCost": 3.3,
 "wildcard": false,
 "winCon": "Run all 5 spells; bait support out, melt every push, finish with Strike + Jolt while Byte Beagle chips.",
 "cards": [
  "Boneshatter Freeze",
  "Strike",
  "Tar Pour",
  "Jolt",
  "Snare Trap",
  "Signal Pointer",
  "Byte Beagle",
  "Echo Dalmatian",
  "Glitch Basenji",
  "Static Sheba Inu",
  "Vibe Shih Tzu"
 ]
},
{
 "name": "DECAPITATION",
 "class": "K9 Circuitry",
 "archetype": "Triple-Assassin Queen Dive",
 "avgCost": 5.0,
 "wildcard": true,
 "winCon": "Ignore the lane war; run every Queen-target threat and assassinate the Queen before they build a defense.",
 "cards": [
  "Crown Foxhound",
  "Jagged",
  "Rosco",
  "Circuit Shiba",
  "Byte Beagle",
  "Ghost Spaniel",
  "Jolt",
  "Snare Trap",
  "Tank Pug",
  "Static Sheba Inu",
  "Drift Sheltie"
 ]
},
{
 "name": "FOUR CROWNS",
 "class": "Boneguard Crew",
 "archetype": "Rainbow Midrange Toolbox",
 "avgCost": 4.6,
 "wildcard": true,
 "winCon": "No single plan: one signature tool from all 4 factions; out-value every matchup by always having the answer.",
 "cards": [
  "Balboa",
  "Aero Malinois",
  "Noir Setter",
  "Chrome Airedale",
  "Razor Vizsla",
  "Grit Bulldog",
  "Prism Poodle",
  "Beacon Basset",
  "Strike",
  "Turbo Jack",
  "Glitch Basenji"
 ]
}
];

// ==========================================================================
// COMBAT CATEGORIES -- domain / targets / splash (Combat Spec sections 1-3)
// Annotated here (and in cards.json SoT via _build_canon.py) so the engine reads
// them verbatim. Derivation rule (Spec section 1/2):
//   targets  : MELEE (range 1) -> 'ground' (cannot hit air);
//              RANGED (range >= 2) -> 'both' (anti-air by default).
//   domain   : 'ground' for everyone EXCEPT the hand-tagged AIR list below.
//   splash   : derived weaponType cannon|spread -> true (radius), else single.
// A few legendary/identity overrides follow the derived defaults.
// ==========================================================================
// ~8-10 FLYERS (domain:'air'), spread across all 4 factions, lore-fit to
// drone / jetpack / hover rigs. At least one anti-air answer exists per faction
// (every range>=2 card is anti-air), so no faction is helpless vs air.
//   Boneguard (1): Tank Pug              -- hover support-drone (the wall stays grounded otherwise)
//   Zoomie    (4): Pixel Greyhound, Neon Whippet, Flash Saluki, Bolt Corgi -- the AIR faction (jetpack sprinters + drone carrier)
//   Leashbreak(2): Ghost Spaniel, Drift Sheltie -- phantom flyer + hover tag-support
//   K9        (2): Neon Dachshund, Pixel Pug     -- tunnel-drone + mini-pup drone
const AIR_UNITS = {
  'Tank Pug':true,
  'Pixel Greyhound':true, 'Neon Whippet':true, 'Flash Saluki':true, 'Bolt Corgi':true,
  'Ghost Spaniel':true, 'Drift Sheltie':true,
  'Neon Dachshund':true, 'Pixel Pug':true,
  // AK-AIRFIX: range-1 MELEE skirmisher variants moved to GROUND so the 35 ground-only
  // cards can answer them (was unhittable melee air). Grounded: Roadblock, Nitro,
  // Crashcage, Hotwire. Kept air below = RANGED (range 2) anti-air flyers, NOT the
  // melee-air break (Spike is range 2 Leashbreak, mispaired with Nitro by stats):
  'Bumper':true, 'Backfire':true, 'Hardline':true, 'Spike':true
};
// Identity splash overrides (Spec section 2/3: a few legendaries crush swarms).
// Beyond the cannon/spread auto-splash, these single-weapon cards also splash.
//   $BCARDD  -- Mythic king, his ram-plow shockwave hits a small radius
//   Crown Foxhound -- Mythic, Royal Hunt shred carries a small AOE
//   Nova Shepherd  -- heavy static turret, burst window splashes
const SPLASH_OVERRIDE = { '$BCARDD':1.4, 'Crown Foxhound':1.3, 'Nova Shepherd':1.5, 'Emplacement':1.5, 'Salvo':1.5 };
// weaponType derivation MUST mirror engine.deriveWeaponType so the splash flag
// matches the projectile the engine launches. (cannon + spread -> splash.)
function _canonWeaponType(role, range, abilityType){
  if(role==='Spawner' || abilityType==='spawn' || abilityType==='chain') return 'spread';
  if(role==='Lancer' || abilityType==='pierce' || abilityType==='line') return 'lance';
  if(role==='Hacker' || role==='Controller' || range>=4) return 'beam';
  if((role==='Vanguard' || role==='Blaster') && range>=2) return 'cannon';
  if((role==='Striker' || role==='Skirmisher') && range>=2) return 'bullet';
  if(range>=2) return 'bullet';
  return 'melee';
}
(function annotateCombat(){
  CANON_CARDS.forEach(function(c){
    var ranged = c.range >= 2;
    var wt = _canonWeaponType(c.role, c.range, c.abilityType);
    var splashes = (wt==='cannon' || wt==='spread');
    var radius = splashes ? (wt==='cannon' ? 2.2 : 1.8) : 0;
    if(SPLASH_OVERRIDE[c.name]){ splashes = true; radius = SPLASH_OVERRIDE[c.name]; }
    c.domain = AIR_UNITS[c.name] ? 'air' : 'ground';
    c.targets = ranged ? 'both' : 'ground';          // melee can't hit flyers
    c.splash = !!splashes;
    c.splashRadius = radius;
  });
})();

// ==========================================================================
// SPELLS -- new card type (Combat Spec section 4). Cast at a TARGET POINT/AREA
// (not lane-deployed). Cost energy + have a cooldown. type:'spell'. The engine
// (mapSpellToEngine + castSpell) reads `effect`, `radius`, `duration`, `cost`,
// `cooldown`, `damage`. All 5 spells built per the locked operator decisions.
// ==========================================================================
const CANON_SPELLS = [
  {
    name: 'Boneshatter Freeze', short: 'FREEZE',
    type: 'spell', factionId: 'boneguard_crew', class: 'Boneguard Crew',
    rarity: 'Epic', cost: 5, cooldown: 14,
    effect: 'freeze', radius: 3.0, duration: 3.0, damage: 0,
    spellNumber: 'S001', glyph: '❄',  // snowflake
    fx: 'freeze',
    description: 'Enemies in the area STOP (no move, no attack) for ~3s. Towers freeze too.'
  },
  {
    name: 'Tar Pour', short: 'TAR SLOW',
    type: 'spell', factionId: 'leashbreak_tactix', class: 'Leashbreak Tactix',
    rarity: 'Rare', cost: 4, cooldown: 12,
    effect: 'slow', radius: 3.2, duration: 4.0, damage: 0, slowPct: 0.35,
    spellNumber: 'S002', glyph: '◉',  // fisheye / tar blob
    fx: 'slow',
    description: 'Tar slick: -35% move + -35% attack speed to enemies in the area for ~4s.'
  },
  {
    name: 'Snare Trap', short: 'SNARE',
    type: 'spell', factionId: 'k9_circuitry', class: 'K9 Circuitry',
    rarity: 'Rare', cost: 3, cooldown: 13,
    effect: 'trap', radius: 1.8, duration: 1.6, damage: 90,
    spellNumber: 'S003', glyph: '☢',  // hazard / trap
    fx: 'trap',
    description: 'Plants a hidden trap. Arms, then roots + small damage when an enemy crosses it. Zone control.'
  },
  {
    name: 'Jolt', short: 'JOLT',
    type: 'spell', factionId: 'zoomie_syndicate', class: 'Zoomie Syndicate',
    rarity: 'Common', cost: 3, cooldown: 9,
    effect: 'zap', radius: 2.4, duration: 0.5, damage: 210, // AK-SPELLFIX: 130->210, scaled proportional to Strike; stays chip+stun (cannot solo a 420-HP troop)
    spellNumber: 'S004', glyph: '⚡',  // high voltage
    fx: 'zap',
    description: 'Instant AOE damage + 0.5s stun. Kills swarms, resets attacks.'
  },
  {
    name: 'Strike', short: 'STRIKE',
    type: 'spell', factionId: 'neutral', class: 'Neutral',
    rarity: 'Epic', cost: 4, cooldown: 11,
    effect: 'strike', radius: 2.6, duration: 0, damage: 520, // AK-SPELLFIX: 320->520 so it kills the cheapest real troops (min HP ~420-504); CC spells (Freeze/Tar/Snare) untouched
    spellNumber: 'S005', glyph: '✹',  // burst star
    fx: 'strike',
    description: 'The fireball: medium AOE burst damage at a point.'
  }
];

if (typeof module !== 'undefined' && module.exports) { module.exports = { CANON_META, CANON_CARDS, CANON_DECKS, CANON_SPELLS }; }
// Browser: top-level const does NOT attach to window, but engine.js reads window.CANON_*.
// Publish to the global object so the engine (and any script) can see the canon.
if (typeof window !== 'undefined') { window.CANON_META = CANON_META; window.CANON_CARDS = CANON_CARDS; window.CANON_DECKS = CANON_DECKS; window.CANON_SPELLS = CANON_SPELLS; }

// AK-ARTRESOLVER 2026-06-18: THE single source of truth for card/spell art, loaded by BOTH index.html and
// shop/shop.html (both load canon.js). Every surface (in-game hand+battlefield artSrc, shop artCandidates, deck
// tileArt) calls this instead of computing paths itself -- ends the "3 resolvers disagree" bug class.
// Returns the path RELATIVE to assets/ (callers prepend their base: index='assets/', shop=ASSET_BASE='../assets/').
// Canonical naming (consolidated): cards = cards/<NNNN>_<name_slug>.png ; spells = spells/<name-slug>.png.
// The custom art for every card was migrated to this name, so the art always follows its card.
(function(g){
  function akSlug(n){ return String(n||'').toLowerCase().replace(/[^a-z0-9]+/g,'_').replace(/^_+|_+$/g,''); }
  g.akSlug = akSlug;
  g.akCardArtRel = function(card){
    if(!card) return '';
    var s = akSlug(card.name);
    if(card.type==='spell' || card.isSpell || card.abilityType==='spell'){
      return s ? ('spells/' + s.replace(/_/g,'-') + '.png') : '';     // spells use a hyphen slug
    }
    var num = String(card.cardNumber || card.num || card.id || '').replace(/[^0-9]/g,'');
    if(!num || !s) return '';
    num = ('0000' + num).slice(-4);
    return 'cards/' + num + '_' + s + '.webp';                         // AK-WEBP 2026-06-18: ~93% smaller than PNG; PNG stays as the akImgErr onerror fallback
  };
  // AK-WEBP onerror fallback: if a .webp <img> fails to load (missing file or no WebP support), swap to the .png
  // ONCE. Returns true if it retried (caller should NOT remove the img yet), false otherwise. Safe no-op on non-webp.
  g.akImgErr = function(img){ try{ if(img && !img._fb && /\.webp(\?|$)/.test(img.src||'')){ img._fb=1; img.src=String(img.src).replace(/\.webp(\?|$)/, '.png$1'); return true; } }catch(_e){} return false; };
})(typeof window !== 'undefined' ? window : (typeof global !== 'undefined' ? global : this));
