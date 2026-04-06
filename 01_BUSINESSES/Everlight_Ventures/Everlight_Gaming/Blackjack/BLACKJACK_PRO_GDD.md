# BLACKJACK PRO -- GAME DESIGN DOCUMENT
**Version:** 1.0 | **Status:** Approved for Pre-Production
**Project:** Alley Kingz / Everlight Gaming
**Author:** Everlight AI Hive Mind | Hive Session: d989e8fb

---

## 1. VISION STATEMENT

Transform the existing lite blackjack prototype into a **PC/console-grade social casino experience** -- think Plato Games with a heartbeat. The table is alive: music pulses from a player-controlled jukebox, lighting shifts with the vibe, and every big win triggers a cinematic moment. This is not just a card game. It's a hangout spot with stakes.

**North Star:** "Vegas lounge you never have to leave."

---

## 2. COMPETITIVE REFERENCE

| Title | What We're Taking | What We're Leaving |
|---|---|---|
| **Plato Games Blackjack** | Social tables, clean UI, casual onboarding | Flat audio, no environment |
| **TouchTunes Jukebox** | Credit-based song queue, shared playlist, community vibe | Physical hardware |
| **Blackjack Bailey VR** | Immersive dealer, table presence | VR-only, niche audience |
| **PokerStars** | Lobby polish, ranked play, avatar system | Real money, legal overhead |

---

## 3. THE JUKEBOX -- CORE FEATURE

### 3.1 Concept
A 3D jukebox sits in the corner of every table lounge. Players spend **Gems or Quarters** (soft currency) to queue songs. The jukebox is always visible, always spinning, always influencing the room.

### 3.2 Jukebox Economy
| Action | Cost |
|---|---|
| Queue 1 song | 5 Quarters |
| Skip to front of queue (fast-pass) | 20 Quarters |
| Play a full custom playlist (5 songs) | 20 Quarters |
| Vote to skip current song | 1 Quarter |
| Buy a Jukebox Skin (cosmetic) | 200 Gems |
| Unlock Premium Genre Pack | 100 Gems |

**Quarters** are a soft currency earned through:
- Daily login bonus
- Winning hands (+1 per win streak)
- Completing missions
- Optional IAP bundles ($0.99 / $2.99 / $9.99)

### 3.3 Playlist Mechanics
- **Community Queue**: Shared across all players at the table. Anyone can add; top-rated player gets "DJ" badge during their song.
- **Song Voting**: After every hand, players see the next 3 queued songs. They vote thumbs up/down. Majority skip triggers the next track.
- **House Mix Mode**: If no one queues songs, the AI fills the queue with genre-matched ambient casino music.
- **DJ Leaderboard**: Weekly leaderboard of who queued the most-upvoted songs. Winner gets a seasonal DJ crown cosmetic.

### 3.4 Music Sources (Legal / No-Rights Issues)
- **Phase 1**: Licensed ambient/casino tracks from Epidemic Sound or Artlist (flat annual fee)
- **Phase 2**: Curated genre packs sold as DLC (Lo-Fi, Hip-Hop, Latin, Jazz, EDM, R&B)
- **Phase 3**: UGC integration via Spotify/Apple Music API (mobile only, SDK permitted)

---

## 4. THE PAIRING FEATURE -- AMBIENCE DIRECTOR

### 4.1 Concept: Music-Reactive Casino Lounge
The jukebox does not just play music -- it **drives the room**. This is the killer differentiator.

Every song has a **Vibe State** (auto-tagged by tempo/genre):
| Vibe State | BPM Range | Effect |
|---|---|---|
| **HYPE** | 128+ BPM | Neon strobes, crowd noise rises, dealer gets animated |
| **CHILL** | 60-90 BPM | Warm amber lighting, smoke effect, slower dealer animations |
| **HEAT** | 90-128 BPM | Red/gold lighting, card deal sounds get sharper |
| **AFTER-HOURS** | <60 BPM | Dim blue lighting, solo spotlight on table, quiet lounge |

### 4.2 Environmental Events
- **Big Win Cinematic**: On any win of 3x+ bet, camera zooms in, confetti drops, jukebox volume ducks briefly, then track swells back up
- **Blackjack Moment**: Freeze frame, cards fan out in 3D, gold shimmer particle burst, crowd "ooohs"
- **Bust Animation**: Cards crash and scatter, dealer does a subtle smirk emote
- **Jackpot Trigger**: Full room goes white, music cuts, jackpot sound plays, then the queued track resumes
- **Dealer Banter**: During HYPE mode, dealer has 5-10% chance to throw a reaction emote per hand

### 4.3 NPC Crowd
- Background NPCs at bar/lounge area react to music and big wins
- During HYPE mode: NPCs dance, clap, raise drinks
- During AFTER-HOURS: NPCs lean against bar, quiet conversations
- Crowd density scales with table player count (more players = fuller lounge)

---

## 5. BLACKJACK PRO -- FULL FEATURE UPGRADE

### 5.1 From Lite to Pro: Feature Delta

| Feature | Lite (Current) | Pro (Target) |
|---|---|---|
| Graphics | Python CLI / Flask 2D | Unity 3D with HDRP lighting |
| Deck count | 1 | 1, 2, 4, 8 (selectable) |
| Player count | Solo | 1-6 players per table |
| Dealer | None (text) | Animated 3D dealer with 3 skins |
| Audio | None | FMOD dynamic mixing + jukebox |
| Chat | None | In-table text + emotes |
| Customization | None | Table themes, card decks, dealer skins |
| Ranking | None | Bronze -> Diamond seasonal ranks |
| Side bets | Planned | War BJ, Pairs, Lucky Ladies, 21+3 |
| Social | None | Friends, private tables, spectate |
| Jukebox | None | Full (see Section 3) |
| Ambience | None | Full (see Section 4) |
| Economy | None | Chips + Quarters + Gems |

### 5.2 Table Variants
1. **Classic Table** -- standard blackjack, 6:5 or 3:2 payout toggle
2. **High Roller Room** -- minimum 500 chips, exclusive decor, no Jukebox community queue (private playlist)
3. **Lounge Table** -- jukebox is center stage, lower stakes, social focus
4. **Tournament Table** -- elimination rounds, 4-8 players, no jukebox during hands (plays between rounds)

### 5.3 Game Flow State Machine
```
LOBBY (select table, adjust settings)
    |
SONG_VOTE (queue jukebox for session, 30 sec)
    |
DEAL (cards dealt, bets locked)
    |
PLAYER_ACTION (hit/stand/double/split -- 30s timer per player)
    |
DEALER_REVEAL (dealer plays out hand)
    |
PAYOUT (chips awarded, streak tracked)
    |
HIGHLIGHT (cinematic moment if big win/blackjack)
    |
SONG_QUEUE_UPDATE (next song previewed, can tip/skip)
    |
DEAL (loop) | LOBBY (if leaving)
```

### 5.4 Side Bets
| Bet | Payout | Trigger |
|---|---|---|
| Perfect Pairs | 25:1 | Identical rank + suit |
| Colored Pairs | 12:1 | Same color, same rank |
| Mixed Pairs | 6:1 | Same rank, different suit+color |
| 21+3 | 9:1 | Player's 2 cards + dealer up = 3-card poker hand |
| Lucky Ladies | 4:1 | Player total = 20 |
| War Blackjack | 1:1 | Player top card > dealer top card |

---

## 6. MONETIZATION ARCHITECTURE

**Rule #1: No pay-to-win. Zero odds advantages for paid players.**

| Revenue Stream | Model | Price |
|---|---|---|
| Jukebox Quarters pack | IAP | $0.99 / $2.99 / $9.99 |
| Dealer Skin pack | IAP | $2.99 |
| Table Theme pack | IAP | $1.99 |
| Card Deck pack | IAP | $1.49 |
| Premium Genre Pack | IAP | $0.99 |
| Battle Pass (seasonal) | Subscription | $4.99/mo |
| High Roller Pass | Subscription | $9.99/mo (private tables, no ads) |
| XLM Tip Jar | P2P | Player tips dealer (goes to game fund) |

**Jukebox = Primary Retention Driver**: Players stay longer to hear their queued songs. Longer sessions -> more chip play -> more IAP conversion. This is the core monetization loop.

---

## 7. PROGRESSION + SOCIAL SYSTEMS

### 7.1 Player Ranks (Seasonal Reset)
```
Newcomer -> Regular -> Shark -> High Roller -> Diamond Whale
```
- Rank unlocks exclusive table access, cosmetic frames, and dealer reactions
- Season duration: 3 months

### 7.2 Achievements / Badges
- "First Blackjack", "5-Win Streak", "DJ Crown Weekly", "Debt-Free Legend"
- Badges display on player profile card at table

### 7.3 Friends + Private Tables
- Add friends via username
- Create private table with invite code (Plato-style)
- Shared private jukebox queue -- host is DJ by default

### 7.4 Spectate Mode
- Non-playing users can enter a table as spectators
- Can react with emotes, tip Quarters to the table jukebox
- Creates audience energy for high-stakes or tournament tables

---

## 8. TECH STACK (RECOMMENDED)

| Layer | Tool | Why |
|---|---|---|
| Game Engine | Unity (URP/HDRP) | Best asset ecosystem for casino + VR path |
| Audio System | FMOD Studio Plugin | Dynamic mixing, win swells, jukebox fade/crossfade |
| Multiplayer | Unity Gaming Services (UGS) or Photon PUN 2 | Session management, relay, chat |
| Backend | Python/FastAPI or Django | Existing Everlight stack, jukebox queue API |
| Database | PostgreSQL (player data) + Redis (queue state) | Redis for real-time jukebox sync |
| Payments | Stripe (IAP web) + Unity IAP (mobile) | Dual-platform |
| Auth | Supabase (existing Everlight auth) | Reuse existing Everlight infra |

---

## 9. DEVELOPMENT PHASES

### Phase 0 -- Vertical Slice (4-6 weeks)
**Goal:** 1 table, 4 players, shared jukebox queue, one cinematic win event
- [ ] Unity 3D table scene (static lounge backdrop)
- [ ] Core blackjack logic ported from Python to C#
- [ ] FMOD integrated: ambient + win sting + jukebox crossfade
- [ ] Basic jukebox UI (queue list, spend Quarters, skip vote)
- [ ] Multiplayer: 4-player Photon test room
- [ ] ONE cinematic moment: blackjack 3D card fan + gold burst

### Phase 1 -- Social MVP (6-8 weeks)
- [ ] Full Ambience Director (4 vibe states + lighting system)
- [ ] NPC crowd system (reactive to vibe)
- [ ] Dealer avatar (1 skin, basic emotes)
- [ ] Text chat + emote system
- [ ] Player profiles + basic progression
- [ ] Quarters economy + jukebox IAP

### Phase 2 -- Pro Launch (8-10 weeks)
- [ ] All table variants
- [ ] Full side bet system
- [ ] Seasonal ranking
- [ ] Friends + private tables
- [ ] Spectate mode
- [ ] Battle Pass
- [ ] 3 dealer skins + 5 table themes
- [ ] Genre pack DLC

### Phase 3 -- Scale
- [ ] Mobile port
- [ ] XLM integration (tip jar, future staking)
- [ ] Tournament infrastructure
- [ ] Spotify/Apple Music API
- [ ] VR table (Meta Quest)

---

## 10. RISK LOG

| Risk | Severity | Mitigation |
|---|---|---|
| Sync drift between music state and hand state | HIGH | Redis pub/sub for authoritative song_id + playback_ms across all clients |
| "Phantom quarters" -- player pays, queue fails | HIGH | Transactional queue writes; compensate on failure with refund |
| Feature creep delaying Phase 0 | HIGH | Hard scope lock: Phase 0 = vertical slice ONLY |
| Pay-to-win perception | MEDIUM | Public fairness FAQ + no-odds-advantage policy in ToS |
| Music licensing violations | MEDIUM | Use only licensed libraries; no copyrighted tracks in base game |
| Asset file size bloat (3D lounge) | MEDIUM | Lazy load audio tracks; LOD on 3D environment |

---

*Document owned by Everlight Gaming. Update version on any scope change.*
