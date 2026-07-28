# LUCREX OS -- The Engine (Phase 1 Design Spec)

- **Status:** Locked design, ready for implementation planning
- **Date:** 2026-06-15 (PT)
- **Owner:** Rich (operator) / Lucrex (build)
- **This spec covers:** Phase 1 only -- the Engine. Phases 2 (auth/profiles/channels) and 3 (Slack-kill comms) are designed-for here but built later.

---

## 0. Decisions locked (operator-approved)

| Decision | Choice |
|---|---|
| v1 scope | **Full big-bang rebuild** of all dashboards through the new engine |
| Style blend | **Per-dashboard vibe dial** -- `boardroom` (crisp) to `arcade` (game-feel) |
| Access tech | QR codes + auto-built aliases + PWA/home-screen. **NFC cut.** |
| Portability | **Build portable now** -- `LUCREX_OS_ROOT`, one `bootstrap.sh`, USB-extractable |
| Hosting | **Local for Rich, e5-mother for the team** (same system, config flip) |
| Auth timing | **Design now, build Phase 2** |
| OS home | **One brain, two renderers** -- `registry.yaml` feeds both the buildless Python static "city" AND the Next.js Command Center shell |
| Comms (Phase 3) | **Adopt Mattermost**, do not hand-roll chat |

---

## 1. Vision

LUCREX OS is a **self-hosted personal + small-team operating system** that replaces Slack and removes the Google dependency. It lives on Rich's phone (instant, local-first), snaps into a full desktop under **Samsung DeX**, and the *same system* deploys to **e5-mother** so trusted teammates can log in from anywhere. It is a **lightweight version of a heavy workstation**: own files, own rails, no SaaS seat fees.

Three phases:
- **Phase 1 -- The Engine (this spec):** the registry brain + one theme + a generator + the access layer. Local-first, buildless on the phone, beautiful, the full city rebuilt.
- **Phase 2 -- The Doors:** Supabase Auth + profiles + authority levels + per-dashboard access grants, published via Cloudflare Access (email OTP, no Google).
- **Phase 3 -- The Slack-Kill:** adopt + brand **Mattermost** on e5-mother for channels/threads/feed/notifications.

---

## 2. Current-state reality (verified against disk)

The system already works but has **no single brain**. The same band/dashboard list is hand-copied across ~6 files (`everlight_shell.zsh` banner, `dashboards_watchdog.sh`, `build_master_hub.py`, `build_command_center.py`, `.zshrc` functions, `PORT_MAP.md`). Adding one dashboard = hand-editing 4-6 files. This is why a "rogue 8503 server" drifted in.

Two half-built foundations exist:
- **Python 2000-band static stack** -- `http.server` + `09_DASHBOARD/reports/` + `build_*.py` generators. Buildless, phone-native. ~173 generated HTML files, each inlining its own copy of the gold CSS (the orphaned `ev_theme.css`/`ev_fx.css` are unused).
- **Next.js Command Center** -- `06_DEVELOPMENT/lucrex-os/` (the live `:2702`), with its own registries (`lib/external-tools.ts`, `lib/hub-data.ts`, `lib/theme.ts`). Real `next build` (asset-fingerprinted), needs node, so it builds on e5, not the phone.

A dormant registry precursor exists at `03_AUTOMATION_CORE/01_Scripts/portal/registry.yaml` + `portal_server.py` (`:8800`). It will be absorbed and retired.

**Security reality (must-fix, baked in now):** real lead PII (names, addresses, phones, a `.gov` email) sits in `09_DASHBOARD/reports/` -- the folder that gets *served* -- and that folder is routinely shipped to Cloudflare Pages. **Pre-rendering gated data to a public CDN is a live authorization hole**, not a hypothetical.

**Infra truth:** the phone has **no `crond`** -- cron entries silently never run. Self-healing must be a singleton daemon loop, never a crontab entry.

---

## 3. Architecture -- The Four Ones

### 3.1 The Registry (the brain) -- `lucrex_os/registry.yaml`

One YAML file is the single source of truth. Everything else is **generated** from it.

**Bands** (defined once):
```yaml
bands:
  - port: 2000   ; name: hub      ; range: "2000"      ; default_vibe: boardroom
  - port: 2100   ; name: markets  ; range: "2100-2199" ; default_vibe: boardroom
  - port: 2200   ; name: reports  ; range: "2200-2299" ; default_vibe: boardroom
  - port: 2300   ; name: intel    ; range: "2300-2399" ; default_vibe: boardroom
  - port: 2400   ; name: apps     ; range: "2400-2499" ; default_vibe: arcade
  - port: 2500   ; name: health   ; range: "2500-2599" ; default_vibe: arcade
  - port: 2700   ; name: memory   ; range: "2700-2799" ; default_vibe: boardroom
```

**Dashboard entry schema:**
```yaml
dashboards:
  - id: kalshi                      # slug, unique
    title: "Kalshi Edge Engine"
    band: 2200
    sub_route: "/reports/kalshi.html"
    renderer: static                # static | next
    source: { type: file, path: ... }   # file | sqlite | supabase | blinko | cmd
    layout: kpi                     # kpi | grid | list | table | detail | today | feed
    vibe: boardroom                 # boardroom | arcade  (defaults to band default)
    access: tailnet                 # public | tailnet | gated
    hero_metric: "all_time_pnl"     # optional: the one number that leads
    refresh_seconds: 90             # optional: tiered freshness
    health_path: "/"                # for the watchdog
    icon: "(emoji)"
    description: "Sports edge engine + timeline"
    mirror_source: "kalshi_dashboard.html"   # optional: e5-mirrored, edit source not output
```

**External tools / services** carry a `license` note (default `internal-safe`; only tools earmarked for Onyx POS / Hive Mind SaaS get a `resellable: yes/no` tag, enforced at SaaS-packaging time, not by a scanner).

**What the registry absorbs:** the dormant `portal/registry.yaml` (salvage its 15-category taxonomy as data), and the Next app's `external-tools.ts` / `hub-data.ts` become **generated** from it (codegen) so they stop being independent registries. `portal_server.py` and the `:8800` surface are retired.

### 3.2 The Theme (one design system on a dial)

- **One linked stylesheet pair:** `lucrex_os/theme/lucrex.css` (tokens + components) + `lucrex.fx.css` (the arcade living layer). Generated dashboards **link** them, so no more 173 inline copies. (The orphaned `ev_theme.css`/`ev_fx.css` are merged in and retired.)
- **Canonical gold = `#D4AF37`** (brand doctrine). The MMA `#c9a84c` retires into it. Tokens are CSS custom properties + a small Python dict the generator reads, **not** a DTCG/Style-Dictionary pipeline (the gold value has never changed in git history; that machinery would centralize a thing that never moves). The inline-hex cleanup is a ~1-hour refactor to point existing inline colors at the tokens.
- **Vibe = a `<body data-vibe>` switch, not cross-repo token governance.** `boardroom` = clean grid, subtle hover-lift, crisp tables, gold as a *sparing accent* (never a status color); `arcade` = adds the FX layer. We do **not** build a formal base+delta token contract spanning the three separate codebases (OS reports / vantaris site / AK game) that never co-render.
- **FX hygiene:** keep static glass/borders and breathing where intended; **delete the infinite ambient loops** (cursor-halo on every mousemove, drifting-grid, rising-mote loops) from `ev_fx.css` -- continuous paint/thermal cost on a phone-GPU driving DeX. Gate all motion behind `@media (prefers-reduced-motion: reduce)` (already present in `ev_fx.css`; copy into vantaris/AK). Add a `document.hidden` guard to the game's `requestAnimationFrame` loop.
- **Data-surface readability (applied opportunistically, not big-bang):** when editing a data-dense board, lift the canvas off pure black (~`#141414`), one card surface (~`#1E1E1E`), desaturate pos/neg series ~20%, add a secondary text tier (~`#A8A8A8`). The one load-bearing rule: **gold is an accent, never a status color.**

### 3.3 The Generator (data in to live surface out) -- `lucrex_os/builder/`

- `build.py` dispatches on the registry entry's `layout` **type via an extensible registry** (so new layouts are additive, no rework tax). v1 layout vocabulary: `kpi`, `grid`, `list`, `table` (read-only), `detail`, `feed`. `today` ships as a concrete composed page, not an enum value. `kanban` deferred to Phase 2.
- For `renderer: static` -> emits branded HTML that **links the shared theme** + a `data.json` the page polls for live updates (buildless, runs on the phone).
- For `renderer: next` -> **codegens** the Next app's TS data files (`external-tools.ts`, `hub-data.ts`) from the same registry; the Next build runs on e5.
- **Data adapters** (pluggable): `file` (json/csv/md), `sqlite`, `supabase`, `blinko`, `cmd` (shell output).
- **KPI contract:** schema requires `value`; `delta` + `baseline_label` are optional, but the renderer auto-stamps a visible "no baseline" chip when absent (so every number is either contextualized or explicitly flagged). Arrow + color + text label together (colorblind-safe).
- **Stale-data honesty badge (cheap, high-value):** every `data.json` carries `generated_at`. Client JS compares to now: within window -> green "live HH:MM PT"; beyond ~2x window -> amber/red "STALE as of HH:MM PT"; fetch fail -> red "DATA UNAVAILABLE -- last good HH:MM PT". Applied to the live decision surfaces (Kalshi, XLM); kills the current always-green "LIVE" dot that lies when the daemon dies.

### 3.4 The Access Layer (one propagate command) -- `lucrex_os/sync.py`

`sync.py` reads the registry and **regenerates** every downstream surface between `# LUCREX-OS:GENERATED` markers:
1. `everlight_shell.zsh` DASHBOARDS block + health-probe curls
2. `dashboards_watchdog.sh` SERVICES array
3. Master hub `index.html` tiles
4. `.zshrc` band functions / aliases (**no more hand-editing to add a band**)
5. QR PNG per dashboard + on-screen QR (no printed/physical QR proliferation; **no NFC**)
6. PWA `manifest.json` (real name "LUCREX OS", maskable + any 192/512 icons, `theme/background #0A0A0A`, `display: standalone`) + a minimal **network-first / versioned** service worker for the installable hub (never cache-first; avoids stale-deploy bugs)
7. Next app TS registries (codegen)
8. Cmd-K command index -- **extends the existing `ev_nav.js` palette** (already ships), fed by the registry; not rebuilt

**Generator safety rails (the three that make big-bang safe):**
- **Fail-closed validation** (stdlib, no new deps): required keys present, hex tokens match `^#[0-9a-fA-F]{6}$`, ports are unique ints, `access`/`layout`/`vibe` in their enums, ids unique. **Zero files written unless the whole registry passes.**
- **`DO-NOT-EDIT` provenance banner** on every generated file (the single highest-ROI line; stops a hand-edit getting silently regenerated away).
- **`sync.py --dry-run`** prints a diff of what would change before any write; **`sync.py --check`** is a read-only drift audit the daemon can run.
- **Mirror-awareness:** entries with `mirror_source` (e.g. `kalshi.html` re-mirrored from e5 every ~5 min) are written to their **source**, never the clobbered output.

*(Explicitly NOT built in the gate: APCA contrast linter, a "no-FX-on-ops" blanket ban -- it would contradict the operator-approved FX command-center hub -- and a checksum drift-audit wired into the daemon. These are team-scale/CI concerns, deferred.)*

---

## 4. One brain, two renderers

```
                         lucrex_os/registry.yaml   <- THE BRAIN (edit here only)
                                   |
            +----------------------+------------------------+
            v                                               v
   (A) PYTHON STATIC CITY                          (B) NEXT.JS SHELL
   builder/build.py -> branded HTML + data.json    codegen -> lib/*.ts
   buildless, runs ON THE PHONE                    next build runs ON e5
   the many read-mostly dashboards                 interactive workstation:
   (markets, reports, intel, health...)            Today view, write-back, auth (P2)
            |                                               |
            +----------------------+------------------------+
                                   v
                 sync.py -> banner . watchdog . hub . aliases . QR . PWA
```

One source of truth; the static path keeps Rich's instant local-first feel on the phone, the Next path gives the interactive shell. Neither can drift from the other because both derive from the same registry.

---

## 5. Workstation layer (not a viewer)

The current generator would emit read-only HTML, structurally a *report*. To read as a *workstation*:
- **Today home** (default landing on the Next shell): a self-hosted calendar + today-filtered task list composed from existing primitives. Read-only in Phase 1; this is the surface that lets Rich stop opening Google Calendar / a Slack home. A persistent nav rail stays (today-as-home, not today-instead-of-nav).
- **One write-back path** (Phase 2): toggle a task status in-page via RLS-gated `supabase-js`, on a dedicated authed route physically separated from the anonymous read surfaces. The RLS policy is the deliverable; the UI is the easy part. Expand to more mutations only after the first survives real use.
- **Task engine:** extend the **Supabase tables / existing Django taskboard** already owned. **Do not** stand up Vikunja or hand-roll a third CRUD/recurrence engine. Recurrence via `python-dateutil` RRULE; a read-only `.ics` feed (no Google) via the `icalendar` lib. Read-write CalDAV explicitly deferred until a proven two-way-sync need. **Gate the whole task build on a named pain point**: if markdown + Blinko already suffices, build only the read views.
- **Quick-capture:** a phone-native entry point (Termux `cap "..."` alias + Android share-sheet target) writing raw text to a Supabase `inbox` table. No NLP on the hot path; parse dates at triage with an off-the-shelf lib.

---

## 6. Security & network (baked in from line one)

- **HARD RULE:** never pre-render access-gated/PII data to a public CDN URL. A static `data.json` on a public `pages.dev` has zero access control; a login screen over it is theater.
- **Default internal dashboards to the tailnet** (Tailscale ACLs = network-layer auth, no RLS surface to misconfigure). Live Supabase-under-RLS is reserved for dashboards that must reach **non-tailnet/external** users (paying SaaS / consulting / Onyx clients seeing their own rows).
- **Phase 2 perimeter:** Cloudflare Access (email one-time-PIN) in front of published dashboards: near-$0 zero-trust, hides origin IP, **no-Google identity gate**. Complements Supabase Auth (CF Access = perimeter; Supabase = in-app profiles/authority).
- **Supabase key hygiene:** publishable key in the browser bundle, scoped secret key for the e5 daemon/edge fns; **never** ship a service-role key to a static bundle. Wrap policies in `(select auth.uid())`, index policy-read columns, run the Security Advisor before each Phase-2/3 ship.

---

## 7. Portability & resilience

- Everything keys off `LUCREX_OS_ROOT` (default = workspace); **no hardcoded `/mnt/sdcard/...`** in the engine.
- `lucrex_os/bootstrap.sh` stands the whole city up on any machine (phone, e5, a fresh laptop); this is the same switch that gives "local for Rich, e5 for the team."
- `lucrex_os/daemon.sh` = a **singleton `while true` loop** (NOT cron -- phone `crond` is dead): health-probe + self-heal each port, throttled regen, `sync.py --check` drift audit. Replaces the (silently-dead) watchdog cron.
- **Sync boundary:** the Next app (`06_DEVELOPMENT/lucrex-os/`) is git-tracked, so git/GitHub is its conflict-aware sync; keep it off Syncthing. The only fix is one `--exclude '06_DEVELOPMENT/lucrex-os/'` line in the rsync path. The portable `lucrex_os/` engine folder rides the existing untracked-data Syncthing channel.

---

## 8. Big-bang rebuild plan (operator's pick)

1. **Inventory** all ~173 dashboards -> classify keep / merge / retire; assign each a `band`, `vibe`, `access`, `layout` in the registry.
2. **Build the engine** (registry + theme + generator + sync) with the three safety rails.
3. **`sync.py --dry-run`** -> review the full diff.
4. **One regeneration pass** rebuilds every dashboard to link the shared theme + carry provenance banners. Because it's generated-from-source, it's fast and reversible.
5. **Regenerate the stale mind map**: `WORKSPACE_MANIFEST.md` port map (still shows 8502/8503) is regenerated from the registry; the hub's data-city view becomes the always-current mind map.

---

## 9. Explicitly CUT / DEFERRED (the lean line)

| Item | Disposition |
|---|---|
| NFC payloads | **Cut** (QR + PWA cover handoff; Android NFC handler broken on 16) |
| Hand-rolled Slack/chat | **Cut** -> adopt **Mattermost** in Phase 3 |
| DTCG / Style-Dictionary token pipeline | **Cut** -> ~1-hr inline-hex cleanup to existing tokens |
| Service-worker "freeze fix" | **Dropped** -- bug doesn't exist (Next auto-fingerprints) |
| Syncthing re-plumbing of the Next app | **Cut** -> one `--exclude` line |
| Cross-repo vibe base+delta token governance | **Cut** -- codebases never co-render |
| APCA build-gate / no-FX-on-ops gate / checksum drift-audit | **Deferred** to team-scale/CI |
| `kanban` layout, drag-to-timeblock | **Deferred** to Phase 2 (use status-grouped `list` first) |
| Vikunja / new task service | **Cut** -> extend owned Supabase / Django taskboard |
| CRDT / sync engines (PowerSync/Yjs/Automerge) | **Cut** -- read-mostly; file-mirror + Supabase suffices |
| Window Controls Overlay | **Cut** -- desktop-Chromium only, invisible on phone/DeX |

---

## 10. File layout

```
09_DASHBOARD/lucrex_os/
  registry.yaml              # THE BRAIN
  theme/
    lucrex.css               # tokens + components (one CSS truth)
    lucrex.fx.css            # arcade living layer (reduced-motion gated)
    fonts.css                # Playfair / Inter / JetBrains Mono / DM Sans
  builder/
    build.py                 # generator (extensible layout dispatch)
    layouts.py               # layout-type renderers
    adapters/                # file . sqlite . supabase . blinko . cmd
  sync.py                    # registry -> banner . watchdog . hub . aliases . QR . PWA . Next TS
  access/
    qr/                      # generated QR pngs
    manifest.json            # PWA manifest (generated)
    sw.js                    # minimal network-first SW (generated)
  hub/index.html             # the data-city home (generated)
  daemon.sh                  # singleton self-heal loop (NOT cron)
  bootstrap.sh               # portable stand-up
  docs/                      # this spec + generated MINDMAP.md
  README.md                  # how it works + how to add a dashboard
```
*Rationale for one self-contained folder (gently bends the "scripts to 03_AUTOMATION_CORE" rule): portability -- the engine must copy to a USB stick whole, per the locked portability decision.*

---

## 11. Acceptance criteria (Phase 1 done = )

1. `registry.yaml` is the only place a dashboard/band is defined; the 6 previously-hand-edited files are generated between markers.
2. `sync.py` regenerates all surfaces; `--dry-run` shows a diff; a malformed registry writes **zero** files.
3. All dashboards link `lucrex.css` (no inline CSS copies); brand change = edit one file + `sync`.
4. Adding a dashboard = ~8 lines in `registry.yaml` + `sync.py` (no other file touched).
5. QR per dashboard, auto-built aliases, and an installable PWA (real icons) all work; **no NFC**.
6. The honesty badge shows STALE/UNAVAILABLE correctly on the live boards.
7. `bootstrap.sh` stands the city up from `LUCREX_OS_ROOT` on a clean machine; `daemon.sh` self-heals (no cron).
8. No gated/PII data is pre-rendered to any public CDN path.
9. The mind map / manifest port map regenerates from the registry (no stale 8502/8503).

---

## 12. Open questions / risks

- **Task engine gate:** confirm a concrete recurring/scheduled-task pain before building task CRUD (else ship read-only views over existing data).
- **Next app build cadence on e5:** define how/when the Next shell rebuilds when the registry changes (daemon-triggered build on e5).
- **Inventory triage:** the keep/merge/retire pass on ~173 files needs a quick operator skim of the retire list before the big-bang run.
