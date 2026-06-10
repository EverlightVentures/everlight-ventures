# Computer Use Runbook
**Last reviewed:** 2026-05-06
**Owner:** Lucrex / Forge (Codex Labs)
**Scope:** desktop_runner + desktop_agent + screen_inhibitor + session_keeper + voice_runner

A single-source-of-truth doc per the documentation doctrine: centralized, dated, simple language, examples first. If you only read one file in this directory, read this one.

---

## What this framework is

A bridge between the Claude CLI (planning brain) and Rich's actual KDE Plasma desktop (mouse + keyboard + screen). The CLI writes a "task envelope" (JSON) to a queue. A long-running runner picks it up and drives Anthropic's Computer Use API to complete the task on the real desktop. Results get written back to a "done" envelope, posted to Slack, and hash-chained into the audit log.

Use it when: a task lives in a browser/GUI that has no API (creating SaaS keys, OAuth flows, dashboard navigation). Don't use it when: the task has an API (always prefer `curl` / SDK calls).

---

## Architecture (1-page ASCII)

```
                         CLI (this Claude session)
                                  |
                                  | writes JSON envelope to:
                                  v
              _logs/browser_tasks/pending/btsk_<id>.json
                                  |
                                  | desktop_runner.py polls every 2s
                                  v
                         desktop_runner.py
                              |        \
                              |         \--> moves envelope to in_progress/
                              v
                         desktop_agent.py
                              |
                              | builds system prompt + initial screenshot
                              v
                  Anthropic Computer Use API
                  (claude-sonnet-4-5, vision)
                              |
                              | returns: action (click/type/key/screenshot)
                              v
                         desktop_agent.py
                              |
                              | xdotool / spectacle / KWin ScreenShot2
                              v
                       KDE Plasma desktop
                       (Firefox in X11 mode)
                              |
                              | screenshot loop until done/max_iter/max_secs
                              v
                         desktop_agent.py
                              |
                              | writes result envelope to:
                              v
              _logs/browser_tasks/done/btsk_<id>.json
              _logs/browser_tasks/failed/btsk_<id>.json
                              |
                              | post to Slack + 1L audit envelope + hash chain
                              v
                CLI session reads result, continues plan
```

---

## How to start a workshift (one-time per day)

```bash
# Start the screen-stays-on inhibitor + KDE permission warm-up
nohup /AA_MY_DRIVE/.venv/bin/python3 \
    /AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/computer_use/session_keeper.py \
    --hours 8 > /tmp/session_keeper.log 2>&1 &

# Start the runner daemon (picks up tasks from pending/)
nohup /AA_MY_DRIVE/.venv/bin/python3 \
    /AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/computer_use/desktop_runner.py \
    > /tmp/desktop_runner.log 2>&1 &
```

If KDE prompts for "remote control privileges" the first time, click **Allow**. Stays warm until logout.

To end the workshift:
```bash
pkill -f session_keeper.py
pkill -f desktop_runner.py
```

---

## How to dispatch a task from the CLI

```python
import sys
sys.path.insert(0, "/AA_MY_DRIVE/06_DEVELOPMENT/everlight_os")
from computer_use import cli_browser_task

task_id = cli_browser_task.write_envelope(
    title="Create Resend API key",
    natural_language_goal="Click 'Create API Key', name it 'lucrex-domain-admin', "
                         "set permission to 'Full access', click Add, then capture "
                         "the re_... key shown in the modal.",
    expected_result_schema={"api_key": "string"},
    max_iterations=20,
    max_seconds=300,
    context={
        "project": "Resend domain setup",
        "success_criteria": [
            "result.api_key starts with 're_'",
            "result.api_key length > 30 characters",
        ],
        "do_not": [
            "Do not navigate away from resend.com/api-keys",
            "Do not create more than one key",
        ],
    },
)
print(f"dispatched: {task_id}")
```

Then poll for completion:
```bash
until [ -f /AA_MY_DRIVE/_logs/browser_tasks/done/${task_id}.json ] || \
      [ -f /AA_MY_DRIVE/_logs/browser_tasks/failed/${task_id}.json ]; do
    sleep 5
done
```

---

## Knowledge base — common gotchas + resolutions

### Gotcha 1: Firefox running Wayland-native (xdotool can't reach it)
**Symptom:** Agent issues `left_click` actions but nothing happens. Screenshots show the same screen iter after iter. `xdotool search --name "Firefox"` returns nothing.

**Diagnosis:** On KDE Plasma 6 Wayland, Firefox launches in Wayland transport by default. xdotool only sees X11/XWayland windows.

**Fix:** Always launch Firefox with `MOZ_ENABLE_WAYLAND=0`:
```bash
pkill -9 -f firefox
sleep 3
DISPLAY=:1 MOZ_ENABLE_WAYLAND=0 firefox --new-tab "<URL>" &
sleep 8  # give it time to load
DISPLAY=:1 xdotool search --name "Firefox" | head -1  # should return a WID
```

**Verify:** `xdotool getactivewindow getwindowname` should return the window title (not empty).

### Gotcha 2: Screen blanks → screenshots come back black/bilevel
**Symptom:** Screenshots are 32KB grayscale instead of 200-300KB color. Agent can't see anything useful.

**Diagnosis:** KDE's idle-screen power management kicked in mid-task.

**Fix:** Already wired — `screen_inhibitor` is acquired by `desktop_agent.run_task()` before the first screenshot. If you see this regression, check that `enable_keepalive=False` (it's the default; True triggers a "remote control" prompt every 60s on Wayland).

### Gotcha 3: KDE keeps prompting for "remote control privileges"
**Symptom:** Every task dispatch triggers a permission dialog you have to click.

**Diagnosis:** The mouse-wiggle keepalive in `screen_inhibitor` was triggering the prompt on every wiggle.

**Fix:** Already shipped (commit `ed73fc0a`). `enable_keepalive=False` is the default. Workshift-long permission persists once you `session_keeper.py --hours 8`.

### Gotcha 4: Agent task killed when Rich uses his terminal
**Symptom:** Task aborts with `human_override` after Rich moves the mouse to type.

**Diagnosis:** Old behavior was "abort on cursor move >150px after agent action". Hostile to multi-tasking.

**Fix:** Already shipped (commit `2605e98e`). New behavior: pause for 5s of user idle, then resume from a fresh screenshot. Never aborts.

### Gotcha 5: OAuth flows defeat the agent
**Symptom:** Resend "Sign in with Google" → account chooser → consent screen. Agent hits max_seconds.

**Diagnosis:** Multi-step page transitions with modal dialogs are the hardest case for screenshot-based agents. Buttons re-render at different coordinates, focus changes, dropdown menus appear.

**Mitigations (in order of effectiveness):**
1. **Pre-load credentials into clipboard** before dispatch. Agent's prompt says "the username is in the clipboard, just press Ctrl+L to focus URL bar then Tab into the email field then Ctrl+V".
2. **Use Proton Pass extension shortcut** — Ctrl+Shift+L by default. Agent triggers the shortcut, Proton Pass autofills.
3. **Pre-launch Firefox to the deepest URL possible** so the agent only handles the last hop.
4. **Manually log in once per workshift** — 30 seconds of Rich's time, $0 in vision tokens. Often the smartest call.

### Gotcha 6: API credit balance too low → all tasks fail with same error
**Symptom:** `desktop_agent.run_task()` returns immediately with status=failed, error mentions "credit balance".

**Fix:** Top up at https://console.anthropic.com/settings/billing. See **Cost expectations** below for sizing.

### Gotcha 7: Anthropic API key conflict with Claude CLI
**Symptom:** Claude CLI shows: *"Auth conflict: Both a token (claude.ai) and an API key (ANTHROPIC_API_KEY) are set."*

**Fix:** Already shipped. `.env` now uses `LUCREX_ANTHROPIC_KEY` (which `desktop_agent.py` reads first); the legacy `ANTHROPIC_API_KEY` can stay unset for the CLI's claude.ai auth.

---

## Cost expectations

Sonnet 4.5 vision pricing (as of 2026): **$3/MTok input**, **$15/MTok output**. Each 1024x1024 screenshot = ~1290 vision tokens. The framework currently re-sends prior screenshots each iter (no prompt caching yet — TODO), so cost grows roughly quadratically with iteration count.

| Task class                          | Typical iter | Typical cost |
|-------------------------------------|--------------|--------------|
| Smoke test ("describe the screen")  | 1            | ~$0.01       |
| Single-form fill (no nav)           | 3-5          | ~$0.03       |
| OAuth login + form                  | 8-15         | ~$0.10-0.30  |
| Failed task hitting max_seconds     | 11-18        | ~$0.30-0.70  |

**Rule of thumb:** Each `max_seconds=300` task burns $0.20-0.50 if it runs to the limit. A 1-hour workshift with 5-10 tasks ≈ $2-5. **$20 of API credit lasts ~1-2 weeks of normal use.**

---

## Voice integration (Meta+Space → terminal)

Press a global hotkey, speak, transcript lands in your clipboard / focused terminal / pipe. See `../voice/VOICE_USAGE.md` for the KDE shortcut binding. Pipeline: **pw-record** → **whisper.cpp small.en** (~488MB local model) → **wl-copy** or **xdotool type**.

```bash
# Smoke test (no audio expected; verifies pipeline)
/AA_MY_DRIVE/.venv/bin/python3 \
    /AA_MY_DRIVE/06_DEVELOPMENT/everlight_os/voice/voice_runner.py \
    --capture --duration 5 --clip
```

---

## Logging & audit (per logging doctrine)

Per the logging best-practices doctrine (structured JSON, log levels, correlation IDs, canonical log lines, centralized, secured):

- **Structured:** every task envelope is JSON with explicit fields (task_id, correlation_id, status, result, started_at, completed_at, screenshots_dir).
- **Correlation:** `correlation_id` propagates from CLI dispatch → desktop_agent → audit envelope → Slack post.
- **Levels:** `desktop_agent` uses Python `logging` at INFO for state changes, WARN for retries, ERROR for failures. Adjust via `LOGLEVEL` env.
- **Canonical line:** the result envelope IS the canonical line — one record per task with iters, elapsed_seconds, status, abort_reason, final_text.
- **Centralized:** all envelopes flow into `_logs/browser_tasks/{pending,in_progress,done,failed}/` with a 1L audit envelope per state transition, hash-chained into 2L→3L per the Hive audit doctrine.
- **Security:** screenshots and envelopes are gitignored. Verified 2026-05-06: no API keys, no passwords leak into envelopes (only descriptive strings like "fill the password field" appear). Screenshots are stored locally only — never pushed to GitHub.
- **Sampling:** N/A (low volume; we keep every task).

---

## Known limitations / future work

| Gap                                         | Workaround today              | Future fix                         |
|---------------------------------------------|-------------------------------|------------------------------------|
| Multi-step OAuth flows hit max_seconds      | Manual login once per shift   | Playwright transport (no vision)   |
| No prompt caching → quadratic token growth  | Cap max_iterations at 20      | Add cache_control breakpoints      |
| CLI ↔ desktop terminal bridge (1/2 prompts) | Rich answers prompts manually | tmux pty tap + answer queue        |
| No parallel task execution                  | Tasks run serially            | Multiple Firefox profiles + queues |
| Wayland window-name unverifiable            | Check WID via xdotool search  | KWin D-Bus windowList (Plasma 7?)  |

---

## File map

| File                  | Purpose                                                            |
|-----------------------|--------------------------------------------------------------------|
| `desktop_runner.py`   | Long-running daemon, polls pending/, dispatches to desktop_agent   |
| `desktop_agent.py`    | Anthropic Computer Use loop, screenshot+action ladder              |
| `screen_inhibitor.py` | KDE D-Bus + systemd-inhibit, prevents idle blanking                |
| `session_keeper.py`   | One-time-per-workshift permission warm-up + 8-hour inhibit         |
| `cli_browser_task.py` | Helper for CLI to write envelopes (in `everlight_os/cli/`)         |
| `SAFETY.md`           | Safety rails + Firefox X11 doctrine                                |
| `RUNBOOK.md`          | This file                                                          |
| `agent.py`            | Older containerized variant, deprecated for the desktop case       |
| `server.py`           | Flask shim, used in container mode                                 |

---

## Two-runner architecture (v5, 2026-05-06)

Two systemd-managed daemons share one queue. Routing predicate decides who claims:

| Envelope hint                                     | Goes to                  | Why                                             |
|---------------------------------------------------|--------------------------|-------------------------------------------------|
| `transport: "browser_use"`                        | browser_use_runner       | Explicit                                         |
| `transport: "computer_use"`                       | desktop_runner           | Explicit                                         |
| `target_url: "https://..."` and no `transport`    | browser_use_runner       | URL-driven default (DOM-driven is cheaper)      |
| Neither (or any other shape)                      | desktop_runner           | Default to Computer Use                         |

### desktop_runner (Computer Use, screenshot+click)
For native apps, OS dialogs, file managers, Photoshop, anything non-browser. Default model **claude-sonnet-4-5** (cap 1568x882). Per-envelope `model_override`:
- `claude-opus-4-7` -- hard visual tasks, dropdown precision via `zoom`, OCR on long alphanumeric. ~5x cost.
- `claude-haiku-4-5-20251001` -- trivial state checks. ~5x cheaper than Sonnet.

### browser_use_runner (DOM-driven, Playwright)
For URL-driven workflows: Resend, Cloudflare, Anthropic console, Stripe, GitHub UI, anything in a browser. Default model **claude-sonnet-4-5**. 10-30x cheaper than Computer Use because:
- No screenshot tokens for navigation (DOM text only).
- Deterministic clicks (DOM IDs, not coordinate guesses).
- OAuth flows work because login forms have stable DOM IDs.

Persistent Chromium context: `/AA_MY_DRIVE/_state/browser_use_chromium/`. First-time login per site is manual (headed Chromium); subsequent tasks reuse cookies. To do an interactive login session: run `browser_use_runner.py --once` then while Chromium is open, log in to the target site, close the page; cookies persist.

### Dispatch from CLI (keyboard-driven)
```bash
# Drop a browser task on the currently active Firefox tab:
browser-dispatch --goal "Summarize the page in 3 bullets"

# Or explicit URL:
browser-dispatch --url "https://example.com" --goal "Get the H1 heading" \
                 --model claude-sonnet-4-5 --persona "Forge"

# Bind to Meta+Shift+B in KDE System Settings -> Shortcuts -> Custom for one-press dispatch.
# (Meta+B is taken by PowerProfile.)
```

### Service control
```bash
# Computer Use runner
runner-status / runner-restart / runner-log / runner-state

# Browser Use runner
browser-status / browser-restart / browser-log / browser-state / browser-dispatch
```

Both auto-restart on crash via systemd. Watchdog cron (`desktop_runner_watchdog.sh`) catches "alive but stuck" cases for desktop_runner; browser_use_runner inherits the same pattern (add a parallel watchdog if needed).

### Cost expectations (post-v5)

| Task class                           | Transport     | Model       | Cost     |
|--------------------------------------|---------------|-------------|----------|
| Smoke test ("describe screen")       | computer_use  | sonnet-4-5  | $0.01    |
| Single-form fill via DOM             | browser_use   | sonnet-4-5  | $0.05    |
| OAuth + form fill (DOM-driven)       | browser_use   | sonnet-4-5  | $0.10-0.30 |
| Failed task (max_iter hit)           | browser_use   | sonnet-4-5  | $0.30    |
| Native app / file dialog             | computer_use  | sonnet-4-5  | $0.30-0.50 |
| Hard visual reasoning (long key OCR) | computer_use  | opus-4-7    | $1-3     |
| Trivial state check                  | browser_use   | haiku-4-5   | $0.02    |

$20 of credits should last 1-2 weeks of normal use.

---

## When to NOT use this framework

- **The system has an API.** `curl` / SDK calls are 100x cheaper, 100x faster, 100% reliable. The desktop_runner exists for the SaaS dashboards that have no public API.
- **The task is one-off and < 2 minutes manual.** A 2-minute click-through costs $0 and is more reliable than the agent. Reserve the framework for repeated tasks or for tasks Rich can't watch.
- **The task involves CAPTCHAs, 2FA codes, or biometric prompts.** Hard-no by design — agent is told to return `BLOCKED_2FA` and yield to Rich.
- **Production systems with destructive permissions.** Keep the agent in read/create-only modes by default. Delete/drop/destroy actions require explicit `safety.allow_destructive=true` in the envelope.
