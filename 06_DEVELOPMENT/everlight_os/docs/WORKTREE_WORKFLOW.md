# Git Worktree Workflow -- Multi-Claude Parallel Sessions

## What this is

`git worktree` lets you have multiple separate working copies of the same git repo,
each on a different branch, all sharing one `.git` folder. Two Claude Code sessions
can run in parallel on different worktrees without stepping on each other's changes.

**The mental model:**
- Main repo: `/mnt/sdcard/AA_MY_DRIVE` (your original) -- branch `everlightventures.io`
- Worktree A: `/mnt/sdcard/AA_MY_DRIVE_worktrees/wholesale` -- branch `worktree/wholesale-build`
- Worktree B: `/mnt/sdcard/AA_MY_DRIVE_worktrees/buyers` -- branch `worktree/buyer-list`

Each is a real on-disk copy. Each runs its own Claude session. Edits in one DON'T
appear in another until you merge branches.

---

## Already-created worktrees

Run this any time to see what's live:

```bash
git -C /mnt/sdcard/AA_MY_DRIVE worktree list
```

**Active right now:**
- `/mnt/sdcard/AA_MY_DRIVE` (everlightventures.io) -- your primary
- `/mnt/sdcard/AA_MY_DRIVE_worktrees/wholesale` (worktree/wholesale-build) -- safe to play in
- `/mnt/sdcard/AA_MY_DRIVE_worktrees/buyers` (worktree/buyer-list) -- safe to play in

---

## How to start a parallel Claude session

Open a NEW Termux session. Then:

```bash
cd /mnt/sdcard/AA_MY_DRIVE_worktrees/wholesale
claude
```

That Claude session sees ONLY the wholesale worktree. You can have your primary
Claude on AA_MY_DRIVE working on Marcus briefs, and a second Claude on the wholesale
worktree adding new lead scrapers. They don't conflict.

---

## Adding a NEW worktree

```bash
cd /mnt/sdcard/AA_MY_DRIVE
git worktree add -b worktree/<name> /mnt/sdcard/AA_MY_DRIVE_worktrees/<name> main
```

Replace `<name>` with anything (one word, hyphens OK):
- `airbnb-research`
- `closing-coordination`
- `tax-strategy`
- `dispo-marketplace-v2`

Examples ready-to-paste:

```bash
# Spin up a worktree for Airbnb side hustle planning
cd /mnt/sdcard/AA_MY_DRIVE
git worktree add -b worktree/airbnb /mnt/sdcard/AA_MY_DRIVE_worktrees/airbnb main

# Spin up a worktree for the LLC + tax setup work
cd /mnt/sdcard/AA_MY_DRIVE
git worktree add -b worktree/tax-llc /mnt/sdcard/AA_MY_DRIVE_worktrees/tax-llc main
```

---

## Merging worktree changes back

When you're done with work in a worktree and want it in main:

```bash
# In your primary AA_MY_DRIVE session
cd /mnt/sdcard/AA_MY_DRIVE
git fetch
git merge worktree/wholesale-build  # or whichever branch
git push
```

The merged code is now live in your primary working tree.

---

## Tearing down a worktree (when done with it)

```bash
cd /mnt/sdcard/AA_MY_DRIVE
git worktree remove /mnt/sdcard/AA_MY_DRIVE_worktrees/wholesale
git branch -D worktree/wholesale-build  # optional: delete the branch too
```

---

## Recommended ADHD-friendly setup

Three Termux sessions running at once (Termux supports tabs/sessions):

| Session | Path | Claude focus |
|---|---|---|
| #1 (primary) | /mnt/sdcard/AA_MY_DRIVE | Strategy + Marcus briefs + wholesale ops |
| #2 (build) | /mnt/sdcard/AA_MY_DRIVE_worktrees/wholesale | Building new modules / features |
| #3 (research) | /mnt/sdcard/AA_MY_DRIVE_worktrees/buyers | Buyer scraping experiments / no-risk tests |

Each session has its OWN Claude. Each Claude can work without blocking the others.
You jump between them based on what your brain wants to focus on.

---

## Things to know

- The `.git/` folder is shared across all worktrees. Don't delete the main repo's
  `.git/` folder or all worktrees break.
- Two worktrees CAN'T have the same branch checked out simultaneously. Each gets
  its own branch.
- Disk: each worktree is ~250MB-2GB depending on what's checked in. Currently
  you have 208GB free, so plenty of room for 50+ worktrees.
- Memory: this matters more than disk -- each Claude session uses RAM for context.
  Probably max 2-3 simultaneous on a phone before slowdown.
