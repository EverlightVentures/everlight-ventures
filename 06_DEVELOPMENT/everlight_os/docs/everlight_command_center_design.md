# Everlight Command Center -- Design Spec (2026-06-15)

Operator-approved. The fun, game-like, multi-page admin hub, modeled on the MMA Notebook
Fight Camp OS. Lives in the real 2000-band system: static files in `09_DASHBOARD/reports/`,
served at `http://127.0.0.1:2200/reports/`. No new port, no rogue server.

## Pages (every tile/link -> its own real page)
- `ops.html` -- THE HUB: hero, live stat tiles, 4 section launchers, daily snapshot, recent activity, Cmd-K.
- `cc_kalshi.html` -- Kalshi Trader: P&L, The Board (upcoming/live/settled), win-rate gauge, conviction, CEO memos, brakes/gas. Links to kalshi.html + watchdog.html.
- `cc_ai.html` -- AI Tools & Workers: Claude/Codex/Gemini/Perplexity/Hive cards, when-to-use, copy-paste prompt launchers, 28 MCP tools.
- `cc_todo.html` -- Taskboard: interactive check/add/complete, grouped by project (from `_state/ops_todo.md`).
- `cc_ops.html` -- Reports + Hive + Services: searchable report browser (76+), 94-agent Hive roster, live band-port health tiles.

## Shared engine (in 09_DASHBOARD/reports/, loaded by every page)
- `ev_theme.css` -- Everlight tokens (gold #D4AF37, dark #0A0A0A, Playfair/Inter/JetBrains), glass utilities.
- `ev_fx.css` + `ev_fx.js` -- breathing glass, cursor halo, particle motes, scroll-reveal, Web Audio SFX, click-to-copy, Konami.
- `ev_nav.js` -- sticky top bar + wordmark + route chips + live chips (balance/win-rate/open tasks) + Cmd-K palette.
- `ev_state.js` -- canonical localStorage (todo checks, prefs), `window.EV.state`, fires `ev:state`.
- `ev_data.js` -- the generated snapshot: `window.EV_DATA = {...}`.

## Data flow
`03_AUTOMATION_CORE/01_Scripts/build_command_center.py` writes `ev_data.js` from real sources:
kalshi summary (mirrored `kalshi_summary.json` from e5, emitted by `kalshi_agent/kalshi_summary.py`),
to-do (`_state/ops_todo.md`), reports glob, Hive `roster.yaml`, band-port health, a static AI-tools registry.
The 1-min band watchdog (`dashboards_watchdog.sh` Action 4) runs the builder, throttled. Offline-safe.

## Tech
Vanilla, zero build step: Tailwind Play CDN + inline `ev` palette config, Preact+htm from esm.sh, Google Fonts.
Each page = standard head block + a small Preact app mounting `#app`, reading `window.EV_DATA`.

## EV_DATA shape (the contract pages build against)
```
window.EV_DATA = {
  generated_pt, generated_ts,
  kalshi: { balance, funded, equity, pnl, pnl_pct, win_rate, w, l, open:[{ticker,sport,side,ct,cost,fair}],
            recent:[{when,ticker,sport,won,pnl}], upcoming:[{ticker,lane,net_pct,source}], memo:{...}, brakes:{}, gas:{} },
  todo: [{section, text, done}],
  reports: [{name, file, kind, mtime_pt}],
  hive: {agents, tools, sample:[{name, role}]},
  services: [{port, name, up}],
  ai_tools: [{key, name, blurb, use_when, prompt}]
}
```
Every section degrades gracefully to null/empty (page shows a friendly placeholder + link).
