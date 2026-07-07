# Proactive Audit -- what Rich is missing (data + tech stack)

Rich asked me to use my knowledge to find gaps he is not aware of, then build them.
This is that audit. Prioritized. Free sources only unless noted.

## THE ONE THING THAT MATTERS MOST (called out first)

**Offline resilience.** A survival OS that dies when the network dies is useless in
the exact moment it is needed. In a real disaster (fire, quake, grid-down) cell towers
saturate or fail. Today the whole dashboard needs live internet + live GPS. Fixes:
1. **Make it a PWA** (installable app, service-worker cache) so the last-known map +
   incidents + safe points survive going offline, and it installs on the phone like a
   real app with native push.
2. **Self-host offline vector map tiles** (Protomaps PMTiles of California on e5, or
   bundled) so the map still draws with no internet.
3. **Cache the last good state** of every layer locally so a signal drop shows the last
   picture, not a blank screen.
4. **Space-weather awareness** (NOAA SWPC, free) because solar storms degrade the GPS
   this whole system leans on. Knowing GPS is unreliable is itself survival info.
This is the single biggest blind spot. Everything else is additive; this is structural.

## DATA LAYERS he has not asked for but would want (free)

| Layer | Why it matters for him | Free source |
|---|---|---|
| **511 traffic events / road closures** | Blocked/closed roads = the core of evac routing + "avoid" (he drives all day) | 511 `traffic/events` (we HAVE the token) -- BUILT this turn |
| **River / flood gauges** | He is next to the Sacramento-San Joaquin Delta; flood + levee risk is real | USGS `waterservices.usgs.gov` (free, no key) |
| **NOAA space weather** | Solar storms disrupt GPS/comms this OS depends on | `services.swpc.noaa.gov/products/*.json` (free) |
| **Power outages** | Grid-down is a top survival signal; PG&E territory | PG&E outage JSON / poweroutage.us (scrape-limited) |
| **Marine / AIS vessels** | Carquinez Strait + SF Bay traffic; tanker/industrial incidents near him | aisstream.io (free key) |
| **Air quality / smoke** | Wildfire smoke health for family; pairs with FIRMS | PurpleAir (free) or AirNow (free key) |
| **Radiation baseline** | Partial fill of the CBRN gap he wanted | Safecast API (free) |
| **Crime history heatmap** | Pattern-of-place: which areas/times are risky on his routes | SpotCrime / CrimeMapping (historical, free-ish) |
| **Amber / Silver / civil alerts** | Family safety, abductions, evacuations | Already via NWS civil-alert relay; add state feeds |
| **GDELT GEO + themes** | Deeper OSINT: protests, unrest, hazards mapped by theme | GDELT GEO 2.0 (free, no key) -- news list BUILT this turn |

## INTELLIGENCE / CORRELATION he has not considered

- **Anomaly detection:** a sudden spike of incidents in one area = something big unfolding,
  alert before any single call is EXTREME.
- **Pattern-of-life for HIS routes:** learn which corridors/times are historically risky
  and warn him proactively on the way to a delivery.
- **Cross-source "story" fusion (Phase 3):** police + EMS + fire + news about one event
  into a single timeline. This is also the gunshot-inference workaround.
- **Predict-ahead heading wedge:** preload the picture in the direction he is driving, not
  just around him (the "bubble" bot's active/preload/heading design).

## TECH-STACK upgrades he has not considered

1. **WebSocket push** instead of polling -> instant alerts, less battery, smoother.
2. **PWA + service worker** -> installable, offline, native push (see offline resilience).
3. **Self-hosted offline map tiles (Protomaps)** -> map works with no signal.
4. **Vite + React pro console on e5** (already the Phase 3 plan) for the intricate PSIM UI.
5. **History store for playback** -> partitioned SQLite (already daily) extended to store
   position snapshots so he can scrub minute-by-minute (he asked for this).
6. **Auth in front of the dashboard** -> only he + his agents, per his private-by-default law.
7. **Redundant source fallbacks** -> every layer already degrades gracefully; formalize a
   health panel so he sees which feeds are live.

## What I BUILT out of this audit right now
- **511 traffic events / road closures** as map incidents (free, token we already have).
- **GDELT local news** panel (the OSINT news-outlet layer).
Everything else above is queued; the offline-resilience PWA + WebSocket + history playback
fold naturally into Phase 3 (the pro console).
