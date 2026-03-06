# Everlight Blackjack -- Project Tracker

## Status: IN PROGRESS

## Phase 1 -- Core Logic (DONE via scaffold)
- [x] Deck.cs -- Fisher-Yates shuffle, draw, rebuild
- [x] Hand.cs -- Card list, Ace recalculation, bust/blackjack checks
- [x] GameManager.cs -- State machine, dealer AI, win/loss/push logic
- [x] UIManager.cs -- Event-driven button wiring, score display

## Phase 2 -- Unity Setup (YOU DO THIS IN EDITOR)
- [ ] Create new Unity project (2022 LTS recommended)
- [ ] Copy Assets/ folder into project
- [ ] Import TextMeshPro (Window > Package Manager)
- [ ] Create Canvas with: DealButton, HitButton, StandButton, BetInput, MessageText, MoneyText, PotText, PlayerScoreText, DealerScoreText
- [ ] Create empty GameObjects: Deck, PlayerHand, DealerHand, GameManager, UIManager
- [ ] Assign script components and wire references in Inspector
- [ ] Add card sprites (free pack: https://opengameart.org/content/playing-cards-vector-png)

## Phase 3 -- Polish
- [ ] Animate card deal (lerp from deck position to hand position)
- [ ] Add sound effects (flip, win, bust)
- [ ] Dealer hole card face-down until dealer turn
- [ ] Double Down button (2x bet, one card, stand)
- [ ] Split pairs support

## Phase 4 -- Ship (optional)
- [ ] Build for Android (File > Build Settings)
- [ ] Add AdMob rewarded ads for chip refills
- [ ] Publish to Google Play

## Rules Implemented
- Dealer hits soft 17 (casino standard)
- Blackjack pays 1.5x (3:2)
- Dealer peeks for natural blackjack before player acts
- Push returns bet
- Auto-rebuild deck if empty

## DO NOT ADD until Phase 1-2 verified
- Multiplayer
- Side bets (Insurance, Perfect Pairs)
- Online leaderboard
