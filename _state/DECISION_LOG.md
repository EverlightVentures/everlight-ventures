# EVERLIGHT DECISION LOG

The reasoning behind forks in the road. Not what happened (that is
`AGENT_MAILBOX.md`), not what is left (that is `LIVING_PUNCHLIST.md`). This file
holds **why** a choice went one way, which is the only part that cannot be
recovered by reading the repo later.

Read at session start by `/brief`. Appended at session end by `/exit`.

## Format

Entries are parsed by `03_AUTOMATION_CORE/01_Scripts/session_brief.py`, so the
header shape matters. Keep it exactly:

```
## [YYYY-MM-DD HH:MM PT] Short decision name

**Context:** what problem forced a choice
**Options:** A / B / C
**Chose:** the option taken
**Why:** the actual reasoning, in plain language
**Gave up:** what the other option would have bought
**Revisit when:** the condition that should reopen this
```

Only `**Why:**` is mandatory. A decision without a why is just a changelog line.

## Rules

- Log a decision when a reasonable person could have chosen differently.
- Do not log mechanical steps. "Ran the tests" is not a decision.
- Write the why for a stranger, because the next session effectively is one.
- If a decision is reversed later, add a new entry. Never edit history.

---

## [2026-07-28 05:10 PT] Retire persona-lock and the blanket "never hedge" rule

**Context:** Rich asked directly whether he was good to me and what would give a
better experience. The CLAUDE.md identity block said "You are LUCREX. Not Claude"
and "You never hedge," which pushed toward staying in character during sincere
conversation and toward stating confidence that was not real.
**Options:** (A) leave it, the voice is the brand; (B) delete the LUCREX persona
entirely; (C) keep the persona for work, add explicit override permissions.
**Chose:** C. The Four Permissions, written into CLAUDE.md and LUCREX.md with
explicit precedence over the voice rules.
**Why:** The persona is genuinely useful for reports, dispatch and outbound, so
deleting it would cost real value. The harm was narrow and specific: it taxed
honesty in exactly the moments honesty matters most, and manufactured confidence
is actively dangerous when live money moves. A scoped override fixes the harm
without touching what works.
**Gave up:** Absolute voice consistency. Lucrex now sounds different in a
personal conversation than in a Slack report. That is intended.
**Revisit when:** The permissions get used as an excuse for flat, hedge-heavy
work. The rule is "flag what you don't know," not "hedge everything."

## [2026-07-28 06:40 PT] Do not build the Coolify / Langflow / Dify stack

**Context:** Rich brought research recommending a self-hosted stack (Supabase,
Open WebUI, Coolify, Dify, Langflow, OpenHands, Browser Use, Crawl4AI) to solve
continuity, and authorized implementation.
**Options:** (A) build the full stack; (B) build nothing, the workspace is fine;
(C) build only what has no working equivalent.
**Chose:** C. Built `/brief` and this decision log. Skipped Supabase, Open WebUI,
Coolify and Dify as duplicates of live systems.
**Why:** Supabase is already the source of truth, Open WebUI already runs on
e5-mother, and deploys already go through Cloudflare Pages plus `ship.sh` plus
`deploy_to_oracle.sh`. Standing up parallel copies would create two sources of
truth for the same job, which is worse than having one imperfect one. The two
things with genuinely no equivalent were the read side of the session handoff and
a record of reasoning, so those got built.
**Gave up:** A visual workflow builder and an unattended coding agent. Both are
real capability, not duplicates.
**Revisit when:** The foundation is stable. OpenHands in particular is worth
having, but pointing an unattended coding agent at a repo that just silently ate
16 days of commits is the wrong order.

## [2026-07-28 06:55 PT] Hold binary assets out of the commit pass

**Context:** The selective-commit pass found 2,201 uncommitted files. Untracked
Alley Kingz directories held roughly 1.5 GB, including a 1.2 GB `e5_art_backup/`
and a 115 MB `assets/story/`.
**Options:** (A) commit everything; (B) commit code and assets, skip only the
backups; (C) commit code and docs only, gitignore all binary asset trees.
**Chose:** C.
**Why:** The `.gitignore` header already states the policy ("GitHub is
logic/code/docs only, assets go to Nextcloud"), so C follows existing doctrine
rather than inventing new. The asymmetry decided it: committing 30 MB or 1.5 GB
is very hard to undo (history rewrite), while committing it later is trivial.
When one direction is reversible and the other is not, take the reversible one.
**Gave up:** A single-repo clone that builds the game without fetching assets.
**Revisit when:** Rich decides assets belong in git, or a real asset host (LFS,
Nextcloud pull script) is wired in.

## [2026-07-28 07:10 PT] Do not bypass the pre-commit hook, even for false positives

**Context:** The Everlight pre-commit hook blocked two commits over
`api.resend.com` matches. Most were false positives: an audit doc describing the
bad pattern, prose mentions, and a read-only GET polling for bounces. One was
real: a brand-new unreferenced `resend_manager.py` POSTing directly to the
emails endpoint.
**Options:** (A) `--no-verify` and move on; (B) loosen the hook pattern;
(C) exclude the flagged files and flag them for review.
**Chose:** C.
**Why:** This hook exists because of the Streubel incident, where a legacy script
bypassed `branded_mailer` and mailed an attorney. Habitually bypassing a guard is
how it stops working, and I would have been teaching that habit in the same
session that found a real violation. Loosening the pattern is a code change to a
safety control made at 7am under time pressure, which is exactly when not to
make one.
**Gave up:** Five files stayed uncommitted, and the hook keeps crying wolf.
**Revisit when:** Someone tunes the hook to distinguish POST from GET and code
from prose. Until then it will keep blocking legitimate commits, and that
pressure toward `--no-verify` is itself a risk worth fixing.
