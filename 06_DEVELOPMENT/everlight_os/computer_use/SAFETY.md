# Desktop Runner Safety Doctrine
**Created:** 2026-05-06
**Owner:** Theo Briggs (legal review) + Forge Steele (engineering)
**Companion to:** `desktop_agent.py`, `desktop_runner.py`, `cli_browser_task.py`

---

## What this system does

`desktop_runner.py` polls `/AA_MY_DRIVE/_logs/browser_tasks/pending/` for browser-task envelopes, then drives Rich's REAL desktop (Wayland Plasma, Firefox session) via the Anthropic Computer Use API to accomplish whatever the natural-language goal says. It clicks, types, scrolls, screenshots — autonomously, in a live browser, with Rich's logged-in cookies.

This is a high-trust, high-blast-radius capability. The brakes below are non-negotiable.

---

## The 8 brakes

### 1. Global outbound halt is honored
`safety.honor_outbound_halt` is `true` by default. If `WHOLESALE_OUTBOUND_HALT=1` in env and the task goal contains keywords matching outbound campaigns ("send email", "send the email", "blast", "send outreach", "fire off email"), the runner refuses with `failed/{id}.json` reason `outbound_halt_active`. **Cannot be bypassed inside a task envelope** — the env flag is checked at runner level, not task level.

### 2. Single-task serial execution
`DESKTOP_RUNNER_MAX_PARALLEL=1`. Two browser sessions colliding on the same Firefox window = chaos. Runner only processes one envelope at a time; remaining tasks queue in `pending/`.

### 3. Human-override detection
`safety.abort_on_human_override` is `true` by default. Runner samples cursor position before each agent action. If the cursor moves more than 150px since the last agent action AND it's been more than 3 seconds since the agent moved, the task aborts with `failed/{id}.json` reason `human_override`. **Rich can ALWAYS abort by moving his mouse.**

### 4. Prohibited URL list
`safety.prohibited_urls` defaults to `["chrome://settings", "about:config", "*.bank.*"]`. If the task goal mentions any of these, runner refuses. Rich can extend per-task.

### 5. OAuth-screen detection
`safety.abort_on_oauth_screen` is `true` by default. **Future enhancement (currently advisory only):** the agent.py will be extended to detect Google/Apple OAuth consent screens via screenshot-similarity matching, and abort with reason `oauth_human_required`. For now, the agent is instructed in its system prompt to surface "LOGIN_REQUIRED" text if it lands on a sign-in page.

### 6. Max iterations + max seconds
Defaults: 30 iterations, 300 seconds. Either limit hits = ABORT. Caller can raise per envelope, but runner-level `DESKTOP_RUNNER_MAX_ITERATIONS_HARD_CAP` (default 100) is the absolute ceiling.

### 7. Audit envelope every action
Every click, type, key press, and scroll writes a chained envelope to `_audit/1L/desktop_agent/...` via `audit_log.write_envelope()`. Tamper-evident. F500-grade traceability for any browser action the agent takes on Rich's behalf.

### 8. Slack notification on every state change
- Runner picked up → `:robot_face:` post to `#deploy-log`
- Task completed (done) → `:white_check_mark:` post with summary
- Task failed → `:x:` post with reason

If you don't see the Slack post within ~10 seconds of dispatching, the runner isn't running. Check `~/.config/systemd/user/desktop-runner.service` status.

---

## What this system DOES NOT do

- **Does not solve OAuth.** Google/Apple consent screens detect WebDriver-style automation and refuse. If a service requires fresh OAuth consent, the task will fail and Rich must do that one click himself. Per Rich's clarification 2026-05-06, this is expected and acceptable as long as it's ~1x/day max, not per-task.
- **Does not bypass 2FA.** If a service prompts for an authenticator code, the agent will likely fail (no way to read TOTP from a phone). Rich must reduce 2FA friction (passkey, hardware key) or provide a service-specific bypass (long session cookie).
- **Does not handle CAPTCHAs.** If a service throws a CAPTCHA, the agent will fail.
- **Does not run during system sleep / lock screen.** The runner is a user-session systemd service. If Rich locks the screen, the cursor capture and screenshot still work, but Firefox interaction may not — depends on KDE Plasma's screen-locker behavior.
- **Does not parallelize.** One task at a time. By design.

---

## How to abort a running task

1. **Move your mouse** — easiest, no shell needed. The cursor delta detector will abort within 2 seconds.
2. **Kill the runner** — `systemctl --user stop desktop-runner` or `pkill -f desktop_runner.py`. The in-progress envelope stays in `in_progress/` until next runner startup, where it'll be picked up and re-processed (idempotency NOT guaranteed for in-flight UI tasks — be careful).
3. **Re-engage the global halt** — `sed -i 's/^WHOLESALE_OUTBOUND_HALT=0/WHOLESALE_OUTBOUND_HALT=1/' /AA_MY_DRIVE/.env`. Future tasks blocked.

---

## Trust boundary checklist (before running ANY browser task)

- [ ] `WHOLESALE_OUTBOUND_HALT` value matches your intent (`1` for halt, `0` for active outbound)
- [ ] You're at a desk and can watch the screen
- [ ] No sensitive personal browsing in active Firefox tabs (the agent SEES whatever's on screen)
- [ ] Slack `#deploy-log` is visible so you can see live progress
- [ ] You know the task goal you authorized (re-read the envelope's `natural_language_goal` field)

---

## Failure modes and responses

| Failure | Cause | Fix |
|---|---|---|
| `failed: human_override` | Mouse moved during execution | Resubmit task; don't touch mouse |
| `failed: outbound_halt_active` | Halt flag is on, task tried to send | Lift halt OR rewrite task to not touch outbound |
| `failed: api_error` | Anthropic API failed (rate limit, transient) | Resubmit; if persistent, check `ANTHROPIC_API_KEY` |
| `failed: max_iterations_reached` | Task too complex for default 30 steps | Raise `max_iterations` per envelope, OR break into smaller tasks |
| `failed: max_seconds_exceeded` | Task too slow (network, page load) | Raise `max_seconds` per envelope |
| `failed: prohibited_url_referenced` | Goal text mentions a blocked URL | Verify task is legitimate; remove the URL OR add to allowlist |
| `done` but result missing expected keys | Agent didn't capture the value as instructed | Refine goal text -- be more specific about HOW to format the captured value |

---

## Appendix: cost expectations

- Each iteration: ~10-15k vision tokens + ~2k input/output text tokens
- Cost per iteration: ~$0.10 (claude-sonnet-4-5 + screenshot)
- Average task: 10-25 iterations
- **Average task cost: $1.00 - $2.50**
- Daily ceiling for cost-control: set `DESKTOP_RUNNER_DAILY_COST_USD_MAX=20` env (FUTURE — not yet enforced)

---

## CRITICAL: Firefox X11 launch flag (KDE Plasma 6 Wayland)

**Discovered 2026-05-06 after 4 failed Resend tasks.**

By default, Firefox on KDE Plasma 6 Wayland runs as a Wayland-native client. xdotool cannot see or send events to Wayland-native windows — they don't appear in `xdotool search`. Every click the agent issues goes into the void.

**FIX: launch Firefox with `MOZ_ENABLE_WAYLAND=0`:**

```bash
DISPLAY=:1 MOZ_ENABLE_WAYLAND=0 firefox --new-window "https://example.com" &
```

This forces Firefox to use XWayland (X11 transport). xdotool then sees and targets it correctly. Verified: agent task completed in 6.6s after this fix vs 217-509s before.

**Symptom of the bug:** `xdotool search --name Firefox` returns nothing even when Firefox is clearly running.

**Verification before dispatching a task:**
```bash
DISPLAY=:1 xdotool search --name "Firefox" | head -1   # should return a window ID
DISPLAY=:1 xdotool windowactivate <WID>                # bring to focus
spectacle -b -n -f -o /tmp/verify.jpg                  # capture should be color, >500KB
```

The `desktop_runner.py` should be updated to verify Firefox X11-visibility BEFORE dispatching, with a clean failure message if Firefox is in Wayland-native mode.
