/* AK-LORE: Alley Kingz card lore -- taglines + bios for every canon card and spell.
   Plain JS, headless-safe. Keys = cardNumber (cards) / spellNumber (spells).
   NO em-dashes anywhere in this file (hook law); use -- instead. */
(function () {
  var LORE = {
    /* ---------------- BONEGUARD CREW ---------------- */
    "0001": {
      tagline: "Crowns get taken, never given. Kneel or bleed.",
      bio: "The Yung Printz. A white-coat Dogo Argentino who took the alley throne bare-fanged and never looked back. Crownbreaker shields him while he walks straight at the Queen herself."
    },
    "0002": {
      tagline: "Walls fall down. I don't.",
      bio: "Old Mastiff enforcer who held the Boneguard gate alone for three nights. His Armor Pulse is the crew's heartbeat; stand close and the hits land softer."
    },
    "0003": {
      tagline: "One hand. Lights out.",
      bio: "Pit-raised Boxer who learned the sweet science under a broken streetlamp. His Haymaker puts the first fool to swing on the Boneguard flat on the concrete."
    },
    "0004": {
      tagline: "Hurt me. See what happens.",
      bio: "A Rottweiler with rebar in his soul. Boneguard keeps him on the front because pain is his fuel; bleed him past forty and the Overclock Rage bite gets ugly."
    },
    "0005": {
      tagline: "Hide behind me. Everybody does.",
      bio: "A St. Bernard mountain of mercy turned muscle. The crew calls his Bodywall the church door; whatever the alley throws, Granite Saint takes it first."
    },
    "0006": {
      tagline: "Round ten is my round one.",
      bio: "A Bulldog who never won pretty, only late. Every minute he brawls, the Brawler bite climbs; the Boneguard bet on him when the fight runs long."
    },
    "0007": {
      tagline: "Back up. I won't ask twice.",
      bio: "An Akita forged in scrapyard discipline. One Shock Push from his alloy shoulders and a whole melee line learns where the Boneguard property line sits."
    },
    "0008": {
      tagline: "Nobody dies on my watch.",
      bio: "A Newfoundland who pulled drowning pups from the canal before he ever pulled rank. His Fortify aura makes every Boneguard body harder to put down."
    },
    "0009": {
      tagline: "Come close. I'll rearrange you.",
      bio: "A rust-coated Cane Corso who works the door at every Boneguard spot. His Grav Pull pulse scatters crowders like bottles off a stoop."
    },
    "0010": {
      tagline: "Small dog. Big damn wall.",
      bio: "A Pug who refused to be the crew mascot, so he became the crew shield. One Shield Bark and an ally walks away from a hit that should have ended them."
    },
    "0011": {
      tagline: "Every bite buys the next one.",
      bio: "A copper Chow who collects debts in teeth. The Bitechain ramps with every hit; the Boneguard say once he latches, the math only gets worse for you."
    },
    "0012": {
      tagline: "Swing on brick, break your paw.",
      bio: "A Bullmastiff poured, not born. When Stonehide kicks in, the Boneguard front line stops feeling anything and the other crew starts feeling everything."
    },

    /* ---------------- ZOOMIE SYNDICATE ---------------- */
    "0013": {
      tagline: "Blink. You're already gone.",
      bio: "The Syndicate's quietest contract. A Doberman who steps through shadow and lands fangs-first on the Queen. Nobody has seen Jagged arrive, only leave."
    },
    "0014": {
      tagline: "One line. Everybody on it pays.",
      bio: "A Vizsla who runs the straightest route in the Syndicate. Pierce Rush turns a lane into a receipt; every dog standing on it gets charged."
    },
    "0015": {
      tagline: "You'll feel the second hit first.",
      bio: "A Malinois trained for double-tap discipline. Twin Strike lands two bites in one swing; Syndicate runners swear the echo hurts more than the shot."
    },
    "0016": {
      tagline: "Catch me after the kill. You won't.",
      bio: "A Greyhound who treats the arena like a loop track. Every kill refreshes the Dash Loop, and Pixel never stops lapping the bodies."
    },
    "0017": {
      tagline: "First bite's already behind you.",
      bio: "A Shiba who wired blink tech into her own collar. Blink Bite hops her past your guard before the opening bell finishes ringing."
    },
    "0018": {
      tagline: "Wrong lane? No such thing.",
      bio: "A Saluki built like a rumor. Sidecut sends her lane to lane into your backline, and by the time you turn around the Syndicate already cashed out."
    },
    "0019": {
      tagline: "I never roll alone. Damn right.",
      bio: "A Corgi with a litter of trouble on speed dial. Spark Pups drops three mini zoomers, and suddenly the Syndicate outnumbers you everywhere at once."
    },
    "0020": {
      tagline: "Shh. Your tricks just died.",
      bio: "A barkless Basenji who speaks fluent static. One Signal Scramble and your favorite ability goes silent right when you needed it to sing."
    },
    "0021": {
      tagline: "Slow? Never met her.",
      bio: "A neon-striped Whippet who slips every net the alley throws. Slipstream shrugs off slows and bends around hits; the Syndicate calls her uncatchable."
    },
    "0022": {
      tagline: "Hello and goodbye, same second.",
      bio: "A Jack Russell with one setting: detonate. Burst Bite crits the instant he lands; Syndicate crews deploy Turbo and start counting the refund."
    },
    "0023": {
      tagline: "Keep up. I'll make you faster.",
      bio: "A Sheltie pacer who runs the Syndicate's warmups. Tag Boost puts wind under every nearby paw; the whole pack moves like it stole something."
    },
    "0024": {
      tagline: "Shields are just suggestions.",
      bio: "A Beagle gunner with a long memory and longer range. Tracer Round punches through shields, and yes, it reaches the Queen."
    },

    /* ---------------- LEASHBREAK TACTIX ---------------- */
    "0025": {
      tagline: "Every leash breaks. I'm the proof.",
      bio: "A Cattle Dog who chewed off his own chain and came back for everyone else's. Leashbreak kills a tower's fire cold, then Rosco walks at the Queen."
    },
    "0026": {
      tagline: "Your tower works for me now.",
      bio: "A Border Collie who herds machines instead of sheep. One Hack Jam and the tower that was shooting your pack just files for unemployment."
    },
    "0027": {
      tagline: "Lights out, sharpshooters.",
      bio: "A Setter in a coat the color of midnight. Blackout drops a dark so thick that ranged shooters fire at memories and hit nothing."
    },
    "0028": {
      tagline: "Hold the line. I'll hold you.",
      bio: "A Border Collie medic with a saboteur's nerve. Barrier Ring drops a shield dome over the front line; Tactix doctrine says nobody advances uncovered."
    },
    "0029": {
      tagline: "Breathe. The pack patches up.",
      bio: "A Husky who carries the field kit and the morale. Heal Beacon pulses life back into the Tactix pack while the towers go dark around them."
    },
    "0030": {
      tagline: "The smile's warm. The bark ain't.",
      bio: "A Samoyed who grins like sunrise and breathes like January. Frost Bark fans out a cone of cold that drags everything caught in it to a crawl."
    },
    "0031": {
      tagline: "Pretty? Sure. Watch your shields.",
      bio: "A Poodle who turned showcoat into camouflage. Shatter strips an enemy's shields to glass dust, then wards a packmate with the pieces."
    },
    "0032": {
      tagline: "I point. The pack erases.",
      bio: "A Pointer who never misses a mark because the mark is the job. Tag Shot lights up hidden dogs and softens them for the Tactix follow-up."
    },
    "0033": {
      tagline: "Swing all you want. I'm not here.",
      bio: "A Spaniel who learned to step sideways out of the world. Phase blinks her untargetable for a breath; the Tactix use that breath to win."
    },
    "0034": {
      tagline: "My howl gets there before I do.",
      bio: "A Dalmatian whose voice rolls down the lane like wet asphalt. Echo Howl drags every enemy in its wake a half-step slower than they need to be."
    },
    "0035": {
      tagline: "One ping. Dead air.",
      bio: "A Shiba who works the Tactix switchboard. Ping clips a quick silence on the first target it finds, cheap and rude and exactly on time."
    },
    "0036": {
      tagline: "Easy now. I got you, hun.",
      bio: "A Shih Tzu who has stitched up half the alley and judged all of it. Soothe drips a small steady heal into whoever is hurting worst."
    },

    /* ---------------- K9 CIRCUITRY ---------------- */
    "0037": {
      tagline: "Castles crack. Queens fall.",
      bio: "A Foxhound bred to run royalty to ground. Royal Hunt shreds structures like wet cardboard, and the trail always ends at the Queen."
    },
    "0038": {
      tagline: "Fetch? I fetch in fives.",
      bio: "A Retriever who never came back with just the ball. Drone Swarm releases five buzzing friends, and K9 Circuitry calls that a light delivery."
    },
    "0039": {
      tagline: "When I burst, the block goes quiet.",
      bio: "A German Shepherd fused into a heavy weapons frame. Overclock winds the turret up to a burst window that ends whole conversations."
    },
    "0040": {
      tagline: "Give me a second. Then run.",
      bio: "A Beagle bolted into a turret chassis. Overheat ramps the fire rate the longer the barrel sings; patience is the most dangerous thing he owns."
    },
    "0041": {
      tagline: "Three sparks, zero mercy.",
      bio: "A Corgi engineer with a battery pack bigger than he is. Spark Pups deploys three drones that swarm like static with a grudge."
    },
    "0042": {
      tagline: "Step in my grid. Stay a while.",
      bio: "A Schnauzer who wired the whole intersection. Grid Lock fields a turret zone that slows every attacker dumb enough to walk through it."
    },
    "0043": {
      tagline: "One bolt, three bodies.",
      bio: "A chrome-plated Airedale marksdog. Arc Shot chains lightning across three targets; Circuitry accountants log it as efficiency."
    },
    "0044": {
      tagline: "I see everything. So does the pack.",
      bio: "A Basset with ears tuned to frequencies the alley forgot. Beacon drags stealth into the open and marks it for everyone holding a grudge."
    },
    "0045": {
      tagline: "Long dog, longer tunnels.",
      bio: "A Dachshund who dug under the whole grid before anyone mapped it. Tunnel Drones pops two attackers up from dirt nobody was watching."
    },
    "0046": {
      tagline: "Tiny? I power the whole block.",
      bio: "A Pomeranian who is ninety percent fur and ten percent reactor. Battery overcharges nearby turrets until the night smells like ozone."
    },
    "0047": {
      tagline: "Walls hate me. Feeling's mutual.",
      bio: "A Terrier with a rail cannon and a personal vendetta against architecture. Rail Shot rides the long line and bills structures double."
    },
    "0048": {
      tagline: "One drone. All heart.",
      bio: "A Pug who saved his whole stipend for a single guard drone. Mini Pup deploys it proudly; Circuitry vets stopped laughing after it clutched a match."
    },

    /* ---------------- BONEGUARD VARIANTS ---------------- */
    "0049": {
      tagline: "They name streets after my left.",
      bio: "A Boxer legend from the old fight pits under the overpass. Cinderblock's Haymaker has ended more openings than the city ended leases."
    },
    "0050": {
      tagline: "Shake my paw. I dare you.",
      bio: "A young Boxer working the Boneguard door circuit. Knuckles greets everybody the same way: one Haymaker, one nap."
    },
    "0051": {
      tagline: "Last thing they read is my name.",
      bio: "A Rottweiler the crew only deploys when it is already personal. Push Tombstone past forty percent and Overclock Rage writes the epitaph."
    },
    "0052": {
      tagline: "The hurt just makes me honest.",
      bio: "A Rottweiler who never learned to fake being fine. Razorgums bleeds, grins, and lets Overclock Rage do the talking from there."
    },
    "0053": {
      tagline: "Hammer all day. I won't dent.",
      bio: "A St. Bernard the Boneguard use as a load-bearing teammate. Anvil's Bodywall soaks the pack's pain like it was poured for the job."
    },
    "0054": {
      tagline: "Big shoulders, short patience.",
      bio: "A St. Bernard who carries the crew and complains the whole time. Hatchet's Bodywall holds anyway; loyalty outlasts the grumbling."
    },
    "0055": {
      tagline: "Round one's a warmup, champ.",
      bio: "A Bulldog who treats every brawl like a payment plan. Bonecrusher's Brawler bite compounds; the longer you stay, the more you owe."
    },
    "0056": {
      tagline: "I start slow. I finish loud.",
      bio: "A Bulldog the bookies always undercount. Switch's Brawler engine takes a minute to warm and a crowbar to stop."
    },
    "0057": {
      tagline: "Lines break when I lean in.",
      bio: "An Akita built like cavalry that lost the horse and kept the attitude. Warhorse's Shock Push folds melee lines back into their own crew."
    },
    "0058": {
      tagline: "Tight spot? I make room.",
      bio: "An Akita who works the Boneguard's narrowest alleys. Lugnut's Shock Push clears a lane the way a tow truck clears a hydrant."
    },
    "0059": {
      tagline: "Stand by me, stand taller.",
      bio: "A Newfoundland who turned harbor-rescue lungs into battlefield doctrine. Ironhide's Fortify aura makes the whole pack harder to bury."
    },
    "0060": {
      tagline: "Crooked teeth, straight loyalty.",
      bio: "A Newfoundland with a grin only the Boneguard could love. Snaggle's Fortify keeps the crew's HP up and their excuses down."
    },
    "0061": {
      tagline: "Gravity works for me now.",
      bio: "A Cane Corso who moves like poured concrete. Slab's Grav Pull pulse drags the nearest fools out of formation and into regret."
    },
    "0062": {
      tagline: "Step in. I'll show you the door.",
      bio: "A Cane Corso bouncer with a velvet-rope memory. Brassknuck's Grav Pull tosses crowders the way he tossed troublemakers: in bulk."
    },

    /* ---------------- ZOOMIE VARIANTS ---------------- */
    "0063": {
      tagline: "Fast enough to be everywhere.",
      bio: "A Greyhound who polices the Syndicate's own streets. Roadblock's Dash Loop refreshes off every kill, so the patrol never actually ends."
    },
    "0064": {
      tagline: "Zero to gone in nothing flat.",
      bio: "A Greyhound pup running her first season. Nitro's Dash Loop keeps her lapping the arena while older dogs argue about lanes."
    },
    "0065": {
      tagline: "Blink twice if you saw me. Liar.",
      bio: "A Shiba bruiser who bolted blink tech onto a brawler's frame. Bullbar's Blink Bite hops the guard and hits like a fender."
    },
    "0066": {
      tagline: "Quick flick. Deep cut.",
      bio: "A Shiba who keeps her work short and her exits shorter. Switchblade's Blink Bite opens every fight a half-step inside your reach."
    },
    "0067": {
      tagline: "I run through, never around.",
      bio: "A Vizsla legend with a roll bar welded to his rig. Rollcage's Pierce Rush takes the straight line through everything wearing a hostile tag."
    },
    "0068": {
      tagline: "Pick a wall. I'm off all of them.",
      bio: "A Vizsla who treats geometry as a suggestion. Ricochet's Pierce Rush threads a lane and bills every dog standing on it."
    },
    "0069": {
      tagline: "Your backline is my fast lane.",
      bio: "A Saluki who crashes formations for sport. Crashcage's Sidecut swings lane to lane and lands where your softest dogs were hiding."
    },
    "0070": {
      tagline: "Borrowed speed, never returned.",
      bio: "A Saluki who hot-rods his own legs before every match. Hotwire's Sidecut flanks the backline before the alarm finishes its first beep."
    },
    "0071": {
      tagline: "Pups up! Squad rolls deep.",
      bio: "A Corgi den mother with a glovebox full of trouble. Bumper's Spark Pups floods the lane with three mini zoomers and zero apologies."
    },
    "0072": {
      tagline: "Loud exit, louder entrance.",
      bio: "A Corgi whose deployments sound like an engine giving up. Backfire's Spark Pups arrive in a bang of three and scatter like sparks."
    },
    "0073": {
      tagline: "Silence is my native tongue.",
      bio: "A Basenji who jams stadiums for fun. Gridiron's Signal Scramble mutes a target's ability right as the crowd leans in."
    },
    "0074": {
      tagline: "Heard nothing? That was me.",
      bio: "A Basenji who leaves no sound and less evidence. Skidmark's Signal Scramble cuts your trick's feed and is gone before the static clears."
    },
    "0075": {
      tagline: "Two hits. You only count one.",
      bio: "A Malinois the Syndicate hires when one bite is not a statement. Deadweight's Twin Strike doubles up so fast the second hit feels like deja vu."
    },
    "0076": {
      tagline: "First beat, second beat, done.",
      bio: "A Malinois with a metronome where her mercy should be. Flatline's Twin Strike lands in rhythm; the chart goes quiet after."
    },

    /* ---------------- LEASHBREAK VARIANTS ---------------- */
    "0077": {
      tagline: "Towers obey me or go dark.",
      bio: "A Border Collie who herds the city's defenses like livestock. Firewall's Hack Jam shuts a tower's mouth mid-sentence."
    },
    "0078": {
      tagline: "I herd code like sheep.",
      bio: "A Border Collie who left the pasture for the power grid. Glitchfork's Hack Jam pens a tower in and leaves it bleating."
    },
    "0079": {
      tagline: "Locked in. Nobody drops today.",
      bio: "A Husky who bolts the door on death itself. Deadbolt's Heal Beacon pulses the Tactix pack back to fighting weight mid-brawl."
    },
    "0080": {
      tagline: "White noise, warm medicine.",
      bio: "A Husky medic who hums while she works. Static's Heal Beacon washes over the pack like a radio between stations, steady and kind."
    },
    "0081": {
      tagline: "Cold front, by request.",
      bio: "A Samoyed who delivers winter on a schedule. Bunkerlink's Frost Bark fans a freezing cone that turns a push into a slow, bad idea."
    },
    "0082": {
      tagline: "Fluffy outside. Freezer inside.",
      bio: "A Samoyed pup with a bark colder than her pedigree. Shortcircuit's Frost Bark slows whole crowds while she wags about it."
    },
    "0083": {
      tagline: "Your shield? Already glass.",
      bio: "A Poodle who studied barriers just to insult them. Faraday's Shatter strips enemy shields and gifts the shards to an ally as a ward."
    },
    "0084": {
      tagline: "I break charms for a living.",
      bio: "A Poodle who works the Tactix counter-magic desk. Hexer's Shatter pops shields cheap and fast, then wards whoever needs it most."
    },
    "0085": {
      tagline: "Aim well. It won't matter.",
      bio: "A Setter who soaks up light like a debt collector. Sandbag's Blackout blinds the ranged line until every shot lands in yesterday."
    },
    "0086": {
      tagline: "Snipers cry in the dark.",
      bio: "A Setter who broadcasts pure nothing. Whitenoise's Blackout drops over the shooters, and the Tactix walk through their misses."
    },
    "0087": {
      tagline: "Marked means finished.",
      bio: "A Pointer who runs the Tactix's quiet list. Blacksite's Tag Shot reveals the hidden, weakens the proud, and files the rest under done."
    },
    "0088": {
      tagline: "I deliver bad news, tagged.",
      bio: "A Pointer courier who never loses an address. Carrier's Tag Shot pins a mark on a target and lets the pack handle the signature."
    },
    "0089": {
      tagline: "Hit the air. I'll wait.",
      bio: "A Spaniel who phases out of the world like rent was due. Hardline's Phase buys an untouchable window the Tactix spend ruthlessly."
    },
    "0090": {
      tagline: "Now you see me. Now you don't.",
      bio: "A Spaniel pup with a ghost's instincts. Spike's Phase slips her out of a killing blow and back in time to bite about it."
    },
    "0091": {
      tagline: "My ring, my rules, my line.",
      bio: "A Border Collie who drew a circle and dared the city to cross it. Bulwark's Barrier Ring shields the whole front line under one roof."
    },
    "0092": {
      tagline: "Dim the lights, raise the wall.",
      bio: "A Border Collie who keeps the grid humble. Brownout's Barrier Ring throws an area shield up just as the lane gets loud."
    },

    /* ---------------- K9 CIRCUITRY VARIANTS ---------------- */
    "0093": {
      tagline: "Dig in. I only get hotter.",
      bio: "A Beagle welded into a forward turret post. Bunker's Overheat ramps fire the longer he holds; he has never once stopped holding."
    },
    "0094": {
      tagline: "Cheap seat, steady heat.",
      bio: "A Beagle turret on a budget chassis. Buckshot's Overheat spins up slow, but the lane learns fast why Circuitry keeps buying them."
    },
    "0095": {
      tagline: "Short legs, heavy ordnance.",
      bio: "A Corgi who signs every delivery with a boom. Howitzer's Spark Pups drops three drones that hit way above their pay grade."
    },
    "0096": {
      tagline: "Mind your step. Too late.",
      bio: "A Corgi who seeds the lane before you know it is a lane. Tripwire's Spark Pups spring three drones out of nowhere worth checking."
    },
    "0097": {
      tagline: "Run through my field. Slowly.",
      bio: "A Schnauzer who fenced the block in slow-light. Flakwall's Grid Lock turns a charge into a crawl and a crawl into target practice."
    },
    "0098": {
      tagline: "My grid never blinks.",
      bio: "A Schnauzer with a watchmaker's patience. Deadeye's Grid Lock field drags attackers down to a speed his turrets find polite."
    },
    "0099": {
      tagline: "Five birds, one bad day.",
      bio: "A Retriever housed in an armored casemate rig. Casemate's Drone Swarm releases five units; Circuitry logs the rest as cleanup."
    },
    "0100": {
      tagline: "I share. Everybody gets a piece.",
      bio: "A Retriever with a generous streak and a violent inventory. Shrapnel's Drone Swarm hands out five drones like party favors."
    },
    "0101": {
      tagline: "One arc, three regrets.",
      bio: "An Airedale dug into a fortified firing slit. Pillbox's Arc Shot chains across three targets before the first one yelps."
    },
    "0102": {
      tagline: "Twitchy? I call it ready.",
      bio: "An Airedale who fires on instinct and apologizes never. Hairtrigger's Arc Shot jumps three bodies the moment one steps wrong."
    },
    "0103": {
      tagline: "Low ears hear every secret.",
      bio: "A Basset who built a listening post out of patience. Stronghold's Beacon drags stealth into the floodlights and marks it for the pack."
    },
    "0104": {
      tagline: "Short range, long memory.",
      bio: "A Basset who never forgets a scent or a slight. Snubnose's Beacon lights up hiders cheap and early, exactly when it stings."
    },
    "0105": {
      tagline: "I am the position. Hold me.",
      bio: "A German Shepherd who became the fortification he was guarding. Emplacement's Overclock burst window ends pushes in one breath."
    },
    "0106": {
      tagline: "Patience, then everything at once.",
      bio: "A German Shepherd turret with military bearing. Salvo's Overclock holds, holds, holds, then empties the whole argument downrange."
    },

    /* ---------------- SPELLS ---------------- */
    "S001": {
      tagline: "The whole block holds its breath.",
      bio: "Boneguard winter doctrine: shatter the cold main and let the street freeze mid-swing. Everything in the zone stops, towers included."
    },
    "S002": {
      tagline: "Sticky streets settle debts.",
      bio: "Leashbreak crews crack a tar line and pour the lane black. Enemies caught in it move slow, swing slow, and think about their choices."
    },
    "S003": {
      tagline: "The floor was never your friend.",
      bio: "K9 Circuitry buries a hidden snare in the asphalt. It arms quiet, then roots the first dog across it with a bite of voltage."
    },
    "S004": {
      tagline: "One spark, whole swarm drops.",
      bio: "Zoomie street-tech in a bottle: an instant jolt that fries a crowd, stuns for a blink, and resets every attack worth fearing."
    },
    "S005": {
      tagline: "Fire answers everything.",
      bio: "The neutral classic. No faction owns it, every faction packs it: one burning burst at a point, paid in full on arrival."
    }
  };

  function AK_LORE_GET(num) {
    if (num != null && LORE[num]) return LORE[num];
    return {
      tagline: "Street legend in the making.",
      bio: "No file on this one yet. The alley keeps its secrets."
    };
  }

  if (typeof window !== "undefined") {
    window.AK_LORE = LORE;
    window.AK_LORE_GET = AK_LORE_GET;
  }
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { AK_LORE: LORE, AK_LORE_GET: AK_LORE_GET };
  }
})();
