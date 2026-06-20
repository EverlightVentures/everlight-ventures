
# ALLEY KINGZ -- HUB WORLD INTERACTION & ROAMING COMBAT SPEC
## Inotia-Style Marketplace + Comic-Book Dialogs + Brawl Stars Roaming Combat
### 2026-06-20 | Tailored for Alley Kingz Dog-Themed Urban Strategy

---

## TABLE OF CONTENTS

1. THE VISION (What We're Building)
2. INOTIA-STYLE MARKETPLACE (Pokémon DS Shop DNA)
3. COMIC-BOOK CHARACTER PORTRAITS (Dialog System)
4. INTERACTIVE SHOP FLOWS (Buy/Sell/Leave with Personality)
5. HUB WORLD BOTS (Your Dog Cards Doing Missions)
6. BRAWL STARS-STYLE ROAMING COMBAT (Toggle Mode)
7. THE ENCOUNTER SYSTEM (Zombies at Night)
8. INTEGRATION WITH EXISTING SYSTEMS
9. ART REQUIREMENTS
10. BUILD ORDER

---

## 1. THE VISION

When you walk into THE DROP (shop), you don't see a generic menu. You see **Scratch the Broker** -- an Alley Kingz dog from the canon collection -- standing behind a graffiti-tagged counter. He talks to you. His portrait pops up in a comic-book speech bubble. When you buy something, he reacts ("Solid choice, mutt. That collar's gonna shine."). When you leave, he says goodbye ("Stay sharp out there. The strays are hungry tonight.").

When you walk the hub, you're NOT alone. Other dogs from YOUR collection are out there -- your Rare Slinger is scrounging scraps near the Gem Mine. Your Epic Boss is guarding the Crew Yard. Your Common Runner is doing a delivery mission for The Fixer. They have little mission icons over their heads. You can tap them to see what they're doing, help them, or just watch them work.

And when you toggle COMBAT MODE (the Brawl Stars button on your HUD), your dog pulls out a weapon -- a neon slingshot, a spray-can flamethrower, a chain-whip -- and you can shoot at other players' roaming dogs (ATA style) or blast zombie strays that spawn at night. It's just for fun. It's a toggle. But it makes the hub feel ALIVE.

---

## 2. INOTIA-STYLE MARKETPLACE (Pokémon DS Shop DNA)

### What Makes Inotia/Pokémon DS Shops Great

**Pokémon DS Shop Pattern:**
- **Left side:** Shopkeeper portrait (static image, expressive)
- **Right side:** Item grid (6-8 items visible, scrollable)
- **Bottom:** Description panel (flavor text + stats + price)
- **Top:** Your currency display (clean, always visible)
- **B button:** Back/Exit (always works, no dead ends)
- **A button:** Select/Buy (confirms with a sound + visual)

**Inotia Shop Pattern:**
- **Full-screen background:** The shop interior (tavern, blacksmith, etc.)
- **NPC stands at a counter** (animated idle, reacts when you approach)
- **Inventory panel slides in** from the right when you talk to them
- **Dialog system:** NPC greets you first, THEN the shop opens
- **Sell tab:** You can sell YOUR items back (dynamic economy)
- **Quest integration:** Some items only appear after quest progress

### AK Adaptation: "The Drop" Interior

```
┌─────────────────────────────────────────────────────────┐
│  [Gold: 1,240]  [Gems: 45]  [Scrap: 89]    [X] Exit   │  <- Currency HUD (persistent)
├─────────────────────────────────────────────────────────┤
│                                                         │
│   ┌──────────┐                                          │
│   │          │    "What you in the market for,          │
│   │  SCRATCH │     partner? I got deals today."        │
│   │  [PORTRAIT]                                        │
│   │  the Broker│    ┌──────────────────────────────┐     │
│   │          │    │  Neon Collar        500 G    │     │
│   └──────────┘    │  Graffiti Spray     200 G    │     │
│                    │  Scrap Bundle       50 G     │     │
│   [COMIC BOOK      │  Lucky Draw Token   10 Gems  │     │
│    STYLE PORTRAIT   │  VIP Pass (7d)      200 Gems │     │
│    WITH TAIL]      │  ─────────────────────────── │     │
│                    │  [Your Items]  [Buy]  [Sell] │     │
│                    └──────────────────────────────┘     │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  "Neon Collar -- A glowing street-collar that   │   │
│  │   pulses Electric Purple. Equip in Drip."      │   │
│  │   [RARE]  +5 Style Points                       │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Shopkeeper Roster (All Canon Dogs)

| Shop | Keeper | Dog ID | Personality | Greeting Lines |
|------|--------|--------|-------------|----------------|
| **THE DROP** (general shop) | Scratch | #0002 | Shady, fast-talking | "What you in the market for?" / "Cash or trade, your call." / "I got deals, friend -- step up." |
| **THE GARAGE** (deck/cards) | Roxy | #0003 | Tough, no-nonsense | "Wanna check the crew? Step up." / "Your deck's lookin' sharp." / "Pick your fighters wisely." |
| **GEM MINE** | Prospector Pip | #0007 | Enthusiastic, western | "Gems don't mine themselves, partner." / "Rich veins today!" / "Careful in the shaft." |
| **GOLD MINT** | Banker Bones | #0008 | Formal, greedy | "Gold's good here. What you need?" / "The mint never sleeps." / "Count it twice -- that's my motto." |
| **CARD FORGE** | Sparks | #0009 | Craftsman, fiery | "Forge is lit. Let's make somethin'." / "Bring me scraps, I'll bring the heat." / "Every legend starts on this anvil." |
| **RESEARCH LAB** | Doc Wattson | #0010 | Mad scientist | "Science waits for no dog." / "The skill tree's bloomin'." / "Knowledge is the sharpest fang." |
| **THE KENNEL** | Mama Bones | #0011 | Maternal, warm | "Lookin' to grow the family?" / "My pups are the finest in the city." / "Breed smart, raise 'em right." |
| **TROPHY HALL** | Goldie | #0012 | Proud, celebratory | "Admire the hardware -- you earned it." / "Every belt tells a story, kid." / "Hall of kings." |
| **PASS HOUSE** | Ticket | #0013 | Hype, energetic | "The season's heatin' up!" / "Premium lane's where it's at." / "Don't miss the tier rewards!" |
| **THE FIXER** (bounties) | Shade | #0014 | Mysterious, quiet | "I got work. You got skills?" / "The streets talk. I listen." / "Discretion is currency here." |
| **CREW YARD** | Chief | #0015 | Authoritative, loyal | "Crew's family. You family?" / "We look out for our own." / "The yard's always open." |

---

## 3. COMIC-BOOK CHARACTER PORTRAITS (Dialog System)

### Visual Design

```css
/* COMIC BOOK DIALOG BOX */
.dialog-box {
  position: fixed;
  bottom: 80px;
  left: 50%;
  transform: translateX(-50%);
  width: min(92vw, 520px);
  background: linear-gradient(135deg, #1a1510 0%, #0d0b08 100%);
  border: 3px solid #c9a84c;
  border-radius: 16px 16px 16px 4px; /* Asymmetric = comic style */
  padding: 18px 22px;
  box-shadow: 
    0 8px 32px rgba(0,0,0,0.6),
    inset 0 1px 0 rgba(201,168,76,0.15),
    4px 4px 0 #8b6914; /* Comic offset shadow */
  font-family: 'Comic Neue', 'Comic Sans MS', cursive;
  color: #e8e8e8;
  z-index: 100;
}

/* PORTRAIT BUBBLE (left side) */
.portrait-bubble {
  position: absolute;
  left: -70px;
  top: -20px;
  width: 90px;
  height: 90px;
  border-radius: 50%;
  border: 4px solid #c9a84c;
  background: #1a1510;
  overflow: hidden;
  box-shadow: 4px 4px 0 #8b6914;
}

.portrait-bubble img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* SPEECH POINTER (comic tail) */
.dialog-box::before {
  content: '';
  position: absolute;
  bottom: -18px;
  left: 30px;
  width: 0;
  height: 0;
  border-left: 14px solid transparent;
  border-right: 14px solid transparent;
  border-top: 20px solid #c9a84c;
}

.dialog-box::after {
  content: '';
  position: absolute;
  bottom: -13px;
  left: 33px;
  width: 0;
  height: 0;
  border-left: 11px solid transparent;
  border-right: 11px solid transparent;
  border-top: 16px solid #1a1510;
}

/* NAME PLATE */
.keeper-name {
  position: absolute;
  top: -14px;
  left: 40px;
  background: #c9a84c;
  color: #1a1206;
  padding: 3px 14px;
  border-radius: 12px;
  font-weight: 900;
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  box-shadow: 2px 2px 0 #8b6914;
}

/* TYPING CURSOR */
.typing-cursor {
  display: inline-block;
  width: 3px;
  height: 18px;
  background: #c9a84c;
  margin-left: 2px;
  animation: blink 0.8s infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* EMOTION STATES (portrait filters) */
.portrait-happy { filter: brightness(1.1) saturate(1.2); }
.portrait-angry { filter: hue-rotate(-30deg) saturate(1.5) brightness(0.9); }
.portrait-sad { filter: grayscale(0.4) brightness(0.8); }
.portrait-surprised { filter: brightness(1.3) contrast(1.2); }
.portrait-shady { filter: contrast(1.3) brightness(0.85); }
```

### Dialog State Machine

```javascript
// DIALOG_FSM.js -- pure state machine for shopkeeper interactions
const DIALOG_STATES = {
  IDLE: 'idle',           // Not talking
  GREETING: 'greeting',   // First approach -- plays greeting line
  TALKING: 'talking',     // Typing out dialog
  WAITING: 'waiting',     // Waiting for player input (choices)
  SHOPPING: 'shopping',   // Shop UI is open
  BUYING: 'buying',       // Purchase confirmation
  SELLING: 'selling',     // Sell confirmation
  FAREWELL: 'farewell',   // Goodbye sequence
  EXITING: 'exiting'      // Fade out, return to hub
};

class DialogController {
  constructor(keeper) {
    this.keeper = keeper;
    this.state = DIALOG_STATES.IDLE;
    this.currentLine = '';
    this.charIndex = 0;
    this.typingSpeed = 35; // ms per char
    this.choices = [];
    this.purchaseItem = null;
  }

  // Called when player walks into shop trigger
  async enter() {
    this.state = DIALOG_STATES.GREETING;
    const greeting = this.pickGreeting();
    await this.typeLine(greeting, 'happy');
    this.state = DIALOG_STATES.WAITING;
    this.showChoices([
      { label: 'Browse wares', action: () => this.openShop() },
      { label: 'Sell items', action: () => this.openSell() },
      { label: 'Talk', action: () => this.talkRandom() },
      { label: 'Leave', action: () => this.farewell() }
    ]);
  }

  async typeLine(text, emotion = 'neutral') {
    this.state = DIALOG_STATES.TALKING;
    this.currentLine = '';
    this.charIndex = 0;

    // Set portrait emotion
    this.setPortraitEmotion(emotion);

    // Typewriter effect
    return new Promise(resolve => {
      const type = () => {
        if (this.charIndex < text.length) {
          this.currentLine += text[this.charIndex];
          this.charIndex++;
          this.render();

          // Sound: typewriter click (varied pitch)
          AK.playSfx('dialog_type', { pitch: 0.95 + Math.random() * 0.1 });

          setTimeout(type, this.typingSpeed);
        } else {
          this.state = DIALOG_STATES.WAITING;
          resolve();
        }
      };
      type();
    });
  }

  async onPurchase(item) {
    this.purchaseItem = item;
    this.state = DIALOG_STATES.BUYING;

    const reactions = {
      cheap: ["Solid choice, mutt.", "That'll do nicely.", "Smart buy."],
      mid: ["Ooh, fancy. I like your style.", "That's a keeper right there.", "Gonna turn heads with that."],
      expensive: ["BIG spender! Respect.", "Now THAT'S how you ball.", "The crown suits you, king."],
      cosmetic: ["That collar's gonna shine.", "Fresh drip, no cap.", "Streets are gonna notice."]
    };

    const tier = item.price < 100 ? 'cheap' : item.price < 500 ? 'mid' : 'expensive';
    const reaction = reactions[tier][Math.floor(Math.random() * reactions[tier].length)];

    await this.typeLine(reaction, 'happy');

    // Visual: item pops out of dialog box
    this.animateItemPop(item);

    AK.playSfx('purchase_success');
    AK.haptic('chest'); // Celebratory haptic
  }

  async farewell() {
    this.state = DIALOG_STATES.FAREWELL;

    const farewells = {
      day: ["Stay sharp out there.", "The streets remember.", "Don't get bit."],
      night: ["Watch your back. Strays are hungry.", "Night's dark, friend. Keep your collar tight.", "The alleys whisper tonight."],
      event: ["Event's heatin' up! Don't miss it!", "Go get that seasonal loot!"]
    };

    const timeKey = isNight() ? 'night' : isEventActive() ? 'event' : 'day';
    const line = farewells[timeKey][Math.floor(Math.random() * farewells[timeKey].length)];

    await this.typeLine(line, 'neutral');

    // Fade out dialog
    this.state = DIALOG_STATES.EXITING;
    await this.fadeOut();

    // Return to hub
    hub.returnFromShop();
  }

  pickGreeting() {
    const hour = new Date().getHours();
    const greetings = {
      morning: ["Mornin', mutt. Coffee first or deals first?", "Early bird gets the bone."],
      day: ["What you in the market for, partner?", "Back again? Must be my charm."],
      evening: ["Evenin'. The night deals come out after dark.", "Sun's down, prices are... flexible."],
      night: ["You're brave walkin' in here this late.", "The night shift. My favorite customers."]
    };

    const time = hour < 12 ? 'morning' : hour < 17 ? 'day' : hour < 21 ? 'evening' : 'night';
    const pool = greetings[time];
    return pool[Math.floor(Math.random() * pool.length)];
  }
}
```

---

## 4. INTERACTIVE SHOP FLOWS

### The Purchase Moment (The "Pop-Out" Effect)

When you tap "Buy" on an item:

1. **Keeper reacts** (dialog line + emotion change)
2. **Item sprite "pops"** out of the shop grid -- scales up from 0 to 1.5x with a bounce, rotates slightly, glows gold
3. **Gold/Gems counter** ticks down with a satisfying animation
4. **Item flies** to your inventory panel (top-right) with a trail
5. **Keeper says** a follow-up line ("Equip that in your Drip locker.")
6. **Sound cascade:** purchase chime + coin clink + success fanfare

```javascript
// Purchase animation sequence
async function animatePurchase(item, keeper) {
  // 1. Keeper reaction
  await keeper.typeLine(keeper.pickPurchaseReaction(item), 'happy');

  // 2. Item pop-out
  const itemEl = document.getElementById(`shop-item-${item.id}`);
  const rect = itemEl.getBoundingClientRect();

  // Create floating clone
  const floater = itemEl.cloneNode(true);
  floater.style.position = 'fixed';
  floater.style.left = rect.left + 'px';
  floater.style.top = rect.top + 'px';
  floater.style.width = rect.width + 'px';
  floater.style.zIndex = 9999;
  floater.style.transition = 'all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1)';
  document.body.appendChild(floater);

  // Animate: scale up, rotate, glow
  requestAnimationFrame(() => {
    floater.style.transform = 'scale(1.5) rotate(8deg)';
    floater.style.filter = 'drop-shadow(0 0 20px #c9a84c)';
  });

  // 3. Currency tick
  animateCurrencyDeduction(item.currency, item.price);

  // 4. Fly to inventory
  const invRect = document.getElementById('inventory-icon').getBoundingClientRect();
  floater.style.transition = 'all 0.4s ease-in';
  floater.style.left = invRect.left + 'px';
  floater.style.top = invRect.top + 'px';
  floater.style.transform = 'scale(0.3)';
  floater.style.opacity = '0';

  await wait(400);
  floater.remove();

  // 5. Inventory bounce
  document.getElementById('inventory-icon').classList.add('bounce');
  setTimeout(() => document.getElementById('inventory-icon').classList.remove('bounce'), 300);

  // 6. Sound
  AK.playSfx('purchase_success');
  AK.playSfx('coin_clink');
  AK.haptic('chest');

  // 7. Keeper follow-up
  await keeper.typeLine("Equip that in your Drip locker. It's gonna shine.", 'happy');
}
```

### The "Wanna Purchase This?" Confirm Dialog

```javascript
// Confirm purchase with keeper asking
function showPurchaseConfirm(item, keeper) {
  // Instead of generic "Are you sure?", the keeper asks
  const confirms = [
    `${item.name}, huh? That's ${item.price} ${item.currency}. You sure, mutt?`,
    `Solid piece. ${item.price} ${item.currency}. Hand it over?`,
    `I got one left at this price. ${item.price} ${item.currency}. Deal?`,
    `Ooh, eyein' the good stuff. ${item.price} ${item.currency}. You ballin' like that?`
  ];

  keeper.typeLine(confirms[Math.floor(Math.random() * confirms.length)], 'shady');

  // Show YES/NO as dialog choices (not generic buttons)
  keeper.showChoices([
    { 
      label: `Yeah, here's ${item.price} ${item.currency}`, 
      action: () => completePurchase(item),
      style: 'gold-button'
    },
    { 
      label: "Nah, just lookin'", 
      action: () => keeper.typeLine("No worries. Lotta lookers, few buyers.", 'neutral'),
      style: 'gray-button'
    }
  ]);
}
```

---

## 5. HUB WORLD BOTS (Your Dog Cards Doing Missions)

### The Living Hub Concept

Your collected dog cards are NOT just inventory -- they're ALIVE in the hub. Each card you own has a chance to spawn as a roaming bot, doing activities based on its:
- **Rarity** (Common = basic missions, Legendary = epic missions)
- **Faction** (Crowned = guarding, Rusted = scavenging, Hologhosts = scouting, Unbound = running deliveries)
- **Archetype** (Brawler = guarding, Slinger = hunting, Runner = delivering, Fixer = repairing, etc.)
- **Level** (Higher level = more impressive missions)

### Mission Types (Visible as Icons Over Their Heads)

| Icon | Mission Type | What They're Doing | You Can... |
|------|-------------|-------------------|------------|
| 📦 | **Delivery** | Carrying a package to another building | Help (speed up) / Steal (risky) / Watch |
| 🔍 | **Scout** | Investigating a suspicious area | Join (co-op mini-mission) / Dismiss |
| ⚔️ | **Guard** | Patrolling near a building | Replace them / Buff them |
| 🔧 | **Repair** | Fixing a damaged building | Help (faster repair) / Donate materials |
| 🎣 | **Gather** | Collecting resources from a node | Claim a share / Steal their spot |
| 💰 | **Trade** | Walking to the Trading Post | Inspect their deal / Counter-offer |
| 🏆 | **Train** | Sparring at Training Grounds | Challenge them (practice match) / Coach them |
| 🎲 | **Gamble** | Playing dice behind the alley | Join the game / Break it up |

### Bot Spawn Logic

```javascript
// hub_bot_spawner.js
class HubBotSpawner {
  constructor() {
    this.activeBots = [];
    this.maxBots = 12; // Cap for performance
    this.respawnTimer = 30; // seconds between spawn checks
  }

  tick(dt) {
    // Remove bots that wandered off-screen or completed missions
    this.activeBots = this.activeBots.filter(bot => bot.isActive);

    // Spawn new bots if under cap
    if (this.activeBots.length < this.maxBots && Math.random() < 0.02) {
      this.spawnBot();
    }

    // Update all bots
    this.activeBots.forEach(bot => bot.update(dt));
  }

  spawnBot() {
    // Pick a random OWNED card from collection
    const ownedCards = getOwnedCards(); // from ak_profile.owned
    if (ownedCards.length === 0) return;

    const card = ownedCards[Math.floor(Math.random() * ownedCards.length)];
    const cardData = CARDS[card.name]; // from canon.js

    // Determine mission based on archetype + faction
    const mission = this.pickMission(cardData);

    // Spawn bot
    const bot = new HubBot({
      card: cardData,
      mission: mission,
      startPos: this.pickSpawnPoint(mission),
      endPos: this.pickDestination(mission),
      speed: 40 + (cardData.level || 1) * 5, // Level affects walk speed
      duration: 20 + Math.random() * 40 // seconds to complete mission
    });

    this.activeBots.push(bot);
  }

  pickMission(cardData) {
    const archetype = cardData.archetype; // Brawler, Slinger, Runner, etc.
    const faction = cardData.faction; // Crowned, Rusted, Hologhosts, Unbound

    // Archetype-weighted mission pool
    const pools = {
      Brawler: ['guard', 'train', 'patrol'],
      Slinger: ['scout', 'hunt', 'guard'],
      Runner: ['delivery', 'gather', 'scout'],
      Fixer: ['repair', 'trade', 'gather'],
      Boss: ['guard', 'train', 'trade'],
      Ghost: ['scout', 'gamble', 'spy'],
      Hype: ['gamble', 'train', 'social'],
      Scribe: ['scout', 'trade', 'research'],
      Muscle: ['guard', 'patrol', 'train'],
      Kid: ['delivery', 'gather', 'gamble']
    };

    const pool = pools[archetype] || ['patrol'];
    return pool[Math.floor(Math.random() * pool.length)];
  }
}

// HubBot class -- each roaming dog
class HubBot {
  constructor(config) {
    this.card = config.card;
    this.mission = config.mission;
    this.pos = { ...config.startPos };
    this.target = { ...config.endPos };
    this.speed = config.speed;
    this.duration = config.duration;
    this.elapsed = 0;
    this.isActive = true;
    this.state = 'walking'; // walking | working | returning | idle

    // Visual
    this.bobOffset = Math.random() * Math.PI * 2;
    this.missionIcon = this.getMissionIcon();
  }

  update(dt) {
    this.elapsed += dt;

    switch(this.state) {
      case 'walking':
        this.moveToward(this.target, dt);
        if (this.reachedTarget()) {
          this.state = 'working';
          this.workTimer = 5 + Math.random() * 10;
        }
        break;

      case 'working':
        this.workTimer -= dt;
        // Emit little "working" particles
        if (Math.random() < 0.1) this.emitWorkParticle();
        if (this.workTimer <= 0) {
          this.state = 'returning';
          // Swap target and start (go back)
          const temp = this.target;
          this.target = this.pos; // Actually need to store start
          // ... return logic
        }
        break;

      case 'returning':
        // Walk back to start, then despawn
        break;
    }

    // Auto-despawn after duration
    if (this.elapsed > this.duration) {
      this.isActive = false;
    }
  }

  draw(ctx, camX, camY) {
    const screenX = this.pos.x - camX;
    const screenY = this.pos.y - camY;

    // Skip if off-screen
    if (screenX < -50 || screenX > W + 50 || screenY < -50 || screenY > H + 50) return;

    // Bobbing animation
    const bob = Math.sin(performance.now() * 0.003 + this.bobOffset) * 3;

    // Draw the dog (smaller than player, uses same sprite)
    ctx.save();
    ctx.translate(screenX, screenY + bob);

    // Shadow
    ctx.fillStyle = 'rgba(0,0,0,0.3)';
    ctx.beginPath();
    ctx.ellipse(0, 12, 10, 4, 0, 0, Math.PI * 2);
    ctx.fill();

    // Dog sprite (scaled down, faction-tinted)
    const sprite = getCardSprite(this.card.name);
    if (sprite && sprite.complete) {
      ctx.drawImage(sprite, -12, -20, 24, 28);
    } else {
      // Fallback: colored circle with faction color
      ctx.fillStyle = FACTION_COLORS[this.card.faction] || '#888';
      ctx.beginPath();
      ctx.arc(0, -5, 10, 0, Math.PI * 2);
      ctx.fill();
    }

    // Name tag (small, above head)
    ctx.fillStyle = 'rgba(8,8,14,0.85)';
    ctx.fillRect(-30, -38, 60, 14);
    ctx.fillStyle = '#e8c55a';
    ctx.font = '700 8px Inter';
    ctx.textAlign = 'center';
    ctx.fillText(this.card.name.slice(0, 12), 0, -28);

    // Mission icon (bouncing above head)
    const iconBob = Math.sin(performance.now() * 0.005) * 2;
    ctx.font = '14px serif';
    ctx.fillText(this.missionIcon, 0, -42 + iconBob);

    // Interaction hint (when player is near)
    const distToPlayer = Math.hypot(this.pos.x - player.x, this.pos.y - player.y);
    if (distToPlayer < 60) {
      ctx.fillStyle = 'rgba(201,168,76,0.9)';
      ctx.font = '700 9px Inter';
      ctx.fillText('[TAP]', 0, 25);
    }

    ctx.restore();
  }

  getMissionIcon() {
    const icons = {
      delivery: '📦', scout: '🔍', guard: '⚔️', repair: '🔧',
      gather: '🎣', trade: '💰', train: '🏆', gamble: '🎲',
      patrol: '👁️', hunt: '🎯', spy: '🕵️', social: '💬',
      research: '🔬'
    };
    return icons[this.mission] || '👁️';
  }

  onTap(player) {
    // Show dialog with this bot
    const dialog = new BotDialog(this);
    dialog.show();

    // Options based on mission
    const options = this.getInteractionOptions();
    dialog.showChoices(options);
  }

  getInteractionOptions() {
    const options = [{ label: 'Watch', action: () => this.watchMission() }];

    switch(this.mission) {
      case 'delivery':
        options.push(
          { label: 'Help carry (+speed)', action: () => this.helpDelivery() },
          { label: 'Steal package (risky)', action: () => this.stealPackage() }
        );
        break;
      case 'guard':
        options.push(
          { label: 'Relieve them', action: () => this.relieveGuard() },
          { label: 'Buff (+defense)', action: () => this.buffGuard() }
        );
        break;
      case 'train':
        options.push(
          { label: 'Spar (practice)', action: () => this.sparBot() },
          { label: 'Coach (+XP)', action: () => this.coachBot() }
        );
        break;
      case 'gamble':
        options.push(
          { label: 'Join game', action: () => this.joinGamble() },
          { label: 'Break it up', action: () => this.breakGamble() }
        );
        break;
    }

    options.push({ label: 'Dismiss', action: () => this.dismiss() });
    return options;
  }
}
```

---

## 6. BRAWL STARS-STYLE ROAMING COMBAT (Toggle Mode)

### The Concept

A **toggle button** on the HUD switches between:
- **PEACE MODE** (default): Walk, explore, talk to NPCs, enter buildings
- **COMBAT MODE**: Your dog pulls out a weapon, can shoot projectiles, can attack other players' roaming dogs or zombie strays

This is **just for fun** -- no stakes, no loot loss, no base damage. It's a mini-game inside the hub. Think of it like GTA5's "passive mode" toggle, or Brawl Stars' practice mode.

### The Toggle Button

```css
/* Combat mode toggle (HUD element) */
#combat-toggle {
  position: fixed;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: linear-gradient(135deg, #ff4444, #cc0000);
  border: 3px solid #ff8888;
  color: white;
  font-size: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  z-index: 10;
  box-shadow: 0 4px 16px rgba(255, 68, 68, 0.4);
  transition: all 0.2s;
}

#combat-toggle.peace {
  background: linear-gradient(135deg, #44ff88, #00cc66);
  border-color: #88ffaa;
  box-shadow: 0 4px 16px rgba(68, 255, 136, 0.4);
}

#combat-toggle:active {
  transform: translateY(-50%) scale(0.9);
}

/* Combat mode indicator */
#combat-indicator {
  position: fixed;
  top: 10px;
  right: 80px;
  background: rgba(255, 68, 68, 0.9);
  color: white;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 0.1em;
  opacity: 0;
  transition: opacity 0.3s;
}

#combat-indicator.active {
  opacity: 1;
}
```

### Combat Mode Controls

```javascript
// combat_mode.js
class RoamingCombat {
  constructor() {
    this.active = false;
    this.weapon = null;
    this.projectiles = [];
    this.cooldown = 0;
    this.ammo = Infinity; // No ammo limits for fun mode
    this.health = 100; // Respawns instantly on "death"
    this.invulnerable = false;
  }

  toggle() {
    this.active = !this.active;

    if (this.active) {
      this.enterCombatMode();
    } else {
      this.exitCombatMode();
    }
  }

  enterCombatMode() {
    // 1. Change player appearance
    player.combatMode = true;
    player.weapon = this.equipWeapon();

    // 2. Show combat HUD
    document.getElementById('combat-indicator').classList.add('active');
    document.getElementById('combat-toggle').classList.remove('peace');

    // 3. Change controls: right side becomes aim + shoot
    this.enableCombatControls();

    // 4. Spawn practice targets (if no enemies nearby)
    if (getNearbyEnemies().length === 0) {
      this.spawnPracticeTargets();
    }

    // 5. Sound + haptic
    AK.playSfx('combat_mode_on');
    AK.haptic('war_now');

    // 6. Banner
    showBanner('COMBAT MODE -- Have fun, no stakes!', 2);
  }

  equipWeapon() {
    // Weapon based on player's highest-level card archetype
    const archetype = getPlayerArchetype(); // From deck

    const weapons = {
      Brawler: { name: 'Knuckle Dusters', type: 'melee', damage: 25, range: 60, fireRate: 0.4, projectile: null },
      Slinger: { name: 'Neon Slingshot', type: 'ranged', damage: 15, range: 200, fireRate: 0.25, projectile: 'neon_orb' },
      Runner: { name: 'Sprint Strike', type: 'dash', damage: 30, range: 100, fireRate: 0.8, projectile: null },
      Fixer: { name: 'Repair Wrench', type: 'melee', damage: 20, range: 50, fireRate: 0.5, projectile: null },
      Boss: { name: 'Chain Whip', type: 'melee', damage: 35, range: 80, fireRate: 0.6, projectile: null },
      Ghost: { name: 'Phantom Blade', type: 'melee', damage: 40, range: 55, fireRate: 0.5, projectile: null },
      Hype: { name: 'Boombox Blast', type: 'ranged', damage: 20, range: 150, fireRate: 0.3, projectile: 'sound_wave' },
      Scribe: { name: 'Data Dart', type: 'ranged', damage: 18, range: 180, fireRate: 0.2, projectile: 'data_shard' },
      Muscle: { name: 'Brass Knuckles', type: 'melee', damage: 30, range: 55, fireRate: 0.45, projectile: null },
      Kid: { name: 'Spray Can', type: 'ranged', damage: 12, range: 120, fireRate: 0.15, projectile: 'paint_blob' }
    };

    return weapons[archetype] || weapons.Brawler;
  }

  enableCombatControls() {
    // Right side of screen = aim zone
    // Tap = shoot in that direction
    // Hold = auto-fire (Brawl Stars style)

    const aimZone = document.createElement('div');
    aimZone.id = 'aim-zone';
    aimZone.style.cssText = `
      position: fixed;
      right: 0;
      top: 0;
      width: 50vw;
      height: 100vh;
      z-index: 4;
      touch-action: none;
    `;
    document.body.appendChild(aimZone);

    // Aim stick (appears on touch)
    aimZone.addEventListener('pointerdown', (e) => this.startAim(e));
    aimZone.addEventListener('pointermove', (e) => this.updateAim(e));
    aimZone.addEventListener('pointerup', (e) => this.endAim(e));
  }

  shoot(angle) {
    if (this.cooldown > 0) return;

    const weapon = player.weapon;
    this.cooldown = weapon.fireRate;

    if (weapon.type === 'melee') {
      // Melee swing
      this.meleeAttack(angle, weapon);
    } else {
      // Ranged projectile
      this.fireProjectile(angle, weapon);
    }

    // Visual: muzzle flash / swing arc
    // Sound
    AK.playSfx(weapon.type === 'melee' ? 'melee_swing' : 'projectile_fire');

    // Haptic
    AK.haptic('melee');
  }

  fireProjectile(angle, weapon) {
    const projectile = {
      x: player.x,
      y: player.y,
      vx: Math.cos(angle) * 300, // speed
      vy: Math.sin(angle) * 300,
      damage: weapon.damage,
      type: weapon.projectile,
      lifetime: weapon.range / 300, // seconds until max range
      owner: 'player'
    };

    this.projectiles.push(projectile);
  }

  meleeAttack(angle, weapon) {
    // Arc attack in front of player
    const arc = Math.PI / 3; // 60 degree arc
    const hitEnemies = getEnemiesInArc(player.x, player.y, angle, weapon.range, arc);

    hitEnemies.forEach(enemy => {
      enemy.takeDamage(weapon.damage);

      // Knockback
      const knockAngle = Math.atan2(enemy.y - player.y, enemy.x - player.x);
      enemy.knockback(knockAngle, 80);

      // Hit effect
      spawnHitEffect(enemy.x, enemy.y);
    });

    // Visual swing arc
    spawnSwingArc(player.x, player.y, angle, weapon.range, arc);
  }

  update(dt) {
    if (!this.active) return;

    // Cooldown
    if (this.cooldown > 0) this.cooldown -= dt;

    // Update projectiles
    this.projectiles = this.projectiles.filter(p => {
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.lifetime -= dt;

      // Check collisions
      const hit = this.checkProjectileHit(p);
      if (hit) {
        hit.takeDamage(p.damage);
        spawnHitEffect(p.x, p.y);
        return false; // Remove projectile
      }

      return p.lifetime > 0;
    });

    // Auto-fire if holding aim
    if (this.aiming && this.cooldown <= 0) {
      this.shoot(this.aimAngle);
    }
  }

  draw(ctx, camX, camY) {
    if (!this.active) return;

    // Draw projectiles
    this.projectiles.forEach(p => {
      const sx = p.x - camX;
      const sy = p.y - camY;

      ctx.save();
      ctx.translate(sx, sy);

      // Projectile sprite based on type
      switch(p.type) {
        case 'neon_orb':
          ctx.shadowColor = '#06B6D4';
          ctx.shadowBlur = 10;
          ctx.fillStyle = '#06B6D4';
          ctx.beginPath();
          ctx.arc(0, 0, 5, 0, Math.PI * 2);
          ctx.fill();
          break;
        case 'paint_blob':
          ctx.fillStyle = '#EC4899';
          ctx.beginPath();
          ctx.arc(0, 0, 6, 0, Math.PI * 2);
          ctx.fill();
          break;
        case 'sound_wave':
          ctx.strokeStyle = '#F97316';
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.arc(0, 0, 8, 0, Math.PI * 2);
          ctx.stroke();
          break;
        default:
          ctx.fillStyle = '#c9a84c';
          ctx.fillRect(-3, -3, 6, 6);
      }

      ctx.restore();
    });

    // Draw aim line (subtle)
    if (this.aiming) {
      const sx = player.x - camX;
      const sy = player.y - camY;
      const ex = sx + Math.cos(this.aimAngle) * 100;
      const ey = sy + Math.sin(this.aimAngle) * 100;

      ctx.strokeStyle = 'rgba(201,168,76,0.3)';
      ctx.lineWidth = 1;
      ctx.setLineDash([5, 5]);
      ctx.beginPath();
      ctx.moveTo(sx, sy);
      ctx.lineTo(ex, ey);
      ctx.stroke();
      ctx.setLineDash([]);
    }
  }
}
```

---

## 7. THE ENCOUNTER SYSTEM (Zombies at Night)

### Night Mode Spawning

When the hub enters NIGHT (tint shift + street lamps on):
- **Stray dogs** spawn at map edges
- **Zombie dogs** (mutant strays) spawn in "wild" zones
- They WANDER toward the center (player's base area)
- They ATTACK the player on sight (detection radius)

### Zombie Types

| Type | HP | Speed | Damage | Behavior | Loot |
|------|-----|-------|--------|----------|------|
| **Stray Pup** | 30 | Fast | 8 | Charges straight | 5-10 Gold |
| **Rabid Hound** | 60 | Medium | 15 | Zigzag approach | 10-20 Gold + chance Scrap |
| **Alpha Stray** | 150 | Slow | 30 | Spawns other strays | 50 Gold + Rare drop |
| **Ghost Stray** | 40 | Very Fast | 12 | Phases through walls | 15 Gold + Bones |

### Combat Rewards (Fun Mode)

Since this is "just for fun" (no stakes):
- **Gold drops** (small amounts, 5-50)
- **Scrap drops** (chance)
- **Bones** (rare, from Ghost Strays)
- **Score streak** (consecutive kills = multiplier)
- **No death penalty** -- you respawn at your base instantly
- **Leaderboard** (daily "Most Strays Cleared")

### The "It's Just For Fun" Safeguards

```javascript
// combat_safeguards.js
const COMBAT_SAFEGUARDS = {
  // No loot loss
  deathPenalty: 'none', // vs 'lose_gold', 'lose_items' in hard modes

  // Instant respawn
  respawnTime: 0, // seconds
  respawnLocation: 'base', // vs 'random', 'corpse'

  // No base damage
  baseInvulnerable: true,

  // No PvP griefing
  pvpDamage: 0.1, // 10% damage (tickles, doesn't kill)
  pvpKillReward: false, // No reward for killing other players

  // Opt-in only
  requireToggle: true, // Must explicitly enter combat mode
  autoExitOnEnterBuilding: true, // Can't fight in shops

  // Visual indicators
  showEnemyHealth: true, // Health bars above enemies
  showDamageNumbers: true, // Floating damage text
  showScore: true // Kill counter
};
```

---

## 8. INTEGRATION WITH EXISTING SYSTEMS

### EventBus Events (New)

```javascript
// New events emitted by these systems
'bot.spawned' { botId, cardName, mission, position }
'bot.interacted' { botId, playerId, action }
'bot.mission.completed' { botId, mission, rewards }
'combat.mode.toggled' { active, weapon }
'combat.projectile.fired' { owner, type, angle }
'combat.enemy.killed' { enemyType, streak, score }
'combat.player.died' { killer, respawnTime }
'dialog.started' { keeperId, line }
'dialog.choice.made' { keeperId, choice }
'dialog.ended' { keeperId }
'shop.purchase' { item, price, currency, keeperReaction }
'shop.sell' { item, price, currency }
```

### Integration Points

| Existing System | How It Connects |
|-----------------|-----------------|
| **hub_proto.html** | Add bot spawner to loop, combat mode toggle to HUD, dialog overlay |
| **engine.js** | Reuse projectile physics, collision detection, damage calc |
| **economy.js** | Bot missions grant small rewards, combat drops add to wallet |
| **shop.js** | Inotia-style layout replaces current shop UI |
| **drip.js** | Combat mode weapon skins = cosmetic slot |
| **social.js** | Bot missions can be "shared" (crew helps your bot) |
| **canon.js** | Card sprites reused for bot avatars |
| **AK_ART_QUEUE** | New art: shop interiors, keeper portraits, weapon sprites, zombie strays |

---

## 9. ART REQUIREMENTS

### New Assets Needed

| Asset | Count | Priority | Route | Notes |
|-------|-------|----------|-------|-------|
| **Shop interiors** | 8 | P0 | Leonardo | The Drop, Garage, Gem Mine, etc. |
| **Keeper portraits** | 12 | P0 | Leonardo | Comic-book style, expressive, faction-colored |
| **Keeper portrait emotions** | 5 per keeper | P1 | Leonardo | Happy, angry, sad, surprised, shady |
| **Weapon sprites** | 10 | P1 | Leonardo | One per archetype |
| **Projectile sprites** | 6 | P1 | Leonardo | Neon orb, paint blob, sound wave, etc. |
| **Zombie stray sprites** | 4 | P1 | Leonardo | Pup, Hound, Alpha, Ghost |
| **Hit effects** | 3 | P2 | ZzFX/synth | Impact burst, blood splatter (stylized), gold spark |
| **Swing arc VFX** | 1 | P2 | Canvas | Procedural arc draw |
| **Mission icons** | 12 | P0 | Emoji fallback | 📦🔍⚔️ etc. (emoji for now, art later) |
| **Combat mode HUD** | 1 | P0 | CSS | Toggle button, indicator, aim line |
| **Dialog box chrome** | 1 | P0 | CSS | Comic-book frame, tail, name plate |

### Portrait Prompt Template

```
"Comic-book style character portrait of [KEEPER_NAME], an anthropomorphic urban street-dog, [ARCHETYPE] type, [FACTION] faction, [EMOTION] expression, bold black outlines, cel-shaded, vibrant NeonReach palette (Electric Purple #8B5CF6, Neon Cyan #06B6D4, Hot Pink #EC4899), gritty cyberpunk dog-gang style, circular crop, transparent background, game asset, readable at 90x90px"
```

---

## 10. BUILD ORDER

### Phase 1: Dialog System (This Week)
1. [ ] CSS dialog box + portrait bubble + typing effect
2. [ ] Dialog state machine (greeting -> choices -> response -> farewell)
3. [ ] Keeper data structure (lines, emotions, reactions)
4. [ ] Wire into existing shop entry flow
5. [ ] Sound: typewriter clicks, purchase chime

### Phase 2: Shop UI Overhaul (Next Week)
6. [ ] Inotia-style shop layout (portrait left, grid right, description bottom)
7. [ ] Purchase pop-out animation
8. [ ] "Wanna purchase this?" confirm dialog
9. [ ] Farewell sequence on exit
10. [ ] Currency tick animations

### Phase 3: Hub Bots (Week 3)
11. [ ] Bot spawner system
12. [ ] Mission assignment logic
13. [ ] Bot movement + animation
14. [ ] Tap-to-interact
15. [ ] Mission completion rewards

### Phase 4: Combat Mode (Week 4)
16. [ ] Toggle button + HUD
17. [ ] Weapon assignment per archetype
18. [ ] Projectile system (ranged)
19. [ ] Melee swing arc
20. [ ] Zombie stray spawning (night only)
21. [ ] Combat rewards (fun mode, no stakes)

### Phase 5: Polish (Week 5)
22. [ ] Art: portraits, interiors, weapons, zombies
23. [ ] Sound: combat SFX, zombie groans, weapon sounds
24. [ ] Haptics: combat feedback
25. [ ] Leaderboard: "Most Strays Cleared"
26. [ ] Integration test: all systems together

---

*This spec is grounded in the uploaded AK canon (hub_proto.html, AK_LIVING_WORLD.md, AK_SQUAD_MMO_SYSTEM.md, AK_GAME_VISION.md) and tailored for Alley Kingz' dog-themed urban street culture.*
