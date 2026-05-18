# REMOTE WORKFLOW -- AceMagician + Phone via Tailscale + GitHub

**Status:** GitHub mirror live, auto-push every 5 min, Tailscale SSH ready.
**Created:** 2026-05-07

---

## 1. The remote stack (what's wired right now)

| Layer | Where | How to use |
|---|---|---|
| Tailscale tailnet | `100.93.253.49` (acemagician) <-> `100.112.180.29` (phone Z Fold 7) | `tailscale status` to see peers |
| GitHub mirror (private) | <https://github.com/EverlightVentures/aa-my-drive> | `git pull / push` from any peer |
| Auto-push timer | AceMagician systemd | Every 5 min, fires if HEAD ahead of origin |
| hive-sync-watch | AceMagician systemd | Auto-fires when phone mounts |
| Browser task queue | `_logs/browser_tasks/pending/` | Drop an envelope from anywhere -> browser_use_runner picks it up |
| Email triage | `lucrex-email-triage.service` | Polls Gmail every 5 min |

---

## 2. From the phone -- the 3 ways to keep working

### (A) SSH into AceMagician via Tailscale (fastest, full power)

```bash
# from Termux on phone (after `tailscale up` once)
ssh richgee@100.93.253.49

# or with the canonical key path
ssh -i ~/.ssh/phone_to_arch richgee@100.93.253.49

# common phone-side commands once SSHed in:
cd /AA_MY_DRIVE
tail -f _logs/swarm_real_runner.log
tail -f _logs/wholesale_runs/daily_seller_list.log
systemctl --user list-timers
git status
git pull origin main          # bring phone-side clone forward
```

### (B) Edit on phone, push, AceMagician auto-pulls (clone-and-edit flow)

```bash
# one-time: clone on phone
cd ~ && git clone https://github.com/EverlightVentures/aa-my-drive.git
cd aa-my-drive

# any time you commit on phone:
git add -A && git commit -m "phone edit" && git push origin main

# AceMagician auto-pull side: NOT YET WIRED -- by default the auto-push timer
# only PUSHES; it doesn't auto-pull. To pull on AceMagician:
ssh richgee@100.93.253.49 'cd /AA_MY_DRIVE && git pull origin main'
# OR add an auto-pull timer (TODO if you want bidirectional auto-sync)
```

### (C) Drop a task envelope from phone (no edit, just dispatch)

```bash
# from phone over SSH:
ssh richgee@100.93.253.49 << 'EOF'
cat > /AA_MY_DRIVE/_logs/browser_tasks/pending/btsk_$(openssl rand -hex 8).json << JSON
{
  "task_id": "btsk_phone_001",
  "transport": "browser_use",
  "target_url": "https://example.com",
  "natural_language_goal": "summarize the page in 3 bullets"
}
JSON
EOF
# browser_use_runner picks it up within 10 seconds.
```

---

## 3. What's NOT yet wired (honest)

- **Tailscale Drive (taildrive)**: needs `drive:share` ACL attribute added at
  `login.tailscale.com/admin/acls`. Workspace admin action -- can't be done via
  CLI. Until then, use SSH+git+rsync (which already works).
- **Auto-pull on AceMagician**: timer only auto-pushes. To make
  changes from phone propagate back, add a pull-timer (TODO) OR `ssh` in and
  `git pull` manually.
- **Channels:join scope on Slack bots**: needs OAuth update at
  `api.slack.com/apps` (admin-side).

---

## 4. The kill-switches (in case something runs away)

```bash
# stop the swarm
systemctl --user stop everlight-swarm-logistics.timer

# stop the wholesale daily run
systemctl --user stop lucrex-daily-seller-list.timer

# stop email triage (drafts only -- safe but stop polling)
systemctl --user stop lucrex-email-triage.service

# stop auto-push (if you don't want commits leaving)
systemctl --user stop lucrex-auto-push.timer

# stop the bash auto-approver (re-prompts you for every command)
# Edit .claude/settings.json and remove the Bash hook block, then restart claude
```

---

## 5. From phone, see daily progress (one-liners)

```bash
ssh richgee@100.93.253.49 'jarvis-status'                           # full system snapshot
ssh richgee@100.93.253.49 'tail -30 /AA_MY_DRIVE/_logs/wholesale_runs/daily_seller_list.log'
ssh richgee@100.93.253.49 'cat /AA_MY_DRIVE/01_BUSINESSES/Everlight_Ventures/Wholesale/buyers/cumulative_seller_list.json | jq .total_qualified'
ssh richgee@100.93.253.49 'cat /tmp/lucrex_status.json'             # current PC busy state
ssh richgee@100.93.253.49 'systemctl --user list-timers --no-pager' # all scheduled work
```

---

**Lucrex directive applies. Solutions-first doctrine applies. The phone is the remote control; AceMagician is the engine.**
