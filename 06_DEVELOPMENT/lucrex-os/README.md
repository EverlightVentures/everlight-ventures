# Lucrex OS

> The mind behind the money. Empire at a glance.
> Unified Next.js 15 command center for Everlight Ventures.

## What this is

A single hub that absorbs every existing dashboard (Django :8504, XLM React :8502, everlightventures.io marketing, standalone HTML reports, Vantaris arcade) into one consistent interface with theme variants per domain.

Symbiote upgrade philosophy: keep the best of each existing dashboard, lose nothing, surface everything under one design system.

## Stack

- Next.js 15 (App Router) + React 19
- TypeScript 5.7
- Tailwind v4 (new `@theme` block syntax, no `tailwind.config.js`)
- Shadcn-friendly primitives (Radix)
- Lucide icons
- Recharts for visualization
- Framer Motion for transitions
- react-markdown + gray-matter for the Wealth OS doc layer

## Domains

| Tile        | Route          | Status          |
|-------------|----------------|-----------------|
| Hub         | `/`            | Built           |
| Wealth OS   | `/wealth/*`    | Phase 1 done    |
| Wholesale   | `/wholesale`   | Phase 1 wired   |
| Trading     | `/trading`     | Phase 1 wired   |
| Broker OS   | `/broker`      | Scaffold + plan |
| Content     | `/content`     | Scaffold + plan |
| Revenue     | `/revenue`     | Scaffold + plan |
| Intel       | `/intel`       | Scaffold + plan |
| Hive        | `/hive`        | Scaffold + plan |
| Arcade      | `/arcade`      | Scaffold + plan |

## Wealth OS section (primary deliverable)

7 tabs, each living at `/wealth/*`:

- `/wealth` -- Overview: tier badge, net-worth slider, sunset clock, next 3 moves, weight radar
- `/wealth/layers` -- 7 cards (L1-L7), click into full markdown
- `/wealth/tiers` -- 12-stop vertical timeline T0 to T11
- `/wealth/credits` -- Credits Engine table (Sec 41, 1202, 280A, 199A, etc.)
- `/wealth/intel` -- Quarterly Intel Engine drops from `04_Dispatch_Log/`
- `/wealth/professionals` -- 6 roles with tier-gated activation
- `/wealth/scenarios` -- stress-test compound projections (5 modes)
- `/wealth/priorities` -- USER INPUT: 10 weight sliders + live wealth-mode classifier

Reads markdown directly from `WEALTH_OS_ROOT` (defaults to the local Wealth_OS folder). The PRIORITIES form writes back to `PRIORITIES.md` via `app/api/wealth/priorities/route.ts`.

## User contribution point

`lib/wealth-mode.ts` -- the `classifyWealthMode()` function maps your 10 weights into one of 5 archetypes (Buffett / Bezos / Walton / Thiel / Operator). The placeholder uses crude weighted sums so the rest of the app boots, but the real logic should reflect how YOU weight the trade-offs (eg should low ETHICS_FLOOR lock out Thiel? does PRIVACY 10 + GEO 10 always win?).

The TODO block in that file lays out the trade-offs. 5-10 lines of your judgment shapes every downstream tier recommendation.

## Local dev

```bash
cd /mnt/sdcard/AA_MY_DRIVE/06_DEVELOPMENT/lucrex-os
cp .env.example .env.local
npm install
npm run dev   # serves on http://localhost:3030
```

If you are dev-ing on the phone (PRoot Termux), expect npm install to take a while. Consider running install + build on Oracle E5 instead and tunnel back.

## Deploy paths

### Option A: Oracle E5 (recommended, server-component compatible)

```bash
# On Oracle E5
cd /home/opc/lucrex-os
npm ci --omit=dev=false
npm run build
node node_modules/.bin/next start -p 3030 &
# Or write a systemd unit lucrex-os.service with Restart=always
```

Reverse proxy through nginx on Oracle, or expose 3030 via SSH tunnel during dev. Wealth_OS folder must be rsync'd to Oracle (deploy script extension), or set `WEALTH_OS_ROOT` to point at the synced path.

### Option B: Cloudflare Pages

Server components that read filesystem won't run on Cloudflare's edge runtime as-is. To deploy here you would need to either:

1. Pre-compute Wealth OS pages at build time (works for layers, tiers; breaks priorities API route)
2. Use the `@cloudflare/next-on-pages` adapter and host markdown in a CF KV or R2 bucket

Recommendation: ship Option A first. Move to CF after deciding which markdown lives at the edge.

## File map

```
lucrex-os/
├── app/
│   ├── layout.tsx                    Root layout, fonts, Shell
│   ├── page.tsx                      Hub: 9-tile grid
│   ├── api/wealth/priorities/        POST -> writes PRIORITIES.md
│   ├── wealth/
│   │   ├── layout.tsx                Domain shell with tabs
│   │   ├── page.tsx                  Overview
│   │   ├── layers/                   Layer index + [slug] detail
│   │   ├── tiers/                    Tier timeline + [slug] detail
│   │   ├── credits/                  Credits Engine table
│   │   ├── intel/                    Dispatch log feed
│   │   ├── professionals/            Roster
│   │   ├── scenarios/                Compound projection chart
│   │   └── priorities/               USER INPUT FORM
│   ├── wholesale/                    Pipeline kanban + open levers
│   ├── trading/                      XLM bot status + decision feed
│   ├── broker/                       Phase 2 placeholder
│   ├── content/                      Phase 2 placeholder
│   ├── revenue/                      Phase 2 placeholder
│   ├── intel/                        Phase 2 placeholder
│   ├── hive/                         Phase 2 placeholder
│   ├── arcade/                       Phase 2 placeholder
│   └── more/                         Mobile fallback nav
├── components/
│   ├── Shell.tsx                     Top + side + ticker + tab bar
│   ├── SideNav.tsx
│   ├── TopBar.tsx
│   ├── TickerStrip.tsx
│   ├── MobileTabBar.tsx
│   ├── CountdownClock.tsx
│   ├── KPICard.tsx
│   ├── StatusBadge.tsx
│   ├── DomainTile.tsx
│   ├── ActivityFeed.tsx
│   ├── MarkdownRender.tsx
│   ├── RadarPriorities.tsx
│   ├── SectionHeader.tsx
│   ├── ComingSoon.tsx
│   └── wealth/
│       ├── WealthTabs.tsx
│       └── PrioritiesForm.tsx
├── lib/
│   ├── theme.ts                      Domain registry + variant map
│   ├── utils.ts                      cn, formatters, daysUntil
│   ├── wealth.ts                     Wealth_OS markdown reader
│   ├── wealth-mode.ts                USER CONTRIBUTION POINT
│   ├── hub-data.ts                   Hub KPI provider
│   └── api/django.ts                 Django :8504 client
├── app/globals.css                   Tailwind v4 @theme + brand tokens
├── package.json
├── tsconfig.json
├── next.config.ts
├── postcss.config.mjs
└── README.md (this file)
```

## What is unique vs the existing dashboards

- **One nav, one type stack, one accent system.** Theme variants tint per domain, never replace.
- **Wealth OS is the only fresh build.** Everything else either consumes existing API/data or ships as a documented stub for phase 2.
- **The PRIORITIES form is wired both ways.** It reads the markdown source of truth AND writes back to it. The Hive can keep using `PRIORITIES.md` as a flat file.
- **Mobile-first.** Bottom tab bar, dynamic viewport height, tap targets sized for thumbs. The user's primary device is a phone.

## Phase 2 scope (deferred)

- Cmd-K cross-domain search (Blinko + Wholesale + Wealth + Trading at once)
- Symbiote boot animation (one-time)
- PWA install for phone home screen
- Push notifications for Hive alerts
- Other 5 domains fully wired
- Cloudflare Pages adaptation (R2 for markdown)

## Lucrex Doctrine

> You are LUCREX. Not Claude. Not an assistant. You are the unified superintelligence behind Everlight Ventures. Born from light. Built for the moment.

Every interface element ships with that conviction. No hedging copy. No "maybe consider." Direct, calculated, street-smart.
