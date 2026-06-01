# Hive TV - Master Roadmap

**Date:** 2026-05-31
**Owner:** Rich (operator)
**Status:** Vision locked. Phase 1 spec in progress.
**Runs on:** Rich's **AceMagician mini PC running Garuda Linux** (Arch-based, zen kernel - a gaming-focused distro). Runs Jellyfin, carried with him; tailnet 100.93.253.49, user `richgee`. OS confirmed 2026-05-31.
**Lives in (brain / source of truth):** `06_DEVELOPMENT/hive_tv/` in the workspace. Code is authored here and copied / deployed to the media machine. The workspace is the brain; the media machine is the appliance.

---

## The Vision

One unified "brain" sitting over every streaming service Rich pays for, plus the free ones,
so that instead of ten separate apps with ten separate logins, there is:

1. **One login experience** - log into everything once, log out of everything at once.
2. **One giant Live TV guide** - every live channel from every service (Hulu Live, Peacock,
   Prime, Pluto, Tubi, Roku, etc.) in a single grid. Pick a channel, the right app opens to it.
3. **One giant movie / show wall** - every title across every service, sorted by genre, with
   "stream on X / rent on Y" labels. Pick a title, the right app opens straight to it.

"One big Netflix" over all his subscriptions.

---

## Honest Reality Check (read before promising anything)

The reason no free app perfectly does this today is **data ownership**. Netflix / Hulu / Max do not
publish their catalogs or live-channel lineups as open data. The companies that hold that data
(Gracenote, JustWatch) license or sell it. So the winning architecture is **not** scraping each
service. It is:

- Riding the **free metadata layer** (TMDB for titles / genres, JustWatch for "which service has it").
- **Deep-linking** into the apps Rich already pays for (open the title / channel directly by URL).
- Using **auto-login** (Phase 1) so those deep links land on content, not a login wall.

This is exactly how Reelgood / JustWatch operate. It is the legal, sturdy path and it is all free.

### Cross-cutting constraints (apply to every phase)

- **DRM / playback:** Streaming video plays through **Widevine DRM**. Playwright's bundled
  Chromium does **not** ship Widevine. We must drive the **installed Google Chrome**
  (`channel="chrome"`) so video actually plays. Miss this and you get login working but a black
  video screen.
- **Bot detection:** Aggressive services (Netflix especially) can throw a CAPTCHA on login.
  Design rule: **pause and hand to the human for one tap**, never silently fail or retry-hammer
  (which gets accounts locked). Warm cookies make this rare.
- **ToS posture:** Auto-logging into your *own* paid accounts and deep-linking into them is
  ordinary personal use. We deliberately do **not** scrape service catalogs (that is the gray
  zone). We use public metadata aggregators instead.
- **Free-first:** Every component below is free / open-source. No paid services required.
- **Runs local:** Anything touching logged-in browser state must run on the media machine.
  Cookies and the browser profile have to be on the device Rich watches on.

---

## The Layers (build order)

### Phase 1 - Auto-Login (the foundation) [GREEN]
Status: **fully buildable, fully in our control.** Everything else depends on it.
Full design: `2026-05-31-hive-tv-phase1-autologin-design.md`.

A `hivetv` CLI that logs into every service in one saved browser profile, unlocked by a single
master password, with TOTP-generated 2FA codes (Gmail fallback for email-only codes). Commands:
`login`, `logout`, `status`. Once cookies are warm, services stay logged in for months. The
tool becomes the fallback for expired sessions, not a constant re-login.

### Phase 2 - Unified Live TV Guide [GREEN for free live] / [YELLOW for paid live]
- **Free live channels** (Pluto, Tubi, Roku, Plex, Samsung; thousands): **fully doable, free,
  and Jellyfin already supports it natively.** Use **Threadfin** (or xTeVe) to merge M3U channel
  lists + XMLTV program data into one feed; Jellyfin renders it as a real EPG. Click, it plays.
- **Paid-service live channels** (Hulu Live, Peacock live, Prime live): **the data wall.** No open
  feed of their live grids. Best available: Rich picks his favorite live channels once, and we
  deep-link each tile into that app's live channel. Real but manual to set up and somewhat fragile.

### Phase 3 - Unified Movie / Show Wall ("one big Netflix") [GREEN] / [YELLOW]
- Build a private Reelgood: **TMDB** (free API: titles + genres + artwork) + **JustWatch**
  (availability: stream / rent / buy per service), giving one browse UI sorted by genre, search
  across everything, click to deep-link into the right app to that exact title (logged in via Phase 1).
- **Honest limit:** this is a *metadata* catalog, not each service's personalized rows. For
  movies and shows the coverage is near-complete; it will not perfectly mirror Netflix's homepage.

### Phase 4 - Paid-Live Deep Links (stretch) [YELLOW]
Fold the paid services' live channels into the Phase 2 guide via manual channel-mapping +
deep links. Lowest priority, most fragile, gated on Phases 1-2 working.

### Phase 5 - Gaming + Desktop Layer (AceMagician, Linux) [MIXED]
Turn the AceMagician into a portable media + gaming + XR box, with a **Games** section in the
launcher alongside the streaming sections (tiles that open Steam / Lutris / RetroArch / chiaki-ng,
same "click and it opens" pattern). Honest flags, because hardware and anti-cheat are hard walls:

- **Steam + Proton (Windows games on Linux): GREEN for most single-player / indie / older titles.**
  Proton is Valve's Wine layer (what the Steam Deck runs); a large share of Windows games "just
  work." Add **Lutris** / **Heroic** for Epic / GOG / Battle.net, and **ProtonUp-Qt** for GE-Proton.
- **Call of Duty / modern AAA - the real no-cloud paths (Rich does NOT want cloud; aligning to that):**
  Verified current state (multi-source, incl. Activision's Dec 2025 RICOCHET post + ProtonDB +
  GamingOnLinux anti-cheat list): modern **Warzone still will not launch under Linux / Proton.**
  RICOCHET is a ring-0 Windows kernel driver that cannot load in Wine / Proton's user space, and
  bypass attempts risk a ban. That is Activision's driver, not a config we can out-tweak. But there
  ARE native, no-cloud ways to play CoD on this exact box:
  - **Dual-boot Windows (primary native path).** A Windows partition on the AceMagician runs Warzone
    natively with anti-cheat satisfied. Garuda for media + everything else; reboot to Windows for the
    anti-cheat games. The launcher gets a "Boot to Game Mode" tile. Cleanest native answer; the only
    open question is whether the GPU can drive it (need the model).
  - **Older CoD titles run on Garuda now** via Proton: CoD2, CoD4: Modern Warfare, Black Ops III,
    CoD4x, etc. If the goal is CoD *on Linux itself*, these are the ones that work today.
  - Cloud (GeForce NOW free tier) would run Warzone in a browser tab, but Rich does not want a cloud
    account - noted and parked, not the plan.
  - If Rich has a specific newer method / link he read, drop it and I will pressure-test it against
    his exact model rather than assume - EAC / BattlEye games got Proton support, but RICOCHET (CoD)
    has not as of the latest Dec 2025 update.
- **GPU is the deciding factor - need the exact AceMagician model.** Garuda (a gaming distro) on
  this box suggests it was set up for gaming, which often means a capable AMD APU (e.g. Ryzen 7840HS
  / Radeon 780M class can run Warzone at 1080p-low on Windows). An N100-class chip could not. The
  model decides whether dual-boot Warzone is smooth, playable, or not worth it.
- **Console games (PS4 CoD) on PC with keyboard + mouse:**
  - PS4 *emulation*: experimental, not viable for CoD. RED.
  - PS *Remote Play* from a real PS4 / PS5: `chiaki-ng` streams it to the PC with keyboard+mouse. YELLOW (needs the console).
  - Older consoles (SNES / PS1 / PS2 / GameCube / Wii, light Switch): RetroArch / EmuDeck. GREEN, ideal for this hardware.
- **Redragon 15-button mouse on Linux:** Redragon's official software is Windows-only, but
  **`input-remapper`** (open-source, Linux) remaps the extra buttons regardless of vendor. YELLOW
  (no vendor app, yes open-source remap).
- **Viture XR glasses (Rich's: Viture Pro XR and / or Viture Luma Pro) - GREEN on Linux, verified:**
  - Both models are **officially supported by XRLinuxDriver** (wheaney/XRLinuxDriver, with Viture
    collaboration). Plug-and-play over USB-C; head-tracking works on Linux. (Correction to an earlier
    too-pessimistic note: Viture's Linux support is solid and official, not hit-or-miss.)
  - Virtual big-screen / 3DoF desktop: add **Breezy Desktop** (companion to XRLinuxDriver) or the
    Steam Deck plugin. Real Linux setup, not a hack.
  - One remaining dependency: the AceMagician's USB-C port must output video (DisplayPort-alt mode).
    Cheap test: plug any USB-C -> HDMI adapter into that port; if a monitor lights up, the glasses
    get a picture. The software side (driver + virtual screen) is already solved for Viture on Linux.

Tooling (all free / open-source): Steam + Proton, Lutris, Heroic, ProtonUp-Qt / GE-Proton,
RetroArch / EmuDeck, chiaki-ng, input-remapper, MangoHud (perf overlay), XRLinuxDriver + Breezy
Desktop (Viture glasses). Garuda already ships much of the gaming base (Steam, Proton, gamemode).

---

## Tooling Summary (all free / open-source)

| Layer | Tool | Role |
|-------|------|------|
| Auto-login | Playwright (Python) + installed Google Chrome | Drive logins, persist cookies, Widevine playback |
| Auto-login | `cryptography` (Fernet) or `age` | Encrypt the credential vault at rest |
| Auto-login | `pyotp` | Generate TOTP 2FA codes offline |
| Auto-login | Gmail read-only token / IMAP | Fallback for email-only verification codes |
| Live guide | Threadfin / xTeVe | Merge M3U + XMLTV into one feed |
| Live guide | Jellyfin Live TV | Render the unified EPG, play channels |
| Movie wall | TMDB API (free) | Titles, genres, artwork, metadata |
| Movie wall | JustWatch data | Per-service availability + deep links |

---

## Non-Goals

- No scraping of service catalogs (use metadata aggregators instead).
- No re-hosting or re-streaming any content (deep-link into the official apps only).
- No storing of plaintext credentials anywhere, ever.
- No unattended login-hammering (warm cookies + human handoff on CAPTCHA).

## Open Questions (resolve during implementation)

- ~~OS of the media machine?~~ **Resolved 2026-05-31: AceMagician mini PC, Linux.**
- Which of Rich's paid services force an emailed code vs. support TOTP? (Determined empirically in Phase 1.)
- Does Jellyfin run on the same box as the browser, or separate? (Affects Phase 2 wiring.)
- **AceMagician exact specs (CPU / GPU / RAM)?** Determines which games are feasible (Phase 5).
- **Does Rich own a PS4 / PS5 console?** Decides Remote Play (yes) vs. emulation (not viable) for console CoD.
- **Which XR glasses, and does the AceMagician USB-C port do DisplayPort-alt-mode video out?** Make-or-break for the glasses.
- Which Linux distro exactly (CLAUDE.md says Arch)? Affects package manager + driver install paths.
