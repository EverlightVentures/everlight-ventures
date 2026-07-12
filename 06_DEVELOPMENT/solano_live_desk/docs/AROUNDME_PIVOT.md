# AroundMe: pivot from private console to national safety app

Repositioning of Solano Live Desk into "AroundMe", a mass-market personal-safety
and situational-awareness app for gig drivers, truckers, and travelers. Produced
2026-07-12 by a 5-lane Hive fan-out (competitive intel, legal/data counsel,
engineering, growth/exit, product/UX), cross-checked and synthesized.

Shareable brief (Everlight-branded HTML): published as a Claude artifact.

## Thesis
Every safety app and every gig platform answers "I am under attack, send help"
(reactive panic button, locked to one employer). Nobody answers "the area around
me is turning dangerous, which way do I move?" That proactive, environmental,
cross-platform lane is open. Our fused-feed map + shelter/evacuate decide engine
already lives there.

## Two moats (carry over unchanged)
1. 18 free public feeds fused into ONE view. Watch Duty = fire only, Waze = roads
   only, Citizen = crime only. Nobody fuses the full picture. Free-data moat a
   buyer cannot cheaply rebuild.
2. Closed-loop decide engine that routes the human out ("fire 1.2 mi NW, head the
   other way"). Pure, location-parameterized code. Zero rewrite to go national.

## Three hard truths (failures first)
1. We are READ-ONLY; competitors dispatch 911. Fix = one-tap SOS that shares
   location + dials 911 via existing dispatch API. Do NOT staff a 24/7 agent desk.
   Win on the awareness lane, not the panic button.
2. "What is this neighborhood about" is illegal as designed. Reputation-of-place
   scoring + the plate/person extraction built into the private tool = the exact
   FHA / redlining / defamation trap that burned Citizen. Fine for Rich's eyes
   only; CANNOT ship in a national paid app.
3. Safety apps churn by design (install after a scare, delete in 30 days). Growth
   comes from gig-driver communities + referral virality + one press moment, NOT
   paid installs.

## The legal reframe (pivotal)
Report WHAT IS HAPPENING near a point right now. Never rate WHAT KIND of place or
person it is.

SHIPS NATIONALLY:
- Live, time-boxed events near a point, auto-expiring on source TTL.
- Federal feeds that scale free to 50 states: NWS, USGS, NASA FIRMS, AirNow, GDACS.
- Shelter/evacuate advice WITH on-screen "advisory, not authoritative" disclaimer
  (currently only a code comment in decide.py) + link to the official order.
- One-tap SOS: share location + dial 911.
- Pre-arrival check ("active incident 400 ft from this stop").

CUT FROM THE PUBLIC APP:
- Any neighborhood reputation / per-area safety score.
- Plate/name/person extraction + code-name tracking from scanner (radio.py).
- Standalone "leave now" push with no route to an official order.
- Server-side capture/restream of Broadcastify audio at commercial scale (ToS;
  Catalog API is $2,500/mo). Live-listen embed only.
- Any IMPLIED national evac coverage we do not have. Gray out uncovered states.

## Competitive snapshot
- Citizen: ~$104M val, $19.99/mo Premium. Gap: 24/7 agent + real 911 dispatch.
- Life360: 95.8M MAU, $70-200/yr. Gap: the guardian graph (safety as a network).
- Watch Duty: 17M users, free/$25yr. Closest template, but fire/flood only.
- Waze: 150M+ MAU, free. Crowd hazard reports inside the driving app.
- DoorDash SafeDash / Uber toolkit / Lyft: reactive panic, ADT-tied, one-employer.
  White-space = cross-platform awareness layer none of them cover.

## Product reframe: verdict-first, not data-first
- Around Me radar: your dot centered, rings 0.5/1/3 mi, status pill Clear/Heads
  up/Act now. NO red on load ever; first message is relief ("clear zone").
- Proximity feed + pre-arrival safe-check (sub-3s verdict on next stop).
- Thumb-bar SOS (long-press) + share-live-location to a trusted contact.
- Hide behind Advanced/Pro: raw transcripts, scanner block-logs, correlation
  graph, lifecycle fields, sources/audit tab, time-scrubber, camera grids.
- Brand feel: calm authority, not siren. Tagline options: "Know what's around
  you." / "Aware, not afraid." / "Your area, in real time."

## Engineering: what ports vs what changes
Brain (PORTS UNCHANGED): threat.py, decide.py, correlate.py, alerts.py routing,
notify.py push pattern, feed-fusion event-dict shape.
Plumbing (SINGLE-TENANT, MUST INVERT):
- CA/Solano-hardwired feeds: chp_parser (CHP sa.xml), 511, Cal OES evac ArcGIS;
  feeds.py COUNTY_FEEDS holds only Solano 06095.
- store.py: one global per-day SQLite; no user dimension. -> Postgres/PostGIS.
- GPS beacon singleton file -> per-user location rows.
- Auth: single SLD_ACCESS_TOKEN magic-link -> real accounts (Supabase Auth).
- alert_worker.py reads ONE location, fires ONE ntfy -> per-incident spatial
  fan-out (query users within radius, push FCM/APNs).

### Phased roadmap
- Phase 0 (DAYS): rename to AroundMe; Capacitor wrap of the existing Next static
  export into an installable app; load-fast (cached first paint + lazy map +
  self-host/subset fonts, drop Playfair to system stack); surface the advisory
  disclaimer in UI; strip legal-risk features from the public build. Single-region
  test build.
- Phase 1 (WEEKS): accounts, per-user location, FCM/APNs replacing single ntfy,
  PostGIS replacing per-day SQLite, SOS + share-live-location + trusted contact.
- Phase 2 (WEEKS-MONTHS): per-state feed adapters on federal backbone, sharded
  ingest writing a shared event lake, geohash-tiled cached reads, spatial fan-out
  alerting.
- Phase 3 (MONTHS): national coverage breadth, App Store hardening + review, load
  testing, first B2B pilot / insurance LOI.

Native path is Capacitor wrap (days to a WebView build), NOT a RN/Flutter rebuild
(months, unjustified). Gotchas: background location (Capacitor Background
Geolocation + iOS Always permission), iOS push (swap web ntfy for FCM/APNs),
App Store safety-app review scrutiny.

## Money + exit
- B2C freemium: FREE = life-safety alerts + panic + share-location + check-on-me
  timer. PAID $2.99-4.99/mo = pro-driver bundle (unlimited contacts, route risk,
  background beacon, area history). NOT $0.99 (signals disposable). Blended paid
  CAC must stay under ~$6-9 or the math never closes given churn.
- B2B (the real prize): do NOT sell them an app; license the real-time risk DATA
  layer. Owner = Trust & Safety / Driver Experience; budget = Insurance/Risk.
  First deal = paid pilot + signed LOI. Trucking + fleet insurance is the cleaner
  money (pays to lower loss ratios; B2B2C shortest path to revenue).
- $500k exit: realistic FLOOR = acqui-hire for data + team. One gig or insurance
  LOI moves it to $1M-3M because you stop selling an app and start selling a moat.
  The exit hinges on the partnership signature, not on downloads.

## Feature additions (operator request 2026-07-12)

### Life360 parity features worth adding
Map to our Phase 1-2 accounts + per-user location work; these are what makes a
consumer safety app sticky and what Life360 monetizes:
- Crash Detection -> auto-SOS. Phone accelerometer detects a hard-deceleration
  crash and auto-fires SOS + shares location even if the driver is unconscious.
  Life360's flagship paid feature; buildable via Capacitor Motion / DeviceMotion.
  Highest value for gig DRIVERS specifically. (Phase 1-2)
- Circle: a small trusted group who see each other live during a shift. Our
  share-live-location, made multi-person. (Phase 1)
- Place Alerts: geofenced arrive/leave push to the Circle ("notify my wife when I
  leave this delivery zone / get home"). (Phase 1-2)
- Location-history breadcrumb: last-known trail if the phone dies. Safety-critical
  for a missing driver. (Phase 1-2)
- Safe-driving score / driving reports: Life360 sells this + ties to insurance.
  Direct feed into the trucking-insurance B2B angle. (Phase 2+)

### Dispersed Egress: coordinated multi-route evacuation routing
The operator's vision: do not just observe traffic and reroute one driver; ACTIVELY
spread evacuees across multiple parallel + back roads so nobody is stuck in one
line. This is the difference between USER-optimal routing (Waze/Google give each
driver their own fastest route, so everyone piles onto the same artery and it
gridlocks, e.g. the 2018 Camp Fire one-road jam) and SYSTEM-optimal routing
(minimize total evacuation time across everyone). Transportation engineers call
this Dynamic Traffic Assignment. NOBODY ships it to consumers. Real moat + the
piece that makes AroundMe interesting to logistics / insurance / emergency mgmt.

BUILDABLE NOW on the existing stack (single-user "smart back-road escape"):
- We already run OSRM (routing.py) + Overpass (OSM). Compute K alternative routes
  from the user to the nearest safe destination (OSRM alternatives).
- Rank by REAL free-flow time, not distance: length / OSM maxspeed, PLUS a time
  penalty per highway=traffic_signals node and per stop sign (the operator's exact
  ask: speed limits, lights, stop signs as time metrics).
- Drop any route crossing an incident-blocked edge (our own crash/closure/fire
  feeds mark those roads impassable).
- Prefer LESS-popular roads (lower road-class / lower-centrality edges) to steer
  off the obvious jammed artery.
- Output: "Skip Main St (crash at 3rd, everyone's on it). Take Parallel Ave, 90s
  longer, clear." (Phase 1-2, current stack)

FULL coordinated version (needs the multi-user data plane, Phase 2-3):
- Live congestion input, free, bootstrapped from: (a) our incident feed blocking
  roads, (b) Caltrans PeMS freeway sensor speeds (FREE in CA), (c) our OWN users'
  GPS beacons as a crowd speed layer once we have density (exactly how Waze
  bootstrapped from zero data).
- Server-side assignment: when many users flee the same zone, assign DIFFERENT
  users DIFFERENT routes to equalize load. Capacity-aware min-cost-flow /
  successive-averages traffic assignment across the K routes, using lane count x
  road class as capacity. THIS is "dispatch routes to manage traffic, not just
  observe": active load-balancing, multiple lanes/routes, congestion dispersed.
- Legal posture: advisory routing (same disclaimer as the decide engine). We
  advise; we do not control signals or claim traffic authority. Same posture Waze
  operates under.

HONEST CONSTRAINT: the hard free input is real-time congestion at national scale.
We do NOT license Google/Waze traffic (not free / not redistributable). We
bootstrap from incidents + PeMS + our own beacons, so it is a "gets better as we
get users" feature. The full coordinated version is gated on the Phase 2
multi-user backend; the single-user smart-egress ships on the current stack.

### The insurance hook (usage-based insurance / telematics)
The safe-driving score is not a vanity feature. It is the B2B revenue engine and
the reason a churny consumer app becomes an acquirable data business. Comps: Root,
Progressive Snapshot, Allstate Drivewise (auto UBI); Nirvana, HDVI, Samsara for
TRUCKING/fleet (they pay real money per seat/mile to lower loss ratios). They buy
a validated driving-risk signal.

We are already one step in: the crash-detection accelerometer shipped 2026-07-12
is the SAME sensor feed a driving score reads. Sub-crash spikes are the score.

Signals (all free, on-device): hard-braking + harsh-acceleration events (accel
magnitude in the 3-6 m/s2 band, below the crash threshold), harsh cornering
(lateral g), speeding vs the road's OSM maxspeed (we already pull maxspeed for
Dispersed Egress), miles driven, and night-driving share. Roll into a weekly 0-100
score card.

Cheapest next primitive: extend CrashGuard's existing motion listener to COUNT
those sub-crash events + track distance from the GPS beacon, and render a weekly
score card. That card is the artifact an insurer LOI gets written against. The full
UBI product (per-user history, a calibrated model, the actuarial partnership) is
Phase 2-3 on the multi-user backend.

Consent + privacy gate (HARD): telematics is sensitive data. Opt-in only, scored
on-device, never sold or shared without explicit consent, clear deletion path.
Same posture as the location-consent record already required for AroundMe.

## Shipped 2026-07-12 (this session)
- Rename to AroundMe + iOS fullscreen add-to-home install meta. LIVE.
- Legal reframe gated behind NEXT_PUBLIC_AROUNDME_MODE=public (lib/mode.ts):
  public build drops the risk-score banner, plate/person entity chips, and the
  whole Intel tab. Advisory disclaimer surfaced on every evacuate/shelter card. LIVE.
- Dispersed Egress smart-escape router: sld/escape.py + /api/escape, 9 unit tests
  green, live-verified end to end. Ranks OSRM alternatives by real free-flow time
  (OSM speed limits + a penalty per traffic light and stop sign), drops
  incident-blocked routes, picks a destination AWAY from the hazard. Frontend:
  multi-route map draw (recommended bright, alternates dashed, blocked red) + dest
  flag + a "WAYS OUT" panel. Tap an EVACUATE card to get it. LIVE.
- Crash detection (CrashGuard.tsx): accelerometer watch (~3g), cancelable 12s
  countdown, auto-fires SOS. Manual SOS button. sld /api/sos fires a max-priority
  ntfy push (breaks Do Not Disturb) with a maps link + a Call 911 fallback.
  Foreground-only in a browser (native app gets the background sensor). LIVE.

## Recommended next move: greenlight Phase 0
1. Rename + Capacitor wrap into an installable app.
2. Load fast (cached first paint, lazy map, self-hosted fonts).
3. Legal reframe (strip reputation scoring + person extraction from public build;
   surface advisory disclaimer in UI).
4. One demo build in hand to show a partner and gather first user feedback.

Provenance: competitive = Cipher desk; legal/data = Priya Bhattacharya (paired
Mani Calder, Mona Castile, Lupe Salazar); engineering = Everlight Architect;
growth/exit = SaaS Growth lead; product/UX = UX Design. Synthesis = Lucrex.
