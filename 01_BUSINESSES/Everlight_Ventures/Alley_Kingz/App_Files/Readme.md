# Arena Advance

A Clash Royale-inspired real-time PvP mobile game with an innovative **Advance Contract** monetization system.

## 🎮 Core Concept

Real-time 2-4 minute PvP battles where players:
- Build 8-card decks from a collection
- Manage elixir economy in battle
- Destroy opponent towers to earn crowns
- Progress through arenas and leagues

**Unique Feature: Advance Contracts**
- Players get premium rewards upfront
- Must complete skill/engagement challenges to keep them
- Fail? Pay a small gem fee or forfeit rewards
- AI-powered advisor estimates success probability

## 📁 Project Structure

```
ArenaAdvance/
├── Assets/
│   ├── Scripts/
│   │   ├── Core/               # Player data, save system
│   │   ├── Data/               # Enums, constants
│   │   ├── Gameplay/           # Battle system, units, towers
│   │   ├── Contracts/          # Advance Contract system
│   │   ├── AI/                 # Contract Advisor, Matchmaking, AI opponent
│   │   ├── Economy/            # Shop, purchases, currency
│   │   ├── Managers/           # Game & Battle managers
│   │   ├── UI/                 # All UI components
│   │   └── Utils/              # Helper classes
│   ├── ScriptableObjects/      # Card definitions, contract templates
│   ├── Prefabs/
│   │   ├── Cards/
│   │   ├── Units/
│   │   ├── Effects/
│   │   └── UI/
│   ├── Scenes/
│   └── Resources/
└── README.md
```

## 🚀 Getting Started

### Prerequisites
- Unity 2022.3 LTS or newer
- TextMeshPro package
- (Optional) Addressables for asset management

### Setup Steps

1. **Create new Unity project** (2D or 2D URP template)

2. **Import the scripts** - Copy the `Assets/Scripts` folder to your project

3. **Install TextMeshPro**
   - Window → TextMeshPro → Import TMP Essential Resources

4. **Create required ScriptableObjects**
   - Right-click in Project → Create → Arena Advance → Card Definition
   - Create cards for your starter deck

5. **Set up Game Manager**
   - Create empty GameObject named "GameManager"
   - Add `GameManager` component
   - This persists across scenes (DontDestroyOnLoad)

6. **Create your first scene**
   - Add BattleManager to handle combat
   - Set up arena with tower positions
   - Add UI Canvas with BattleHUD

## 🎴 Creating Cards

1. Right-click in Project window
2. Create → Arena Advance → Card Definition
3. Fill in the card properties:
   - Basic Info: ID, name, description, art
   - Properties: rarity, type, elixir cost, unlock arena
   - Combat Stats: HP, damage, attack speed, range
   - Targeting: ground/air, area damage, etc.

Example starter cards:
- Knight (3 elixir, melee tank)
- Archers (3 elixir, ranged DPS)
- Fireball (4 elixir, area damage spell)
- Giant (5 elixir, building targeter)

## 📜 Advance Contract System

The core innovation - "loans" disguised as challenges:

### Contract Types
- **Performance Contracts** - Reach rank, win X battles
- **Engagement Contracts** - Play X days, complete quests
- **Hybrid Contracts** - Mix of both (OR logic)

### Player Credit System
```
Bronze (0-20)   → 1 contract, small rewards
Silver (21-50)  → 2 contracts, medium rewards
Gold (51-80)    → 3 contracts, large rewards
Platinum (81+)  → 4 contracts, huge rewards
```

### Contract Flow
1. Player views available contracts
2. AI Advisor shows success probability
3. Player accepts → Gets rewards immediately
4. Player plays during season
5. End of season:
   - Success → Rewards permanent, credit score up
   - Fail → Choose: pay gems, forfeit, or redemption quest

### Ethical Design Principles
- ✅ Never call it "debt" or "loan" in UI
- ✅ Always show clear conditions upfront
- ✅ Provide free "forfeit" escape option
- ✅ No real-world money interest or APR
- ✅ Skill-based, not purely pay-to-skip

## 🤖 AI Systems

### Contract Advisor
Estimates success probability using:
- Player's recent win rate
- Average matches per day
- Historical contract completion
- Time remaining in season

Output:
- Success probability (0-100%)
- Difficulty bucket (Easy/Fair/Hard/Extreme)
- Personalized notes
- Churn risk assessment

### Smart Matchmaking
Goals: 51-55% win rate sweet spot

Features:
- Trophy-based matching
- Card level consideration
- "Morale boost" after losing streaks
- "Challenge" matches after win streaks
- Fair matches for contract holders

### AI Opponent
For single player / bot matches:
- Multiple personalities (Aggressive, Defensive, Balanced, Cycle)
- Skill-based reaction time
- Intentional mistake rate
- Strategic card evaluation

## 💰 Monetization Stack

### Revenue Streams
1. **Season Pass** ($7.99/season) - Premium reward track
2. **VIP Subscription** ($4.99/month) - Daily rewards, better contract terms
3. **Gem Packs** - Hard currency for shop
4. **Advance Contracts** - Settlement fees from failures

### Player Segments (for offer targeting)
- New Player → Starter packs
- F2P Grinder → Value conversion offers
- Light Spender → Season pass, small bundles
- Whale → Premium exclusive bundles
- At-Risk Churn → Comeback offers
- Contract Holder → Gem support packs

### Ethical Monetization Rules
- ✅ Same prices for all players (no dynamic pricing)
- ✅ Base game fully playable F2P
- ✅ No hidden fees or dark patterns
- ✅ Clear value proposition

## 🎯 Key Classes Reference

### Core Systems

| Class | Purpose |
|-------|---------|
| `GameManager` | Singleton managing game state, player data, contracts |
| `BattleManager` | Handles real-time combat, unit updates, tower damage |
| `EconomyManager` | Shop offers, purchases, player segmentation |
| `PlayerData` | All player progression, stats, card collection |

### Contract System

| Class | Purpose |
|-------|---------|
| `AdvanceContract` | Contract data: conditions, rewards, penalties |
| `ContractAdvisor` | AI that estimates success probability |
| `PlayerCreditProfile` | Credit score, tier, contract history |
| `ContractTemplates` | Factory methods for standard contracts |

### Battle System

| Class | Purpose |
|-------|---------|
| `BattleState` | Match state: timers, players, units, crowns |
| `BattlePlayer` | Per-player state: elixir, deck, hand, towers |
| `BattleUnit` | Active unit in combat |
| `Tower` | Tower health, damage, activation state |

### AI Systems

| Class | Purpose |
|-------|---------|
| `Matchmaker` | Finds fair opponents, applies morale boosts |
| `AIOpponent` | Bot decision-making for single player |
| `ContractAdvisor` | Success probability estimation |

## 🔧 Configuration

### Battle Timing (BattleState)
```csharp
REGULAR_TIME = 120f;      // 2 minutes
DOUBLE_ELIXIR_TIME = 60f; // 1 minute  
OVERTIME_TIME = 60f;      // 1 minute sudden death
```

### Credit Tiers (PlayerCreditProfile)
```csharp
Bronze:   0-20 score,  1 contract,  $3 max value
Silver:  21-50 score,  2 contracts, $10 max value
Gold:    51-80 score,  3 contracts, $25 max value
Platinum: 81+ score,   4 contracts, $50 max value
```

### Matchmaking (Matchmaker)
```csharp
TARGET_WIN_RATE = 0.48 - 0.55  // Sweet spot
TROPHY_RANGE_BASE = 100
MAX_CARD_LEVEL_DIFF = 2
```

## 📱 UI Components

### BattleHUD
- Timer display
- Crown indicators (3 per player)
- Elixir bar with double-elixir color change
- 4-card hand + next card preview
- Surrender/pause buttons

### ContractOfferUI
- Contract name, description, duration
- Conditions list (wins, rank, play days)
- Rewards preview
- AI Advisor panel:
  - Success probability percentage
  - Difficulty indicator (color-coded)
  - Personalized recommendation
  - "Show easier version" button

### ContractProgressUI
- Progress bar
- Days remaining
- Individual goal tracking
- Status message from AI Advisor

## 🗺️ Development Roadmap

### Phase 1: Core Prototype ✅
- [x] Battle system (elixir, units, towers)
- [x] Basic matchmaking
- [x] Player data persistence
- [x] Card system

### Phase 2: Contract System ✅
- [x] Advance Contract data model
- [x] Contract Advisor AI
- [x] Credit profile system
- [x] Settlement options

### Phase 3: Economy & Shop ✅
- [x] Shop offer system
- [x] Player segmentation
- [x] Currency management
- [ ] IAP integration

### Phase 4: Polish
- [ ] Visual effects & animations
- [ ] Sound effects & music
- [ ] Tutorial flow
- [ ] Push notifications

### Phase 5: Live Ops
- [ ] Seasonal content system
- [ ] Event framework
- [ ] Analytics integration
- [ ] A/B testing infrastructure

## 🧪 Testing Checklist

### Battle System
- [ ] Elixir regenerates correctly (1x and 2x speed)
- [ ] Cards play from hand and cycle
- [ ] Units move, target, and attack
- [ ] Towers take damage and activate king
- [ ] Crown counting and win conditions
- [ ] Overtime triggers on tie

### Contract System
- [ ] Contracts display correct conditions
- [ ] Progress updates after matches
- [ ] Success detection works
- [ ] Settlement options function
- [ ] Credit score updates properly
- [ ] Cooldown applied after forfeit

### Economy
- [ ] Gold/gem spending works
- [ ] Offers display correctly
- [ ] Segment-specific offers appear
- [ ] Card upgrades cost correctly

## 📄 License

This project is a learning/portfolio piece. The game design concepts are inspired by Clash Royale (Supercell) but all code is original.

---

**Remember:** The Advance Contract system is designed to be ethical and player-friendly. Never use dark patterns, always provide clear information, and ensure F2P players can compete without spending.
