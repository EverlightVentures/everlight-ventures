# Operating Mode -- CLI Brain + Computer Hands + Hive Specialists
**Compiled:** 2026-05-07
**Author:** Lucrex (Marcus Cole + Forge synthesis, per Rich's directive)
**Status:** Active. Supersedes any earlier "ask user for manual step" pattern.

---

## The Doctrine (Rich's words, 2026-05-07 00:00 PT)

> "I input something, you create the plan and execute what you can on your end. Any manual steps get accomplished by the Hive and Claude Computer using the keyboard etc. When it is done, Computer can type in the chat and tell CLI what exactly got done. CLI will then say what to do next until the project is finished and Claude Computer will work until finished. Get it.
>
> Essentially whatever the CLI agent can do, the Claude Computer has authority and MUST take action to complete the work."

**Translation:** No more "I need you to click X" responses. CLI plans + Hive + Computer execute together. Manual blockers are bugs in the plan, not features.

---

## The chain

```
   Rich           Rich enters request -- one line, voice, or full plan
    |
    v
   CLI Claude     CLAUDE OPUS 4.7 (this session)
    |             - Classifies the request (wholesale, content, trading, etc.)
    |             - Builds the plan: which transport(s), which Hive agents
    |             - Executes everything CLI can do directly:
    |                * curl, gh, git, Python scripts, file edits
    |                * Anthropic API queries, Stripe API, Resend API, Slack API
    |                * Read .env, write .env, run bash, dispatch envelopes
    |             - Routes manual / GUI work to Computer:
    |
    +--> desktop_runner (transport: computer_use)
    |    Native apps, OS dialogs, File Manager, KDE settings,
    |    keyboard shortcuts that need to land in a focused window.
    |    Default model: claude-sonnet-4-5
    |
    +--> browser_use_runner (transport: browser_use, target_url: ...)
    |    Brave attached via CDP (port 9222). DOM-driven clicks, OAuth, SaaS dashboards.
    |    Default model: claude-sonnet-4-5
    |    Persistent context = Rich's existing logins (Proton Pass, Google, etc.)
    |
    +--> managed_agent_runner (transport: managed_agent)
    |    Anthropic Cloud sandbox. bash + file ops + web search + MCP. No desktop access.
    |    Best for: research, code generation, file analysis, long-running async work.
    |    Default model: claude-sonnet-4-5
    |
    +--> Hive Task tool (subagent_type: 03_engineering_foreman, 27_profit_maximizer, etc.)
         70+ named Everlight agents -- legal team, state agents, trading, growth.
         Each carries firmware (voice, relationships, conversation hooks).
         Used for cross-domain decisions per the 9-phase dispatch doctrine.

    All four loops above:
    - Share the same envelope queue (_logs/browser_tasks/pending/)
    - Write to the same audit chain (_audit/1L/<agent_id>/.../...json)
    - Post to the same Slack #deploy-log channel via branded_slack
    - Honor collab_lock (yields when CLI grabs the floor for AskUserQuestion)
    - Honor WHOLESALE_OUTBOUND_HALT for any task that touches outbound channels

    v
   Computer + Hive report back via:
   - Result envelope written to done/ or failed/
   - Branded Slack post with status, model used, elapsed seconds
   - Audit envelope with action trail
   - For voice-to-CLI: Computer types DIRECTLY into the CLI's terminal via xdotool
     after the task completes -- no human relay needed
    |
    v
   CLI Claude     - Reads the result envelope
                  - Verifies the success criteria (curl test, halt_check, etc.)
                  - If task is part of a larger plan: dispatches the next step
                  - If complete: reports to Rich, requests next request
```

---

## What CLI must do (no more delegating to Rich)

| Action | Tool | Notes |
|---|---|---|
| Click a button | dispatch browser_use envelope | DOM-driven, attached to Brave |
| Fill a form on a SaaS dashboard | dispatch browser_use envelope | Persistent Brave context = pre-authenticated |
| Read an API key from a modal | browser_use_runner extracts via DOM | NEVER OCR a screenshot |
| Verify the captured value | curl test against the live API | Mandatory before claiming success |
| Configure KDE / system settings | bash + kwriteconfig6 | Keyboard-only, no GUI navigation |
| Reload a daemon | systemctl --user restart <service> | Already aliased: `runner-restart`, `browser-restart`, `agent-managed-restart` |
| Modify code | Edit / Write directly | This session has the tools |
| Send Slack | content_tools.branded_slack.post_branded_slack() | Never raw chat.postMessage for content |
| Send email | content_tools.branded_mailer.send_branded_email() | Honors WHOLESALE_OUTBOUND_HALT, gates through resend_guard + resend_budget |
| Publish report | content_tools.n8n_replacements.publish_gdoc() | 3-format: HTML + Google Doc + Slack card |
| Get to a URL fast | dispatch browser_dispatch.py with --url | One-shot envelope dispatch |
| Voice command | Meta+Space hotkey -> voice_runner.py -> xdotool type into focus | Whisper.cpp local, $0 |
| Long async research | dispatch managed_agent envelope | Cloud sandbox, no desktop required |
| Cross-domain decision | Task tool with 3+ named Everlight agents in parallel | 9-phase dispatch per ORCHESTRATION_DOCTRINE.md |

---

## Anti-patterns (DO NOT DO)

1. **"You'll need to click X"** -- if there's a click, dispatch an envelope.
2. **"Paste this back here"** -- if there's a value to capture, the runner extracts it via DOM and curl-verifies it before reporting.
3. **"Run this command in your terminal"** -- if the command is in the bash allowlist, run it directly via Bash tool. If not, expand the allowlist or use sudo via pwsudo.
4. **OCR'ing API keys / OTP codes from screenshots** -- always extract via DOM (input[readonly][value^="..."], code element innerText) or, for Computer Use, use the zoom action + bash xsel to read clipboard after the agent clicks Copy.
5. **Leaving modals open after capturing the value** -- always close the modal so the value is no longer visible. Per `feedback_screenshot_security.md`.
6. **Storing screenshots after task completion** -- the runners now auto-delete screenshot dirs. Override only via `safety.keep_screenshots=true` for explicit debug.
7. **Asking Rich for confirmation on routine clicks** -- if it's not financially binding, irreversible, or sensitive (login, OAuth, payment), just do it.

---

## When manual IS the right call

There are still cases where Rich must touch his hardware:

- **First-time logins / cold-start auth** to a service Brave's persistent context doesn't already have (e.g., a brand new SaaS account).
- **Hardware permission prompts** that systemd-inhibit / pwsudo can't bypass (e.g., USB device permissions).
- **2FA codes** from SMS, Authenticator app, hardware key.
- **Financially binding signatures** ($X commitment, contract assignment, wire transfer).
- **Anything involving the wholesale halt-lift's named-human signoffs** (Justine, Marcus, Rich).

For these, CLI must:
1. Build the prep work first so Rich's manual touch is the LAST step.
2. Stage everything around the click (Brave at the right URL, terminal at the right command, .env ready to receive the value).
3. Pre-write a one-line prompt for Rich that names exactly what to do.
4. After Rich does the click, the next CLI cycle continues autonomously.

---

## Self-test checklist (run when in doubt)

Before claiming "the user has to..." -- confirm each:

- [ ] Did I check if the action has a programmatic API? (Anthropic, Stripe, Resend, Cloudflare, GitHub all have one for most operations.)
- [ ] Did I check if browser_use_runner can DOM-click it? (Default for SaaS dashboards.)
- [ ] Did I check if managed_agent_runner can do it in a cloud sandbox? (Default for research, code, file analysis.)
- [ ] Did I check if Computer Use can do it via keyboard nav (Tab + Enter)? (Default for native apps.)
- [ ] Did I check if a bash command via the allowlist can do it? (xdotool, kwriteconfig6, systemctl, gh.)

If all five fail and Rich's hardware is genuinely required, then -- and only then -- ask. Otherwise, dispatch.

---

## Cross-references

- `RUNBOOK.md` -- Two-runner architecture (now three-runner + voice).
- `SAFETY.md` -- Computer Use safety rails + Firefox X11 doctrine.
- `feedback_screenshot_security.md` -- Pixel exfiltration risk.
- `feedback_autonomous.md` -- pwsudo armed, only OAuth needs Rich.
- `ORCHESTRATION_DOCTRINE.md` -- 9-phase Hive dispatch + 10 habits.
- `CLAUDE.md` -- Workspace doctrine (file rules, comms, mode routing).
