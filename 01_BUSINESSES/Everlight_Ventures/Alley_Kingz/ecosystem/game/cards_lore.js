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
      bio: "A Pug who refused to be the crew mascot, so he became the crew shield. One Shield Bark and an ally walks away from a hit that should have ended them. The catch he hides under a joke about his size: every shield he drops is HP he quietly peels off his own count, and he stands where the wall ends because a pup once got clipped from the one angle he was too short to cover."
    },
    "0011": {
      tagline: "Every bite buys the next one.",
      bio: "A copper Chow who collects debts in teeth. The Bitechain ramps with every hit; the Boneguard say once he latches, the math only gets worse for you. He fronted his own family a whole season on a handshake once and never got paid, so now no marker on his row runs on trust, and there is one old tab he goes stone silent about and will never zero out."
    },
    "0012": {
      tagline: "Swing on brick, break your paw.",
      bio: "A Bullmastiff poured, not born. When Stonehide kicks in, the Boneguard front line stops feeling anything and the other crew starts feeling everything. He keeps one seam soft on purpose, because the block's other Bullmastiff, the Lot Warden, is what a dog becomes when the plate cures all the way through, and every time Brick turns the feeling off he is a half-second slower turning it back on."
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
      bio: "A neon-striped Whippet who slips every net the alley throws. Slipstream shrugs off slows and bends around hits; the Syndicate calls her uncatchable. She never lets a dog run at her shoulder, though, because she slipped a net clean once and left a slower packmate tangled in it, and uncatchable turned out to be one letter and a lifetime from un-reachable."
    },
    "0022": {
      tagline: "Hello and goodbye, same second.",
      bio: "A Jack Russell with one setting: detonate. Burst Bite crits the instant he lands; Syndicate crews deploy Turbo and start counting the refund. He pours his whole self into that first strike so nothing is left to test, which means he is never there for the middle of a fight, and lately he has started to hate the empty second after the crit as much as he loves the loud one before it."
    },
    "0023": {
      tagline: "Keep up. I'll make you faster.",
      bio: "A Sheltie pacer who runs the Syndicate's warmups. Tag Boost puts wind under every nearby paw; the whole pack moves like it stole something. She is the slowest dog in her own pack by design, handing out a race she can never enter, and she still carries the pup her pace once made fast enough to reach a bout he could not come back from."
    },
    "0024": {
      tagline: "Shields are just suggestions.",
      bio: "A Beagle gunner with a long memory and longer range. Tracer Round punches through shields, and yes, it reaches the Queen. Glass-bodied and patient, he has measured every distance on the block to the paw, including the throne rail he never talks about, and he carries one range he never fired at: the shot he held too long waiting for perfect while a dog he could have covered went down at two hundred and twelve paws."
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
      bio: "A Dalmatian whose voice rolls down the lane like wet asphalt. Echo Howl drags every enemy in its wake a half-step slower than they need to be. The howl has no wire for the Signal King to jam and no source anyone can trace, not even Doc Wattson's log, which is exactly the problem the night it rolls to the wrong ears and cannot be called back."
    },
    "0035": {
      tagline: "One ping. Dead air.",
      bio: "A Shiba who works the Tactix switchboard. Ping clips a quick silence on the first target it finds, cheap and rude and exactly on time. He has one clean cut in him before the line snaps back live, so everything he is happens in that half-second of dead air, and the wire he once severed wrong, killing a crewmate's call for help in the same breath as an enemy's, is the one silence he replays long."
    },
    "0036": {
      tagline: "Easy now. I got you, hun.",
      bio: "A Shih Tzu who has stitched up half the alley and judged all of it. Soothe drips a small steady heal into whoever is hurting worst. Her mouth judges while her paws mend, and the half-beat she once spent sorting a dog she had written off is the only part of her a wound cannot afford; she swore hands before verdict, worst-first, every time."
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
      bio: "A Basset with ears tuned to frequencies the alley forgot. Beacon drags stealth into the open and marks it for everyone holding a grudge. The truest eye on the DOCKS and the root of her own line, forked against Stronghold's ear -- but the beacon only ever reports the past: she marks where a thing WAS, a beat too late, and the one rooftop that came back empty on the Crown Foxhound has a name she still won't check."
    },
    "0045": {
      tagline: "Long dog, longer tunnels.",
      bio: "A Dachshund who dug under the whole grid before anyone mapped it. Tunnel Drones pops two attackers up from dirt nobody was watching. He learned the underneath so well he stopped surfacing, and one raid he stayed a beat too deep to hear his own crew call down the shaft; he digs shallow enough to answer now, one level down instead of four."
    },
    "0046": {
      tagline: "Tiny? I power the whole block.",
      bio: "A Pomeranian who is ninety percent fur and ten percent reactor. Battery overcharges nearby turrets until the night smells like ozone. She has no dial, only full or off, so everything near her burns brighter and shorter; after a cooked barrel put a friend on a cot she swore to hold her turrets to the rating and let bright enough be the new loud."
    },
    "0047": {
      tagline: "Walls hate me. Feeling's mutual.",
      bio: "A Terrier with a rail cannon and a personal vendetta against architecture. Rail Shot rides the long line and bills structures double. He can only break, never build, and the day he brought a wall down on a sheltering pup he learned to read what a wall holds up before he reads where it fails; the grudge is really the fear that one day he will need a wall he never learned to be."
    },
    "0048": {
      tagline: "One drone. All heart.",
      bio: "A Pug who saved his whole stipend for a single guard drone. Mini Pup deploys it proudly; Circuitry vets stopped laughing after it clutched a match. His whole heart rides one fragile machine, and the blink it once froze at cost a pup a cot; he tunes the freeze out of it before every fight now and sends out all of himself each time, one blink from nothing and going anyway."
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
      bio: "A Rottweiler who never learned to fake being fine. Razorgums bleeds, grins, and lets Overclock Rage do the talking from there. The stripped [STREET] fork of the Iron Rottweiler line: he tore the plates off the night his brother Tombstone welded the crew's dead into his own, and now he pays the family tab in the open, in his own blood, at forty percent -- where he swears he does his only honest fighting."
    },
    "0053": {
      tagline: "Hammer all day. I won't dent.",
      bio: "A St. Bernard the Boneguard use as a load-bearing teammate. Anvil's Bodywall soaks the pack's pain like it was poured for the job."
    },
    "0054": {
      tagline: "Big shoulders, short patience.",
      bio: "A St. Bernard who carries the crew and complains the whole time. Hatchet's Bodywall holds anyway; loyalty outlasts the grumbling. The grumbling is a costume: like his brother Anvil under the press-gate, Hatchet has never once set an important thing down, and he still carries the jacks from the wave-off he obeyed the night his brother chose to hold till dawn."
    },
    "0055": {
      tagline: "Round one's a warmup, champ.",
      bio: "A Bulldog who treats every brawl like a payment plan. Bonecrusher's Brawler bite compounds; the longer you stay, the more you owe."
    },
    "0056": {
      tagline: "I start slow. I finish loud.",
      bio: "A Bulldog the bookies always undercount. Switch's Brawler engine takes a minute to warm and a crowbar to stop. Slow to warm is slow to arrive, and the family's fatal short round has cost him a packmate; he warms up before the bell now, and he still will not say whose paw threw the towel that ended his brother's fight, because he saw it a half-beat too late to know."
    },
    "0057": {
      tagline: "Lines break when I lean in.",
      bio: "An Akita built like cavalry that lost the horse and kept the attitude. Warhorse's Shock Push folds melee lines back into their own crew."
    },
    "0058": {
      tagline: "Tight spot? I make room.",
      bio: "An Akita who works the Boneguard's narrowest alleys. Lugnut's Shock Push clears a lane the way a tow truck clears a hydrant. He admired the room he made and never the far side where the shove landed, until a dog went down at his back; he checks where a push sends a dog before he counts the space it opens now, because the Alloy Akita line has a ghost waiting at the end of every lane it ever cleared."
    },
    "0059": {
      tagline: "Stand by me, stand taller.",
      bio: "A Newfoundland who turned harbor-rescue lungs into battlefield doctrine. Ironhide's Fortify aura makes the whole pack harder to bury."
    },
    "0060": {
      tagline: "Crooked teeth, straight loyalty.",
      bio: "A Newfoundland with a grin only the Boneguard could love. Snaggle's Fortify keeps the crew's HP up and their excuses down. Capacity was how he stayed dry: raising the crew's heads meant he never had to put his own under, and he is only now learning to dive the black water his whole Warden Newfie line has ever leaned over instead of getting into."
    },
    "0061": {
      tagline: "Gravity works for me now.",
      bio: "A Cane Corso who moves like poured concrete. Slab's Grav Pull pulse drags the nearest fools out of formation and into regret."
    },
    "0062": {
      tagline: "Step in. I'll show you the door.",
      bio: "A Cane Corso bouncer with a velvet-rope memory. Brassknuck's Grav Pull tosses crowders the way he tossed troublemakers: in bulk. The [STREET] fork of the Rust Cane Corso line: he tore the plate off to stay a door that opens, then bricked it shut, and where his brother Slab froze into a wall at the FACTORY ROW gate, Brassknuck froze into a wall that runs -- scattering every crowder equal because the one time he sorted a rope, he waved the wrong dog through."
    },

    /* ---------------- ZOOMIE VARIANTS ---------------- */
    "0063": {
      tagline: "Fast enough to be everywhere.",
      bio: "A Greyhound who polices the Syndicate's own streets. Roadblock's Dash Loop refreshes off every kill, so the patrol never actually ends."
    },
    "0064": {
      tagline: "Zero to gone in nothing flat.",
      bio: "A Greyhound pup running her first season. Nitro's Dash Loop keeps her lapping the arena while older dogs argue about lanes. The [STREET] fork of the Pixel Greyhound line: undefeated only because no dog has yet dropped in her lane, she calls the elders' grief slowness and haunts the 4 a.m. board like Pixel does, rehearsing the day the bill lands -- and swearing that when it does she will stop on purpose and stay, the first in the blood to survive the stopping instead of outrunning it."
    },
    "0065": {
      tagline: "Blink twice if you saw me. Liar.",
      bio: "A Shiba bruiser who bolted blink tech onto a brawler's frame. Bullbar's Blink Bite hops the guard and hits like a fender."
    },
    "0066": {
      tagline: "Quick flick. Deep cut.",
      bio: "A Shiba who keeps her work short and her exits shorter. Switchblade's Blink Bite opens every fight a half-step inside your reach. The [STREET] fork of the Circuit Shiba line: she stripped every gram of her mother's blink-tech off her own collar and went silent the season Bullbar's misfire proved the family math scaled wrong, and she has waited years for that empty collar to be read -- only now learning that silence is the one blade that cannot reach a mother who files it in a drawer."
    },
    "0067": {
      tagline: "I run through, never around.",
      bio: "A Vizsla legend with a roll bar welded to his rig. Rollcage's Pierce Rush takes the straight line through everything wearing a hostile tag."
    },
    "0068": {
      tagline: "Pick a wall. I'm off all of them.",
      bio: "A Vizsla who treats geometry as a suggestion. Ricochet's Pierce Rush threads a lane and bills every dog standing on it. The [STREET] fork of the Razor Vizsla line and the one swerve that lived the night the straight line ran into a shutter; he banks every shot off the walls the line dies on, because a clean lane -- the thing his brother Rollcage caged himself to never swerve from -- is the one thing Ricochet can no longer run."
    },
    "0069": {
      tagline: "Your backline is my fast lane.",
      bio: "A Saluki who crashes formations for sport. Crashcage's Sidecut swings lane to lane and lands where your softest dogs were hiding."
    },
    "0070": {
      tagline: "Borrowed speed, never returned.",
      bio: "A Saluki who hot-rods his own legs before every match. Hotwire's Sidecut flanks the backline before the alarm finishes its first beep. The [STREET] fork of the Flash Saluki line: the feud with his brother Crashcage is theater their mother wrote, never the same lane the same night so no raid takes both, and Hotwire plays the loud estranged decoy so well he has lost the stage directions -- borrowing speed he never returns so he never has to stand still and ask whether he was the son they protected or the bait they spent."
    },
    "0071": {
      tagline: "Pups up! Squad rolls deep.",
      bio: "A Corgi den mother with a glovebox full of trouble. Bumper's Spark Pups floods the lane with three mini zoomers and zero apologies."
    },
    "0072": {
      tagline: "Loud exit, louder entrance.",
      bio: "A Corgi whose deployments sound like an engine giving up. Backfire's Spark Pups arrive in a bang of three and scatter like sparks. The [STREET] fork of the Bolt Corgi line: he counts three loud and clean because his father counts four, one more than he deploys, a bowl set at the den door every season for the pup a wagon took -- and Backfire buries the fourth to stay the sane one, until he admits the night he answered the phone alone, heard breathing on the family code, and hung up."
    },
    "0073": {
      tagline: "Silence is my native tongue.",
      bio: "A Basenji who jams stadiums for fun. Gridiron's Signal Scramble mutes a target's ability right as the crowd leans in."
    },
    "0074": {
      tagline: "Heard nothing? That was me.",
      bio: "A Basenji who leaves no sound and less evidence. Skidmark's Signal Scramble cuts your trick's feed and is gone before the static clears. The [STREET] fork of the Glitch Basenji line: he learned brief from watching Gridiron hold a jam two seconds too long, but a scalpel that never stays never sees its own wound, and Skidmark may have erased the very line-noise the block still argues about -- so he preaches short precisely so he never has to hear the corner he might have silenced."
    },
    "0075": {
      tagline: "Two hits. You only count one.",
      bio: "A Malinois the Syndicate hires when one bite is not a statement. Deadweight's Twin Strike doubles up so fast the second hit feels like deja vu."
    },
    "0076": {
      tagline: "First beat, second beat, done.",
      bio: "A Malinois with a metronome where her mercy should be. Flatline's Twin Strike lands in rhythm; the chart goes quiet after. The [STREET] fork of the Aero Malinois line: she does both halves of a broken pair herself now, one dog carrying a two-dog count, so no second dog ever again waits on the beat she once called a stride too late."
    },

    /* ---------------- LEASHBREAK VARIANTS ---------------- */
    "0077": {
      tagline: "Towers obey me or go dark.",
      bio: "A Border Collie who herds the city's defenses like livestock. Firewall's Hack Jam shuts a tower's mouth mid-sentence."
    },
    "0078": {
      tagline: "I herd code like sheep.",
      bio: "A Border Collie who left the pasture for the power grid. Glitchfork's Hack Jam pens a tower in and leaves it bleating. The [STREET] fork of the Synth Collie line: he broke the family's shared jam-signature into a dirty unsigned fork so no single hash could collar the whole crew again -- and he has never told anyone the fork sometimes jams his own kit, or that Volt keeps quietly patching the corruption out of the DOCKS grid."
    },
    "0079": {
      tagline: "Locked in. Nobody drops today.",
      bio: "A Husky who bolts the door on death itself. Deadbolt's Heal Beacon pulses the Tactix pack back to fighting weight mid-brawl."
    },
    "0080": {
      tagline: "White noise, warm medicine.",
      bio: "A Husky medic who hums while she works. Static's Heal Beacon washes over the pack like a radio between stations, steady and kind. The [STREET] fork of the Holo Husky line: she heals with no wall and folds to one shot because she was once on the warm side of Deadbolt's bolted door, one of the asset-rated dogs the log saved while a dog scratched outside -- and every exposed heartbeat is her handing back the second of relief she felt at being the one worth saving."
    },
    "0081": {
      tagline: "Cold front, by request.",
      bio: "A Samoyed who delivers winter on a schedule. Bunkerlink's Frost Bark fans a freezing cone that turns a push into a slow, bad idea."
    },
    "0082": {
      tagline: "Fluffy outside. Freezer inside.",
      bio: "A Samoyed pup with a bark colder than her pedigree. Shortcircuit's Frost Bark slows whole crowds while she wags about it. The [STREET] fork of the Chill Samoyed line: her blood learned the Regent's freeze as a lesson to show weather instead of feeling, and where her elders grin over the cold she strips the grin and shows plain frost -- proud she is the honest one, blind that the frost is only the grin inverted, a bunker for the warmest, softest pup in the line."
    },
    "0083": {
      tagline: "Your shield? Already glass.",
      bio: "A Poodle who studied barriers just to insult them. Faraday's Shatter strips enemy shields and gifts the shards to an ally as a ward."
    },
    "0084": {
      tagline: "I break charms for a living.",
      bio: "A Poodle who works the Tactix counter-magic desk. Hexer's Shatter pops shields cheap and fast, then wards whoever needs it most. The [STREET] fork of the Prism Poodle line: she breaks every shield in the open and itemizes each one so no dog asks about the single ward she never touches, her mother's, with the family resonance humming inside -- because she holds that master key too, same as her sister Faraday, and points the light at everyone's locks to keep the dark over her own."
    },
    "0085": {
      tagline: "Aim well. It won't matter.",
      bio: "A Setter who soaks up light like a debt collector. Sandbag's Blackout blinds the ranged line until every shot lands in yesterday."
    },
    "0086": {
      tagline: "Snipers cry in the dark.",
      bio: "A Setter who broadcasts pure nothing. Whitenoise's Blackout drops over the shooters, and the Tactix walk through their misses. The [STREET] fork of the Noir Setter line: where her brother Sandbag sells the dark back as a debt, she floods the channel with free white noise instead -- owed to no one, and blind to everyone in it, her own pack included the night Prospector Pip had to call the retreat."
    },
    "0087": {
      tagline: "Marked means finished.",
      bio: "A Pointer who runs the Tactix's quiet list. Blacksite's Tag Shot reveals the hidden, weakens the proud, and files the rest under done."
    },
    "0088": {
      tagline: "I deliver bad news, tagged.",
      bio: "A Pointer courier who never loses an address. Carrier's Tag Shot pins a mark on a target and lets the pack handle the signature. The [STREET] fork of the Signal Pointer line: he knocks on every door before he tags it, warning the mark and folding to one clean shot for the mercy, because his most famous warning on the wrong-mark night was delivered to the wrong address and came back Return To Sender with a dog's whole life on it. Roxy signs for his routes and has watched him wear his paws out hunting the one door he missed."
    },
    "0089": {
      tagline: "Hit the air. I'll wait.",
      bio: "A Spaniel who phases out of the world like rent was due. Hardline's Phase buys an untouchable window the Tactix spend ruthlessly."
    },
    "0090": {
      tagline: "Now you see me. Now you don't.",
      bio: "A Spaniel pup with a ghost's instincts. Spike's Phase slips her out of a killing blow and back in time to bite about it. The [STREET] fork of the Ghost Spaniel line: she runs the family phase like a toy, one breath and gone from every hard hour, and folds to one clean shot because she never learned the trick was survival. She swears she saw an elder stay in the doorway the night the family debt was called; Banker Bones knows she phased out and missed it, and that she invented the witness because she could not bear to have vanished too."
    },
    "0091": {
      tagline: "My ring, my rules, my line.",
      bio: "A Border Collie who drew a circle and dared the city to cross it. Bulwark's Barrier Ring shields the whole front line under one roof."
    },
    "0092": {
      tagline: "Dim the lights, raise the wall.",
      bio: "A Border Collie who keeps the grid humble. Brownout's Barrier Ring throws an area shield up just as the lane gets loud. The [STREET] fork of the Pulse Border Collie line: he dims his own core to black to stretch the ring one dog past the margin his sister Bulwark signs -- and Patch has pulled him out of two full blackouts without ever telling the line how close the whole wall came to dropping."
    },

    /* ---------------- K9 CIRCUITRY VARIANTS ---------------- */
    "0093": {
      tagline: "Dig in. I only get hotter.",
      bio: "A Beagle welded into a forward turret post. Bunker's Overheat ramps fire the longer he holds; he has never once stopped holding."
    },
    "0094": {
      tagline: "Cheap seat, steady heat.",
      bio: "A Beagle turret on a budget chassis. Buckshot's Overheat spins up slow, but the lane learns fast why Circuitry keeps buying them. The [STREET] fork of the Laser Beagle line: he rolls where the fight is and never welds down, a barrel that ramps on time and never holds long enough, because he swore off posts the gap night his brother unbolted. The Foreman calls the rolling seat a flinch on wheels, and Buckshot swears the fall-back order reached the post to bury the truth that he rerouted its runner through the den rows himself."
    },
    "0095": {
      tagline: "Short legs, heavy ordnance.",
      bio: "A Corgi who signs every delivery with a boom. Howitzer's Spark Pups drops three drones that hit way above their pay grade."
    },
    "0096": {
      tagline: "Mind your step. Too late.",
      bio: "A Corgi who seeds the lane before you know it is a lane. Tripwire's Spark Pups spring three drones out of nowhere worth checking. The [STREET] fork of the Volt Corgi line: she seeds nameless, no mark on the work, and never once reads the bench mark on the cells she plants, because a name is a target. She swears the den-row wall fell on a sabotaged cell to keep from ever learning she may have planted her own grandfather's missing twelfth cell, bought off a no-name crate. Sparks tests every family cell and knows she tests none."
    },
    "0097": {
      tagline: "Run through my field. Slowly.",
      bio: "A Schnauzer who fenced the block in slow-light. Flakwall's Grid Lock turns a charge into a crawl and a crawl into target practice."
    },
    "0098": {
      tagline: "My grid never blinks.",
      bio: "A Schnauzer with a watchmaker's patience. Deadeye's Grid Lock field drags attackers down to a speed his turrets find polite. The [STREET] fork of the Grid Schnauzer line: he keeps his grid portable and dates a prototype at the crossing before the market crash, insisting it failed. It did not fail. It was switched off at dawn for the cart runs, by the family's own paw, while a young Deadeye carried the stall-keepers' complaint and said nothing. Volt keeps both intake dates dark and knows Deadeye says failed to avoid the word off."
    },
    "0099": {
      tagline: "Five birds, one bad day.",
      bio: "A Retriever housed in an armored casemate rig. Casemate's Drone Swarm releases five units; Circuitry logs the rest as cleanup."
    },
    "0100": {
      tagline: "I share. Everybody gets a piece.",
      bio: "A Retriever with a generous streak and a violent inventory. Shrapnel's Drone Swarm hands out five drones like party favors. The [STREET] fork of the Circuit Retriever line: he sends the five out to fragment and never calls one home, because a piece that never returns can't return wrong -- a generosity that is really a refusal to grieve, logged by Doc Wattson as the longest unrecovered column on the DOCKS."
    },
    "0101": {
      tagline: "One arc, three regrets.",
      bio: "An Airedale dug into a fortified firing slit. Pillbox's Arc Shot chains across three targets before the first one yelps."
    },
    "0102": {
      tagline: "Twitchy? I call it ready.",
      bio: "An Airedale who fires on instinct and apologizes never. Hairtrigger's Arc Shot jumps three bodies the moment one steps wrong. The [STREET] fork of the Chrome Airedale line: he fires first-motion and swears the third-body flag is a ghost, calling his careful brother haunted. Doc Wattson's LAB log shows the truth in ten thousand arcs: his flag never renders because he looses before it can draw, so somewhere in all that speed are third bodies he chained to and never let himself see."
    },
    "0103": {
      tagline: "Low ears hear every secret.",
      bio: "A Basset who built a listening post out of patience. Stronghold's Beacon drags stealth into the floodlights and marks it for the pack."
    },
    "0104": {
      tagline: "Short range, long memory.",
      bio: "A Basset who never forgets a scent or a slight. Snubnose's Beacon lights up hiders cheap and early, exactly when it stings. The [STREET] fork of the Beacon Basset line: he floodlights a hundred small hiders a night, cheap and personal, and folds the moment the light turns on him. He swears his brother's sealed tape already cracked because he heard three seconds of it, a ranked and beloved name, and has kept the whole dock lit ever since so his own beacon never has to fall on the one corner he already knows the shape of. Doc Wattson logs every reveal and knows the many are how he buries the one."
    },
    "0105": {
      tagline: "I am the position. Hold me.",
      bio: "A German Shepherd who became the fortification he was guarding. Emplacement's Overclock burst window ends pushes in one breath."
    },
    "0106": {
      tagline: "Patience, then everything at once.",
      bio: "A German Shepherd turret with military bearing. Salvo's Overclock holds, holds, holds, then empties the whole argument downrange. The [STREET] fork of the Nova Shepherd line: he strips the plate for a hotter window and owns every burst out loud, answering 'which of us fired' with his own name -- a name Sparks, who tunes both his rig and his brother Emplacement's, quietly knows the split-night shot never matched."
    },


    /* ---------------- AK-FACTION11 2026-07-18: CREW DECK FILLERS ---------------- */
    /* -------- K-CLUB -------- */
    "0107": {
      tagline: "Hand it over. I never lost a thing yet.",
      bio: "A Mudi who works the DOWNTOWN door hatch and holds what the club can't carry inside. Her Shield Bark is the same instinct: whatever you hand her, nothing gets to it."
    },
    /* -------- SCRAPJAW -------- */
    "0108": {
      tagline: "First cut's the only one I owe you.",
      bio: "A Tosa Inu bred silent for a pit that no longer exists. In THE YARDS he opens every job with one Burst Bite and then works the rest of the shift like a mechanic, which is worse."
    },
    "0109": {
      tagline: "Quarter turn at a time. That's how anything holds.",
      bio: "A corded Bergamasco who patches SCRAPJAW between shifts with scrap tape and patience. His Soothe is not fast and was never meant to be; it is the same quarter turn he gives every bolt in THE YARDS."
    },
    "0110": {
      tagline: "I don't come to you. Everything comes to me.",
      bio: "An Anatolian Shepherd welded into the old crane platform over THE YARDS. He has not stepped off it in four years, and his Overheat is the only reason the fence line still exists."
    },
    /* -------- ASHLINE -------- */
    "0111": {
      tagline: "Fire don't stop at one. Neither do I.",
      bio: "A Presa Canario who works the long lance off the FACTORY ROW catwalks. His Arc Shot jumps three deep because he learned burning the hard way: nothing on this row ever takes just one."
    },
    "0112": {
      tagline: "Everything that burns is thirsty. Line up.",
      bio: "A Chinook who runs the water cart down FACTORY ROW behind every ASHLINE push. Her Heal Beacon is that cart: it does not stop the fire, it just keeps arriving after it."
    },
    "0113": {
      tagline: "You won't see it coming. Nobody ever does.",
      bio: "A Boerboel who reads a room's air the way other dogs read a face. His Blackout drops the smoke a half second before the room turns, and on FACTORY ROW that half second is the whole trade."
    },
    "0114": {
      tagline: "Every mark on me is a night I stayed.",
      bio: "A mottled Catahoula who came up on FACTORY ROW with nothing but a bad coat and a worse temper. His Bitechain builds the same way he did: nothing on the first hit, everything by the fifth."
    },
    /* -------- CROWN LOT -------- */
    "0115": {
      tagline: "Numbers don't lie. Dogs who write them do.",
      bio: "A wrinkled Neapolitan Mastiff who has kept CROWN LOT's count since before the crown existed. His Shield Bark goes on whoever the sheet says is worth the most tonight, and the sheet is never wrong."
    },
    "0116": {
      tagline: "Everything under this lot belongs to me.",
      bio: "A sharp-eared Pumi who mapped the conduit under CROWN LOT before anybody thought to ask what was down there. Her Tunnel Drones come up wherever she has already been, which is everywhere."
    },
    "0117": {
      tagline: "Everybody pays. That's the only fair thing on this lot.",
      bio: "A ridgebacked hunter who stands the CROWN LOT approach and charges every single dog who crosses it. His Shock Push is the price list, and it has never once been negotiated."
    },
    "0118": {
      tagline: "The interest is the part you agreed to.",
      bio: "A hairless Xolo who collects CROWN LOT's vig and has never once had to raise a paw to do it. Her Shatter takes what a dog was hiding behind and then puts it on somebody who paid."
    },
    "0119": {
      tagline: "This is where the lot ends. Ask anybody.",
      bio: "A Caucasian Shepherd the size of a parked car who marks the edge of CROWN LOT with his own body. His Stonehide is not a technique. It is what happens when something that big decides not to move."
    },
    "0120": {
      tagline: "I didn't ask for it. I'm still going to carry it.",
      bio: "A Dogue de Bordeaux born into CROWN LOT's oldest name and handed a crown-adjacent seat he never wanted. His Burst Bite is what happens when a dog who has been polite his entire life finally leads with something."
    },
    /* -------- RUST HALO -------- */
    "0121": {
      tagline: "Slow water gets through anything.",
      bio: "A desert-bred Sloughi who ended up under the street with a tin cup and a lot of patience. Her Soothe is the tunnels themselves: nothing dramatic, just the same drop landing on the same spot until the stone gives."
    },
    "0122": {
      tagline: "Everything down here was built by somebody. Everything comes down.",
      bio: "A skeletal Azawakh who learned the UNDERCITY by learning what holds it up. His Rail Shot goes through structures because he spent four years reading them, and reading a thing is how you learn where it fails."
    },
    "0123": {
      tagline: "I don't send them out. They go. There's a difference.",
      bio: "A blue Thai Ridgeback who builds her drones out of what the UNDERCITY throws away and lets them run loose above the tunnels. Her Spark Pups always come back, and she has never once been able to explain to the crew why that bothers her."
    },
    "0124": {
      tagline: "Down here nobody's the good guy. That's restful.",
      bio: "A huge-eared Ibizan Hound who came down from the surface with a reputation and let the dark strip the color out of it. Her Echo Howl fills a whole tunnel because down here there is nothing to bounce off but everybody at once."
    },
    "0125": {
      tagline: "Bad air, good aim. Only one of those is going to kill me.",
      bio: "A brindle Kai Ken who has breathed the deep levels so long his chest sounds like machinery. His Tag Shot never misses, and the crew has stopped remarking on the fact that he takes it sitting down now."
    },
    "0126": {
      tagline: "I'm the last light on this level. Act like it.",
      bio: "A black-and-white Karelian who fights under the one working lamp on the deep run and refuses to fight anywhere else. His Haymaker lands first because in his ring, he is the only thing anybody can see."
    },
    "0127": {
      tagline: "I turned the grid off. Ask me why.",
      bio: "The old Malamute who killed the UNDERCITY's power grid eleven years ago and has run the dark ever since. Every dog down here has a theory about why. His Blackout is not a weapon he learned. It is the night he made, repeating."
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
