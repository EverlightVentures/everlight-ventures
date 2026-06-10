# ALLEY KINGZ -- PLATFORM & FEATURE GAP + ROADMAP
**Reality check (2026-06-09): alleykingz.online is a playable MATCH, not a PLATFORM. You drop straight into a battle. There's no front door, no identity, no reason to come back tomorrow. That's the gap to close.**

================================================================
## A. WHAT REAL GAMING WEBSITES HAVE THAT WE DON'T (your priority)
================================================================
Right now: no home page, no lobby, no accounts, nothing social. Here's the standard stack every real game site/app has:

1. **Home / landing page** -- hero, a 10-sec gameplay trailer/loop, "PLAY NOW" button, feature highlights, screenshots, the $BCARDD tie-in, social links. The front door. (We have none -- you load straight into a match.)
2. **Account system** -- sign up / log in (email, Google, wallet). Without it there's NO save, NO progression that sticks, NO cross-device, NO leaderboard identity. This is the #1 missing foundation.
3. **Lobby / main menu** -- the hub you return to between matches: Play, Deck Lab, Shop, Profile, Leaderboard, Settings. (We jump into combat; there's no "home base.")
4. **Player profile** -- avatar, level, trophies, win/loss, card collection showcase, badges. Identity = retention.
5. **Cloud save / persistence** -- progress tied to the account, not the browser. Right now everything's localStorage = wiped if they clear the browser or switch devices.
6. **Social layer** -- friends list, leaderboards (global + friends), clans/crews, chat, share-your-deck. This is what makes people stay and bring friends.
7. **Daily reward / login streak** -- the single biggest retention hook in mobile games. Come back daily, get gems/chests.
8. **News / announcements** -- patch notes, events, "what's new." Signals the game is alive.
9. **Settings / account management** -- sound, controls, logout, delete account, support.
10. **Onboarding / tutorial** -- a guided first match so new players aren't lost.
11. **Web store** -- the gem shop surfaced on the site (not just in-match), with the flashy art.
12. **Community hub** -- Discord/Telegram/X links front and center.

================================================================
## B. WHAT CLASH ROYALE HAS THAT WE DON'T (gameplay / meta)
================================================================
- **Tilted 3D camera** for depth (your ARENA_CAMERA_TILT_BRIEF_PHASE2 -- Phase 2).
- **Trophy Road / Arenas / Leagues** -- the ladder that gives every match stakes + unlocks.
- **Real-time PvP** (we're PvE vs AI right now -- this is the big one, see C).
- **Clans + Clan Wars** -- join a crew, donate cards, war together. Huge social retention.
- **Seasons + a Battle/Season Pass** -- the modern monetization + engagement engine.
- **Challenges + Tournaments** -- special rule sets, prizes, competitive ladders.
- **Events / Limited-Time Modes** -- keeps the meta fresh, drives daily logins.
- **Quests / daily + weekly missions** -- directed goals + rewards.
- **Emotes in battle**, **replays / spectate**, **2v2** -- polish + social.
- **Card mastery / progression depth** beyond just level (we have copies-to-level; good start).

================================================================
## C. THE BIG ONE -- REAL-TIME PvP
================================================================
You're playing vs AI (PvE). The entire social + competitive + viral loop of Clash is **player vs player**. PvP needs: accounts + matchmaking + a realtime server (authoritative, anti-cheat). It's the hardest build but it's THE thing that turns a single-player toy into a game people obsess over and tell friends about. Plan it, but it comes AFTER the platform foundation (accounts/lobby), because PvP is meaningless without identity.

================================================================
## D. PRIORITIZED ROADMAP (build for max impact, cheapest-first)
================================================================
**PHASE 1 -- The Front Door + Identity (makes it a real product)**
- Real home/landing page (Next.js or a clean static page; hero + trailer + PLAY).
- Account system via **Supabase Auth** (email + Google + optional wallet) -- you already use Supabase.
- Lobby/main menu hub.
- Cloud save (move localStorage -> Supabase tied to the account).
- Player profile (level, trophies, collection).
> This is the layer that turns "a match" into "a game with a home." Highest ROI.

**PHASE 2 -- Retention + Social (cheap hooks, big stickiness)**
- Daily reward / login streak.
- Leaderboards (global + friends) -- needs accounts from Phase 1.
- News/announcements panel.
- Friends list + share-your-deck.
- Camera tilt (the arena Phase 2 brief) for the visual upgrade.

**PHASE 3 -- The Meta Engine (depth + monetization)**
- Trophy Road / arenas / progression ladder.
- Seasons + a Battle Pass (free + premium track) -- the modern money engine.
- Quests / daily missions.
- Web-surfaced gem store with the flashy art (in progress).

**PHASE 4 -- Multiplayer (the obsession loop)**
- Real-time PvP + matchmaking (authoritative server, anti-cheat).
- Clans/crews + clan wars.
- Tournaments, 2v2, events.

**CROSS-CUTTING**
- $BCARDD tie-in: holder perks (skins/tables), "powered by $BCARDD," cross-link the coin site (kept as CULTURE, never "the game makes the coin moon" -- securities-safe).
- Keep the casino (B-CARDD BET) a SEPARATE product (no money rail to the coin).

## THE ONE-LINE STRATEGY
Build the **front door + accounts (Phase 1) first.** Everything social, competitive, and monetizable (leaderboards, seasons, PvP) is impossible without player identity. A login + a lobby + cloud save is the unlock for all of it.
