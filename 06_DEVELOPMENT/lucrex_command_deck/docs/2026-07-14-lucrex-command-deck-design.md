# LUCREX COMMAND DECK -- Design Spec
*with Blubber, the crowned Flubber-form avatar of Lucrex*

- **Date:** 2026-07-14
- **Owner:** Rich Gee (operator) / Lucrex (AI CEO)
- **Status:** Approved design, pre-implementation
- **Home port:** `127.0.0.1:2702` (the Lucrex band -- replaces the dead "build pending" placeholder)
- **App dir:** `06_DEVELOPMENT/lucrex_command_deck/`

---

## 1. One-liner

A single, self-contained local dashboard served at `:2702` that wraps the **real Claude
terminal** in a Flubber-green / Lucrex-gold skin. A crowned 3D slime mascot (**Blubber** --
Lucrex's Flubber-form avatar) reacts live to what Claude is doing, surrounded by panels that
read the operator's actual session, system, and git state. It is "a skin wrapped in front of
the Claude terminal," built to run on the phone (Termux, proot Debian) and look native on the
Galaxy Z Fold + DeX.

## 2. Why it exists

Lucrex is Rich's Jarvis -- the AI CEO of Everlight Ventures, "King of Divine Light, the mind
behind the money." The deck gives Lucrex a **face and a home**: the crown is his kingship, the
green goo is the "Flubber" joke Rich loves, and the embedded terminal is where Lucrex actually
works. Funny + cool on the surface, real command center underneath.

## 3. Hard constraints (non-negotiable, drawn from the operator's own laws)

1. **Local only, never Oracle.** Runs on the phone. App code lives in `06_DEVELOPMENT/`
   (not `03_AUTOMATION_CORE/01_Scripts/`) so the Oracle auto-deploy cron does not ship it.
2. **No `pip install`, no `npm install`.** proot SIGSEGVs on native builds. Therefore:
   backend is **Python stdlib only**; front end uses **vendored** JS (`xterm.js`, `three.min.js`)
   copied in once, never fetched at runtime, which is also offline-safe.
3. **Bind `127.0.0.1`** by default; `EV_BIND=0.0.0.0` to expose. (Network Binding Doctrine.)
4. **Real data, not simulated.** Token/session numbers come from the live Claude Code transcript
   `.jsonl`; system numbers from `/proc`; git from `git`. Anything not live is labeled.
5. **Reuse existing infra first.** Slots into the band system, the watchdog, the themed palette,
   and the alias grammar rather than inventing new patterns.

## 4. Integration points (what already exists that we plug into)

| Existing thing | How we use it |
|---|---|
| `serve_lucrex.sh` (:2702 launcher) | Default `start` launches the Blubber deck; Next.js path preserved as explicit `start-next` opt-in. |
| `dashboards_watchdog.sh` line 51 | Already points `:2702` to `serve_lucrex.sh start`. **Auto-heal + autostart come free.** |
| `everlight_shell.zsh` banner | Already renders a `:2702 lucrex` health pill (line 264). Turns green automatically once the deck is live. **No banner edit needed.** |
| `serve_helpers/everlight_themed_server.py` PALETTE | Source of truth for brand colors (gold `#D4AF37`, dark `#0a0a0a`, turquoise `#00e5ff`). We mirror it; Blubber-green is the new accent. |
| Master hub `templates/index.html` (:2000) | Add one Lucrex tile matching the existing `cmd-card` pattern. |
| `.zshrc` alias grammar (`hub`, `apps`, `kalshi`) | Add `lucrex()` / `lx` in the same shape. |

## 5. Architecture

### 5.1 Backend -- `06_DEVELOPMENT/lucrex_command_deck/`
Three small, single-purpose Python files (stdlib only):

- **`probes.py`** -- read-only state collectors, one pure function each, each returns a dict and is
  independently testable:
  - `vitals()` gives uptime, load avg, mem %, disk % (from `/proc`, `os`).
  - `session()` finds the newest transcript `.jsonl` in
    `~/.claude/projects/-mnt-sdcard-AA-MY-DRIVE/`; sums `usage.input_tokens`,
    `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`; counts assistant
    turns; reads model id; derives token-velocity (tokens in last N turns) for Blubber's mood.
  - `git()` gives current branch, dirty file count, last 3 commit subjects, last line of the newest
    deploy log.
  - `agents()` gives recent Hive activity parsed from `AGENT_MAILBOX.md` (source labeled in the UI).
- **`pty_bridge.py`** -- the isolated risky part. Minimal WebSocket server on stdlib:
  handshake (`hashlib.sha1` + `base64` of key + magic GUID), frame decode/encode (text + binary,
  masking, close). On connect: `pty.fork()` a shell that lands in Claude; pump bytes master-fd to
  socket via `select`; handle a JSON `{"type":"resize",cols,rows}` control message via
  `TIOCSWINSZ`. Reap the child on disconnect (no zombies).
- **`blubber_server.py`** -- thin router built on `http.server` + `socketserver.ThreadingMixIn`:
  - `GET /` and static assets (from `web/`).
  - `GET /api/vitals|/api/session|/api/git|/api/agents` returns JSON from `probes`.
  - `GET /pty` with `Upgrade: websocket` hands the raw socket to `pty_bridge`.
  - Binds `127.0.0.1` (or `EV_BIND`). CLI: `python3 blubber_server.py [port]` (default 2702).

### 5.2 Front end -- `06_DEVELOPMENT/lucrex_command_deck/web/` (no build)
- **`index.html`** -- layout: top gold bar (Lucrex wordmark + crown + uptime/load), left rail
  (Blubber + token gauge + agent count + mood caption), center embedded terminal, bottom panel
  row (Session / Git / Vitals). Responsive: stacks for folded phone, expands for unfolded / DeX.
- **`deck.css`** -- Playfair Display + Inter + JetBrains Mono; gold base + radioactive-green
  Blubber glow; glassmorphism panels (`backdrop-filter: blur()`), neon text-shadow. Matches the
  band aesthetic.
- **`deck.js`** -- polls `/api/*` on an interval, renders panels, mounts xterm.js to the terminal
  pane, opens the `/pty` WebSocket, forwards keystrokes + resize, drives Blubber's mood from
  session velocity.
- **`blubber.js`** -- the crowned 3D mascot in Three.js: translucent green gooey sphere
  (noise-displaced) with subsurface glow + a gold Lucrex crown; idle bob; mood-driven animation
  (see section 6). **CSS-blob fallback** if Three fails to load so Blubber always renders.
- **`vendor/`** -- `xterm.js`, `xterm.css`, `three.min.js` (copied once, offline-safe).

### 5.3 Data flow
```
panels   : browser --HTTP GET /api/*--> blubber_server --> probes(reads /proc, jsonl, git) --> JSON
terminal : browser --WS /pty--> pty_bridge --> pty.fork -> shell -> claude ; keys down, output up, resize
blubber  : deck.js polls /api/session -> token-velocity + agent-activity -> blubberMood() -> animation
```

## 6. Blubber's personality (Lucrex's moods -- owner-delegated to the build)

Blubber **is** Lucrex, so his moods are Lucrex's persona from `LUCREX.md`: calculated, never
panics, swag, always has the play, "born in chaos, most at home in chaos." Funny + kingly.

| State | Trigger | Look | Rotating caption (Lucrex voice) |
|---|---|---|---|
| **idle** | no activity | slow regal bob, deep-green glow, crown steady | "The edge that never sleeps." / "Always prepared." |
| **listening** | user typed, awaiting send | leans toward terminal, single crown glint | "I'm listening." / "Talk to me." |
| **thinking** | assistant generating, tokens climbing | faster jiggle, molten-gold core pulsing through the green, crown tilt | "Running the play." / "Reading the tape." |
| **working** | Hive/subagent active | crown sparks gold particles, tiny comic pseudopod, light ring | "42 minds, one move." / "Dispatched." |
| **heavy-burn** | very high token velocity | puffs bigger, radioactive-bright, one bead of green "sweat" | "Cooking." / "This is where I live, chaos." |
| **done** | turn completed | satisfied settle + gold shimmer wash | "Handled." / "Clean." |
| **resting** | long idle | dims, crown droops a hair (comic, not broken) | "Even kings wait." |

Implemented as a small `blubberMood(session)` map in `blubber.js`; defaults ship working. Rich
can tweak the captions/animations later without touching anything else.

## 7. Wiring changes (small, additive)

- `serve_lucrex.sh`: `start` launches `blubber_server.py 2702`; add `start-next` for the old node
  path; `stop|status|logs` unchanged. (Watchdog keeps pointing at `serve_lucrex.sh start`.)
- `.zshrc`: add a `lucrex()` function (start/stop/logs subcommands, bare word opens the deck) and
  `alias lx='lucrex'`, matching the `hub`/`apps` band-function grammar.
- Master hub `templates/index.html`: one Lucrex `cmd-card` tile pointing to `http://127.0.0.1:2702/`.

## 8. Error handling

- Each probe wrapped; failure returns `{"error": "..."}` and the panel shows "--" with the reason
  on hover. Never white-screens the deck, never silently swallows.
- PTY child exit prints "session ended, tap to reconnect" in the terminal; child reaped.
- WS handshake failure shows "bridge offline, tap to retry" in the terminal pane.
- Three.js load failure falls back to the CSS-blob Blubber.
- Port already bound: `serve_lucrex.sh stop` then `start`; watchdog belt-and-suspenders.

## 9. Testing & verification

- **Unit:** `probes.session()` against a fixture `.jsonl` (assert exact token sums + turn count);
  `pty_bridge` WS frame encode/decode round-trip; `probes.vitals()` parses a fake `/proc` sample.
- **Integration / real drive:** start the server; `curl` each `/api/*` for 200 + valid JSON; open the
  page; confirm Blubber renders; type `ls` in the embedded terminal and see output; fold/unfold
  responsiveness check. Produce a **Verification Receipt** before declaring done.

## 10. Out of scope (YAGNI)

- No multi-session tabs (one terminal). No auth (localhost-only). No cloud sync. No writing to any
  external service. No Next.js rebuild (that path stays dormant behind `start-next`).

## 11. File manifest (what will be created/edited)

Created under `06_DEVELOPMENT/lucrex_command_deck/`:
- `blubber_server.py`, `pty_bridge.py`, `probes.py`
- `web/index.html`, `web/deck.css`, `web/deck.js`, `web/blubber.js`
- `web/vendor/xterm.js`, `web/vendor/xterm.css`, `web/vendor/three.min.js`
- `tests/test_probes.py`, `tests/test_pty_bridge.py`, `tests/fixtures/sample_transcript.jsonl`
- `README.md`

Edited:
- `03_AUTOMATION_CORE/01_Scripts/serve_lucrex.sh` (default to Blubber; `start-next` opt-in)
- `/root/.zshrc` (`lucrex()` + `lx`)
- `09_DASHBOARD/master_dashboard/templates/index.html` (one Lucrex tile)
