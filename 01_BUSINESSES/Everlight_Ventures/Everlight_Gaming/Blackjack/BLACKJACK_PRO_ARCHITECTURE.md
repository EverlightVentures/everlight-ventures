# BLACKJACK PRO -- SYSTEM ARCHITECTURE
**Version:** 1.0 | Hive Session: d989e8fb
**Stack:** Unity + FMOD + Photon PUN 2 + FastAPI/Django + Redis

---

## MODULE MAP

```
+------------------+     +------------------+     +------------------+     +------------------+
|  BlackjackCore   |<--->|  JukeboxService  |<--->| AmbienceDirector |<--->|  TableNetSync    |
|  (game logic)    |     |  (music queue)   |     |  (environment)   |     |  (multiplayer)   |
+------------------+     +------------------+     +------------------+     +------------------+
        |                        |                        |                        |
        v                        v                        v                        v
  C# Game Logic            FastAPI/Django            Unity FMOD              Photon PUN 2
  (server auth)            REST + Redis              + Particle FX           + UGS Relay
```

---

## MODULE 1: BlackjackCore (C# -- Unity)

**Responsibility:** Game rules, hand state, betting, payouts. Server-authoritative.

### Key Classes
```
GameManager        -- orchestrates state machine transitions
Deck               -- create, shuffle, deal (supports 1/2/4/8 decks)
Hand               -- card collection + score calculation (Ace flex logic)
BetManager         -- chip wagers, side bets, payout ratios
GameStateMachine   -- states: LOBBY | SONG_VOTE | DEAL | PLAYER_ACTION |
                               DEALER_REVEAL | PAYOUT | HIGHLIGHT | QUEUE_UPDATE
```

### State Machine (simplified)
```
[LOBBY]
  on StartRound -> [SONG_VOTE]

[SONG_VOTE] (30s)
  on TimerExpire or AllReady -> [DEAL]

[DEAL]
  DealToAllPlayers(2 cards each)
  -> [PLAYER_ACTION]

[PLAYER_ACTION] (30s per player, round-robin)
  Hit | Stand | Double | Split
  If Bust -> advance to next player
  AllPlayersActed -> [DEALER_REVEAL]

[DEALER_REVEAL]
  DealerPlaysToSoft17()
  -> [PAYOUT]

[PAYOUT]
  ResolveAllHands()
  EmitPayoutEvents -> AmbienceDirector + JukeboxService
  -> [HIGHLIGHT] if BigWin | [QUEUE_UPDATE] otherwise

[HIGHLIGHT] (3-5s cinematic)
  -> [QUEUE_UPDATE]

[QUEUE_UPDATE] (10s -- show next song, let players vote/queue)
  -> [DEAL]
```

### Payout Rules
- Blackjack: 3:2 (or 6:5 on Classic table setting)
- Win: 1:1
- Push: bet returned
- Insurance: 2:1

---

## MODULE 2: JukeboxService (FastAPI + Redis)

**Responsibility:** Manage the shared song queue per table session. Real-time sync via Redis pub/sub.

### Data Model
```python
# Redis key structure
jukebox:{table_id}:queue      -- List of song_ids in order
jukebox:{table_id}:now_playing -- Hash: {song_id, title, artist, bpm, vibe_state, started_at_ms}
jukebox:{table_id}:votes       -- Hash: {song_id: vote_count}

# PostgreSQL -- permanent records
Table: jukebox_transactions
  id, player_id, table_id, song_id, quarters_spent, action, timestamp

Table: songs
  id, title, artist, bpm, vibe_state, genre, license_source, file_url
```

### API Endpoints
```
POST /jukebox/{table_id}/queue        -- Add song to queue (deduct Quarters)
POST /jukebox/{table_id}/skip-vote    -- Vote to skip current song
POST /jukebox/{table_id}/fastpass     -- Pay to move song to front
GET  /jukebox/{table_id}/state        -- Current song + queue (for client sync)
WS   /jukebox/{table_id}/stream       -- Real-time updates to all clients
```

### Queue Logic
```python
def add_to_queue(table_id, player_id, song_id, quarters):
    # 1. Debit quarters from player wallet (atomic)
    # 2. RPUSH jukebox:{table_id}:queue song_id
    # 3. Publish to jukebox:{table_id}:stream
    # 4. Log to jukebox_transactions
    # On any failure: rollback quarters, return error

def advance_queue(table_id):
    # Called when song ends or skip vote passes
    # LPOP jukebox:{table_id}:queue
    # Update now_playing hash
    # Publish vibe_state change -> AmbienceDirector listens
    # If queue empty: trigger HouseMix mode (AI-filled ambient tracks)
```

### Vibe State Tagging
```python
def get_vibe_state(bpm: int) -> str:
    if bpm >= 128: return "HYPE"
    if bpm >= 90:  return "HEAT"
    if bpm >= 60:  return "CHILL"
    return "AFTER_HOURS"
```

---

## MODULE 3: AmbienceDirector (Unity C# + FMOD)

**Responsibility:** Drive all visual/audio environment changes based on JukeboxService vibe state events.

### Key Components
```
AmbienceDirector.cs     -- listens to jukebox WS stream, dispatches vibe changes
FMODMixer.cs            -- controls FMOD parameters: ambient_vol, crowd_energy, music_vol
LightingController.cs   -- adjusts HDRP volume profiles per vibe state
CrowdAnimator.cs        -- blends NPC animation states (idle/dance/cheer)
CinematicManager.cs     -- triggers event cinematics (blackjack, big win, jackpot)
ParticleController.cs   -- confetti, gold burst, smoke, strobe effects
```

### Vibe State -> Environment Map
```
HYPE:
  FMOD: ambient_vol=0.4, crowd_energy=1.0, music_vol=0.8
  Lighting: PostProcessing profile "Neon_Night" (cyan/magenta, high bloom)
  Crowd: DanceState animation blend weight = 1.0
  Particles: LightStrobe.Play()

HEAT:
  FMOD: ambient_vol=0.5, crowd_energy=0.7, music_vol=0.8
  Lighting: PostProcessing profile "RedGold" (warm high contrast)
  Crowd: ExcitedIdle blend weight = 0.7
  Particles: none

CHILL:
  FMOD: ambient_vol=0.7, crowd_energy=0.3, music_vol=0.7
  Lighting: PostProcessing profile "AmberLounge" (warm dim, fog on)
  Crowd: CasualLean blend weight = 1.0
  Particles: SmokeHaze.Play()

AFTER_HOURS:
  FMOD: ambient_vol=0.9, crowd_energy=0.1, music_vol=0.6
  Lighting: PostProcessing profile "NightBlue" (deep blue, spotlight on table)
  Crowd: BarLean blend weight = 1.0
  Particles: none
```

### Cinematic Events
```csharp
// Called by BlackjackCore on payout resolution
public void OnBlackjack(Player player) {
    // 1. Freeze table camera for 0.5s
    // 2. CinematicCamera.ZoomIn(player.seatPosition)
    // 3. ParticleController.PlayGoldBurst()
    // 4. FMODMixer.DuckMusic(duration: 1.5f)
    // 5. FMODMixer.PlaySting("blackjack_sting")
    // 6. FMODMixer.ResumeMusic(fadeIn: 1.0f)
}

public void OnBigWin(Player player, float multiplier) {
    if (multiplier >= 3f) {
        // Camera zoom + confetti + music swell
        CinematicManager.PlayBigWinSequence(player, multiplier);
    }
}
```

---

## MODULE 4: TableNetSync (Photon PUN 2 + UGS)

**Responsibility:** Keep all player clients in sync on game state, jukebox state, and environmental events.

### Network Objects
```
PhotonView: TableManager    -- game state (dealer hand, player hands, bets, current seat)
PhotonView: JukeboxSync     -- song_id, playback_ms, vibe_state (synced every 2s)
PhotonView: PlayerSeat[N]   -- per-seat: hand, bet, action, emote
```

### Sync Strategy
```
Game State:  Server-authoritative (MasterClient or dedicated server)
Jukebox:     Master client polls JukeboxService WS, broadcasts to room via PUN RPC
Visuals:     Client-side only (particles, camera). Never synced.
Chat:        Photon Chat (separate channel per table)
```

### RPC Calls
```csharp
[PunRPC] void SyncJukeboxState(string songId, int playbackMs, string vibeState)
[PunRPC] void NotifyHandResult(int seatIndex, string result, float payout)
[PunRPC] void TriggerCinematic(string cinematicType, int seatIndex)
[PunRPC] void PlayerEmote(int seatIndex, string emoteId)
```

### Latency + Anti-Cheat
- All hand resolution happens on MasterClient or server; clients only send actions
- JukeboxSync uses `playback_ms` timestamp so late-joining clients can seek to correct position
- Bet amounts validated server-side before PUN state update

---

## CROSS-MODULE EVENT BUS

```
BlackjackCore.OnBlackjack
    -> TableNetSync.TriggerCinematic("blackjack", seatIndex)   [all clients]
    -> AmbienceDirector.OnBlackjack(player)                    [local + RPC]

JukeboxService.OnSongChange(song)
    -> TableNetSync.SyncJukeboxState(song.id, 0, song.vibeState)
    -> AmbienceDirector.SetVibeState(song.vibeState)            [all clients via RPC]

BlackjackCore.OnRoundStart
    -> JukeboxService.NotifyRoundStart()  [server call -- for future: tempo sync to deal rhythm]
```

---

## PHASE 0 VERTICAL SLICE -- CHECKLIST

- [ ] Unity project created, HDRP enabled, 1 lounge scene
- [ ] BlackjackCore: Deck, Hand, GameStateMachine (no side bets yet)
- [ ] FMOD project: ambient_loop, win_sting, jukebox_crossfade event
- [ ] JukeboxService: FastAPI + Redis, 10 test tracks, queue + advance endpoints
- [ ] AmbienceDirector: 4 vibe states wired to FMOD params + lighting profiles
- [ ] Photon PUN 2: 4-player room, seat sync, game state sync
- [ ] Jukebox UI panel: queue list, spend Quarters, skip vote button
- [ ] ONE cinematic: blackjack card fan + gold burst + music sting
- [ ] End-to-end test: 4 local clients, queue a song, play 3 hands, trigger blackjack cinematic

---

*Architecture doc -- update with each sprint retro.*
