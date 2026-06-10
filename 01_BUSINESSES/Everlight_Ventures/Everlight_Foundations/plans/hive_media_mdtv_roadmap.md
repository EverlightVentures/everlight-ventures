# Hive Media / MDtv -- Canonical Build Roadmap

**Date:** 2026-05-06 11:35 PT
**Author:** Lucrex (synthesis of 6-lane Hive dispatch -- 55 / 67 / 62 / 63 / 69 / 68)
**Status:** Greenfield. No code exists. This doc is the single source of truth.
**Codename:** **MDtv** (kept as branding for the Next.js shell. "MD" = brand mark. Not a competing product.)

---

## 1. What Rich Asked For (verbatim parse)

1. Audit current media-server state.
2. Surface his Android media apps inside ONE TV guide.
3. QR-code login that auto-syncs his account into the media-server apps.
4. Massive live-TV guide -- scroll changes from Pluto block -> Prime Live block -> Tubi block -> all sources, like infinite DirecTV.
5. Movies section pulling Netflix / Prime / Disney+ catalogs ("all my media platforms").
6. Streaming + torrent integration.
7. UI must beat Google TV. Use Next.js + React + Everlight gold theme as the TV shell.
8. Personal and private. Not exposed to the open internet.

## 2. Audit Result

- **No `MDtv` codebase exists** in `/AA_MY_DRIVE`. Prior reference is the Tier-3 deferred `jelly_and_paperclip_eval.md` (Apr 2026, "deliberate NO until Oracle disk clears").
- **Library directory exists**: `/AA_MY_DRIVE/04_MEDIA_LIBRARY/{Audio,Music,Photos,Videos}` -- empty volumes ready to fill.
- **Reusable theme exists**: `/AA_MY_DRIVE/06_DEVELOPMENT/everlightventures/` (Next.js + Shadcn + gold theme tokens). Inherit via CSS-token import, do NOT duplicate.
- **Compute headroom on PC**: ~10 GiB RAM after current load (Langfuse / Blinko / n8n / homarr / MinIO / ClickHouse). Fits the proposed stack.

## 3. Stack Decision (locked)

**Custom Next.js 15 shell ("MDtv") on Jellyfin + Threadfin + *arr stack + AIOStreams sidecar.**

Hive scoring matrix top 3:
1. Custom Next.js + Jellyfin API + Threadfin + *arr -- **64/70**
2. Channels DVR + Jellyfin hybrid -- 55/70
3. Stremio + AIOStreams + Real-Debrid + Jellyfin -- 54/70

Why #1 wins: only stack that scores 9+ on EPG aggregation, plugin ecosystem, custom UI, self-hosted, and torrent integration simultaneously. Custom shell is the only path to "beats Google TV" -- Channels DVR has the best EPG but its UI is locked. Stremio is the best movie discovery surface but weak on live-TV.

**Drops (locked):**
- **ErsatzTV** -- repo archived Feb 2026, dead.
- **Plex** -- cloud auth violates "private" requirement.
- **Torrentio** -- cooked per Apr 2026 dev statement. Use **AIOStreams / MediaFusion / Comet** as Stremio addon backends.
- **Cookie-sync of Netflix/Prime/Disney+ login** -- DRM (Widevine L1) makes this impossible AND ToS-violating. Justine would block it.

**Honest answer on "auto-sync my login":**
- Self-hosted services (Jellyfin / Plex / Sonarr / Radarr / Stremio) -> YES, full QR pair, one scan signs them all in.
- DRM streamers (Netflix / Prime / Disney+ / HBO Max) -> NO. We **deeplink-launch the native app** on Android TV / FireTV / Apple TV. User signs in once per device per service via the streamer's own pairing flow. MDtv surfaces the catalog and routes the click. We do not impersonate.

## 4. Service Topology

```
[TV / Tablet / Phone -- Cloudflare Pages CDN]
    |
    v public HTTPS
[tv.everlightventures.io] -- Cloudflare Pages, Next.js shell
    |                                                    |
    |  pair flow only                                    | media + library + EPG
    v                                                    v
[pair.everlightventures.io -- Oracle E5]      [Tailscale mesh, MagicDNS only]
[FastAPI Pair Broker, public, behind Cloudflare WAF]  [PC: 100.x.x.x]
    |
    v device JWT
[All subsequent traffic goes Tailscale-only]
                                                        |
                                                        v
                            +---------------------------+--------------------------+
                            |              |              |              |              |
                       [Jellyfin]   [Threadfin]    [Sonarr/Radarr]  [qBit+gluetun]   [FastAPI Gateway]
                       :8096        :34400         :8989/:7878      :8080            :8800
                                                                                      |
                            EPG Aggregator | Catalog Service | Deeplink Resolver | Supabase RLS
```

Two-plane design:
- **Public plane (Oracle + Cloudflare)**: pair broker only. Tiny FastAPI service, OAuth 2.0 Device Authorization Grant (RFC 8628). Issues device JWT after phone confirms. **No media, no creds, no library.**
- **Private plane (PC, Tailscale)**: Jellyfin, *arr stack, qBittorrent (VPN-killswitched), Threadfin, FastAPI gateway. All media traffic, library proxying, credential vault. Reachable only over Tailscale.

## 5. Service Inventory

| Service | Host | Port | Purpose | Restart |
|---|---|---|---|---|
| Next.js shell ("MDtv") | Cloudflare Pages | 443 | TV UI, edge-cached | Cloudflare-managed |
| Pair Broker (FastAPI) | Oracle E5 | 8443 | QR pair + device JWT | systemd always |
| FastAPI Gateway | PC (Tailscale) | 8800 | Single typed API, aggregator | systemd always |
| EPG Aggregator | PC | 8801 | Threadfin + custom Pluto/Tubi/Plex-FAST/Samsung-TV+ scrapers | systemd always |
| Catalog Service | PC | 8802 | TMDB + JustWatch fusion + Redis cache | systemd always |
| Jellyfin | PC | 8096 | Library, transcode (VAAPI), DVR engine | systemd always |
| Threadfin | PC | 34400 | M3U/EPG proxy -> Jellyfin Live TV | systemd always + watchdog |
| Prowlarr | PC | 9696 | Indexer aggregation | systemd always |
| Sonarr | PC | 8989 | TV acquisition | systemd always |
| Radarr | PC | 7878 | Movie acquisition | systemd always |
| Bazarr | PC | 6767 | Subtitle automation | systemd always |
| qBittorrent (gluetun-bound) | PC | 8080 | Download client, kill-switched | systemd always |
| Redis | PC | 6379 | EPG/JustWatch/session cache | systemd always |
| PostgreSQL | PC | 5432 | Jellyfin meta + EPG materialized grid | systemd always |
| AIOStreams sidecar | PC | 11470 | Stremio addon for movie discovery | systemd always |

## 6. Authentication (the QR pair flow, locked)

OAuth 2.0 Device Authorization Grant (RFC 8628) -- same shape as Plex Quick Connect / GitHub device flow.

1. **TV boots, hits pair broker** -> POST `pair.everlightventures.io/device/code` with `device_id` + Ed25519 pubkey. Broker returns `device_code`, 8-char `user_code` (e.g. `GLD-X4Q`), 600s TTL.
2. **TV renders QR** = `https://pair.everlightventures.io/?u=GLD-X4Q`. (Public URL, because the phone may be on cellular when scanning.)
3. **Phone scans** -> opens PWA, already auth'd to Rich's Hive account via passkey.
4. **Phone shows confirm sheet**: "Pair Living Room TV?" with device fingerprint visible.
5. **Biometric confirm** -> phone signs `{user_code, device_id, ts}` with phone's device key -> POST `/device/approve`.
6. **TV polls** `/device/token` every 5s -> on approval, gets short-lived JWT (15min) + rotating refresh token (30d) bound to `device_id`.
7. **TV uses JWT** to fetch per-service tokens from `/v1/vault/credentials` -- Jellyfin API key, Sonarr/Radarr keys, IPTV creds. Gateway proxies; raw secrets never sit unencrypted at rest on the TV.

**Token residence:** refresh in TV's TPM/keystore (encrypted file w/ device key on x86). Per-service tokens are RAM-only, fetched on-demand, expire on app close.
**Credential vault:** Supabase table `media_credentials` with libsodium secretbox ciphertext. Master key derived from passkey via HKDF on phone, sent to gateway only at unlock, RAM-only. Supabase sees ciphertext, can't decrypt even if breached.
**Revocation:** any paired device can `devices.revoked_at = now()` for any other device. Refresh tokens for revoked device_id refuse to mint.

## 7. Frontend Architecture

**Repo:** `/AA_MY_DRIVE/06_DEVELOPMENT/mdtv/` (new)
**Stack:** Next.js 15 (app router) + React 19 + Tailwind v4 + Shadcn/UI + Norigin Spatial Navigation + Vidstack player.
**Theme:** import `everlightventures/src/styles/tokens.css` as single source of truth. Zero hex literals -- `grep '#D4A843'` returns nothing in this codebase.

**Routes:**
`/` (For You) -> `/guide` -> `/movies` -> `/shows` -> `/apps` -> `/library` -> `/search` -> `/title/[id]` -> `/watch/[id]` -> `/pair` -> `/settings`

**IA shelf order (locked, per UX synthesis):** **For You -> Live -> Movies -> Shows -> Library -> Apps -> Search.** "For You" leads because 70% of TV sessions are passive. Movies/Shows split (Google lumps them) because intent differs.

**12 reusable components:**
- `GuideGrid` -- viewport-virtualized 2D EPG canvas (`@tanstack/react-virtual`), owns scroll + focus.
- `ChannelRow` -- horizontal channel lane, lazy-mounts ProgramCells.
- `ProgramCell` -- one program, width = duration/30min, memoized on `(programId, isFocused, isLive)`.
- `SourceHeader` -- sticky source pill ("Pluto Lineup", "Tubi Lineup") + ambient gradient shift in time-bar (Pluto-teal -> Prime-blue -> Tubi-orange, 800ms fade).
- `SourceFilter` -- chip row to jump-scroll between source blocks.
- `HeroRail` -- full-bleed featured carousel, autoplays trailers muted (8s loop).
- `ContentCard` -- poster tile, 1.08x scale on focus, metadata bar on focus.
- `FocusableTile` -- generic focusable wrapper.
- `PlayerOverlay` -- top/bottom chrome over Vidstack, auto-hides at 4s idle.
- `QRPairCard` -- big QR + 6-char fallback, polls pair endpoint.
- `AppTile` -- Android app deeplink launcher (Netflix/Prime/Disney+ as native-app handoff).
- `WatchProgressBar` -- gold progress underline on Continue Watching cards.

**Live Guide UX (the "infinite DirecTV scroll"):** Sticky source pill morphs as the dominant source under the viewport changes (IntersectionObserver, debounced 200ms). Time-bar bg ambient-gradient-shifts to match the source. Channel numbers reset to 1 at each source boundary, separated by a 4px gold hairline divider with the source name embossed in 10px Inter caps. **No hard break, no modal, no clicks** -- just keep scrolling and the lineup changes.

**For You rail order (locked):** Hero (Cipher's #1 pick with confidence score) -> Continue Watching -> Live Now for You -> Because you finished [X] -> New in your Library -> Trending across the Hive.

**5 beat-Google-TV moves (locked):**
1. **Now-Playing audio visualizer** -- thin gold waveform, bottom 4px edge.
2. **"Name That Sound"** -- Shazam-style remote button, drops to Library notes.
3. **VIP Ad-Mute** -- Pluto/Tubi ad breaks auto-mute; overlay shows 30s Hive Mind market pulse (XLM price, broker leads, Slack pulse).
4. **Cipher Overlay** -- long-press any tile, agent floats in: "Cipher: 8.4. Plot mirrors *Heat*. Runtime fits your usual window."
5. **Instant-Restart** -- single button rewinds live or in-progress to t=0.

**3 perf traps to dodge:**
1. Don't render 1000 channels -- virtualize both axes, mount viewport +-2 rows / +-4 hours, ~120 live nodes max.
2. Memoize `ProgramCell` with custom equality on `(programId, isFocused, isLive)` only, not whole program object.
3. Don't animate scroll with Framer on 1000 cells -- native `scroll-behavior: smooth` + `transform: translate3d`. Focus scale uses `transform`, never `width` (no layout thrash).

**D-pad: Norigin Spatial Navigation.** React 19-native, declarative `useFocusable`, used by Sky/BBC iPlayer in production. Nests under our layout; `setFocus('GUIDE_GRID')` deep-links focus on route change.

**Player: Vidstack.** React 19 native, headless + composable (matches Shadcn philosophy), HLS/DASH/MP4, 200KB vs Shaka's 600KB, better TS story than JW. We don't need Widevine L1 on a private server.

## 8. Backend API Surface (FastAPI Gateway, Tailscale-only)

| Method | Path | Purpose |
|---|---|---|
| POST | /v1/auth/pair/start | TV requests pair code (proxies to Oracle pair broker) |
| POST | /v1/auth/pair/complete | Phone PKCE exchange, binds device |
| GET | /v1/library/items | Paginated library (Jellyfin proxy + enriched) |
| GET | /v1/library/items/{id} | Item detail + stream URL + subtitle tracks |
| GET | /v1/catalog/search?q= | TMDB search + JustWatch providers merged |
| GET | /v1/catalog/{tmdb_id}/watch | "Where to watch" + deeplink set per device |
| POST | /v1/deeplink/launch | Returns app deeplink URI for TV launcher |
| GET | /v1/epg/grid?from=&to= | Unified channel grid, paginated by hour |
| GET | /v1/epg/channel/{id}/now | Current + next program |
| POST | /v1/acquire/request | Send title to Sonarr/Radarr |
| GET | /v1/acquire/jobs | qBit + arr job state |
| POST | /v1/playback/heartbeat | Watch progress to Supabase |

## 9. Supabase Data Model (RLS on every table)

- `users` -- id, email, plan, created_at
- `devices` -- id, user_id, name, kind (tv/phone/tablet), tailscale_ip, ed25519_pubkey, last_seen, paired_at, revoked_at
- `library_items` -- id, jellyfin_id, tmdb_id, title, kind, path, fingerprint, cipher_score, indexed_at
- `epg_channels` -- id, source (pluto/tubi/plex_fast/samsung/iptv/dvr), source_channel_id, name, logo, category, sort_order
- `epg_programs` -- id, channel_id, start_utc, end_utc, title, description, tmdb_id (nullable)
- `watch_history` -- id, user_id, item_id, position_sec, duration_sec, completed_at
- `media_credentials` -- id, user_id, service_name, ciphertext (libsodium), nonce, created_at
- `torrent_jobs` -- id, user_id, source (sonarr/radarr), external_id, title, status, progress, hash
- `addons` -- id, user_id, kind (stremio/aiostreams), manifest_url, enabled, last_synced

RLS rule for everything: `user_id = auth.uid()` AND for sensitive tables `device_id IN (user_devices WHERE revoked_at IS NULL)`.

## 10. Deployment (PC docker-compose outline)

```
networks: media (bridge), tailscale (external)
volumes:  media -> /AA_MY_DRIVE/04_MEDIA_LIBRARY, configs -> /opt/mdtv/config

services:
  jellyfin:        # devices: /dev/dri (VAAPI), :8096
  threadfin:       # :34400, healthcheck: curl /api/v1.0/streams (5min watchdog)
  prowlarr:        # :9696
  sonarr:          # :8989, depends: prowlarr
  radarr:          # :7878, depends: prowlarr
  bazarr:          # :6767, depends: sonarr+radarr
  gluetun:         # WireGuard kill-switch wrapper for qbit
  qbittorrent:     # :8080+:6881, network_mode: service:gluetun (kill-switched)
  fastapi_gateway: # :8800
  epg_aggregator:  # :8801
  catalog_service: # :8802
  redis:           # :6379
  postgres:        # :5432

restart: unless-stopped on all
```

**Pair broker** lives on Oracle E5 as a separate systemd unit, NOT in this compose. Oracle-side has its own one-service compose + Cloudflare Tunnel.

**Auto-deploy:** `.github/workflows/deploy-mdtv.yml` -- on push to `main`, SSH to PC, `docker compose pull && up -d`. Same git-push doctrine as xlm_bot.

## 11. Hardware Transcoding

Ryzen 9 iGPU (RDNA2/Vega depending on chip) -> VAAPI on Mesa, `radeonsi` driver. Pass `/dev/dri/renderD128` into Jellyfin container.
- Concurrent estimate: 3-4x 1080p H.264 transcodes, 2x 4K HEVC -> 1080p tone-mapped. Direct-play unlimited.
- Cap concurrent transcodes at 4 in Jellyfin admin to protect RAM budget.
- **Upgrade path under $200 if it chokes:** Intel Arc A310 ($110-130), AV1 encode, 8+ concurrent 4K transcodes, low TDP, drop-in PCIe x4.

## 12. RAM Budget (10 GiB headroom on PC, ~7.5 GiB peak forecast)

| Service | Idle | Peak |
|---|---|---|
| Jellyfin | 400 MB | 2.5 GB transcoding |
| Sonarr | 250 MB | 500 MB |
| Radarr | 250 MB | 500 MB |
| Prowlarr | 150 MB | 250 MB |
| Bazarr | 200 MB | 400 MB |
| qBit + gluetun | 400 MB | 1.2 GB |
| Threadfin | 80 MB | 150 MB |
| FastAPI gateway + EPG agg + catalog | 300 MB | 600 MB |
| Redis + Postgres | 250 MB | 800 MB |
| Buffer/cache | -- | 2 GB |
| **Total peak** | ~2.3 GB | **~8.9 GB** |

Fits inside 10 GiB headroom with margin. Add Arc A310 only if Jellyfin sustained transcode > 85%.

## 13. Top 5 Risks + Mitigations

1. **EPG sources fragile / hostile to scraping** -> Redis cache aggressively (24h channel meta, 6h programs), per-source circuit breaker, never block grid render on a single source down. Mark `degraded`, not `down`.
2. **Torrent IP leak on residential connection** -> qBittorrent `network_mode: service:gluetun` enforces kill-switch. Daily cron from inside qbit container curls `ifconfig.me`; if it matches home IP, branded_slack alert + auto-stop torrents.
3. **Pair flow phishing target** -> 600s TTL pair codes, PKCE, signed approval (Ed25519), device fingerprint, rate-limit per IP, broker behind Cloudflare WAF.
4. **Threadfin silent death** -> systemd timer 5min watchdog: `curl /api/v1.0/streams` -> restart container on 3 consecutive failures. branded_slack alert.
5. **Tailscale leak / public exposure regression** -> weekly automated `nmap` from external VPS confirms zero public ports beyond pair broker. Jellyfin/Plex bind to Tailscale interface only, `iptables -A INPUT -i eth0 -p tcp --dport 8096 -j DROP`.

## 14. 14-Day Delivery Plan

| Phase | Days | Scope | Gate |
|---|---|---|---|
| **1 Foundation** | D1-3 | Supabase schemas + RLS, Jellyfin install on PC w/ VAAPI, library scan of `/AA_MY_DRIVE/04_MEDIA_LIBRARY/`, FastAPI gateway skeleton, OpenAPI contract published. | Schema review (Zara security + Henrik deploy). |
| **2 Auth + Library** | D4-6 | Pair broker on Oracle, QR flow end-to-end, `/v1/library` proxy through Jellyfin, watch_history wired. | Pen-test pair flow (Zara). |
| **3 Catalog + Deeplinks** | D7-9 | TMDB ingest, JustWatch lookup w/ Redis cache, deeplink resolver for top 8 apps (Netflix, Prime, Disney+, Hulu, Max, Apple TV+, YouTube TV, Paramount+), `/v1/catalog/*` live. | -- |
| **4 EPG + Acquire** | D10-12 | Threadfin + EPG aggregator workers (Pluto, Tubi, Plex FAST, Samsung TV+, free IPTV M3U), unified grid materialized hourly, Prowlarr+Sonarr+Radarr+qBit-via-gluetun deployed, `/v1/acquire/*`. | -- |
| **5 Shell v0.1 + Harden** | D13-14 | Next.js shell `/guide`, `/movies`, `/pair`, `/title/[id]`, `/watch/[id]` shipped to Cloudflare Pages, focus nav working, Vidstack player. Load test (500-channel grid). Monitoring (Prometheus + Grafana). | Living-room demo to Rich. |

**v0.2 backlog (post-shipping the v0.1):** Apps grid + Android companion (deeplink launcher), AIOStreams sidecar wired into movie discovery, Cipher Overlay (long-press recommendations), VIP Ad-Mute, Name That Sound, Instant-Restart, profiles + multi-user, mobile companion app for remote.

## 15. What Needs Rich's Go/No-Go

1. **Codename:** keep "MDtv" as the brand for the Next.js shell? Or rename to "Hive Media", "Lucrex TV", "Everlight Lounge"? **My pick: MDtv** -- it's already the name in your head, short, brandable.
2. **Domain:** `tv.everlightventures.io` for the shell, `pair.everlightventures.io` for the broker. Confirm or alternate.
3. **Phase 1 start date.** I have the spec; I need green-light to scaffold the repo at `/AA_MY_DRIVE/06_DEVELOPMENT/mdtv/`.
4. **Storage volume.** Is `/AA_MY_DRIVE/04_MEDIA_LIBRARY/` the final media root, or do we plan a NAS/Pi-disk migration in 60 days? Affects Jellyfin path strategy.
5. **Hardware transcoding.** Stay on Ryzen iGPU at start, or pre-buy Arc A310 to skip the upgrade interruption?
6. **DRM streamers reality.** Does Rich accept "deeplink + native-app SSO once per device" as the answer, or does he want me to revisit cookie-sync (Justine will block, but he can override)?

## 16. Phone Discovery Service (PDS) -- the "all my apps" piece

**Trigger:** Rich's clarification 2026-05-06 -- "all the media apps on my phone should be included (all my subscriptions)... my phone is on and connected so you should be able to see all my services, tools, channels."

**Reality:** Phone (richards-z-fold7, Tailscale 100.112.180.29) was offline at audit time (last seen 1d ago, ADB no devices). But App_List.docx already enumerates 200+ apps. We seed the catalog now, refresh from live ADB on next phone-online event.

**Seed file shipped:** `/AA_MY_DRIVE/06_DEVELOPMENT/mdtv/seed/phone_apps.json` -- structured catalog with category, Android package ID, deeplink scheme, public-API capability, OAuth strategy, EPG aggregability per app.

**Architecture:**

```
[Phone richards-z-fold7] -- ADB or Tailscale-Termux ssh
        |
        v daily cron + on-pair refresh
[Phone Discovery Service :8804] -- new FastAPI worker on PC
        |
   +----+--------+--------+--------+
   |             |        |        |
[Apps Detector] [OAuth Hub] [EPG Reconciler] [Subscription Confirmer]
                |
                v
         [Supabase: user_subscriptions, oauth_tokens, app_inventory]
                |
                v
        Surfaces in MDtv shell:
         - /apps grid (deeplink launchers)
         - /movies + /shows (catalog enriched with "where to watch" badges)
         - /music (Spotify + YouTube Music live data)
         - /library/books (Nook deeplink)
```

**Three modes of integration per app:**

1. **OAuth-federated (the gold tier)** -- Spotify, YouTube/YT Music, Trakt, TMDB, Plex. Real catalog data flows into MDtv. User clicks "Connect" once on TV, scans QR, phone runs OAuth on Rich's behalf, refresh token lands in libsodium-encrypted vault. From then on, MDtv shows actual playlists / subscriptions / watched history.
2. **Catalog-cross-mapped (the silver tier)** -- Netflix, Prime, Peacock, Paramount+, Crunchyroll. No public API, DRM blocked. We use TMDB watch providers + JustWatch + Reelgood data to know "title X is on Netflix" -- when user picks the title, we deeplink-launch Netflix on the TV. This is the realistic "all my subscriptions in one guide" -- catalog is unified, playback handoffs are native.
3. **EPG-aggregable (the bronze tier)** -- Tubi, Pluto, Plex FAST, Samsung TV+, Roku Channel. Threadfin scrapes M3U + XMLTV, fed straight into Jellyfin Live TV. These channels appear inline in the unified Live Guide alongside any IPTV M3U Rich drops in.

**Trakt is the secret weapon.** It's the only system that gives a cross-DRM watch graph. If Rich connects Trakt and enables scrobbling on Netflix / Prime / Peacock (Trakt has unofficial scrobblers per service), MDtv suddenly has a single timeline of "what Rich watched, where" -- regardless of which streamer hosts it. Continue Watching becomes truly universal.

**Subscription confirmation flow (one-time, in MDtv settings):**

When PDS finishes its first ADB scan, it lists the detected media apps in `/settings/subscriptions`. Rich confirms which ones he actually pays for ("Netflix yes, Prime yes, Peacock yes, Paramount+ yes, Spotify Premium yes"). Anything in the seed JSON's `missing_subscriptions_to_ask_rich` block (Disney+, Hulu, Max, Apple TV+) gets a "Do you subscribe to this? Not detected on phone" prompt. PDS writes confirmed subscriptions to Supabase `user_subscriptions` and the catalog filter respects them ("only show me titles I can actually watch tonight without paying extra").

**ADB enumeration command (when phone online):**

```bash
adb -s 100.112.180.29:5555 shell pm list packages -f -3 -u | \
  awk -F: '{split($2,a,"="); print a[2]}' > /tmp/installed_packages.txt
```

Cross-references against `seed/phone_apps.json::android_packages_to_verify_via_adb`. Diff = (a) additions to surface in /apps, (b) removals to suppress.

**OAuth callbacks:**

The Oracle pair-broker gains 5 new endpoints (kept lightweight, no media plane access):
- `GET /oauth/spotify/callback`
- `GET /oauth/google/callback` (YouTube + YT Music in one scope)
- `GET /oauth/trakt/callback`
- `GET /oauth/tmdb/callback`
- `GET /oauth/plex/callback`

Each writes the refresh token into Supabase `media_credentials` (libsodium-encrypted) tied to user_id. PDS worker on PC reads tokens at API-call time, never persists access tokens at rest.

**14-day plan integration:** PDS slots into Phase 3 (Catalog + Deeplinks, D7-9) as a parallel track. Phase 3 becomes:
- D7: TMDB ingest + JustWatch lookup (existing scope)
- D8: PDS ADB-pull worker + seed reconciliation + /settings/subscriptions UI
- D9: OAuth hub for Spotify + YouTube + Trakt + Plex; deeplink resolver covers all confirmed apps

**Status:** Seed JSON shipped. Live ADB refresh waits for phone to come back online on Tailscale. Repo skeleton at `/AA_MY_DRIVE/06_DEVELOPMENT/mdtv/` created; awaiting Phase 1 green-light to scaffold full Next.js + FastAPI codebase.

---

## 17. Provenance (who contributed what)

- **Stack matrix + ErsatzTV/Torrentio kill-shots:** 55_competitive_intel
- **Backend architecture, API surface, data model, 14-day plan:** 67_backend_architect
- **File tree, 12 components, perf traps, Norigin/Vidstack picks, theme inheritance:** 62_frontend_architect
- **IA, infinite-source-scroll cues, For You rail order, 5 beat-GTV moves, failure copy:** 63_ui_ux_designer
- **OAuth 2.0 device-flow handshake, DRM honesty, libsodium vault, Tailscale-only topology:** 69_security_engineer
- **Service placement, hardware transcoding, RAM budget, docker-compose outline, watchdog ops:** 68_devops_engineer

Conflicts resolved:
- **Shell hosting:** Cloudflare Pages wins (Henrik) over PC-Tailscale (Sebastian) -- TVs roam, CDN beats VPN-only for static shell.
- **Pair URL public vs Tailscale:** Pair broker on Cloudflare-public Oracle (Henrik) wins over Tailscale-only (Zara) -- phone may scan from cellular. Constrained: pair broker has ZERO media/cred/library access.
- **ErsatzTV included or dropped:** Dropped (competitive intel evidence: archived Feb 2026).
- **Torrentio for Stremio addon:** Dropped, AIOStreams replaces (competitive intel evidence: April 2026 dev statement).

Best-of-both merges:
- Maren's "VIP Ad-Mute -> 30s Hive Mind market pulse" + Forge's Vidstack `onAdBreak` event hook + Sebastian's `/v1/playback/heartbeat` data path = single feature.
- Maren's "Cipher Overlay 8.4 score" + Sebastian's catalog endpoint with `cipher_score` column on `library_items` = same data path, surfaced two ways.

---

**End of canonical doc. Anything not in this file is conjecture.**
