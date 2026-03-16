# Blackjack Vegas -- Architecture & Monetization Roadmap
Everlight Games | Hive Mind Output: 2026-03-01

---

## Pit Boss Audit (Your Script)

| Area | Score | Notes |
|------|-------|-------|
| Core game logic | 7/10 | Hit/Stand/Bust/Push correct. Dealer AI present. |
| State management | 3/10 | Raw booleans -- replace with state machine (done below) |
| Card visuals | 0/10 | Text-only. Add Sprite-based CardData SOs |
| Save/persistence | 0/10 | Nothing persists on browser refresh |
| Monetization hooks | 0/10 | No gems, no IAP, no subscriptions |
| Multiplayer/social | 0/10 | Single-player only |
| WebGL readiness | 4/10 | Needs Brotli compression + responsive Canvas |

Verdict: Solid cargo. Needs containerizing before it ships.

---

## File Map (this project)

```
BlackjackVegas/
├── Scripts/
│   ├── Core/
│   │   └── GameManager.cs          ← State machine (IDLE→BETTING→DEAL→...)
│   ├── Data/
│   │   ├── CardData.cs             ← ScriptableObject per card (52x)
│   │   ├── DeckController.cs       ← 6-deck shoe, Fisher-Yates shuffle
│   │   └── TableConfigSO.cs        ← Bet limits, house rules per table tier
│   ├── Economy/
│   │   ├── PlayerProfile.cs        ← Chips, Gems, Clout XP, cosmetics
│   │   ├── GemManager.cs           ← Shop, gem spending, IAP callbacks
│   │   ├── SaveSystem.cs           ← PlayerPrefs JSON (WebGL-safe)
│   │   └── IAPManager.cs           ← Unity IAP bridge (stub until package installed)
│   ├── UI/
│   │   └── UIManager.cs            ← All panels, DOTween hooks, HUD refresh
│   ├── Audit/
│   │   └── PitBossAuditor.cs       ← JSONL audit trail, anomaly detection
│   └── Multiplayer/                ← (Phase 2) Photon PUN2 lobby scripts
├── Assets/
│   ├── Cards/                      ← 52 PNG card fronts (any free set)
│   ├── Chips/                      ← Chip stack sprites
│   ├── UI/                         ← Panel backgrounds, buttons, icons
│   └── Sounds/                     ← Card deal SFX, win jingle, etc.
└── Docs/
    └── ARCHITECTURE.md             ← This file
```

---

## State Machine Flow

```
IDLE ──[Deal pressed]──► BETTING
BETTING ──[Bet placed]──► DEALING
DEALING ──[4 cards out]──► PLAYER_TURN
PLAYER_TURN
  ├── Hit      → (bust?) → RESOLVE : stay PLAYER_TURN
  ├── Stand    → DEALER_TURN
  └── Double   → Hit once → DEALER_TURN
DEALER_TURN ──[≥17]──► RESOLVE
RESOLVE ──[calc payout]──► PAYOUT
PAYOUT ──[save + delay]──► IDLE
```

---

## Monetization Stack

### Dual Currency
| Currency | Type | Source | Use |
|----------|------|--------|-----|
| Chips | Soft | Daily grant, winning hands | Bets, chip shop |
| Gems | Hard | Real money (IAP) | Cosmetics, VIP access, chip top-ups |

### Revenue Lanes

1. **Gem Bundles** (consumable IAP)
   - $0.99 → 100 gems
   - $4.99 → 550 gems (+10%)
   - $9.99 → 1,400 gems (+16%)
   - $49.99 → 8,000 gems (+23%, Best Value badge)

2. **Subscriptions** (recurring)
   - Gold Table: $4.99/mo → 2.5x daily chips, gold card back, no ads
   - VIP Pit: $9.99/mo → 5x daily chips, all cosmetics unlocked, private table, priority support
   - Math: 200 Gold subs = $1,000 MRR. 100 VIP subs = $1,000 MRR.
   - Target: 500 players, 15% convert = $750-$1,500 MRR within 90 days

3. **Cosmetics** (gem spend)
   - Card backs: Gold (200 gems), Vegas Night (500 gems), Diamond (1,500 gems)
   - Table felts: Red, Blue, Velvet, Neon (100-800 gems)
   - Dealer avatars: Standard to Celebrity (0-2,000 gems)
   - Chip sets: Classic, Gold, Crypto (0-500 gems)

4. **Clout / Status** (FOMO driver)
   - Levels 1-100 (XP from every hand)
   - Leaderboard resets weekly -- Top 10 get exclusive cosmetics
   - Clout badges displayed at tables (social proof)
   - Level-gated VIP rooms (Level 20+ only, etc.)

---

## Phase Roadmap

### Phase 0 -- Architecture (NOW, 1-2 days)
- [x] State machine GameManager
- [x] CardData + DeckController ScriptableObjects
- [x] PlayerProfile + SaveSystem
- [x] GemManager + IAPManager stubs
- [x] PitBossAuditor
- [x] UIManager skeleton

### Phase 1 -- Core Loop (1 week)
- [ ] Import free card sprite pack (52 PNGs)
- [ ] Build Unity scene: Canvas, card zones, chip counter
- [ ] Wire all UI buttons to GameManager
- [ ] DOTween: card slide-in, chip count up, result bounce
- [ ] Test full round in Editor: Deal → Hit/Stand → Resolve → Payout

### Phase 2 -- Economy (1 week)
- [ ] Install Unity IAP (com.unity.purchasing)
- [ ] Wire GemManager → IAPManager
- [ ] Build Gem Shop UI panel
- [ ] Daily chip grant on session start
- [ ] Cosmetic unlock + equip flow (card backs)

### Phase 3 -- WebGL Deploy (3 days)
- [ ] Build Settings → Platform: WebGL
- [ ] Enable Brotli compression
- [ ] Canvas Scaler: Scale with screen size
- [ ] Test in Chrome + mobile Safari
- [ ] Deploy to itch.io (free) for beta
- [ ] Stripe Checkout for subscriptions (server-side webhook)

### Phase 4 -- Social / Clout (2 weeks)
- [ ] Clout leaderboard (Unity Gaming Services or PlayFab free tier)
- [ ] Weekly tournament mode
- [ ] Photon PUN2: multiplayer tables (up to 6 players)
- [ ] Pit Boss spectator mode

### Phase 5 -- Monetization Polish (ongoing)
- [ ] A/B test gem bundle pricing
- [ ] Push notifications (WebGL: browser push API)
- [ ] Referral system: invite friends → bonus chips
- [ ] Seasonal cosmetics (holiday card backs, etc.)

---

## WebGL Setup Quick-Start

```
1. File > Build Settings > Switch Platform: WebGL
2. Player Settings > Publishing Settings:
   - Compression: Brotli
   - Template: Minimal
3. Player Settings > Resolution:
   - Run In Background: ON (keep audio going)
   - WebGL Memory Size: 512 MB
4. Host on itch.io, set to HTML game type
5. For Stripe subs: create a Node/Python webhook server,
   grant SubscriptionTier via PlayFab/custom backend
```

---

## Package Manager Dependencies

| Package | ID | Purpose |
|---------|----|---------|
| DOTween | Asset Store (free) | Card animations |
| Unity IAP | com.unity.purchasing | Gem/sub purchases |
| TextMeshPro | com.unity.textmeshpro | Sharp UI text |
| Unity Gaming Services | com.unity.services.core | Leaderboards (Phase 4) |
| Photon PUN2 | Asset Store (free tier) | Multiplayer (Phase 4) |

---

## House Edge Reference (Vegas Strip Rules)
- Blackjack pays 3:2 (1.5x bet)
- Dealer hits on soft 17
- 6-deck shoe, 75% penetration before reshuffle
- Double after split allowed
- No surrender
- House edge: ~0.5% with basic strategy

The house doesn't need to cheat -- the math wins long-term.
Your gem shop is the real house edge.
