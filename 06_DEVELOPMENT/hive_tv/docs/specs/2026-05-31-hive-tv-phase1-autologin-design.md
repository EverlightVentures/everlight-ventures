# Hive TV - Phase 1: Auto-Login - Design Spec

**Date:** 2026-05-31
**Owner:** Rich (operator)
**Parent:** `2026-05-31-hive-tv-roadmap.md`
**Status:** Design for review.

---

## Goal

A small command-line tool, `hivetv`, that logs Rich into every streaming service in **one saved
browser profile**, unlocked by a **single master password**, generating 2FA codes locally where
possible and pulling emailed codes from Gmail where not. After the first run, cookies stay warm
and services remain logged in for months; the tool is the fallback when a session expires.

### Success criteria

- `hivetv login` opens the saved Chrome profile, logs into each configured service that is not
  already logged in, and ends with every service showing a logged-in state. Video plays (Widevine).
- `hivetv logout` clears every session at once.
- `hivetv status` reports which services are currently logged in.
- No plaintext credential ever touches disk. The vault is encrypted at rest.
- A CAPTCHA pauses for a human tap and then continues, rather than failing or locking the account.

### Non-goals (Phase 1)

- No unified guide, no movie wall (Phases 2-3).
- No headless / unattended scheduled runs at launch (run it when you want; cookies do the rest).
- No mobile app. This is the media machine's local tool.

---

## Architecture

Six small units, each with one job and a clear boundary.

```
            +------------------+
   master   |   hivetv (CLI)   |   commands: login | logout | status
   password |  orchestrator    |
            +---------+--------+
                      |
        +-------------+--------------+--------------------+
        |             |              |                    |
        v             v              v                    v
  +-----------+ +-----------+ +--------------+   +------------------+
  |  Vault    | | Recipes   | | 2FA Resolver |   |  Browser Driver  |
  | (crypto)  | | (config)  | | TOTP + Gmail |   | Playwright+Chrome|
  +-----------+ +-----------+ +--------------+   +------------------+
                                                          |
                                                          v
                                                 +------------------+
                                                 |  Saved Profile   |
                                                 | (cookies = state)|
                                                 +------------------+
```

### 1. CLI / orchestrator (`hivetv`)
- Subcommands: `login`, `logout`, `status` (optionally `login <service>` to target one).
- On `login`: prompt once for the master password, unlock the vault, open the saved Chrome
  profile, then for each enabled service: if `status` says logged out, run its recipe.
- What it depends on: all five other units. It owns no login logic itself; it sequences them.

### 2. Credential vault (`vault.py`)
- One encrypted file (e.g. `~/.hivetv/vault.enc`), unlocked by the master password.
- Library: `cryptography` Fernet, key derived from the master password via a KDF (scrypt/PBKDF2).
- Holds per-service: `email`, `password`, optional `totp_secret`, optional `email_code_sender`.
- API: `unlock(master_password) -> creds dict`; `add/update(service, fields)`; never returns to disk
  in plaintext. The master password is never stored anywhere.
- This is exactly Rich's "env file" idea, but encrypted: one file the script pulls, locked by one password.

### 3. Service recipes (`recipes/*.yaml`)
- One small config per service. No code per service; the driver reads the recipe.
- Fields: `login_url`, `selectors` (email box, password box, submit, "logged-in" marker),
  `flow` (single-page vs. email-then-password two-step), `twofa` (`totp` | `email` | `none`),
  `logged_in_check` (URL or element that proves success), optional `logout_url`.
- Living in plain config means a site redesign is a 2-minute selector edit, not a code change.

### 4. 2FA resolver (`twofa.py`)
- `totp`: generate the 6-digit code locally with `pyotp` from the stored secret. Offline, instant, reliable.
- `email`: fetch the latest code from Gmail (read-only token or IMAP), regex it out, return it.
  Bounded wait (e.g. up to 60s) for the email to arrive; time out cleanly if it does not.
- Boundary: returns a code string; knows nothing about browsers.

### 5. Browser driver (`driver.py`)
- Playwright (Python), **`channel="chrome"`** (installed Google Chrome, has Widevine for playback).
- **Persistent context** via `launch_persistent_context(user_data_dir=~/.hivetv/profile)`. This is
  the single source of session truth: cookies live here, so logins survive between runs.
- Executes a recipe: navigate, fill from vault, submit, request 2FA code from the resolver if asked,
  verify the logged-in marker. Human-like pacing to avoid tripping bot detection.
- On CAPTCHA / unexpected challenge: surface it in the visible window and **pause for a human tap**,
  then resume. Never loop-retry a failed login.

### 6. Saved profile (state, not code)
- The Chrome `user_data_dir`. Backing it up = portability ("carry it everywhere"). Deleting it = full logout.

---

## Data flow: one `login` run

1. `hivetv login` prompts for the master password (once).
2. Vault unlocks, returns creds for enabled services.
3. Driver opens the saved Chrome profile (headed, so Rich can watch / tap a CAPTCHA if needed).
4. For each enabled service:
   a. Check the logged-in marker. If already in, skip (the common case once warm).
   b. Else: navigate to `login_url`, fill email + password from the vault, submit.
   c. If the recipe says `twofa: totp` or `email`, ask the resolver for the code, enter it.
   d. If a CAPTCHA appears, pause and wait for the human tap, then continue.
   e. Verify the logged-in marker. Record pass / fail.
5. Print a summary: which services are now logged in, which need attention.

---

## Service list (Phase 1)

**Premium (vault holds credentials + TOTP):**
Netflix, Amazon Prime Video, Hulu, Max (HBO), Peacock, Apple TV+, Disney+, Paramount+, Starz.

**Free (mostly zero-login; the job is just to open them in the same profile so they remember the device):**
Tubi, Pluto TV, The Roku Channel, Amazon Freevee, Crackle, Xumo.

Recipes are written first for the premium set (where the real login work is). Free services get a
minimal "open and remember" recipe with no credentials.

---

## Error handling

| Situation | Behavior |
|-----------|----------|
| Wrong master password | Vault fails to decrypt; abort cleanly with a clear message. No partial run. |
| CAPTCHA / device challenge | Pause in the visible window, wait for human tap, then resume. Never retry-hammer. |
| Selector no longer matches (site redesign) | Mark that one service failed, keep going with the rest, report it. Fix is a recipe edit. |
| Email code never arrives | Time out after the bounded wait; mark that service for manual login; continue. |
| Already logged in | Skip the service (no needless re-login; protects against bot flags). |
| Wrong stored credentials | Service reports login failure; flagged in the summary for Rich to update the vault. |

---

## Security model

- **Encrypted at rest:** vault file encrypted with a master-password-derived key. No plaintext on disk.
- **Master password is never stored** (entered each run, or optionally cached in the OS keyring if Rich opts in).
- **File permissions:** vault + profile dir locked to the user (`chmod 600` / `700`).
- **Repo hygiene:** `vault.enc`, `~/.hivetv/`, and any token files are `.gitignore`d. No credential ever
  enters the workspace or git.
- **Gmail access (fallback only):** read-only scope, token stored locally on the media machine,
  gitignored. Used only to read verification codes for email-only services.
- **Plaintext spreadsheet (the original idea) is explicitly rejected** in favor of this vault.

---

## Testing

- **Vault unit test:** round-trip encrypt/decrypt; wrong password fails; no plaintext written.
- **TOTP unit test:** `pyotp` generates a code matching a known secret/timestamp.
- **Recipe validation:** a `--dry-run` that loads each recipe and checks required fields + that the
  login page's expected selectors are present (catches broken recipes before a real run).
- **First real run is headed and supervised:** Rich watches, taps any CAPTCHA, confirms each service
  lands logged in. This is the acceptance test for Phase 1.
- **`hivetv status`** doubles as a regression check: run it later to confirm sessions are still warm.

---

## Deployment

- **Where:** the media machine (must be local; cookies + profile live there).
- **Prerequisites:** Python 3, Google Chrome installed, `pip install playwright pyotp cryptography`,
  `playwright install` (we still use `channel="chrome"` for Widevine).
- **Flow:** code authored in `06_DEVELOPMENT/hive_tv/` here, copied to the media machine. First-run
  setup: create the vault (enter each service's email/password, scan TOTP secrets), then `hivetv login`.
- **Author cannot see the media machine's screen.** First login is done together / supervised; the
  ongoing tool runs solo afterward.

---

## Decisions resolved

- Tiles open in a **web browser** -> Playwright drives the same browser. (Confirmed 2026-05-31.)
- **TOTP-first** 2FA where a service supports it; Gmail email-code fallback otherwise. (Confirmed 2026-05-31.)
- Credentials in an **encrypted vault**, not a plaintext spreadsheet. (Confirmed 2026-05-31.)

## Open questions for implementation

- Media machine OS (Windows / macOS / Linux)? Drives Chrome path, keyring option, run UX.
- Which premium services force an emailed code vs. allow TOTP? Determined empirically on first setup.
- Cache master password in the OS keyring (more convenient) or prompt every run (more secure)? Rich's call.
